from collections.abc import Hashable
from dataclasses import dataclass
from enum import Enum

from tetris_shared.models import EndReason, MessageType, Result
from tetris_shared.protocol import encode


class FasePartida(str, Enum):
    AGUARDANDO = "aguardando"
    PREPARACAO = "preparacao"
    ATIVA = "ativa"
    ENCERRADA = "encerrada"


@dataclass(frozen=True)
class EnviarMensagem:
    conexao: Hashable
    tipo_mensagem: MessageType
    campos: tuple[str, ...]


@dataclass(frozen=True)
class FecharConexao:
    conexao: Hashable


AcaoServidor = EnviarMensagem | FecharConexao


@dataclass(frozen=True)
class ResultadoParticipante:
    conexao: Hashable
    resultado: Result


@dataclass(frozen=True)
class DecisaoPartida:
    motivo: EndReason
    resultados: tuple[ResultadoParticipante, ...]


@dataclass
class _Participante:
    conexao: Hashable
    apelido: str | None = None
    pronto: bool = False
    conectado: bool = True


class ControladorPartida:
    def __init__(self) -> None:
        self._participantes: dict[Hashable, _Participante] = {}
        self._fase = FasePartida.AGUARDANDO
        self._decisao: DecisaoPartida | None = None

    @property
    def fase(self) -> FasePartida:
        return self._fase

    @property
    def decisao(self) -> DecisaoPartida | None:
        return self._decisao

    def admitir(self, conexao: Hashable) -> list[AcaoServidor]:
        if self._fase == FasePartida.ENCERRADA:
            return [FecharConexao(conexao)]
        if conexao in self._participantes:
            raise ValueError("Conexão já admitida")
        if len(self._participantes) == 2:
            return [FecharConexao(conexao)]
        self._participantes[conexao] = _Participante(conexao)
        return []

    def receber(self, conexao: Hashable, tipo_mensagem: MessageType,
                campos: tuple[str, ...]) -> list[AcaoServidor]:
        participante = self._participantes.get(conexao)
        if self._fase == FasePartida.ENCERRADA or participante is None:
            return []
        try:
            encode(tipo_mensagem, campos)
        except (TypeError, ValueError):
            return self.falhar(conexao, EndReason.PROTOCOL)
        if participante.apelido is None:
            if tipo_mensagem != MessageType.HELLO:
                return self.falhar(conexao, EndReason.PROTOCOL)
            participante.apelido = campos[0]
            return self._preparar()
        if tipo_mensagem == MessageType.KEEPALIVE:
            return []
        if tipo_mensagem == MessageType.READY and campos == ("PLAYER",):
            if self._fase == FasePartida.ATIVA:
                return []
            if self._fase == FasePartida.PREPARACAO:
                participante.pronto = True
                if all(outro.pronto for outro in self._participantes.values()):
                    self._fase = FasePartida.ATIVA
                    return [EnviarMensagem(outro.conexao, MessageType.READY, ("GO",))
                            for outro in self._participantes.values()]
                return []
        if self._fase == FasePartida.ATIVA:
            if tipo_mensagem in (MessageType.BOARD, MessageType.ATTACK):
                return [EnviarMensagem(outro.conexao, tipo_mensagem, campos)
                        for outro in self._participantes.values() if outro is not participante]
            if tipo_mensagem == MessageType.KO:
                return self._concluir(EndReason.KO, participante)
        return self.falhar(conexao, EndReason.PROTOCOL)

    def desconectar(self, conexao: Hashable) -> list[AcaoServidor]:
        return self.falhar(conexao, EndReason.DISCONNECT)

    def falhar(self, conexao: Hashable, motivo: EndReason) -> list[AcaoServidor]:
        if not isinstance(motivo, EndReason) or motivo not in (
            EndReason.DISCONNECT, EndReason.TIMEOUT, EndReason.PROTOCOL,
        ):
            raise ValueError("Falha exige DISCONNECT, TIMEOUT ou PROTOCOL")
        participante = self._participantes.get(conexao)
        if self._fase == FasePartida.ENCERRADA or participante is None:
            return []
        participante.conectado = False
        if participante.apelido is None:
            del self._participantes[conexao]
            return [FecharConexao(conexao)]
        return [FecharConexao(conexao), *self._concluir(motivo, participante)]

    def parar(self) -> list[AcaoServidor]:
        if self._fase == FasePartida.ENCERRADA:
            return []
        return self._concluir(EndReason.SERVER_STOP)

    def _preparar(self) -> list[AcaoServidor]:
        if len(self._participantes) != 2 or any(
            participante.apelido is None for participante in self._participantes.values()
        ):
            return []
        self._fase = FasePartida.PREPARACAO
        primeiro, segundo = self._participantes.values()
        return [
            EnviarMensagem(primeiro.conexao, MessageType.MATCH, (segundo.apelido,)),
            EnviarMensagem(segundo.conexao, MessageType.MATCH, (primeiro.apelido,)),
        ]

    def _concluir(self, motivo: EndReason,
                  perdedor: _Participante | None = None) -> list[AcaoServidor]:
        resultados = []
        for participante in self._participantes.values():
            if participante.apelido is None:
                continue
            resultado = Result.CANCEL
            if self._fase == FasePartida.ATIVA and motivo != EndReason.SERVER_STOP:
                resultado = Result.LOSE if participante is perdedor else Result.WIN
            resultados.append(ResultadoParticipante(participante.conexao, resultado))
        self._decisao = DecisaoPartida(motivo, tuple(resultados))
        self._fase = FasePartida.ENCERRADA
        acoes: list[AcaoServidor] = []
        for participante in self._participantes.values():
            if participante.apelido is None:
                participante.conectado = False
                acoes.append(FecharConexao(participante.conexao))
            elif participante.conectado:
                resultado = next(item.resultado for item in resultados
                                 if item.conexao == participante.conexao)
                acoes.append(EnviarMensagem(participante.conexao, MessageType.GAMEOVER,
                                            (resultado.value, motivo.value)))
        return acoes
