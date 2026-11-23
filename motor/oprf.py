"""Token de conta por OPRF: corrige o ataque de dicionário da chave HMAC compartilhada.

Problema da versão anterior: todos os membros tinham a mesma chave HMAC. Um membro mal-intencionado
podia calcular o token de qualquer CPF ou conta, comparar com o que o hub devolve e descobrir quem
os outros membros consideram suspeito.

Agora o token é SHA-256( k · H(HMAC_m(conta)) ), um ponto da curva, com duas chaves separadas:
- m, dos membros: o hub não tem, então não consegue testar contas sozinho;
- k, do hub: os membros não têm, então não calculam token nenhum sem pedir ao hub.
O membro manda r · H(HMAC_m(conta)), cego por um r aleatório; o hub multiplica por k sem ver a
entrada; o membro tira o r. O hub conta os pedidos de cada membro por rodada: um membro que pede milhares de
tokens a mais do que tem de clientes está tentando um ataque de dicionário e aparece no registro.
Limite que sobra: membro e hub juntos (conluio) conseguem testar contas.

Curva: Ed25519 (libsodium, via PyNaCl), protocolo 2HashDH. A entrada vai para a curva por tentativa e
incremento: o hash só é aceito quando cai num ponto válido do subgrupo principal, então ninguém
conhece o logaritmo discreto dele. Esse passo não é de tempo constante; como a entrada já é um HMAC
com chave secreta, o vazamento por tempo não revela a conta.
"""

import hashlib
import hmac
import secrets
from collections import Counter

from nacl import bindings as nb


def _escalar() -> bytes:
    return nb.crypto_core_ed25519_scalar_reduce(secrets.token_bytes(64))


def _para_curva(dado: bytes) -> bytes:
    """Hash para um ponto do subgrupo principal de Ed25519, por tentativa e incremento."""
    for i in range(1000):
        y = hashlib.sha512(i.to_bytes(2, "big") + dado).digest()[:32]
        if nb.crypto_core_ed25519_is_valid_point(y):
            return y
    raise ValueError("hash não caiu na curva em 1000 tentativas")


class Hub:
    """Guarda k. Só vê elementos cegos; não vê conta, CPF nem o HMAC dos membros."""

    def __init__(self, k: bytes | None = None):
        self._k = k if k is not None else _escalar()
        self.pedidos = Counter()  # membro -> quantos tokens pediu nesta rodada

    def avaliar(self, membro: str, cegos: list[bytes]) -> list[bytes]:
        self.pedidos[membro] += len(cegos)
        for a in cegos:
            if not nb.crypto_core_ed25519_is_valid_point(a):
                raise ValueError("ponto inválido recebido")
        return [nb.crypto_scalarmult_ed25519_noclamp(self._k, a) for a in cegos]

    def suspeitos_de_dicionario(self, clientes_por_membro: dict[str, int], folga: float = 2.0) -> list[str]:
        """Membros que pediram mais tokens do que `folga` vezes o número de clientes que declararam."""
        return [m for m, n in self.pedidos.items() if n > folga * clientes_por_membro.get(m, 0)]


class Membro:
    """Guarda m (compartilhada só entre membros). Cega antes de mandar ao hub."""

    def __init__(self, nome: str, chave_membros: bytes):
        self.nome = nome
        self._m = chave_membros

    def cegar(self, contas: list[str]) -> tuple[list[bytes], list[bytes]]:
        rs = [_escalar() for _ in contas]
        cegos = [nb.crypto_scalarmult_ed25519_noclamp(r, _para_curva(hmac.new(self._m, str(c).encode(), hashlib.sha256).digest()))
                 for c, r in zip(contas, rs)]
        return cegos, rs

    @staticmethod
    def descegar(avaliados: list[bytes], rs: list[bytes]) -> list[str]:
        return [hashlib.sha256(nb.crypto_scalarmult_ed25519_noclamp(nb.crypto_core_ed25519_scalar_invert(r), b)).hexdigest()[:16]
                for b, r in zip(avaliados, rs)]

    def tokenizar(self, contas: list[str], hub: Hub) -> list[str]:
        cegos, rs = self.cegar(contas)
        return self.descegar(hub.avaliar(self.nome, cegos), rs)


def token_direto(conta: str, chave_membros: bytes, k: bytes) -> str:
    """Token calculado por quem tem as duas chaves. Só a avaliação da simulação faz isso, para conferir
    o resultado com o gabarito; no protocolo real ninguém tem m e k ao mesmo tempo."""
    h = _para_curva(hmac.new(chave_membros, str(conta).encode(), hashlib.sha256).digest())
    return hashlib.sha256(nb.crypto_scalarmult_ed25519_noclamp(k, h)).hexdigest()[:16]
