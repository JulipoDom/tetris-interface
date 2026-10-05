import contextlib
import curses
import io
import unittest
from unittest.mock import patch

from tetris_client.__main__ import main
from tetris_client.ui import _run
from tests.test_menu_and_delay import Screen


class GameScreen(Screen):
    def keypad(self, flag):
        pass

    def timeout(self, delay):
        pass


class EntryPointTests(unittest.TestCase):
    def test_cli_passes_server_to_ui_without_startup_connection(self):
        with patch('sys.argv', ['tetris_client', '--mode', 'network', '--host', 'server.test',
                                '--port', '9000', '--nickname', 'Ana']), \
             patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=True), \
             patch('tetris_client.ui.run') as run, \
             patch('tetris_client.network.NetworkSession.start') as start:
            self.assertEqual(main(), 0)
            run.assert_called_once_with('network', 'Ana', host='server.test', port=9000)
            start.assert_not_called()

    def test_invalid_port_is_argument_error(self):
        for port in ('0', '65536', '-1'):
            with self.subTest(port=port), patch('sys.argv', ['tetris_client', '--port', port]), \
                 contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc:
                    main()
                self.assertEqual(exc.exception.code, 2)

    def test_menu_network_uses_endpoint_and_returns_to_menu_when_pending(self):
        screen = GameScreen((curses.KEY_DOWN, 10, 27))
        with patch('tetris_client.ui._palette', return_value={i: 0 for i in range(9)}), \
             patch('tetris_client.ui.curses.curs_set'), \
             patch('tetris_client.ui.NetworkSession') as factory:
            factory.return_value.start.side_effect = NotImplementedError("TODO[EP-REDE]: conectar")
            _run(screen, None, 'Ana', host='server.test', port=9000)
            factory.assert_called_once_with('server.test', 9000)
            factory.return_value.start.assert_called_once_with('Ana')
            factory.return_value.close.assert_called_once_with()
            self.assertTrue(any('indisponível' in text for _, _, text in screen.lines))

    def test_cli_reports_pending_network_with_nonzero_exit(self):
        with patch('sys.argv', ['tetris_client', '--mode', 'network']), \
             patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=True), \
             patch('tetris_client.ui.run', side_effect=NotImplementedError('TODO[EP-REDE]: conectar')), \
             contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(main(), 2)
            self.assertIn('TODO[EP-REDE]', output.getvalue())

    def test_explicit_network_mode_raises_stub_and_does_not_start_thread(self):
        screen = GameScreen()
        with patch('tetris_client.ui._palette', return_value={i: 0 for i in range(9)}), \
             patch('tetris_client.ui.curses.curs_set'), \
             patch('tetris_client.network.threading.Thread') as thread:
            with self.assertRaisesRegex(NotImplementedError, r'TODO\[EP-REDE\]'):
                _run(screen, 'network', 'Ana')
            thread.assert_not_called()
