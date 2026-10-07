import errno
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import sys
import tempfile
import termios
import time
import unittest


class TestesTerminal(unittest.TestCase):
    def iniciar(self, *argumentos, tipo_terminal="xterm-256color"):
        diretorio = tempfile.TemporaryDirectory()
        self.addCleanup(diretorio.cleanup)
        self.mestre, escravo = pty.openpty()
        self.addCleanup(os.close, self.mestre)
        self.addCleanup(os.close, escravo)
        self.atributos_originais = termios.tcgetattr(escravo)
        termios.tcsetwinsize(self.mestre, (28, 80))
        ambiente = dict(os.environ, TERM=tipo_terminal, PYTHONUTF8="1",
                        PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
        self.processo = subprocess.Popen(
            [sys.executable, "-m", "tetris_client", *argumentos],
            stdin=escravo, stdout=escravo, stderr=escravo,
            cwd=diretorio.name, env=ambiente, start_new_session=True,
        )
        self.addCleanup(self.encerrar)
        self.saida = b""

    def encerrar(self):
        if self.processo.poll() is None:
            self.processo.kill()
        self.processo.wait(timeout=5)

    def aguardar(self, texto):
        esperado = texto.encode("utf-8")
        limite = time.monotonic() + 5
        while esperado not in self.saida and time.monotonic() < limite:
            disponiveis, _, _ = select.select([self.mestre], [], [], 0.05)
            if disponiveis:
                try:
                    trecho = os.read(self.mestre, 65536)
                except OSError as erro:
                    if erro.errno != errno.EIO:
                        raise
                    break
                if not trecho:
                    break
                self.saida += trecho
            elif self.processo.poll() is not None:
                break
        self.assertIn(esperado, self.saida, self.saida.decode("utf-8", errors="replace"))

    def enviar(self, teclas):
        self.saida = b""
        os.write(self.mestre, teclas)

    def conferir_saida(self, codigo=0):
        self.assertEqual(self.processo.wait(timeout=5), codigo)
        self.assertEqual(termios.tcgetattr(self.mestre), self.atributos_originais)

    def test_menu_edita_apelido_inicia_treino_e_restaura_terminal(self):
        self.iniciar("--nickname", "An")
        self.aguardar("Apelido: An")
        self.enviar(b"x\x7fa\n")
        self.aguardar("Ana")
        self.aguardar("TREINO LOCAL")
        self.enviar(b"p")
        self.aguardar("PAUSADO")
        self.enviar(b"p")
        self.aguardar("Jogando")
        self.enviar(b"q")
        self.conferir_saida()

    def test_redimensionamento_recupera_tela_e_aceita_saida(self):
        self.iniciar("--mode", "local")
        self.aguardar("Guardada: vazia")
        self.saida = b""
        termios.tcsetwinsize(self.mestre, (12, 40))
        self.processo.send_signal(signal.SIGWINCH)
        self.aguardar("Terminal pequeno")
        self.saida = b""
        termios.tcsetwinsize(self.mestre, (28, 80))
        self.processo.send_signal(signal.SIGWINCH)
        self.aguardar("Guardada: vazia")
        self.enviar(b"q")
        self.conferir_saida()

    def test_simulacao_autoriza_jogo_e_confirma_vitoria(self):
        self.iniciar("--mode", "simulated", "--nickname", "Ana")
        self.aguardar("SEM REDE")
        self.aguardar("Enter para ficar pronto")
        self.enviar(b"\n")
        self.aguardar("Jogando")
        self.enviar(b"v")
        self.aguardar("WIN / KO")
        self.enviar(b"q")
        self.conferir_saida()

    def test_simulacao_cancela_antes_do_inicio(self):
        self.iniciar("--mode", "simulated")
        self.aguardar("Enter para ficar pronto")
        self.enviar(b"b")
        self.aguardar("CANCEL / SERVER_STOP")
        self.enviar(b"q")
        self.conferir_saida()

    def test_simulacao_desconecta_sem_inventar_resultado(self):
        self.iniciar("--mode", "simulated")
        self.aguardar("Enter para ficar pronto")
        self.enviar(b"d")
        self.aguardar("resultado não confirmado")
        self.enviar(b"q")
        self.conferir_saida()

    def test_rede_pendente_restaura_terminal_e_retorna_dois(self):
        self.iniciar("--mode", "network")
        self.aguardar("TODO[EP-REDE]")
        self.conferir_saida(2)

    def test_multiplayer_retorna_menu_preservando_apelido(self):
        self.iniciar("--nickname", "Ana")
        self.aguardar("Apelido: Ana")
        self.enviar(b"\x1bOB\n")
        self.aguardar("Multiplayer indisponível")
        self.enviar(b"\n")
        self.aguardar("TREINO LOCAL")
        self.aguardar("Ana")
        self.enviar(b"q")
        self.conferir_saida()

    def test_interrupcao_restaura_terminal_monocromatico(self):
        self.iniciar("--mode", "local", tipo_terminal="vt100")
        self.aguardar("TREINO LOCAL")
        self.processo.send_signal(signal.SIGINT)
        self.conferir_saida()
