"""
Busca de cartas no Scryfall, com cache no banco.
"""
import time

import httpx

from edh_recommender.config import SCRYFALL_BASE, SCRYFALL_HEADERS
from edh_recommender.models import Card, nome_da_frente

_ultima_chamada = 0.0
PAUSA = 0.1         # intervalo minimo entre requisicoes em segundos
TENTATIVAS = 3      

_client = httpx.Client(base_url=SCRYFALL_BASE, headers=SCRYFALL_HEADERS, timeout=30)

def _pausa():
    global _ultima_chamada
    sleep = PAUSA - (time.monotonic() - _ultima_chamada)
    if sleep > 0:
        time.sleep(sleep)
    _ultima_chamada = time.monotonic()

def _pedir(metodo, caminho, **kwargs):
    """Faz a requisicao respeitando a pausa e repete ate TENTATIVAS"""
    for tentativa in range(TENTATIVAS):
        _pausa()
        resposta = metodo(caminho, **kwargs)
        if resposta.status_code != 429:
            return resposta
        time.sleep(2 ** tentativa)
    return resposta

def buscar_carta(nome: str) -> Card | None:
    nome = nome_da_frente(nome)
    resposta = _pedir(_client.get, "/cards/named", params={"exact": nome})
    if resposta.status_code == 404:
        return None
    resposta.raise_for_status()
    return Card.from_scryfall(resposta.json())

def buscar_cartas(nomes: list[str]) -> tuple[list[Card], list[str]]:
    nomes = [nome_da_frente(nome) for nome in nomes]

    cartas = []
    nao_encontradas = []
    for inicio in range(0, len(nomes), 75):
        lote = nomes[inicio:inicio + 75]
        resposta = _pedir(_client.post, "/cards/collection",
                          json={"identifiers": [{"name": nome} for nome in lote]})
        resposta.raise_for_status()
        dados = resposta.json()
        cartas += [Card.from_scryfall(carta) for carta in dados["data"]]
        nao_encontradas += [item.get("name", "?") for item in dados.get("not_found", [])]
    return cartas, nao_encontradas

# todo: salvar as cartas no banco pra nn precisar ficar repetindo a requisição