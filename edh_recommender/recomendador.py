"""O algoritmo de recomendacao."""

from edh_recommender.edhrec import sinais
from edh_recommender.models import Card, Deck
from edh_recommender.scryfall import cartas_por_nome
from edh_recommender.tags import categorias

REFERENCIA = {"ramp": 12, "remocao": 10, "compra": 12,
              "board_wipe": 4, "tutor": 3, "protecao": 3}

REFERENCIA_SENSIBILIDADE = {"ramp": 12, "remocao": 10, "compra": 10,
                            "board_wipe": 4, "tutor": 6, "protecao": 6}


def sinais_por_carta(comandante: str, conn) -> dict[str, tuple[float, float]]:
    """Os sinais do EDHREC com o nome do Scryfall como chave."""
    sinais_edhrec = sinais(comandante)
    cartas = cartas_por_nome(list(sinais_edhrec), conn)
    return {cartas[nome].name: valores for nome, valores in sinais_edhrec.items()
            if nome in cartas}


def candidatos(deck: Deck, sinais_edhrec: dict, conn) -> list[Card]:
    """Cartas do EDHREC fora do deck e dentro da identidade de cor."""
    nomes_no_deck = {carta.name.casefold() for carta in deck.todas_as_cartas()}
    cores_do_comandante = set(deck.commander.color_identity)

    escolhidas = {}
    for carta in cartas_por_nome(list(sinais_edhrec), conn).values():
        if carta.name.casefold() in nomes_no_deck:
            continue
        if not set(carta.color_identity).issubset(cores_do_comandante):
            continue
        escolhidas[carta.name] = carta

    return list(escolhidas.values())


def lacunas(deck: Deck, conn, referencia=REFERENCIA) -> dict[str, int]:
    """Quanto falta em cada categoria: max(0, alvo - quantas o deck tem)."""
    quantidade_no_deck = {categoria: 0 for categoria in referencia}
    for carta in deck.todas_as_cartas():
        for categoria in categorias(carta.oracle_id, conn):
            if categoria in quantidade_no_deck:
                quantidade_no_deck[categoria] += 1

    return {categoria: max(0, alvo - quantidade_no_deck[categoria])
            for categoria, alvo in referencia.items()}


def _normalizar(valores: dict[str, float]) -> dict[str, float]:
    """Coloca todos os valores entre 0 e 1 (min-max)."""
    if not valores:
        return {}

    menor, maior = min(valores.values()), max(valores.values())
    if maior == menor:
        return {chave: 0.0 for chave in valores}

    return {chave: (valor - menor) / (maior - menor) for chave, valor in valores.items()}


def pontuar(cartas_candidatas, sinais_edhrec, lacunas_do_deck, conn,
            peso=0.5) -> list[tuple[str, float]]:
    """[(nome, nota), ...] da maior para a menor."""
    inclusao_por_carta = {carta.name: sinais_edhrec.get(carta.name, (0, 0))[0]
                          for carta in cartas_candidatas}
    sinergia_por_carta = {carta.name: sinais_edhrec.get(carta.name, (0, 0))[1]
                          for carta in cartas_candidatas}

    inclusao_normalizada = _normalizar(inclusao_por_carta)
    sinergia_normalizada = _normalizar(sinergia_por_carta)
    popularidade = _normalizar({nome: inclusao_normalizada[nome] + sinergia_normalizada[nome]
                                for nome in inclusao_por_carta})

    lacuna_por_carta = {}
    for carta in cartas_candidatas:
        maior_lacuna = 0
        for categoria in categorias(carta.oracle_id, conn):
            lacuna_da_categoria = lacunas_do_deck.get(categoria, 0)
            maior_lacuna = max(maior_lacuna, lacuna_da_categoria)
        lacuna_por_carta[carta.name] = maior_lacuna

    lacuna_normalizada = _normalizar(lacuna_por_carta)

    nota_por_carta = {nome: peso * popularidade[nome] + (1 - peso) * lacuna_normalizada[nome]
                      for nome in popularidade}

    nomes_ordenados = sorted(nota_por_carta,
                             key=lambda nome: (-nota_por_carta[nome], -popularidade[nome], nome))
    return [(nome, nota_por_carta[nome]) for nome in nomes_ordenados]


def recomendar(deck: Deck, conn, peso: float = 0.5, quantidade: int = 10,
               referencia=REFERENCIA) -> list[tuple[str, float]]:
    """As melhores cartas para o deck: [(nome, nota), ...]."""
    if deck.commander is None:
        raise ValueError("o deck precisa de um comandante para receber recomendacoes")

    sinais_edhrec = sinais_por_carta(deck.commander.name, conn)
    candidatos_restantes = {carta.name: carta
                            for carta in candidatos(deck, sinais_edhrec, conn)}
    lacunas_do_deck = lacunas(deck, conn, referencia)

    escolhidas = []
    for _ in range(quantidade):
        nomes_ordenados = pontuar(list(candidatos_restantes.values()), sinais_edhrec,
                                  lacunas_do_deck, conn, peso=peso)
        if not nomes_ordenados:
            break

        nome, nota = nomes_ordenados[0]
        escolhidas.append((nome, nota))
        carta_escolhida = candidatos_restantes.pop(nome)

        for categoria in categorias(carta_escolhida.oracle_id, conn):
            if lacunas_do_deck.get(categoria):
                lacunas_do_deck[categoria] -= 1

    return escolhidas
