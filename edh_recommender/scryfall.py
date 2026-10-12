"""
Busca de cartas no Scryfall, com cache no banco.
"""
import time

import httpx

from edh_recommender.config import SCRYFALL_BASE, SCRYFALL_HEADERS
from edh_recommender.db import cores_para_texto, texto_para_cores
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

def _cartas_em_cache(nomes: list[str], conn) -> dict[str, Card]:
    """As cartas que ja estao no banco, no formato {nome em minusculas: Card}."""
    parametros = ",".join("?" * len(nomes))
    linhas = conn.execute(
        f"SELECT * FROM cards WHERE name COLLATE NOCASE IN ({parametros})", nomes)
    return {
        linha["name"].casefold(): Card(
            oracle_id=linha["oracle_id"],
            name=linha["name"],
            color_identity=texto_para_cores(linha["color_identity"]),
            cmc=linha["cmc"],
            type_line=linha["type_line"],
        )
        for linha in linhas
    }

def _salvar(cartas: list[Card], conn):
    """Grava as cartas no banco, sobrescrevendo as que ja existirem."""
    conn.executemany(
        "INSERT OR REPLACE INTO cards (name, oracle_id, color_identity, cmc, type_line)"
        " VALUES (?,?,?,?,?)",
        [(carta.name, carta.oracle_id, cores_para_texto(carta.color_identity),
          carta.cmc, carta.type_line)
         for carta in cartas],
    )
    conn.commit()

def sem_repetir_por_caixa(nomes: list[str]) -> list[str]:
    """['Sol Ring', 'SOL RING'] -> ['Sol Ring']"""
    vistos, resultado = set(), []
    for nome in nomes:
        chave = nome.casefold()
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(nome)
    return resultado

def buscar_com_cache(nomes: list[str], cache: dict, buscar_na_rede) -> dict:
    """Resolve os nomes lendo do cache e buscando na rede so o que faltar."""
    fora_do_cache = [nome for nome in nomes if nome not in cache]
    if fora_do_cache:
        cache.update(buscar_na_rede(fora_do_cache))

    return {nome: cache[nome] for nome in nomes if nome in cache}

def cartas_por_nome(nomes: list[str], conn) -> dict[str, Card]:
    """Nomes -> {nome: Card}. Le do banco primeiro e busca na rede o que faltar.

    Nomes que o Scryfall nao reconhece nao entram no resultado: viram um aviso.
    """
    def chave(nome: str) -> str:
        return nome_da_frente(nome).casefold()

    unicos = {}
    for nome in nomes:
        unicos.setdefault(chave(nome), nome_da_frente(nome))
    if not unicos:
        return {}

    conhecidas = _cartas_em_cache(list(unicos.values()), conn)

    faltando = [frente for k, frente in unicos.items() if k not in conhecidas]
    if faltando:
        achadas, nao_encontradas = buscar_cartas(faltando)
        _salvar(achadas, conn)
        conhecidas.update({chave(carta.name): carta for carta in achadas})
        if nao_encontradas:
            print(f"Aviso: {len(nao_encontradas)} cartas nao encontradas: "
                  + ", ".join(nao_encontradas))

    return {nome: conhecidas[chave(nome)] for nome in nomes if chave(nome) in conhecidas}