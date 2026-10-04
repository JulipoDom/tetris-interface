"""Futuro adaptador TCP. Não usar FakeSession como fallback."""

from tetris_shared.models import BoardSnapshot, LossReason, SessionEvent


class NetworkSession:
    # Pendente: conectar via TCP e enviar HELLO com o apelido recebido.
    def start(self, nickname: str) -> None:
        raise NotImplementedError("TODO[EP-REDE]: conexão TCP, HELLO e timers")

    # Pendente: enviar READY com PLAYER para confirmar prontidão.
    def ready(self) -> None:
        raise NotImplementedError("TODO[EP-REDE]: enviar READY|PLAYER")

    # Pendente: enviar BOARD contendo os 200 blocos fixos.
    def offer_board(self, board: BoardSnapshot) -> None:
        raise NotImplementedError("TODO[EP-REDE]: enviar BOARD")

    # Pendente: enviar ATTACK com uma quantidade válida de lixo.
    def attack(self, amount: int) -> None:
        raise NotImplementedError("TODO[EP-REDE]: enviar ATTACK")

    # Pendente: enviar KO com o motivo da derrota local.
    def defeat(self, reason: LossReason) -> None:
        raise NotImplementedError("TODO[EP-REDE]: enviar KO")

    # Pendente: ler e escrever sem bloquear, traduzir eventos e manter atividade.
    def poll(self) -> list[SessionEvent]:
        raise NotImplementedError("TODO[EP-REDE]: leitura/escrita, tradução e KEEPALIVE")

    # Pendente: liberar socket, buffers e recursos da conexão.
    def close(self) -> None:
        raise NotImplementedError("TODO[EP-REDE]: fechar conexão e buffers")
