"""Adaptador TCP: a thread de rede troca bytes e a thread principal conserva o jogo."""

from collections import deque
from collections.abc import Callable
import errno
from ipaddress import ip_address
import select
import socket
import threading
import time

from tetris_shared.models import (
    AttackReceived, BoardReceived, BoardSnapshot, ConnectionLost, EndReason,
    LossReason, MatchResult, MessageType, OpponentDefined, Result, SessionEvent,
    StartAuthorized,
)
from tetris_shared.protocol import Framer, encode, parse
from .session import (
    AttackOffered, BoardOffered, DefeatOffered, HelloOffered, ReadyOffered,
    SessionOutput, validate_nickname,
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_QUEUED_COMMANDS = 256
MAX_INCOMING_EVENTS = 256
COMMANDS_PER_CYCLE = 32
WORKER_INTERVAL = 0.02
CLOSE_WAIT = 0.2
MAX_PENDING_BYTES = 4096
CONNECT_TIMEOUT = 5.0
KEEPALIVE_INTERVAL = 5.0
INACTIVITY_TIMEOUT = 15.0


# Valida o destino sem abrir sockets ou iniciar uma thread.
def validate_endpoint(host: str, port: int):
    if not host or type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Servidor exige endereço e porta entre 1 e 65535")
    try:
        return ip_address("127.0.0.1" if host == "localhost" else host)
    except ValueError as exc:
        raise ValueError("Servidor exige IP literal ou localhost") from exc


class NetworkSession:
    """Traduz intenções e eventos TVP/1 sem executar o motor na thread de rede."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, *,
                 clock: Callable[[], float] = time.monotonic) -> None:
        """Valida o destino e prepara filas, estados e temporizadores sem conectar."""
        address = validate_endpoint(host, port)
        self.host, self.port = host, port
        self._family = socket.AF_INET6 if address.version == 6 else socket.AF_INET
        self._address = ((str(address), port, 0, 0) if address.version == 6
                         else (str(address), port))
        self._clock = clock
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._outgoing: deque[SessionOutput] = deque()
        self._incoming: deque[SessionEvent] = deque()
        self._terminal: ConnectionLost | None = None
        self._started = False
        self._closed = False
        self._connected = False
        self._phase = "new"
        self._socket: socket.socket | None = None
        self._framer = Framer()
        self._pending = bytearray()
        self._hello_sent = False
        self._last_received: float | None = None
        self._last_keepalive: float | None = None

    @property
    def connected(self) -> bool:
        """Informa à interface se a conexão TCP já foi estabelecida."""
        with self._lock:
            return self._connected and not self._stop.is_set()

    def start(self, nickname: str) -> None:
        """Entrega a abertura da sessão ao fluxo de rede."""
        self._start_worker(nickname)

    def ready(self) -> None:
        """Agenda prontidão apenas durante a preparação da dupla."""
        with self._lock:
            if self._closed or self._stop.is_set() or self._phase == "finished":
                return
            if self._phase == "ready":
                return
            if self._phase != "preparing":
                raise RuntimeError("Prontidão fora da preparação")
            self._phase = "ready"
        self._enqueue(ReadyOffered())

    def rematch(self) -> None:
        """Envia um único aceite; a mesma conexão espera GO do servidor."""
        with self._lock:
            if self._closed or self._stop.is_set() or self._phase == 'rematch':
                return
            if self._phase != 'finished':
                raise RuntimeError('Revanche fora do resultado')
            self._phase = 'rematch'
        self._enqueue(ReadyOffered('REMATCH'))

    def offer_board(self, board: BoardSnapshot) -> None:
        """Enfileira os blocos fixos sem acessar o socket no fluxo do jogo."""
        if not isinstance(board, BoardSnapshot):
            raise TypeError("Tabuleiro deve ser BoardSnapshot")
        with self._lock:
            if self._closed or self._stop.is_set() or self._phase == "finished":
                return
            if self._phase != "playing":
                raise RuntimeError("Tabuleiro fora da partida")
        self._enqueue(BoardOffered(board))

    def attack(self, amount: int) -> None:
        """Valida a quantidade e agenda o ataque para o adversário."""
        if type(amount) is not int or amount not in (1, 2, 4):
            raise ValueError("Ataque deve conter 1, 2 ou 4 linhas")
        with self._lock:
            if self._closed or self._stop.is_set() or self._phase == "finished":
                return
            if self._phase != "playing":
                raise RuntimeError("Ataque fora da partida")
        self._enqueue(AttackOffered(amount))

    def defeat(self, reason: LossReason) -> None:
        """Agenda uma única derrota e mantém a conexão até o resultado."""
        if not isinstance(reason, LossReason):
            raise ValueError("Motivo de derrota inválido")
        with self._lock:
            if self._closed or self._stop.is_set() or self._phase == "finished":
                return
            if self._phase == "awaiting_result":
                return
            if self._phase != "playing":
                raise RuntimeError("Derrota fora da partida")
            self._phase = "awaiting_result"
        self._enqueue(DefeatOffered(reason))

    def _connect(self) -> None:
        # connect_ex e select permitem que close interrompa a tentativa de conexão.
        """Conecta sem bloquear o teclado e respeita o prazo de abertura."""
        deadline = self._clock() + CONNECT_TIMEOUT
        if self._stop.is_set():
            return
        connection = socket.socket(self._family, socket.SOCK_STREAM)
        self._socket = connection
        try:
            connection.setblocking(False)
            code = connection.connect_ex(self._address)
            if code not in (0, errno.EISCONN):
                if code not in (errno.EINPROGRESS, errno.EALREADY,
                                errno.EWOULDBLOCK, errno.EINTR):
                    raise OSError(code, "Não foi possível conectar ao servidor")
                while not self._stop.is_set():
                    remaining = deadline - self._clock()
                    if remaining <= 0:
                        raise TimeoutError("Tempo de conexão esgotado")
                    _, writable, exceptional = select.select(
                        [], [connection], [connection], min(WORKER_INTERVAL, remaining),
                    )
                    if writable or exceptional:
                        error = connection.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                        if error:
                            raise OSError(error, "Não foi possível conectar ao servidor")
                        break
            if self._stop.is_set():
                return
            with self._lock:
                self._connected = True
            self._last_received = self._clock()
        except OSError:
            connection.close()
            self._socket = None
            raise

    def _send(self, command: SessionOutput) -> None:
        """Traduz uma intenção tipada em bytes e limita a saída pendente."""
        if isinstance(command, HelloOffered):
            data = encode(MessageType.HELLO, (command.nickname,))
        elif isinstance(command, ReadyOffered):
            data = encode(MessageType.READY, (command.choice,))
        elif isinstance(command, BoardOffered):
            board = "".join(str(cell) for row in command.board.cells for cell in row)
            data = encode(MessageType.BOARD, (board,))
        elif isinstance(command, AttackOffered):
            data = encode(MessageType.ATTACK, (str(command.amount),))
        elif isinstance(command, DefeatOffered):
            data = encode(MessageType.KO, (command.reason.value,))
        else:
            raise TypeError("Intenção de sessão desconhecida")
        if len(self._pending) + len(data) > MAX_PENDING_BYTES:
            self._flush_pending()
        if len(self._pending) + len(data) > MAX_PENDING_BYTES:
            raise BufferError("Servidor lento: limite de 4096 bytes de saída excedido")
        self._pending.extend(data)
        if isinstance(command, HelloOffered):
            self._hello_sent = True
            self._last_keepalive = self._clock()

    def _flush_pending(self) -> None:
        """Envia o que o socket permite e conserva o restante para outro ciclo."""
        if self._socket is None:
            raise ConnectionError("Conexão TCP indisponível")
        while self._pending:
            try:
                written = self._socket.send(self._pending)
            except (BlockingIOError, InterruptedError):
                return
            if written == 0:
                raise ConnectionError("Servidor encerrou o envio")
            del self._pending[:written]

    def _receive_events(self) -> list[SessionEvent]:
        """Reconstrói frames recebidos e prioriza o resultado confirmado."""
        self._flush_pending()
        assert self._socket is not None
        try:
            data = self._socket.recv(4096)
        except (BlockingIOError, InterruptedError):
            return []
        if not data:
            raise ConnectionError("Servidor encerrou a conexão")
        events: list[SessionEvent] = []
        parts = data.split(b"\n")
        for part in parts[:-1]:
            # Um resultado completo prevalece sobre bytes inválidos que venham depois.
            for line in self._framer.feed(part + b"\n"):
                kind, fields = parse(line)
                event = self._accept_message(kind, fields)
                if event is not None:
                    events.append(event)
                if isinstance(event, MatchResult):
                    return [event]
        if parts[-1]:
            self._framer.feed(parts[-1])
        return events

    def _accept_message(self, kind: MessageType, fields: tuple[str, ...]) -> SessionEvent | None:
        """Valida direção e fase antes de atualizar o estado da sessão."""
        with self._lock:
            phase = self._phase
            event: SessionEvent | None = None
            if kind == MessageType.KEEPALIVE and phase in (
                "waiting", "preparing", "ready", "playing", "awaiting_result",
                "finished", "rematch",
            ):
                pass
            elif kind == MessageType.MATCH and phase == "waiting":
                event = OpponentDefined(fields[0])
                self._phase = "preparing"
            elif kind == MessageType.READY and fields == ("GO",) and phase in ('ready', 'rematch'):
                event = StartAuthorized()
                self._phase = "playing"
            elif kind == MessageType.BOARD and phase in ("playing", "awaiting_result"):
                rows = tuple(tuple(int(cell) for cell in fields[0][i:i + 10])
                             for i in range(0, 200, 10))
                event = BoardReceived(BoardSnapshot(rows))
            elif kind == MessageType.ATTACK and phase in ("playing", "awaiting_result"):
                event = AttackReceived(int(fields[0]))
            elif kind == MessageType.GAMEOVER and phase in (
                "waiting", "preparing", "ready", "playing", "awaiting_result",
            ):
                result = Result(fields[0])
                reason = EndReason(fields[1])
                active = phase in ("playing", "awaiting_result")
                valid = ((reason == EndReason.SERVER_STOP and result == Result.CANCEL)
                         or (reason == EndReason.KO and active
                             and result in (Result.WIN, Result.LOSE))
                         or (reason in (EndReason.DISCONNECT, EndReason.TIMEOUT,
                                        EndReason.PROTOCOL)
                             and result == (Result.WIN if active else Result.CANCEL)))
                if not valid:
                    raise ValueError("Resultado do servidor incompatível com a partida")
                event = MatchResult(result, reason)
                self._phase = "finished"
            elif kind == MessageType.GAMEOVER and phase in ('finished', 'rematch'):
                return None
            else:
                raise ValueError("Mensagem do servidor fora de direção ou fase")
            self._last_received = self._clock()
            return event

    def _process_timers(self) -> None:
        """Detecta silêncio do servidor e agenda KEEPALIVE sem eco."""
        now = self._clock()
        if self._last_received is not None and now - self._last_received >= INACTIVITY_TIMEOUT:
            raise TimeoutError("Servidor sem atividade por 15 segundos")
        if (self._hello_sent and self._last_keepalive is not None
                and now - self._last_keepalive >= KEEPALIVE_INTERVAL):
            data = encode(MessageType.KEEPALIVE, ())
            if len(self._pending) + len(data) > MAX_PENDING_BYTES:
                raise BufferError("Servidor lento: limite de 4096 bytes de saída excedido")
            self._pending.extend(data)
            self._last_keepalive = now

    def _close_connection(self) -> None:
        """Libera o socket e descarta bytes pertencentes à sessão encerrada."""
        connection, self._socket = self._socket, None
        self._pending.clear()
        self._framer = Framer()
        with self._lock:
            self._connected = False
        if connection is not None:
            connection.close()

    def _start_worker(self, nickname: str) -> None:
        """Agenda HELLO e inicia a comunicação sem bloquear a interface."""
        validate_nickname(nickname)
        with self._lock:
            if self._started or self._closed:
                raise RuntimeError("A sessão não pode ser reutilizada")
            self._started = True
            self._phase = "waiting"
            self._outgoing.append(HelloOffered(nickname))
            self._thread = threading.Thread(target=self._run, name="tetris-network", daemon=True)
            self._thread.start()

    def _enqueue(self, command: SessionOutput) -> None:
        """Entrega uma intenção ao fluxo de rede sem serializar nem esperar pela comunicação."""
        with self._lock:
            if not self._started or self._closed:
                raise RuntimeError("A sessão não está aberta")
            if self._stop.is_set():
                return
            if len(self._outgoing) >= MAX_QUEUED_COMMANDS:
                self._fail_locked("Fila de saída excede 256 intenções")
                return
            self._outgoing.append(command)

    def _publish(self, event: SessionEvent) -> None:
        """Entrega um evento ao jogo sem executar física no fluxo de rede."""
        with self._lock:
            if self._stop.is_set():
                return
            if isinstance(event, MatchResult):
                self._incoming.clear()
                self._incoming.append(event)
                return
            if len(self._incoming) >= MAX_INCOMING_EVENTS:
                self._fail_locked("Fila de entrada excede 256 eventos")
                return
            self._incoming.append(event)

    def poll(self) -> list[SessionEvent]:
        """Consulta somente a fila; este método nunca realiza entrada ou saída de rede."""
        with self._lock:
            if self._closed:
                return []
            events = list(self._incoming)
            self._incoming.clear()
            if self._terminal is not None:
                events.append(self._terminal)
                self._terminal = None
            return events

    def close(self) -> None:
        """Sinaliza parada e aguarda no máximo 200 ms para liberar o terminal."""
        with self._lock:
            self._closed = True
            self._stop.set()
            self._incoming.clear()
            self._outgoing.clear()
            self._terminal = None
            worker = self._thread
        # Uma operação de rede bloqueada deve observar parada ao retornar.
        # A liberação do transporte pertence ao bloco finally do fluxo de rede.
        if worker is not None and worker is not threading.current_thread():
            worker.join(CLOSE_WAIT)

    def _fail_locked(self, detail: str) -> None:
        """Registra uma falha terminal enquanto o bloqueio da fila está adquirido."""
        if not self._stop.is_set():
            self._terminal = ConnectionLost(f"{detail[:48]}; resultado não confirmado")
            self._stop.set()

    def _fail(self, detail: str) -> None:
        """Protege o registro de falha contra acesso concorrente."""
        with self._lock:
            self._fail_locked(detail)

    def _run(self) -> None:
        """Troca bytes em segundo plano e entrega eventos à interface."""
        try:
            self._connect()
            while not self._stop.is_set():
                # Limitar o lote evita que envios monopolizem o ciclo de recepção.
                for _ in range(COMMANDS_PER_CYCLE):
                    with self._lock:
                        if self._stop.is_set() or not self._outgoing:
                            break
                        command = self._outgoing.popleft()
                    self._send(command)
                if self._stop.is_set():
                    break
                for event in self._receive_events():
                    self._publish(event)
                    if self._stop.is_set():
                        break
                if self._stop.is_set():
                    break
                self._process_timers()
                # Espera interrompível: reduz uso de CPU e responde ao fechamento.
                self._stop.wait(WORKER_INTERVAL)
        except PermissionError:
            self._fail("Conexão TCP bloqueada pelo sistema")
        except ConnectionRefusedError:
            self._fail("Servidor recusou a conexão")
        except TimeoutError as exc:
            self._fail(str(exc))
        except (ConnectionError, BufferError, ValueError) as exc:
            self._fail(str(exc))
        except OSError as exc:
            self._fail(f"Falha na conexão TCP: {exc.strerror or exc}")
        except Exception as exc:
            self._fail(f"Falha na thread de rede: {exc}")
        finally:
            try:
                self._close_connection()
            except Exception as exc:
                self._fail(f"Falha ao liberar conexão: {exc}")
            with self._lock:
                self._outgoing.clear()
