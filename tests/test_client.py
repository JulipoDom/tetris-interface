import random
import unittest

from tetris_client.app import App, State
from tetris_client.engine import Engine, GarbageLimitError, Piece, SHAPES
from tetris_client.network import NetworkSession
from tetris_client.session import (
    AttackOffered, BoardOffered, DefeatOffered, FakeSession, ReadyOffered,
)
from tetris_shared import protocol
from tetris_shared.models import (
    AttackProduced, AttackReceived, BoardProduced, BoardReceived, BoardSnapshot,
    ConnectionLost, EndReason, LocalDefeat, LossReason, MatchResult, MessageType,
    OpponentDefined, PieceKind, Result, StartAuthorized,
)


class Clock:
    # Cria um relógio controlado pelo teste.
    def __init__(self):
        self.now = 0.0

    # Retorna o instante configurado sem consultar o relógio real.
    def __call__(self):
        return self.now


# Cria um motor determinístico com geradores e relógio de teste.
def engine(clock=None):
    return Engine(piece_rng=random.Random(7), garbage_rng=random.Random(12),
                  clock=clock if clock is not None else Clock())


class EngineTests(unittest.TestCase):
    # Confere que cada coleção embaralhada tem sete peças distintas.
    def test_each_bag_has_seven_distinct_pieces(self):
        game = engine()
        pieces = [game.next_kind] + [game._draw() for _ in range(20)]
        for start in (0, 7, 14):
            self.assertEqual(set(pieces[start:start + 7]), set(PieceKind))

    # Confere que a gravidade usa o relógio e limita a recuperação de passos atrasados.
    def test_gravity_uses_clock_and_limits_catch_up(self):
        clock = Clock()
        game = engine(clock)
        game.start()
        clock.now = 0.699
        game.tick()
        self.assertEqual(game.active.y, 0)
        clock.now = 0.7
        game.tick()
        self.assertEqual(game.active.y, 1)
        clock.now = 70
        game.tick()
        self.assertEqual(game.active.y, 5)
        game.tick()
        self.assertEqual(game.active.y, 5)

    # Confere a colisão e a rotação sem deslocamentos corretivos.
    def test_collision_and_rotation_without_wall_kicks(self):
        game = engine()
        game.start()
        game.active = Piece(PieceKind.T, 0, 0, SHAPES[PieceKind.T][1])
        initial = game.active
        game.move(-1)
        self.assertEqual(game.active, initial)
        game.rotate()
        self.assertEqual(game.active.cells, ((2, 1), (1, 0), (1, 1), (1, 2)))
        for _ in range(3):
            game.rotate()
        self.assertEqual(game.active, initial)
        game.board[2][1] = 8
        game.rotate()
        self.assertEqual(game.active, initial)

    # Confere que a peça O não gira e a peça I mantém o tamanho do quadrado.
    def test_o_does_not_rotate_and_i_keeps_square_size(self):
        game = engine()
        game.start()
        game.active = Piece(PieceKind.O, 4, 0, SHAPES[PieceKind.O][1])
        initial = game.active
        game.rotate()
        self.assertEqual(game.active, initial)
        game.active = Piece(PieceKind.I, 3, 0, SHAPES[PieceKind.I][1])
        game.rotate()
        self.assertEqual(game.active.cells, ((2, 0), (2, 1), (2, 2), (2, 3)))

    # Confere a pontuação, o ataque e a remoção simultânea de linhas.
    def test_score_attack_and_simultaneous_clear(self):
        for count, score, attack in ((1, 100, 0), (2, 300, 1), (3, 500, 2), (4, 800, 4)):
            with self.subTest(count=count):
                game = engine()
                game.start()
                game.active = Piece(PieceKind.I, 2, 16, ((2, 0), (2, 1), (2, 2), (2, 3)))
                for y in range(20 - count, 20):
                    game.board[y] = [8] * 10
                    game.board[y][4] = 0
                events = game.hard_drop()
                self.assertEqual(game.score, score)
                attacks = [e.amount for e in events if isinstance(e, AttackProduced)]
                self.assertEqual(attacks, [attack] if attack else [])
                self.assertFalse(any(all(row) for row in game.board))

    # Confere que o lixo aguarda a fixação e preserva o restante.
    def test_garbage_waits_for_lock_and_preserves_remainder(self):
        game = engine()
        game.start()
        game.receive_garbage(4)
        game.receive_garbage(2)
        self.assertFalse(any(8 in row for row in game.board))
        game.soft_drop()
        self.assertEqual(game.pending_garbage, 6)
        game.hard_drop()
        self.assertEqual(game.pending_garbage, 2)
        for row in game.board[-4:]:
            self.assertEqual(row.count(8), 9)
            self.assertEqual(row.count(0), 1)

    # Confere que o transbordamento informa uma única derrota e congela o jogo.
    def test_overflow_reports_single_loss_and_freezes(self):
        game = engine()
        game.start()
        game.board[0][0] = 8
        game.receive_garbage(1)
        events = game.hard_drop()
        self.assertEqual(events[-1], LocalDefeat(LossReason.OVERFLOW))
        self.assertEqual(sum(isinstance(e, LocalDefeat) for e in events), 1)
        self.assertEqual(game.hard_drop(), [])
        self.assertEqual(game.soft_drop(), [])
        self.assertEqual(game.tick(), [])

    # Confere que ocupar apenas a primeira linha não significa derrota.
    def test_first_row_alone_does_not_mean_loss(self):
        game = engine()
        game.board[0][0] = 8
        game.start()
        self.assertIsNone(game.loss)
        self.assertTrue(game.running)

    # Confere a derrota por nascimento bloqueado.
    def test_spawn_blocked(self):
        game = engine()
        game.next_kind = PieceKind.O
        game.board[0][4] = 8
        self.assertEqual(game.start()[-1], LocalDefeat(LossReason.SPAWN))
        self.assertEqual(game.start(), [])

    # Confere a ordem de ataque, retrato do tabuleiro e derrota.
    def test_attack_snapshot_loss_order(self):
        game = engine()
        game.start()
        game.active = Piece(PieceKind.I, 2, 16, ((2, 0), (2, 1), (2, 2), (2, 3)))
        for y in (18, 19):
            game.board[y] = [8] * 10
            game.board[y][4] = 0
        game.board[0][0] = 8
        game.receive_garbage(4)
        events = game.hard_drop()
        self.assertEqual([type(e) for e in events], [AttackProduced, BoardProduced, LocalDefeat])
        self.assertEqual(events[0].amount, 1)
        self.assertEqual(events[-1].reason, LossReason.OVERFLOW)

    # Confere que o retrato do tabuleiro é uma cópia independente e não inclui a peça ativa.
    def test_snapshot_is_detached_and_does_not_include_active_piece(self):
        game = engine()
        game.start()
        snapshot = game.snapshot()
        self.assertFalse(any(any(row) for row in snapshot.cells))
        game.board[19][0] = 8
        self.assertEqual(snapshot.cells[19][0], 0)
        with self.assertRaises(TypeError):
            snapshot.cells[0][0] = 1

    # Confere que exceder o limite pendente é uma falha de sessão, não uma derrota.
    def test_pending_limit_is_failure_not_defeat(self):
        game = engine()
        game.start()
        for _ in range(10):
            game.receive_garbage(4)
        with self.assertRaises(GarbageLimitError):
            game.receive_garbage(1)
        self.assertEqual(game.pending_garbage, 40)
        self.assertIsNone(game.loss)

    # Confere que um novo motor reinicia a pontuação e o lixo.
    def test_new_engine_resets_score_and_garbage(self):
        first = engine()
        first.score = 800
        first.receive_garbage(4)
        second = engine()
        self.assertEqual((second.score, second.pending_garbage), (0, 0))


class AppTests(unittest.TestCase):
    # Cria uma aplicação simulada e sua sessão para os testes.
    def make_app(self):
        fake = FakeSession()
        app = App("simulated", "Jogador", engine=engine(), session=fake)
        app.start()
        return app, fake

    # Conduz a aplicação de teste até o início autorizado do jogo.
    def playing(self):
        app, fake = self.make_app()
        fake.inject(OpponentDefined("Outro"))
        app.update()
        app.ready()
        fake.inject(StartAuthorized())
        app.update()
        return app, fake

    # Confere que a prontidão não inicia a física.
    def test_readiness_does_not_start_physics(self):
        app, fake = self.make_app()
        self.assertEqual(app.state, State.WAITING)
        app.action("drop")
        self.assertIsNone(app.engine.active)
        fake.inject(OpponentDefined("Outro"))
        app.update()
        self.assertEqual(app.state, State.PREPARING)
        app.ready()
        app.ready()
        self.assertEqual(app.state, State.READY)
        self.assertFalse(app.engine.running)
        self.assertEqual(sum(isinstance(e, ReadyOffered) for e in fake.outgoing), 1)
        fake.inject(StartAuthorized())
        app.update()
        self.assertEqual(app.state, State.PLAYING)
        self.assertIsInstance(fake.outgoing[-1], BoardOffered)

    # Confere que as entradas remotas não são retransmitidas.
    def test_remote_inputs_are_not_echoed(self):
        app, fake = self.playing()
        before = len(fake.outgoing)
        board = app.engine.snapshot()
        fake.inject(BoardReceived(board), AttackReceived(2))
        app.update()
        self.assertEqual(app.remote_board, board)
        self.assertEqual(app.engine.pending_garbage, 2)
        self.assertEqual(len(fake.outgoing), before)

    # Confere que a derrota aguarda o resultado e mantém as consultas à sessão.
    def test_ko_waits_for_result_and_keeps_polling(self):
        app, fake = self.playing()
        app.engine.board[0][0] = 8
        app.engine.receive_garbage(1)
        app.action("drop")
        self.assertEqual(app.state, State.AWAITING_RESULT)
        self.assertIsInstance(fake.outgoing[-1], DefeatOffered)
        fake.inject(MatchResult(Result.LOSE, EndReason.KO))
        app.update()
        self.assertEqual(app.state, State.FINISHED)
        self.assertEqual(app.result.result, Result.LOSE)

    # Confere que o resultado para o motor ativo e descarta os eventos posteriores.
    def test_result_stops_alive_engine_and_discards_later_events(self):
        app, fake = self.playing()
        fake.inject(MatchResult(Result.WIN, EndReason.KO), AttackReceived(4))
        app.update()
        self.assertFalse(app.engine.running)
        self.assertEqual(app.engine.pending_garbage, 0)
        self.assertTrue(fake.closed)

    # Confere o cancelamento antes do início.
    def test_cancel_before_start(self):
        app, fake = self.make_app()
        fake.simulate_cancel()
        app.update()
        self.assertEqual(app.result.result, Result.CANCEL)
        self.assertEqual(app.state, State.FINISHED)

    # Confere que a desconexão não produz um resultado inventado.
    def test_disconnect_has_no_invented_result(self):
        app, fake = self.playing()
        fake.simulate_disconnect()
        app.update()
        self.assertEqual(app.state, State.INTERRUPTED)
        self.assertIsNone(app.result)
        self.assertIn("resultado não confirmado", app.notice)

    # Confere que o limite de lixo fecha a sessão sem informar derrota.
    def test_garbage_limit_closes_session_without_ko(self):
        app, fake = self.playing()
        for _ in range(10):
            app.engine.receive_garbage(4)
        fake.inject(AttackReceived(1))
        app.update()
        self.assertEqual(app.state, State.INTERRUPTED)
        self.assertTrue(fake.closed)
        self.assertIsNone(app.engine.loss)
        self.assertFalse(any(isinstance(e, DefeatOffered) for e in fake.outgoing))

    # Confere que a aplicação preserva a ordem de ataque, tabuleiro e derrota.
    def test_app_preserves_attack_board_ko_order(self):
        app, fake = self.playing()
        game = app.engine
        game.active = Piece(PieceKind.I, 2, 16, ((2, 0), (2, 1), (2, 2), (2, 3)))
        for y in (18, 19):
            game.board[y] = [8] * 10
            game.board[y][4] = 0
        game.board[0][0] = 8
        game.receive_garbage(4)
        app.action("drop")
        self.assertEqual([type(e) for e in fake.outgoing[-3:]],
                         [AttackOffered, BoardOffered, DefeatOffered])

    # Confere que a pausa é apenas local e reinicia o relógio.
    def test_pause_is_only_local_and_resets_clock(self):
        clock = Clock()
        app = App("local", "Treino", engine=engine(clock))
        app.start()
        app.action("pause")
        clock.now = 20
        app.update()
        self.assertEqual(app.engine.active.y, 0)
        app.action("pause")
        app.update()
        self.assertEqual(app.engine.active.y, 0)
        simulated, _ = self.playing()
        simulated.action("pause")
        self.assertFalse(simulated.paused)

    # Confere que a demonstração executa espera, partida, prontidão, início, tabuleiro, ataque e resultado.
    def test_demo_runs_wait_match_ready_go_board_attack_result(self):
        fake = FakeSession(demo=True)
        app = App("simulated", "Demo", engine=engine(), session=fake)
        app.start()
        app.update()
        self.assertEqual(app.state, State.WAITING)
        app.update()
        self.assertEqual(app.state, State.PREPARING)
        app.ready()
        app.update()
        self.assertEqual(app.state, State.READY)
        app.update()
        self.assertEqual(app.state, State.PLAYING)
        app.update()
        self.assertIsNotNone(app.remote_board)
        for _ in range(4):
            fake.offer_board(app.engine.snapshot())
        app.update()
        self.assertEqual(app.engine.pending_garbage, 1)
        fake.defeat(LossReason.SPAWN)
        app.update()
        self.assertEqual(app.result.result, Result.LOSE)


class BoundaryTests(unittest.TestCase):
    # Confere que existem exatamente oito tipos de mensagem.
    def test_exactly_eight_message_types(self):
        self.assertEqual(len(MessageType), 8)

    def test_network_and_protocol_are_pending_without_fake_fallback(self):
        for call in (lambda: protocol.encode(MessageType.KEEPALIVE, ()),
                     lambda: protocol.parse(b"TVP/1|KEEPALIVE\n"),
                     lambda: protocol.Framer().feed(b"data")):
            with self.assertRaisesRegex(NotImplementedError, r"TODO\[EP-REDE\]"):
                call()
        session = NetworkSession()
        with self.assertRaisesRegex(NotImplementedError, r"TODO\[EP-REDE\]"):
            session.start("Ana")
        self.assertIsNone(session._thread)
        self.assertEqual(session.poll(), [])
        session.close()
        session.close()

    # Confere a validação do apelido e do retrato do tabuleiro.
    def test_nickname_and_snapshot_validation(self):
        for nickname in ("", "nome com espaço", "á", "x" * 21):
            with self.assertRaises(ValueError):
                App("local", nickname)
        with self.assertRaises(ValueError):
            BoardSnapshot(((0,),))


if __name__ == "__main__":
    unittest.main()
