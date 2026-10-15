"""
Popularidade das cartas segundo o EDHREC.
"""

import json
import re
import unicodedata

import httpx

from edh_recommender.config import DATA_DIR, EDHREC_BASE, SCRYFALL_HEADERS
from edh_recommender.models import nome_da_frente

PASTA = DATA_DIR / "edhrec"


def _slug(nome: str) -> str:
    """'Lim-Dul the Necromancer' -> 'lim-dul-the-necromancer'."""
    nome = nome_da_frente(nome)
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9-]", "", nome.lower().replace(" ", "-"))

def _baixar(slug: str) -> dict | None:
    """O JSON do comandante, do disco ou da rede. None se ele nao existe la.
    """
    arquivo = PASTA / f"{slug}.json"
    if arquivo.exists():
        return json.loads(arquivo.read_text(encoding="utf-8"))

    resposta = httpx.get(f"{EDHREC_BASE}/{slug}.json", headers=SCRYFALL_HEADERS,
                         timeout=30, follow_redirects=True)
    if resposta.status_code != 200:
        return None

    PASTA.mkdir(parents=True, exist_ok=True)
    arquivo.write_bytes(resposta.content)
    return resposta.json()


def sinais(comandante: str) -> dict[str, tuple[float, float]]:
    """{nome da carta: (inclusion, synergy)}. Vazio se o comandante nao existir."""
    dados = _baixar(_slug(comandante))
    if dados is None:
        return {}

    sinais_por_carta = {}
    for lista_de_cartas in dados["container"]["json_dict"]["cardlists"]:
        for carta in lista_de_cartas["cardviews"]:
            decks_possiveis = carta["potential_decks"]
            inclusion = carta["num_decks"] / decks_possiveis if decks_possiveis else 0.0
            sinais_por_carta[carta["name"]] = (inclusion, carta["synergy"])
    return sinais_por_carta
