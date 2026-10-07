from dataclasses import FrozenInstanceError
import unittest

from tetris_server.partida import ControladorPartida, EnviarMensagem, FecharConexao, FasePartida
from tetris_shared.models import EndReason, MessageType


class TestesAdmissao(unittest.TestCase):
    def test_rejeita_terceira_conexao_antes_de_hello(self):
        controlador = ControladorPartida()
        self.assertEqual(controlador.admitir("a"), [])
        self.assertEqual(controlador.admitir("b"), [])
        self.assertEqual(controlador.admitir("c"), [FecharConexao("c")])
        self.assertEqual(controlador.fase, FasePartida.AGUARDANDO)
        self.assertIsNone(controlador.decisao)

    def test_primeiro_hello_aguarda_segundo_e_match_informa_oponente(self):
        controlador = ControladorPartida()
        controlador.admitir("a")
        self.assertEqual(controlador.receber("a", MessageType.HELLO, ("Ana",)), [])
        controlador.admitir("b")
        self.assertEqual(controlador.receber("b", MessageType.HELLO, ("Beto",)), [
            EnviarMensagem("a", MessageType.MATCH, ("Beto",)),
            EnviarMensagem("b", MessageType.MATCH, ("Ana",)),
        ])
        self.assertEqual(controlador.fase, FasePartida.PREPARACAO)

    def test_apelidos_iguais_nao_confundem_conexoes(self):
        controlador = ControladorPartida()
        primeiro, segundo = object(), object()
        controlador.admitir(primeiro)
        controlador.admitir(segundo)
        controlador.receber(primeiro, MessageType.HELLO, ("Mesmo",))
        self.assertEqual(controlador.receber(segundo, MessageType.HELLO, ("Mesmo",)), [
            EnviarMensagem(primeiro, MessageType.MATCH, ("Mesmo",)),
            EnviarMensagem(segundo, MessageType.MATCH, ("Mesmo",)),
        ])

    def test_candidato_desconectado_libera_posicao_sem_cancelar_identificado(self):
        controlador = ControladorPartida()
        controlador.admitir("a")
        controlador.receber("a", MessageType.HELLO, ("Ana",))
        controlador.admitir("b")
        self.assertEqual(controlador.desconectar("b"), [FecharConexao("b")])
        self.assertEqual(controlador.admitir("c"), [])
        self.assertEqual(controlador.receber("c", MessageType.HELLO, ("Caio",)), [
            EnviarMensagem("a", MessageType.MATCH, ("Caio",)),
            EnviarMensagem("c", MessageType.MATCH, ("Ana",)),
        ])
        self.assertIsNone(controlador.decisao)

    def test_conexao_admitida_nao_pode_ser_admitida_novamente(self):
        controlador = ControladorPartida()
        controlador.admitir("a")
        with self.assertRaises(ValueError):
            controlador.admitir("a")

    def test_callbacks_de_conexoes_desconhecidas_nao_afetam_partida(self):
        controlador = ControladorPartida()
        self.assertEqual(controlador.desconectar("desconhecida"), [])
        self.assertEqual(controlador.receber("desconhecida", MessageType.KO, ("SPAWN",)), [])
        self.assertIsNone(controlador.decisao)


class TestesProntidao(unittest.TestCase):
    def preparar(self):
        controlador = ControladorPartida()
        for conexao, apelido in (("a", "Ana"), ("b", "Beto")):
            controlador.admitir(conexao)
            controlador.receber(conexao, MessageType.HELLO, (apelido,))
        return controlador

    def test_so_autoriza_apos_ambos_prontos_em_qualquer_ordem(self):
        for primeiro, segundo in (("a", "b"), ("b", "a")):
            with self.subTest(primeiro=primeiro):
                controlador = self.preparar()
                self.assertEqual(controlador.receber(primeiro, MessageType.READY, ("PLAYER",)), [])
                self.assertEqual(controlador.fase, FasePartida.PREPARACAO)
                self.assertEqual(controlador.receber(segundo, MessageType.READY, ("PLAYER",)), [
                    EnviarMensagem("a", MessageType.READY, ("GO",)),
                    EnviarMensagem("b", MessageType.READY, ("GO",)),
                ])
                self.assertEqual(controlador.fase, FasePartida.ATIVA)

    def test_ready_repetido_e_atrasado_nao_reinicia_partida(self):
        controlador = self.preparar()
        controlador.receber("a", MessageType.READY, ("PLAYER",))
        self.assertEqual(controlador.receber("a", MessageType.READY, ("PLAYER",)), [])
        self.assertEqual(controlador.fase, FasePartida.PREPARACAO)
        controlador.receber("b", MessageType.READY, ("PLAYER",))
        for conexao in ("a", "b"):
            self.assertEqual(controlador.receber(conexao, MessageType.READY, ("PLAYER",)), [])
        self.assertEqual(controlador.fase, FasePartida.ATIVA)


def preparar_partida(fase=FasePartida.ATIVA):
    controlador = ControladorPartida()
    for conexao, apelido in (("a", "Ana"), ("b", "Beto")):
        controlador.admitir(conexao)
        if fase != FasePartida.AGUARDANDO or conexao == "a":
            controlador.receber(conexao, MessageType.HELLO, (apelido,))
    if fase == FasePartida.ATIVA:
        controlador.receber("a", MessageType.READY, ("PLAYER",))
        controlador.receber("b", MessageType.READY, ("PLAYER",))
    return controlador


class TestesJogo(unittest.TestCase):
    def test_encaminha_board_e_ataques_apenas_ao_oponente(self):
        controlador = preparar_partida()
        for origem, destino in (("a", "b"), ("b", "a")):
            for tipo, campos in ((MessageType.BOARD, ("0123456780" * 20,)),
                                 (MessageType.ATTACK, ("1",)),
                                 (MessageType.ATTACK, ("2",)),
                                 (MessageType.ATTACK, ("4",))):
                with self.subTest(origem=origem, tipo=tipo, campos=campos):
                    self.assertEqual(controlador.receber(origem, tipo, campos),
                                     [EnviarMensagem(destino, tipo, campos)])

    def test_go_precede_qualquer_encaminhamento(self):
        controlador = preparar_partida(FasePartida.PREPARACAO)
        controlador.receber("a", MessageType.READY, ("PLAYER",))
        acoes = controlador.receber("b", MessageType.READY, ("PLAYER",))
        acoes += controlador.receber("b", MessageType.BOARD, ("0" * 200,))
        self.assertEqual(acoes, [
            EnviarMensagem("a", MessageType.READY, ("GO",)),
            EnviarMensagem("b", MessageType.READY, ("GO",)),
            EnviarMensagem("a", MessageType.BOARD, ("0" * 200,)),
        ])

    def test_keepalive_nao_responde_apos_hello_em_todas_as_fases(self):
        for fase in (FasePartida.AGUARDANDO, FasePartida.PREPARACAO, FasePartida.ATIVA):
            with self.subTest(fase=fase):
                controlador = preparar_partida(fase)
                self.assertEqual(controlador.receber("a", MessageType.KEEPALIVE, ()), [])
                self.assertEqual(controlador.fase, fase)
                self.assertIsNone(controlador.decisao)

    def test_antes_de_hello_descarta_mensagem_sem_cancelar_oponente(self):
        casos = ((MessageType.KEEPALIVE, ()), (MessageType.READY, ("PLAYER",)),
                 (MessageType.BOARD, ("0" * 200,)), (MessageType.HELLO, ("á",)),
                 (MessageType.HELLO, ()), (MessageType.ATTACK, ("2",)))
        for tipo, campos in casos:
            with self.subTest(tipo=tipo, campos=campos):
                controlador = preparar_partida(FasePartida.AGUARDANDO)
                self.assertEqual(controlador.receber("b", tipo, campos), [FecharConexao("b")])
                self.assertEqual(controlador.fase, FasePartida.AGUARDANDO)
                self.assertIsNone(controlador.decisao)
                self.assertEqual(controlador.admitir("c"), [])

    def test_ready_antes_de_match_e_jogo_antes_de_go_sao_violacoes(self):
        for fase in (FasePartida.AGUARDANDO, FasePartida.PREPARACAO):
            casos = [(MessageType.BOARD, ("0" * 200,)), (MessageType.ATTACK, ("2",)),
                     (MessageType.KO, ("SPAWN",))]
            if fase == FasePartida.AGUARDANDO:
                casos.append((MessageType.READY, ("PLAYER",)))
            for tipo, campos in casos:
                with self.subTest(fase=fase, tipo=tipo):
                    controlador = preparar_partida(fase)
                    acoes = controlador.receber("a", tipo, campos)
                    self.assertIn(FecharConexao("a"), acoes)
                    self.assertEqual(controlador.fase, FasePartida.ENCERRADA)
                    self.assertEqual(controlador.decisao.motivo.value, "PROTOCOL")
                    self.assertTrue(all(item.resultado.value == "CANCEL"
                                        for item in controlador.decisao.resultados))

    def test_cliente_nao_envia_match_go_ou_gameover(self):
        for fase in (FasePartida.PREPARACAO, FasePartida.ATIVA):
            for tipo, campos in ((MessageType.MATCH, ("Intruso",)),
                                 (MessageType.READY, ("GO",)),
                                 (MessageType.GAMEOVER, ("WIN", "KO"))):
                with self.subTest(fase=fase, tipo=tipo):
                    controlador = preparar_partida(fase)
                    resultado = "WIN" if fase == FasePartida.ATIVA else "CANCEL"
                    self.assertEqual(controlador.receber("a", tipo, campos), [
                        FecharConexao("a"),
                        EnviarMensagem("b", MessageType.GAMEOVER, (resultado, "PROTOCOL")),
                    ])

    def test_hello_repetido_e_campos_invalidos_encerram_identificado(self):
        for tipo, campos in ((MessageType.HELLO, ("Outro",)),
                             (MessageType.ATTACK, ("3",)),
                             (MessageType.BOARD, ("0" * 199,)),
                             (MessageType.KO, ("INVALIDO",)),
                             (MessageType.KEEPALIVE, ("EXTRA",)),
                             ("PING", ()), (MessageType.ATTACK, (1,))):
            with self.subTest(tipo=tipo, campos=campos):
                controlador = preparar_partida()
                self.assertEqual(controlador.receber("a", tipo, campos), [
                    FecharConexao("a"),
                    EnviarMensagem("b", MessageType.GAMEOVER, ("WIN", "PROTOCOL")),
                ])


class TestesEncerramento(unittest.TestCase):
    def test_ko_registra_resultado_antes_de_devolver_notificacoes(self):
        for motivo in ("SPAWN", "OVERFLOW"):
            with self.subTest(motivo=motivo):
                controlador = preparar_partida()
                self.assertEqual(controlador.receber("a", MessageType.KO, (motivo,)), [
                    EnviarMensagem("a", MessageType.GAMEOVER, ("LOSE", "KO")),
                    EnviarMensagem("b", MessageType.GAMEOVER, ("WIN", "KO")),
                ])
                self.assertEqual(controlador.fase, FasePartida.ENCERRADA)
                self.assertEqual(controlador.decisao.motivo.value, "KO")
                self.assertEqual({item.conexao: item.resultado.value
                                  for item in controlador.decisao.resultados},
                                 {"a": "LOSE", "b": "WIN"})

    def test_primeiro_ko_decide_inclusive_quando_segundo_chega_logo_depois(self):
        for primeiro, segundo in (("a", "b"), ("b", "a")):
            with self.subTest(primeiro=primeiro):
                controlador = preparar_partida()
                controlador.receber(primeiro, MessageType.KO, ("SPAWN",))
                decisao = controlador.decisao
                self.assertEqual(controlador.receber(segundo, MessageType.KO, ("OVERFLOW",)), [])
                self.assertIs(controlador.decisao, decisao)
                self.assertEqual({item.conexao: item.resultado.value for item in decisao.resultados},
                                 {primeiro: "LOSE", segundo: "WIN"})

    def test_falhas_causam_cancel_antes_e_vitoria_durante_jogo(self):
        for fase in (FasePartida.PREPARACAO, FasePartida.ATIVA):
            for motivo in (EndReason.DISCONNECT, EndReason.TIMEOUT, EndReason.PROTOCOL):
                with self.subTest(fase=fase, motivo=motivo):
                    controlador = preparar_partida(fase)
                    vencedor = "WIN" if fase == FasePartida.ATIVA else "CANCEL"
                    perdedor = "LOSE" if fase == FasePartida.ATIVA else "CANCEL"
                    self.assertEqual(controlador.falhar("a", motivo), [
                        FecharConexao("a"),
                        EnviarMensagem("b", MessageType.GAMEOVER, (vencedor, motivo.value)),
                    ])
                    self.assertEqual({item.conexao: item.resultado.value
                                      for item in controlador.decisao.resultados},
                                     {"a": perdedor, "b": vencedor})
                    self.assertEqual(controlador.decisao.motivo, motivo)

    def test_desconectar_identificado_nao_libera_posicao_para_substituto(self):
        controlador = preparar_partida(FasePartida.PREPARACAO)
        self.assertEqual(controlador.desconectar("a"), [
            FecharConexao("a"),
            EnviarMensagem("b", MessageType.GAMEOVER, ("CANCEL", "DISCONNECT")),
        ])
        self.assertEqual(controlador.admitir("c"), [FecharConexao("c")])

    def test_falha_do_unico_identificado_fecha_candidato_sem_gameover(self):
        controlador = preparar_partida(FasePartida.AGUARDANDO)
        self.assertEqual(controlador.desconectar("a"), [FecharConexao("a"), FecharConexao("b")])
        self.assertEqual([(item.conexao, item.resultado.value)
                          for item in controlador.decisao.resultados], [("a", "CANCEL")])

    def test_falha_do_unico_jogador_impede_reutilizacao(self):
        controlador = ControladorPartida()
        controlador.admitir("a")
        controlador.receber("a", MessageType.HELLO, ("Ana",))
        self.assertEqual(controlador.desconectar("a"), [FecharConexao("a")])
        self.assertEqual(controlador.admitir("b"), [FecharConexao("b")])
        self.assertEqual(controlador.decisao.motivo.value, "DISCONNECT")

    def test_timeout_e_protocolo_de_anonimo_liberam_posicao(self):
        for motivo in (EndReason.TIMEOUT, EndReason.PROTOCOL):
            with self.subTest(motivo=motivo):
                controlador = preparar_partida(FasePartida.AGUARDANDO)
                self.assertEqual(controlador.falhar("b", motivo), [FecharConexao("b")])
                self.assertIsNone(controlador.decisao)
                self.assertEqual(controlador.admitir("c"), [])

    def test_parada_planejada_cancela_em_todas_as_fases(self):
        for fase in (FasePartida.AGUARDANDO, FasePartida.PREPARACAO, FasePartida.ATIVA):
            with self.subTest(fase=fase):
                controlador = preparar_partida(fase)
                acoes = [EnviarMensagem("a", MessageType.GAMEOVER, ("CANCEL", "SERVER_STOP"))]
                acoes.append(FecharConexao("b") if fase == FasePartida.AGUARDANDO else
                             EnviarMensagem("b", MessageType.GAMEOVER, ("CANCEL", "SERVER_STOP")))
                self.assertEqual(controlador.parar(), acoes)
                self.assertEqual(controlador.decisao.motivo.value, "SERVER_STOP")
                self.assertTrue(all(item.resultado.value == "CANCEL"
                                    for item in controlador.decisao.resultados))

    def test_parada_sem_jogador_e_idempotente(self):
        controlador = ControladorPartida()
        self.assertEqual(controlador.parar(), [])
        decisao = controlador.decisao
        self.assertIsNotNone(decisao)
        self.assertEqual(decisao.resultados, ())
        self.assertEqual(controlador.parar(), [])
        self.assertIs(controlador.decisao, decisao)
        self.assertEqual(controlador.admitir("a"), [FecharConexao("a")])

    def test_mensagens_e_falhas_tardias_nao_alteram_resultado(self):
        controlador = preparar_partida()
        controlador.receber("a", MessageType.KO, ("SPAWN",))
        decisao = controlador.decisao
        for tipo, campos in ((MessageType.BOARD, ("0" * 200,)),
                             (MessageType.ATTACK, ("4",)), (MessageType.HELLO, ("Outro",)),
                             (MessageType.KEEPALIVE, ()), ("INVALIDO", ())):
            self.assertEqual(controlador.receber("b", tipo, campos), [])
        self.assertEqual(controlador.falhar("b", EndReason.PROTOCOL), [])
        self.assertEqual(controlador.desconectar("b"), [])
        self.assertEqual(controlador.parar(), [])
        self.assertIs(controlador.decisao, decisao)

    def test_duas_desconexoes_nao_mudam_vencedor_registrado(self):
        controlador = preparar_partida()
        controlador.desconectar("a")
        decisao = controlador.decisao
        self.assertEqual(controlador.desconectar("b"), [])
        self.assertIs(controlador.decisao, decisao)
        self.assertEqual({item.conexao: item.resultado.value for item in decisao.resultados},
                         {"a": "LOSE", "b": "WIN"})

    def test_decisao_e_acoes_sao_imutaveis(self):
        controlador = preparar_partida()
        acoes = controlador.receber("a", MessageType.KO, ("SPAWN",))
        with self.assertRaises(FrozenInstanceError):
            controlador.decisao.motivo = None
        with self.assertRaises(FrozenInstanceError):
            controlador.decisao.resultados[0].resultado = None
        with self.assertRaises(FrozenInstanceError):
            acoes[0].campos = ("WIN", "KO")

    def test_motivos_invalidos_de_falha_sao_erros_de_api(self):
        controlador = preparar_partida()
        for motivo in ("TIMEOUT", EndReason.KO, EndReason.SERVER_STOP, None):
            with self.subTest(motivo=motivo):
                with self.assertRaises(ValueError):
                    controlador.falhar("a", motivo)
        self.assertEqual(controlador.fase, FasePartida.ATIVA)
        self.assertIsNone(controlador.decisao)
