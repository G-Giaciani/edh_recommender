"""A interface de linha de comando."""

import re

import click

from edh_recommender.db import get_conn
from edh_recommender.models import Deck
from edh_recommender.recomendador import REFERENCIA, lacunas, recomendar
from edh_recommender.scryfall import cartas_por_nome
from edh_recommender.tags import categorias

QUANTIDADE = re.compile(r"^\d+\s*x?\s+", re.IGNORECASE)


def ler_nomes(caminho: str) -> list[str]:
    """Os nomes de carta de um arquivo de deck, na ordem em que aparecem."""
    nomes = []
    for linha in open(caminho, encoding="utf-8"):
        linha = linha.strip()
        if not linha or linha.startswith(("//", "#")):
            continue
        nomes.append(QUANTIDADE.sub("", linha).strip())
    return nomes


def carregar_deck(caminho: str, conn) -> Deck:
    """Monta um Deck a partir do arquivo. A primeira linha e o comandante."""
    nomes = ler_nomes(caminho)
    if not nomes:
        raise ValueError(f"{caminho} nao tem nenhuma carta")

    cartas = cartas_por_nome(nomes, conn)
    if nomes[0] not in cartas:
        raise ValueError(f"comandante nao encontrado no Scryfall: {nomes[0]!r}"
                         f" - confira a grafia na primeira linha do arquivo")

    return Deck(name=caminho,
                commander=cartas[nomes[0]],
                cards=[cartas[nome] for nome in nomes[1:] if nome in cartas])


@click.command()
@click.argument("arquivo", type=click.Path(exists=True, dir_okay=False))
@click.option("--peso", default=0.5, show_default=True,
              help="1 = so popularidade, 0 = so lacunas do deck")
@click.option("-n", "quantidade", default=10, show_default=True,
              help="quantas cartas sugerir")
def main(arquivo, peso, quantidade):
    """Sugere cartas para um deck de Commander."""
    conn = get_conn()
    try:
        deck = carregar_deck(arquivo, conn)
    except ValueError as erro:
        raise click.ClickException(str(erro))

    cores = "".join(deck.commander.color_identity) or "incolor"
    click.echo(f"\nComandante: {deck.commander.name} ({cores})"
               f" | {len(deck.cards)} cartas no deck")

    faltando = {categoria: quanto for categoria, quanto
                in lacunas(deck, conn).items() if quanto}
    if faltando:
        texto = " | ".join(f"{categoria} {quanto}" for categoria, quanto in
                           sorted(faltando.items(), key=lambda par: -par[1]))
        click.echo(f"Faltando:   {texto}")
    else:
        click.echo(f"Faltando:   nada - as {len(REFERENCIA)} categorias estao completas")

    click.echo(f"\npeso = {peso}\n")
    click.echo(f"  {'#':>2}  {'carta':<34} categorias")
    for posicao, (nome, _nota) in enumerate(
            recomendar(deck, conn, peso=peso, quantidade=quantidade), 1):
        carta = cartas_por_nome([nome], conn)[nome]
        categorias_da_carta = ", ".join(sorted(categorias(carta.oracle_id, conn))) or "-"
        click.echo(f"  {posicao:>2}  {nome:<34} {categorias_da_carta}")
    click.echo()


if __name__ == "__main__":
    main()
