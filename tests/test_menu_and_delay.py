import curses
import random
import unittest

from tetris_client.app import App
from tetris_client.engine import Engine, Piece, SHAPES
from tetris_client.session import FakeSession, HelloOffered
from tetris_client.ui import _menu, _render
from tetris_shared.models import BoardProduced, OpponentDefined, PieceKind


class Clock:
    # Cria um relógio controlado pelo teste.
    def __init__(self):
        self.now = 0.0

    # Retorna o instante configurado sem consultar o relógio real.
    def __call__(self):
        return self.now


class Screen:
    """Substitui apenas o terminal externo; executa a UI real."""

    # Prepara teclas simuladas e um registro do desenho do terminal.
    def __init__(self, keys=()):
        self.keys = iter(keys)
        self.lines = []

    # Fornece o tamanho de um terminal suficiente para os testes.
    def getmaxyx(self):
        return 28, 80

    # Limpa o desenho anterior para verificar o próximo quadro.
    def erase(self):
        self.lines.clear()

    # Registra o texto que a interface enviaria ao terminal.
    def addnstr(self, y, x, text, limit, attr):
        self.lines.append((y, x, text[:limit]))

    # Finaliza um quadro de teste sem acessar um terminal real.
    def refresh(self):
        pass

    # Entrega a próxima tecla preparada para o teste do menu.
    def getch(self):
        return next(self.keys)


class LockDelayTests(unittest.TestCase):
    # Prepara uma peça apoiada e um relógio controlado para cada teste.
    def setUp(self):
        self.clock = Clock()
        self.game = Engine(clock=self.clock, piece_rng=random.Random(7))
        self.game.start()
        self.game.active = Piece(PieceKind.T, 3, 17, ((2, 1), (1, 0), (1, 1), (1, 2)))

    # Checks that collision allows rotation before locking.
    def test_collision_allows_rotation_before_locking(self):
        piece = self.game.active
        self.assertEqual(self.game.soft_drop(), [])
        self.assertIs(self.game.active, piece)
        self.game.move(1)
        self.game.rotate()
        self.assertNotEqual(self.game.active.cells, piece.cells)
        self.assertFalse(any(any(row) for row in self.game.board))
        self.clock.now = 0.799
        self.assertEqual(self.game.tick(), [])
        self.clock.now = 0.8
        self.assertTrue(any(isinstance(e, BoardProduced) for e in self.game.tick()))

    # Checks that repeated moves and down do not extend lock deadline.
    def test_repeated_moves_and_down_do_not_extend_lock_deadline(self):
        self.game.soft_drop()
        for instant in (0.1, 0.3, 0.6, 0.79):
            self.clock.now = instant
            self.game.move(1)
            self.game.move(-1)
            self.game.soft_drop()
        self.clock.now = 0.8
        self.assertTrue(any(isinstance(e, BoardProduced) for e in self.game.tick()))

    # Checks that delay shortens after thirty seconds of play.
    def test_delay_shortens_after_thirty_seconds_of_play(self):
        self.clock.now = 30
        self.game.soft_drop()
        self.clock.now = 30.749
        self.assertEqual(self.game.tick(), [])
        self.clock.now = 30.75
        self.assertTrue(any(isinstance(e, BoardProduced) for e in self.game.tick()))

    # Checks that delay never falls below two hundred ms.
    def test_delay_never_falls_below_two_hundred_ms(self):
        self.clock.now = 3600
        self.game.soft_drop()
        self.clock.now = 3600.199
        self.assertEqual(self.game.tick(), [])
        self.clock.now = 3600.2
        self.assertTrue(any(isinstance(e, BoardProduced) for e in self.game.tick()))

    # Checks that pause preserves remaining lock time.
    def test_pause_preserves_remaining_lock_time(self):
        app = App("local", "Ana", engine=self.game)
        app.start()
        self.game.soft_drop()
        self.clock.now = 0.3
        app.action("pause")
        self.clock.now = 100
        app.update()
        app.action("pause")
        self.clock.now = 100.499
        app.update()
        self.assertFalse(any(any(row) for row in self.game.board))
        self.clock.now = 100.5
        app.update()
        self.assertTrue(any(any(row) for row in self.game.board))

    # Checks that landing starts delay before next gravity step.
    def test_landing_starts_delay_before_next_gravity_step(self):
        self.game.active = Piece(PieceKind.O, 4, 17, SHAPES[PieceKind.O][1])
        self.game.soft_drop()
        self.clock.now = 0.7
        self.assertEqual(self.game.tick(), [])
        self.clock.now = 0.8
        self.assertTrue(any(isinstance(e, BoardProduced) for e in self.game.tick()))

    # Checks that hard drop remains immediate.
    def test_hard_drop_remains_immediate(self):
        events = self.game.hard_drop()
        self.assertTrue(any(isinstance(e, BoardProduced) for e in events))
        self.assertEqual(self.clock.now, 0)

    # Checks that new piece gets its own lock timer.
    def test_new_piece_gets_its_own_lock_timer(self):
        self.game.soft_drop()
        self.clock.now = 0.8
        self.game.tick()
        self.game.active = Piece(PieceKind.O, 0, 18, SHAPES[PieceKind.O][1])
        self.assertEqual(self.game.soft_drop(), [])
        self.clock.now = 1.599
        self.assertEqual(self.game.tick(), [])
        self.clock.now = 1.6
        self.assertTrue(any(isinstance(e, BoardProduced) for e in self.game.tick()))

    # Checks that waiting and pause do not increase difficulty.
    def test_waiting_and_pause_do_not_increase_difficulty(self):
        clock = Clock()
        game = Engine(clock=clock)
        clock.now = 120
        app = App("local", "Ana", engine=game)
        app.start()
        app.action("pause")
        clock.now = 3600
        app.action("pause")
        game.active = Piece(PieceKind.O, 4, 18, SHAPES[PieceKind.O][1])
        game.soft_drop()
        clock.now = 3600.799
        app.update()
        self.assertFalse(any(any(row) for row in game.board))
        clock.now = 3600.8
        app.update()
        self.assertTrue(any(any(row) for row in game.board))

    # Checks that expired deadline does not lock an airborne piece.
    def test_expired_deadline_does_not_lock_an_airborne_piece(self):
        self.game.active = Piece(PieceKind.O, 4, 16, SHAPES[PieceKind.O][1])
        self.game.board[18][4] = 8
        self.game.soft_drop()
        self.game.move(2)
        self.clock.now = 0.8
        self.assertEqual(self.game.tick(), [])
        self.assertEqual(self.game.active.y, 17)
        self.game.soft_drop()
        self.assertTrue(any(isinstance(e, BoardProduced) for e in self.game.tick()))


class MenuAndNameTests(unittest.TestCase):
    # Confere que esperar pela partida não reduz o atraso exibido na tela.
    def test_waiting_screen_keeps_initial_lock_delay(self):
        clock = Clock()
        app = App("simulated", "Ana", engine=Engine(clock=clock), session=FakeSession())
        app.start()
        clock.now = 120
        screen = Screen()
        _render(screen, app, {i: 0 for i in range(9)})
        self.assertIn((8, 53, "Fixação: 800 ms"), screen.lines)

    # Checks that menu offers practice and multiplayer.
    def test_menu_offers_practice_and_multiplayer(self):
        screen = Screen((curses.KEY_DOWN, 10))
        self.assertEqual(_menu(screen, "Ana"), ("network", "Ana"))
        labels = [text for _, _, text in screen.lines]
        self.assertTrue(any("Prática" in label for label in labels))
        self.assertTrue(any("Multiplayer" in label for label in labels))
        self.assertFalse(any("Simulação" in label for label in labels))

    # Checks that chosen menu name reaches hello and player header.
    def test_chosen_menu_name_reaches_hello_and_player_header(self):
        screen = Screen((*[127] * 7, *map(ord, "Ana_42"), 10))
        mode, name = _menu(screen, "Jogador")
        fake = FakeSession()
        app = App("simulated", name, session=fake)
        app.start()
        self.assertEqual(fake.outgoing[0], HelloOffered("Ana_42"))
        _render(screen, app, {i: 0 for i in range(9)})
        self.assertIn((3, 2, "Você: Ana_42"), screen.lines)

    # Checks that opponent header waits for match name.
    def test_opponent_header_waits_for_match_name(self):
        screen = Screen()
        fake = FakeSession()
        app = App("simulated", "Ana", session=fake)
        app.start()
        _render(screen, app, {i: 0 for i in range(9)})
        self.assertIn((3, 28, "Aguardando jogador"), screen.lines)
        fake.inject(OpponentDefined("Bruno"))
        app.update()
        _render(screen, app, {i: 0 for i in range(9)})
        self.assertIn((3, 28, "Bruno"), screen.lines)


if __name__ == "__main__":
    unittest.main()
