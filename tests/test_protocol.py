import unittest

from tetris_shared.models import MessageType
from tetris_shared.protocol import Framer, encode, parse


EXEMPLOS = (
    (MessageType.HELLO, ("Jogador_A",), b"TVP/1|HELLO|Jogador_A\n"),
    (MessageType.MATCH, ("Jogador_B",), b"TVP/1|MATCH|Jogador_B\n"),
    (MessageType.READY, ("PLAYER",), b"TVP/1|READY|PLAYER\n"),
    (MessageType.READY, ("GO",), b"TVP/1|READY|GO\n"),
    (MessageType.BOARD, ("0123456780" * 20,), b"TVP/1|BOARD|" + b"0123456780" * 20 + b"\n"),
    (MessageType.ATTACK, ("1",), b"TVP/1|ATTACK|1\n"),
    (MessageType.ATTACK, ("2",), b"TVP/1|ATTACK|2\n"),
    (MessageType.ATTACK, ("4",), b"TVP/1|ATTACK|4\n"),
    (MessageType.KO, ("SPAWN",), b"TVP/1|KO|SPAWN\n"),
    (MessageType.KO, ("OVERFLOW",), b"TVP/1|KO|OVERFLOW\n"),
    (MessageType.GAMEOVER, ("WIN", "KO"), b"TVP/1|GAMEOVER|WIN|KO\n"),
    (MessageType.GAMEOVER, ("LOSE", "DISCONNECT"), b"TVP/1|GAMEOVER|LOSE|DISCONNECT\n"),
    (MessageType.GAMEOVER, ("CANCEL", "TIMEOUT"), b"TVP/1|GAMEOVER|CANCEL|TIMEOUT\n"),
    (MessageType.GAMEOVER, ("WIN", "PROTOCOL"), b"TVP/1|GAMEOVER|WIN|PROTOCOL\n"),
    (MessageType.GAMEOVER, ("CANCEL", "SERVER_STOP"), b"TVP/1|GAMEOVER|CANCEL|SERVER_STOP\n"),
    (MessageType.KEEPALIVE, (), b"TVP/1|KEEPALIVE\n"),
)


class TestesCodec(unittest.TestCase):
    def test_codifica_exemplos_literais(self):
        for tipo, campos, linha in EXEMPLOS:
            with self.subTest(tipo=tipo, campos=campos):
                self.assertEqual(encode(tipo, campos), linha)

    def test_interpreta_exemplos_literais(self):
        for tipo, campos, linha in EXEMPLOS:
            with self.subTest(linha=linha):
                self.assertEqual(parse(linha), (tipo, campos))

    def test_apelidos_nos_limites(self):
        for tipo in (MessageType.HELLO, MessageType.MATCH):
            for apelido in ("A", "_", "0123456789abcdefghij"):
                with self.subTest(tipo=tipo, apelido=apelido):
                    self.assertEqual(parse(encode(tipo, (apelido,))), (tipo, (apelido,)))

    def test_rejeita_campos_invalidos_no_encoder_e_parser(self):
        casos = (
            (MessageType.HELLO, ("",)),
            (MessageType.HELLO, ("a" * 21,)),
            (MessageType.HELLO, ("João",)),
            (MessageType.MATCH, ("nome sobrenome",)),
            (MessageType.MATCH, ("A-B",)),
            (MessageType.MATCH, ("A\r",)),
            (MessageType.MATCH, ("A\n",)),
            (MessageType.MATCH, ("A|B",)),
            (MessageType.MATCH, ("A\x00",)),
            (MessageType.READY, ("player",)),
            (MessageType.READY, ("GO ",)),
            (MessageType.ATTACK, ("0",)),
            (MessageType.ATTACK, ("3",)),
            (MessageType.ATTACK, ("-1",)),
            (MessageType.ATTACK, ("01",)),
            (MessageType.ATTACK, ("１",)),
            (MessageType.KO, ("KO",)),
            (MessageType.BOARD, ("0" * 199,)),
            (MessageType.BOARD, ("0" * 201,)),
            (MessageType.BOARD, ("9" + "0" * 199,)),
            (MessageType.BOARD, ("٠" * 200,)),
            (MessageType.GAMEOVER, ("DRAW", "KO")),
            (MessageType.GAMEOVER, ("WIN", "SPAWN")),
        )
        for tipo, campos in casos:
            with self.subTest(tipo=tipo, campos=campos):
                with self.assertRaises(ValueError):
                    encode(tipo, campos)
                linha = ("TVP/1|" + tipo.value + "|" + "|".join(campos) + "\n").encode("utf-8")
                with self.assertRaises(ValueError):
                    parse(linha)

    def test_rejeita_campos_extras_e_ausentes(self):
        for tipo, campos, _ in EXEMPLOS:
            variantes = [campos + ("",), campos + ("EXTRA",)]
            if campos:
                variantes.append(campos[:-1])
            for variante in variantes:
                with self.subTest(tipo=tipo, campos=variante):
                    with self.assertRaises(ValueError):
                        encode(tipo, variante)
                    linha = "|".join(("TVP/1", tipo.value, *variante)) + "\n"
                    with self.assertRaises(ValueError):
                        parse(linha.encode("ascii"))

    def test_rejeita_linhas_malformadas(self):
        for linha in (
            b"", b"\n", b"TVP/1|KEEPALIVE", b"TVP/1|KEEPALIVE\r\n",
            b"TVP/1|KEEPALIVE\n\n", b"TVP/1|KEEPALIVE\nTVP/1|KEEPALIVE\n",
            b"TVP/2|KEEPALIVE\n", b" TVP/1|KEEPALIVE\n", b"TVP/1|PING\n",
            b"TVP/1|keepalive\n", b"TVP/1\n", b"TVP/1|HELLO|\xff\n",
            b"TVP/1|HELLO|" + b"a" * 512 + b"\n",
        ):
            with self.subTest(linha=linha):
                with self.assertRaises(ValueError):
                    parse(linha)

    def test_rejeita_argumentos_python_incorretos(self):
        for tipo, campos in (("HELLO", ("Ana",)), (None, ()),
                             (MessageType.HELLO, "Ana"), (MessageType.HELLO, ["Ana"]),
                             (MessageType.HELLO, (1,))):
            with self.subTest(tipo=tipo, campos=campos):
                with self.assertRaises(TypeError):
                    encode(tipo, campos)
        for linha in (None, "TVP/1|KEEPALIVE\n", bytearray(b"TVP/1|KEEPALIVE\n")):
            with self.subTest(linha=linha):
                with self.assertRaises(TypeError):
                    parse(linha)


class TestesDelimitacao(unittest.TestCase):
    def test_fragmenta_em_todos_os_pontos_sem_perder_ordem(self):
        linhas = [linha for _, _, linha in EXEMPLOS]
        fluxo = b"".join(linhas)
        for posicao in range(len(fluxo) + 1):
            with self.subTest(posicao=posicao):
                delimitador = Framer()
                recebidas = delimitador.feed(fluxo[:posicao])
                recebidas += delimitador.feed(fluxo[posicao:])
                self.assertEqual(recebidas, linhas)
                self.assertEqual([parse(linha) for linha in recebidas],
                                 [(tipo, campos) for tipo, campos, _ in EXEMPLOS])
                self.assertEqual(delimitador.feed(b""), [])

    def test_recebe_byte_a_byte(self):
        delimitador = Framer()
        linha = b"TVP/1|HELLO|Ana\n"
        for valor in linha[:-1]:
            self.assertEqual(delimitador.feed(bytes([valor])), [])
        self.assertEqual(delimitador.feed(b"\n"), [linha])

    def test_preserva_fragmento_apos_linhas_completas(self):
        delimitador = Framer()
        self.assertEqual(delimitador.feed(b"TVP/1|KEEPALIVE\nTVP/1|REA"),
                         [b"TVP/1|KEEPALIVE\n"])
        self.assertEqual(delimitador.feed(b""), [])
        self.assertEqual(delimitador.feed(b"DY|GO\n"), [b"TVP/1|READY|GO\n"])

    def test_isola_fragmentos_por_conexao(self):
        primeiro, segundo = Framer(), Framer()
        self.assertEqual(primeiro.feed(b"TVP/1|HELLO|"), [])
        self.assertEqual(segundo.feed(b"TVP/1|KEEPALIVE\n"), [b"TVP/1|KEEPALIVE\n"])
        self.assertEqual(primeiro.feed(b"Ana\n"), [b"TVP/1|HELLO|Ana\n"])

    def test_limite_inclui_lf(self):
        delimitador = Framer()
        self.assertEqual(delimitador.feed(b"x" * 511), [])
        self.assertEqual(delimitador.feed(b"\n"), [b"x" * 511 + b"\n"])
        self.assertEqual(Framer().feed(b"x" * 511 + b"\n"), [b"x" * 511 + b"\n"])

    def test_rejeita_excesso_com_ou_sem_lf(self):
        for dados in (b"x" * 512, b"x" * 512 + b"\n", b"x" * 100000):
            with self.subTest(tamanho=len(dados)):
                with self.assertRaises(ValueError):
                    Framer().feed(dados)

    def test_excesso_fragmentado_invalida_delimitador(self):
        delimitador = Framer()
        self.assertEqual(delimitador.feed(b"x" * 500), [])
        with self.assertRaises(ValueError):
            delimitador.feed(b"x" * 12)
        for dados in (b"", b"\n", b"TVP/1|KEEPALIVE\n"):
            with self.assertRaises(ValueError):
                delimitador.feed(dados)

    def test_limite_por_linha_nao_por_lote(self):
        linhas = [b"TVP/1|KEEPALIVE\n"] * 1000
        self.assertEqual(Framer().feed(b"".join(linhas)), linhas)

    def test_excesso_apos_linha_completa(self):
        with self.assertRaises(ValueError):
            Framer().feed(b"TVP/1|KEEPALIVE\n" + b"x" * 512)

    def test_delimitacao_deixa_validacao_lexica_para_parser(self):
        self.assertEqual(Framer().feed(b"\n\xff\r\n"), [b"\n", b"\xff\r\n"])

    def test_rejeita_dados_que_nao_sao_bytes(self):
        for dados in (None, "TVP/1|KEEPALIVE\n", bytearray(b"a")):
            with self.subTest(dados=dados):
                with self.assertRaises(TypeError):
                    Framer().feed(dados)
