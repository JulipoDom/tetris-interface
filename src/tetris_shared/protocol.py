"""Pontos de implementação da codificação e delimitação TVP/1 para a equipe.

A gramática está em 00-contexto-geral.md, seção 7. Nenhuma mensagem é
serializada, interpretada ou delimitada nesta etapa.
"""

from .models import MessageType


# Validar os campos e produzir ASCII com prefixo TVP/1 e LF final.
def encode(message_type: MessageType, fields: tuple[str, ...]) -> bytes:
    raise NotImplementedError("TODO[EP-REDE]: validar e serializar TVP/1 em ASCII")


# Validar uma linha e devolver tipo e campos; direção/estado ficam no adaptador.
def parse(line: bytes) -> tuple[MessageType, tuple[str, ...]]:
    raise NotImplementedError("TODO[EP-REDE]: validar sintaxe e campos TVP/1")


class Framer:
    # Acumular fragmentos, separar todas as linhas LF e limitar cada linha a 512 bytes.
    def feed(self, data: bytes) -> list[bytes]:
        raise NotImplementedError("TODO[EP-REDE]: acumular bytes, separar LF e limitar linhas")
