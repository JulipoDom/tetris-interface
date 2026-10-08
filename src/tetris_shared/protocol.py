"""Codec TVP/1 compartilhado: valida campos e delimita o fluxo TCP."""

import re

from .models import MessageType


LIMITE_LINHA = 512
PADROES_CAMPOS = {
    MessageType.HELLO: (r"[A-Za-z0-9_]{1,20}",),
    MessageType.MATCH: (r"[A-Za-z0-9_]{1,20}",),
    MessageType.READY: (r"PLAYER|GO|REMATCH",),
    MessageType.BOARD: (r"[0-8]{200}",),
    MessageType.ATTACK: (r"1|2|4",),
    MessageType.KO: (r"SPAWN|OVERFLOW|INACTIVITY",),
    MessageType.GAMEOVER: (r"WIN|LOSE|CANCEL", r"KO|DISCONNECT|TIMEOUT|PROTOCOL|SERVER_STOP"),
    MessageType.KEEPALIVE: (),
}


def _validar_campos(tipo_mensagem: MessageType, campos: tuple[str, ...]) -> None:
    """Confere campos da gramática; direção e fase pertencem aos adaptadores."""
    if not isinstance(tipo_mensagem, MessageType):
        raise TypeError("Tipo da mensagem deve ser MessageType")
    if not isinstance(campos, tuple) or any(not isinstance(campo, str) for campo in campos):
        raise TypeError("Campos devem ser uma tupla de strings")
    padroes = PADROES_CAMPOS[tipo_mensagem]
    if len(campos) != len(padroes):
        raise ValueError("Quantidade de campos inválida")
    if any(re.fullmatch(padrao, campo) is None for padrao, campo in zip(padroes, campos)):
        raise ValueError("Campo inválido para " + tipo_mensagem.value)


def encode(tipo_mensagem: MessageType, campos: tuple[str, ...]) -> bytes:
    """Produz um frame ASCII completo, incluindo o delimitador LF."""
    _validar_campos(tipo_mensagem, campos)
    return ("|".join(("TVP/1", tipo_mensagem.value, *campos)) + "\n").encode("ascii")


def parse(linha: bytes) -> tuple[MessageType, tuple[str, ...]]:
    """Interpreta somente uma linha completa, sem aceitar campos adicionais."""
    if not isinstance(linha, bytes):
        raise TypeError("Linha deve ser bytes")
    if len(linha) > LIMITE_LINHA or not linha.endswith(b"\n") or linha.count(b"\n") != 1:
        raise ValueError("Linha deve terminar em um único LF e ter no máximo 512 bytes")
    try:
        partes = linha[:-1].decode("ascii").split("|")
    except UnicodeDecodeError as erro:
        raise ValueError("Mensagem deve usar somente ASCII") from erro
    if len(partes) < 2 or partes[0] != "TVP/1":
        raise ValueError("Prefixo de protocolo inválido")
    try:
        tipo_mensagem = MessageType(partes[1])
    except ValueError as erro:
        raise ValueError("Tipo de mensagem desconhecido") from erro
    campos = tuple(partes[2:])
    _validar_campos(tipo_mensagem, campos)
    return tipo_mensagem, campos


class Framer:
    """Conserva fragmentos e extrai todos os frames completos de cada lote."""

    def __init__(self) -> None:
        """Prepara o acumulador limitado; erro de framing invalida a conexão."""
        self._fragmento = bytearray()
        self._invalido = False

    def feed(self, dados: bytes) -> list[bytes]:
        """Separa frames por LF sem depender dos limites de chamadas recv."""
        if not isinstance(dados, bytes):
            raise TypeError("Dados devem ser bytes")
        if self._invalido:
            raise ValueError("Delimitador inválido; encerre a conexão")
        linhas = []
        inicio = 0
        while inicio < len(dados):
            fim = dados.find(b"\n", inicio)
            limite = len(dados) if fim == -1 else fim + 1
            tamanho = len(self._fragmento) + limite - inicio
            if tamanho > LIMITE_LINHA or (fim == -1 and tamanho >= LIMITE_LINHA):
                self._fragmento.clear()
                self._invalido = True
                raise ValueError("Linha excede o limite de 512 bytes incluindo LF")
            self._fragmento.extend(dados[inicio:limite])
            if fim == -1:
                break
            linhas.append(bytes(self._fragmento))
            self._fragmento.clear()
            inicio = limite
        return linhas
