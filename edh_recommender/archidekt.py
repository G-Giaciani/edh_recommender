"""Decks reais do Archidekt, para a avaliacao do sistema."""

import json
import re

import httpx

from edh_recommender.config import (
    ARCHIDEKT_BASE,
    ARQUIVO_AMOSTRA,
    DATA_DIR,
    SCRYFALL_HEADERS,
)
from edh_recommender.models import Deck
from edh_recommender.scryfall import cartas_por_nome

PASTA = DATA_DIR / "decks"

CATEGORIA_COMANDANTE = "Commander"

LINK = re.compile(r"archidekt\.com/decks/(\d+)")


def ler_amostra(caminho=ARQUIVO_AMOSTRA) -> list[tuple[int, str]]:
    """[(id do deck, arquetipo), ...] lidos do arquivo da amostra."""
    arquetipo, decks = "", []
    for linha in open(caminho, encoding="utf-8"):
        if linha.startswith("## "):
            arquetipo = linha[3:].strip()
        link_encontrado = LINK.search(linha)
        if link_encontrado:
            decks.append((int(link_encontrado.group(1)), arquetipo))
    return decks


def baixar_deck(deck_id: int) -> dict:
    """O JSON do deck, do disco ou da rede."""
    arquivo = PASTA / f"{deck_id}.json"
    if arquivo.exists():
        return json.loads(arquivo.read_text(encoding="utf-8"))

    resposta = httpx.get(f"{ARCHIDEKT_BASE}/{deck_id}/", headers=SCRYFALL_HEADERS, timeout=30)
    resposta.raise_for_status()

    PASTA.mkdir(parents=True, exist_ok=True)
    arquivo.write_bytes(resposta.content)
    return resposta.json()


def _entradas_do_deck(dados: dict) -> list[dict]:
    """As entradas do deck, sem as que estao em categorias fora dele."""
    categorias_fora = {categoria["name"] for categoria in dados.get("categories") or []
                       if not categoria.get("includedInDeck")}
    return [entrada for entrada in dados["cards"]
            if not (set(entrada.get("categories") or []) & categorias_fora)]


def nomes_do_deck(dados: dict) -> tuple[list[str], str]:
    """(nomes das cartas, nome do comandante)."""
    entradas = _entradas_do_deck(dados)

    entradas_do_comandante = [entrada for entrada in entradas
                              if CATEGORIA_COMANDANTE in (entrada.get("categories") or [])]
    if len(entradas_do_comandante) != 1:
        raise ValueError(f"deck {dados.get('id')} tem {len(entradas_do_comandante)}"
                         f" comandantes, esperava 1")

    nomes = []
    for entrada in entradas:
        if entrada in entradas_do_comandante:
            continue
        nomes += [entrada["card"]["oracleCard"]["name"]] * entrada["quantity"]

    return nomes, entradas_do_comandante[0]["card"]["oracleCard"]["name"]


def carregar_deck(deck_id: int, conn) -> Deck:
    """O deck do Archidekt como objeto Deck, pronto para o algoritmo."""
    nomes, comandante = nomes_do_deck(baixar_deck(deck_id))

    cartas = cartas_por_nome([comandante] + nomes, conn)
    if comandante not in cartas:
        raise ValueError(f"comandante do deck {deck_id} nao encontrado no Scryfall:"
                         f" {comandante!r}")

    return Deck(name=str(deck_id),
                commander=cartas[comandante],
                cards=[cartas[nome] for nome in nomes if nome in cartas])
