import curses
import random
import unittest
from unittest.mock import patch

from tetris_client import ui
from tetris_client.app import App, State
from tetris_client.engine import Engine, Piece, SHAPES
from tetris_client.session import BoardOffered, DefeatOffered, FakeSession
from tetris_shared.models import BoardProduced, LocalDefeat, LossReason, PieceKind
from tests.test_menu_and_delay import Clock, Screen


class HoldTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.game = Engine(clock=self.clock, piece_rng=random.Random(7))
        self.game.next_kind = PieceKind.T
        self.game.start()

    def test_first_hold_consumes_next_piece_without_fixing_or_applying_garbage(self):
        next_kind = self.game.next_kind
        self.game.receive_garbage(2)
        before = self.game.snapshot()
        self.assertEqual(self.game.hold(), [])
        self.assertEqual(self.game.held_kind, PieceKind.T)
        self.assertEqual(self.game.active.kind, next_kind)
        self.assertNotEqual(self.game.next_kind, next_kind)
        self.assertEqual(self.game.snapshot(), before)
        self.assertEqual((self.game.score, self.game.pending_garbage), (0, 2))

    def test_hold_is_limited_until_a_lock_and_swap_preserves_queue(self):
        self.game.move(1)
        self.game.rotate()
        self.game.hold()
        active, next_kind = self.game.active, self.game.next_kind
        self.assertEqual(self.game.hold(), [])
        self.assertEqual((self.game.active, self.game.next_kind), (active, next_kind))
        self.game.hard_drop()
        replaced, next_kind = self.game.active.kind, self.game.next_kind
        self.game.move(1)
        self.game.rotate()
        self.game.hold()
        self.assertEqual(self.game.held_kind, replaced)
        self.assertEqual(self.game.active, Piece(PieceKind.T, 3, 0, SHAPES[PieceKind.T][1]))
        self.assertEqual(self.game.next_kind, next_kind)
        active = self.game.active
        self.game.hold()
        self.assertEqual(self.game.active, active)

    def test_hold_is_disabled_before_start_during_pause_and_after_stop(self):
        idle = Engine(clock=self.clock)
        self.assertEqual(idle.hold(), [])
        self.assertIsNone(idle.held_kind)
        active = self.game.active
        self.game.pause()
        self.game.hold()
        self.assertEqual(self.game.active, active)
        self.assertIsNone(self.game.held_kind)
        self.game.resume()
        self.game.stop()
        self.game.hold()
        self.assertEqual(self.game.active, active)
        self.assertIsNone(self.game.held_kind)

    def test_hold_resets_gravity_and_ground_deadline_for_replacement(self):
        self.game.active = Piece(PieceKind.T, 3, 18, SHAPES[PieceKind.T][1])
        self.game.soft_drop()
        self.clock.now = 0.79
        self.game.hold()
        self.clock.now = 0.8
        self.assertEqual(self.game.tick(), [])
        self.assertEqual(self.game.active.y, 0)
        self.clock.now = 1.49
        self.game.tick()
        self.assertEqual(self.game.active.y, 1)

    def test_blocked_hold_reports_board_then_single_spawn_defeat(self):
        for occupied_reserve in (False, True):
            with self.subTest(occupied_reserve=occupied_reserve):
                game = Engine(clock=self.clock, piece_rng=random.Random(7))
                game.next_kind = PieceKind.T
                game.start()
                if occupied_reserve:
                    game.hold()
                    game.hard_drop()
                game.active = Piece(PieceKind.O, 0, 18, SHAPES[PieceKind.O][1])
                game.board[0] = [8] * 10
                game.board[1] = [8] * 10
                before = game.snapshot()
                events = game.hold()
                self.assertEqual(events, [BoardProduced(before), LocalDefeat(LossReason.SPAWN)])
                self.assertFalse(game.running)
                self.assertIsNone(game.active)
                self.assertEqual(game.hold(), [])
                self.assertEqual(game.tick(), [])

    def test_app_publishes_hold_defeat_and_waits_for_result(self):
        fake = FakeSession()
        app = App('simulated', 'Ana', engine=self.game, session=fake)
        app.state = State.PLAYING
        app.action('hold')
        self.assertEqual(fake.outgoing, [])
        self.game.hard_drop()
        self.game.board[0] = [8] * 10
        self.game.board[1] = [8] * 10
        app.action('hold')
        self.assertEqual(app.state, State.AWAITING_RESULT)
        self.assertEqual(fake.outgoing, [BoardOffered(self.game.snapshot()), DefeatOffered(LossReason.SPAWN)])
        self.assertFalse(fake.closed)

    def test_local_hold_defeat_finishes_training(self):
        app = App('local', 'Ana', engine=self.game)
        app.start()
        self.game.board[0] = [8] * 10
        self.game.board[1] = [8] * 10
        app.action('hold')
        self.assertEqual(app.state, State.FINISHED)
        self.assertEqual(app.notice, 'Fim do treino')


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.game = Engine(clock=self.clock)
        self.game.start()
        self.game.active = Piece(PieceKind.T, 3, 0, SHAPES[PieceKind.T][1])

    def test_clockwise_counterclockwise_and_half_turn(self):
        initial = self.game.active
        for turns, expected in (
            (1, ((2, 1), (1, 0), (1, 1), (1, 2))),
            (-1, ((0, 1), (1, 2), (1, 1), (1, 0))),
            (2, ((1, 2), (2, 1), (1, 1), (0, 1))),
        ):
            with self.subTest(turns=turns):
                self.game.active = initial
                self.game.rotate(turns)
                self.assertEqual(self.game.active.cells, expected)
                self.game.rotate(-turns)
                self.assertEqual(self.game.active, initial)

    def test_half_turn_checks_destination_without_intermediate_collision(self):
        self.game.board[0][4] = 8  # Ocupa só o giro intermediário de 90 graus.
        self.game.rotate(2)
        self.assertEqual(self.game.active.cells, ((1, 2), (2, 1), (1, 1), (0, 1)))

    def test_rotations_reject_collisions_and_bounds_without_wall_kicks(self):
        for turns in (-1, 1, 2):
            with self.subTest(turns=turns):
                initial = Piece(PieceKind.T, 3, 0, SHAPES[PieceKind.T][1])
                self.game.active = initial
                self.game.board[2][4] = 8
                self.game.rotate(turns)
                self.assertEqual(self.game.active, initial)
                self.game.board[2][4] = 0
                floor_piece = Piece(PieceKind.T, 3, 18, SHAPES[PieceKind.T][1])
                self.game.active = floor_piece
                self.game.rotate(turns)
                self.assertEqual(self.game.active, floor_piece)

    def test_o_is_unchanged_and_paused_or_stopped_game_cannot_rotate(self):
        self.game.active = Piece(PieceKind.O, 4, 0, SHAPES[PieceKind.O][1])
        initial = self.game.active
        for turns in (-1, 1, 2):
            self.game.rotate(turns)
            self.assertEqual(self.game.active, initial)
        self.game.active = Piece(PieceKind.T, 3, 0, SHAPES[PieceKind.T][1])
        initial = self.game.active
        self.game.pause()
        self.game.rotate(-1)
        self.assertEqual(self.game.active, initial)
        self.game.resume()
        self.game.stop()
        self.game.rotate(2)
        self.assertEqual(self.game.active, initial)

    def test_new_rotations_preserve_grounded_lock_deadline(self):
        self.game.active = Piece(PieceKind.T, 3, 17, ((2, 1), (1, 0), (1, 1), (1, 2)))
        self.game.soft_drop()
        self.clock.now = 0.5
        self.game.rotate(-1)
        self.game.rotate(2)
        self.clock.now = 0.8
        self.assertTrue(any(isinstance(event, BoardProduced) for event in self.game.tick()))


class SevenBagTests(unittest.TestCase):
    def test_many_bags_have_all_seven_pieces_and_no_three_equal_draws(self):
        for seed in range(10):
            game = Engine(clock=Clock(), piece_rng=random.Random(seed))
            pieces = [game.next_kind] + [game._draw() for _ in range(699)]
            for start in range(0, 700, 7):
                self.assertCountEqual(pieces[start:start + 7], list(PieceKind))
            self.assertTrue(all(a != b or b != c for a, b, c in zip(pieces, pieces[1:], pieces[2:])))
            self.assertGreater(len({tuple(pieces[i:i + 7]) for i in range(0, 700, 7)}), 1)


class Terminal(Screen):
    def __init__(self, keys):
        super().__init__(keys)
        self.frames = []

    def keypad(self, enabled):
        pass

    def timeout(self, milliseconds):
        pass

    def refresh(self):
        self.frames.append(tuple(self.lines))


class ControlsTests(unittest.TestCase):
    def run_ui(self, keys, mode='local'):
        screen = Terminal(keys)
        apps = []

        def make_app(mode, nickname, session):
            game = Engine(clock=Clock(), piece_rng=random.Random(7))
            game.next_kind = PieceKind.T
            app = App(mode, nickname, engine=game, session=session)
            apps.append(app)
            return app

        with (
            patch.object(ui, 'App', side_effect=make_app),
            patch.object(ui, '_palette', return_value={i: 0 for i in range(9)}),
            patch.object(ui.curses, 'curs_set'),
        ):
            ui._run(screen, mode, 'Ana')
        return apps[0], screen

    def test_z_x_a_and_up_rotate_real_piece(self):
        for key, cells in (
            ('z', ((0, 1), (1, 2), (1, 1), (1, 0))),
            ('Z', ((0, 1), (1, 2), (1, 1), (1, 0))),
            ('x', ((2, 1), (1, 0), (1, 1), (1, 2))),
            ('X', ((2, 1), (1, 0), (1, 1), (1, 2))),
            ('a', ((1, 2), (2, 1), (1, 1), (0, 1))),
            ('A', ((1, 2), (2, 1), (1, 1), (0, 1))),
            (curses.KEY_UP, ((2, 1), (1, 0), (1, 1), (1, 2))),
        ):
            with self.subTest(key=key):
                app, _ = self.run_ui([ord(key) if isinstance(key, str) else key, ord('q')])
                self.assertEqual(app.engine.active.cells, cells)

    def test_c_holds_and_ui_draws_reserve(self):
        for key in ('c', 'C'):
            app, screen = self.run_ui([ord(key), ord('q')])
            self.assertEqual(app.engine.held_kind, PieceKind.T)
            self.assertTrue(any('Guardada: vazia' in text for _, _, text in screen.frames[0]))
            lines = screen.frames[-1]
            self.assertTrue(any('Guardada: T' in text for _, _, text in lines))
            self.assertTrue(any(y >= 17 and x >= 53 and text == '[]' for y, x, text in lines))

    def test_simulation_c_holds_while_b_cancels(self):
        for key, state in (('c', State.PLAYING), ('C', State.PLAYING), ('b', State.FINISHED)):
            app, _ = self.run_ui([-1, 10, -1, -1, ord(key), ord('q')], mode='simulated')
            self.assertEqual(app.state, state)
            if state == State.PLAYING:
                self.assertEqual(app.engine.held_kind, PieceKind.T)
                self.assertIsNone(app.result)


if __name__ == '__main__':
    unittest.main()
