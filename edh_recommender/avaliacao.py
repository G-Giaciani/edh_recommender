"""Avaliacao do sistema: esconder parte de um deck e ver quanto ele reconstroi."""

import csv
import random

from edh_recommender.archidekt import carregar_deck, ler_amostra
from edh_recommender.config import SEED
from edh_recommender.models import Deck
from edh_recommender.recomendador import (
    REFERENCIA,
    REFERENCIA_SENSIBILIDADE,
    candidatos,
    recomendar,
    sinais_por_carta,
)
from edh_recommender.tags import categorias


def esconder_cartas(deck: Deck, conn, seed: int = SEED, fracao: float = 1 / 3,
                    minimo: int = 4) -> tuple[Deck, set[str]]:
    """Esconde ~`fracao` das cartas de cada categoria. (deck parcial, escondidas)."""
    sorteio = random.Random(seed)

    cartas_por_categoria: dict[str, list] = {}
    for carta in deck.cards:
        for categoria in categorias(carta.oracle_id, conn):
            cartas_por_categoria.setdefault(categoria, []).append(carta)

    escondidas: set[str] = set()
    for categoria in sorted(cartas_por_categoria):
        cartas_da_categoria = cartas_por_categoria[categoria]
        if len(cartas_da_categoria) < minimo:
            continue
        quantas_esconder = max(1, int(len(cartas_da_categoria) * fracao))
        escondidas.update(carta.name for carta in
                          sorteio.sample(cartas_da_categoria, quantas_esconder))

    parcial = Deck(name=deck.name,
                   commander=deck.commander,
                   cards=[carta for carta in deck.cards if carta.name not in escondidas])
    return parcial, escondidas


def precisao_em_k(recomendadas: list[str], escondidas: set[str], k: int) -> float:
    """Dos k sugeridos, que fracao estava escondida."""
    if k <= 0:
        return 0.0
    return len([nome for nome in recomendadas[:k] if nome in escondidas]) / k


def revocacao_em_k(recomendadas: list[str], escondidas: set[str], k: int) -> float:
    """Das escondidas, que fracao apareceu nos k sugeridos."""
    if not escondidas:
        return 0.0
    return len(set(recomendadas[:k]) & escondidas) / len(escondidas)


def baseline(deck: Deck, conn, quantidade: int) -> list[str]:
    """O EDHREC como referencia: as cartas de maior taxa de inclusao."""
    sinais_edhrec = sinais_por_carta(deck.commander.name, conn)
    cartas_candidatas = candidatos(deck, sinais_edhrec, conn)
    ordenadas = sorted(cartas_candidatas,
                       key=lambda carta: (-sinais_edhrec.get(carta.name, (0, 0))[0], carta.name))
    return [carta.name for carta in ordenadas[:quantidade]]


def baseline_ingenuo(deck: Deck, conn, quantidade: int) -> list[str]:
    """A lista do EDHREC como ela aparece na pagina, sem olhar o deck."""
    sinais_edhrec = sinais_por_carta(deck.commander.name, conn)
    ordenadas = sorted(sinais_edhrec.items(), key=lambda item: (-item[1][0], item[0]))
    return [nome for nome, _sinais in ordenadas[:quantidade]]


PESOS = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
KS = [5, 10, 20]
PERFIS = {"principal": REFERENCIA, "sensibilidade": REFERENCIA_SENSIBILIDADE}
ARQUIVO_RESULTADOS = "resultados.csv"

COLUNAS = ["deck", "comandante", "arquetipo", "perfil", "peso", "k",
           "escondidas", "alcancaveis", "teto_revocacao", "candidatos",
           "precisao_sistema", "revocacao_sistema",
           "precisao_baseline", "revocacao_baseline",
           "precisao_ingenuo", "revocacao_ingenuo"]


def rodar(conn, saida: str = ARQUIVO_RESULTADOS) -> list[dict]:
    """Roda o experimento inteiro e grava o CSV. Devolve as linhas."""
    maior_k = max(KS)
    linhas = []

    for deck_id, arquetipo in ler_amostra():
        deck = carregar_deck(deck_id, conn)
        parcial, escondidas = esconder_cartas(deck, conn)

        sinais_edhrec = sinais_por_carta(deck.commander.name, conn)
        nomes_candidatos = {carta.name for carta in candidatos(parcial, sinais_edhrec, conn)}
        alcancaveis = escondidas & nomes_candidatos

        recomendadas_baseline = baseline(parcial, conn, maior_k)
        recomendadas_ingenuo = baseline_ingenuo(parcial, conn, maior_k)

        for nome_perfil, referencia in PERFIS.items():
            for peso in PESOS:
                recomendadas_sistema = [nome for nome, _nota in recomendar(
                    parcial, conn, peso=peso, quantidade=maior_k, referencia=referencia)]
                for k in KS:
                    linhas.append({
                        "deck": deck_id,
                        "comandante": deck.commander.name,
                        "arquetipo": arquetipo,
                        "perfil": nome_perfil,
                        "peso": peso,
                        "k": k,
                        "escondidas": len(escondidas),
                        "alcancaveis": len(alcancaveis),
                        "teto_revocacao": len(alcancaveis) / len(escondidas) if escondidas else 0.0,
                        "candidatos": len(nomes_candidatos),
                        "precisao_sistema": precisao_em_k(recomendadas_sistema, escondidas, k),
                        "revocacao_sistema": revocacao_em_k(recomendadas_sistema, escondidas, k),
                        "precisao_baseline": precisao_em_k(recomendadas_baseline, escondidas, k),
                        "revocacao_baseline": revocacao_em_k(recomendadas_baseline, escondidas, k),
                        "precisao_ingenuo": precisao_em_k(recomendadas_ingenuo, escondidas, k),
                        "revocacao_ingenuo": revocacao_em_k(recomendadas_ingenuo, escondidas, k),
                    })

    with open(saida, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        escritor.writeheader()
        escritor.writerows(linhas)
    return linhas


if __name__ == "__main__":
    from edh_recommender.db import get_conn

    resultado = rodar(get_conn())
    print(f"{len(resultado)} linhas gravadas em {ARQUIVO_RESULTADOS}")
