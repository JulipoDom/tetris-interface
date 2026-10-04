"""TVP/1 reservado para a equipe; catálogo em models.MessageType.

Sem codec funcional nesta etapa. Especificação: 00-contexto-geral.md, seção 7.
"""

from .models import MessageType


# Pendente: validar os campos e gerar uma mensagem ASCII terminada em LF.
def encode(message_type: MessageType, fields: tuple[str, ...]) -> bytes:
    raise NotImplementedError("TODO[EP-REDE]: validar e serializar TVP/1 em ASCII")


# Pendente: validar uma linha TVP/1 e retornar seu tipo e campos.
def parse(line: bytes) -> tuple[MessageType, tuple[str, ...]]:
    raise NotImplementedError("TODO[EP-REDE]: validar sintaxe, campos e direção")


class Framer:
    # Pendente: separar linhas completas e preservar o fragmento TCP restante.
    def feed(self, data: bytes) -> list[bytes]:
        raise NotImplementedError("TODO[EP-REDE]: acumular bytes, separar LF e limitar linhas")
