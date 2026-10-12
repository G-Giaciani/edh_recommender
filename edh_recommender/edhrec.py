"""
Popularidade das cartas segundo o EDHREC.
"""

import re
import unicodedata

from edh_recommender.models import nome_da_frente


def _slug(nome: str) -> str:
    """'Lim-Dul the Necromancer' -> 'lim-dul-the-necromancer'."""
    nome = nome_da_frente(nome)
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9-]", "", nome.lower().replace(" ", "-"))