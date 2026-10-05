import unittest

from tetris_shared.models import MessageType
from tetris_shared.protocol import Framer, encode, parse


class ProtocolStubTests(unittest.TestCase):
    def test_encoder_remains_for_student_implementation(self):
        with self.assertRaisesRegex(NotImplementedError, r"TODO\[EP-REDE\]"):
            encode(MessageType.KEEPALIVE, ())

    def test_parser_remains_for_student_implementation(self):
        with self.assertRaisesRegex(NotImplementedError, r"TODO\[EP-REDE\]"):
            parse(b"TVP/1|KEEPALIVE\n")

    def test_framing_remains_for_student_implementation(self):
        with self.assertRaisesRegex(NotImplementedError, r"TODO\[EP-REDE\]"):
            Framer().feed(b"TVP/1|KEEPALIVE\n")
