import threading
import time
import unittest
from unittest.mock import patch

from tetris_client.app import App, State
from tetris_client.engine import Engine
from tetris_client.network import NetworkSession
from tetris_client.session import (
    AttackOffered, BoardOffered, DefeatOffered, HelloOffered, ReadyOffered,
)
from tetris_shared.models import (
    AttackReceived, BoardSnapshot, ConnectionLost, LossReason, OpponentDefined,
)


def wait_until(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("A thread não alcançou a condição esperada")


class ThreadHarness(NetworkSession):
    """Substitui os pontos de rede apenas para testar fluxos de execução, sem abrir conexão."""

    def __init__(self, *, block_connect=False, block_send=False):
        super().__init__()
        self.entered = threading.Event()
        self.release = threading.Event()
        self.cleaned = threading.Event()
        self.block_connect = block_connect
        self.block_send = block_send
        self.calls = []
        self.inputs = []
        self.input_lock = threading.Lock()

    def _connect(self):
        self.calls.append(("conectar", threading.get_ident()))
        self.entered.set()
        if self.block_connect:
            self.release.wait(2)

    def _send(self, command):
        if self.block_send:
            self.entered.set()
            self.release.wait(2)
        self.calls.append((command, threading.get_ident()))

    def _receive_events(self):
        with self.input_lock:
            events, self.inputs = self.inputs, []
            return events

    def _process_timers(self):
        pass

    def _close_connection(self):
        self.calls.append(("fechar", threading.get_ident()))
        self.cleaned.set()

    def inject(self, *events):
        with self.input_lock:
            self.inputs.extend(events)


class ThreadStructureTests(unittest.TestCase):
    def setUp(self):
        self.sessions = []

    def tearDown(self):
        for session in self.sessions:
            session.release.set()
            session.close()
            self.assertTrue(session.cleaned.wait(1))

    def session(self, **options):
        session = ThreadHarness(**options)
        self.sessions.append(session)
        session._start_worker("Ana")
        return session

    def test_network_entry_points_remain_explicit_stubs(self):
        session = NetworkSession()
        board = BoardSnapshot([[0] * 10 for _ in range(20)])
        calls = [lambda: session.start("Ana"), session.ready,
                 lambda: session.offer_board(board), lambda: session.attack(1),
                 lambda: session.defeat(LossReason.SPAWN), session._connect,
                 lambda: session._send(HelloOffered("Ana")), session._receive_events,
                 session._process_timers, session._close_connection]
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaisesRegex(NotImplementedError, r"TODO\[EP-REDE\]"):
                    call()
        self.assertIsNone(session._thread)
        self.assertEqual(session.poll(), [])
        session.close()

    def test_worker_preserves_hello_attack_board_defeat_order(self):
        session = self.session()
        board = BoardSnapshot([[0] * 10 for _ in range(20)])
        commands = [ReadyOffered(), AttackOffered(2), BoardOffered(board),
                    DefeatOffered(LossReason.OVERFLOW)]
        for command in commands:
            session._enqueue(command)
        wait_until(lambda: len(session.calls) >= 6)
        sent = [entry for entry, _ in session.calls if not isinstance(entry, str)]
        self.assertEqual(sent, [HelloOffered("Ana"), *commands])
        session.close()
        self.assertEqual({owner for _, owner in session.calls}, {session._thread.ident})
        self.assertNotEqual(session._thread.ident, threading.get_ident())

    def test_blocked_connection_does_not_block_poll_or_close(self):
        session = self.session(block_connect=True)
        self.assertTrue(session.entered.wait(1))
        began = time.monotonic()
        for _ in range(100):
            self.assertEqual(session.poll(), [])
        self.assertLess(time.monotonic() - began, 0.1)
        began = time.monotonic()
        session.close()
        self.assertLess(time.monotonic() - began, 0.4)
        session.release.set()
        self.assertTrue(session.cleaned.wait(1))
        self.assertEqual(session.poll(), [])
        self.assertEqual([entry for entry, _ in session.calls], ["conectar", "fechar"])

    def test_engine_ticks_while_worker_send_is_blocked(self):
        session = self.session(block_send=True)
        self.assertTrue(session.entered.wait(1))
        now = [0.0]
        game = Engine(clock=lambda: now[0])
        game.start()
        now[0] = 0.7
        game.tick()
        self.assertEqual(game.active.y, 1)
        self.assertEqual(session.poll(), [])

    def test_received_events_change_app_only_on_main_thread_update(self):
        session = self.session()
        app = App("network", "Ana", session=session)
        app.state = State.WAITING
        session.inject(OpponentDefined("Bob"))
        wait_until(lambda: len(session._incoming) == 1)
        self.assertIsNone(app.opponent)
        app.update()
        self.assertEqual(app.opponent, "Bob")
        self.assertEqual(app.state, State.PREPARING)

    def test_worker_failure_is_reported_once_without_fake_fallback(self):
        session = ThreadHarness()
        self.sessions.append(session)
        with patch.object(session, '_connect', side_effect=NotImplementedError("TODO[EP-REDE]: conectar")):
            session._start_worker("Ana")
            self.assertTrue(session.cleaned.wait(1))
        events = session.poll()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], ConnectionLost)
        self.assertIn("TODO[EP-REDE]", events[0].detail)
        self.assertEqual(session.poll(), [])

    def test_incoming_queue_limit_reports_failure_without_silent_drop(self):
        session = self.session()
        session.inject(*([AttackReceived(1)] * 257))
        wait_until(lambda: session._stop.is_set())
        events = session.poll()
        self.assertEqual(events[:-1], [AttackReceived(1)] * 256)
        self.assertIsInstance(events[-1], ConnectionLost)

    def test_outgoing_queue_limit_reports_failure(self):
        session = self.session(block_connect=True)
        self.assertTrue(session.entered.wait(1))
        for _ in range(256):
            session._enqueue(AttackOffered(1))
        events = session.poll()
        self.assertIsInstance(events[-1], ConnectionLost)
        self.assertIn("256", events[-1].detail)

    def test_close_is_idempotent_stops_worker_and_prevents_reuse(self):
        session = self.session()
        self.assertTrue(session.entered.wait(1))
        session.close()
        session.close()
        self.assertFalse(session._thread.is_alive())
        self.assertEqual(session.poll(), [])
        with self.assertRaises(RuntimeError):
            session._start_worker("Ana")

    def test_queue_rejects_commands_before_start_or_after_close(self):
        session = ThreadHarness()
        with self.assertRaises(RuntimeError):
            session._enqueue(AttackOffered(1))
        session.close()
        with self.assertRaises(RuntimeError):
            session._enqueue(AttackOffered(1))
