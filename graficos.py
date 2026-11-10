"""Gera os graficos do capitulo 5 (resultados) a partir de `resultados.csv`.

    python graficos.py

Sai um PNG (300 dpi) e um PDF (vetorial) de cada figura, em `figuras/`. O PNG e
o que vai para a monografia, porque o Google Docs nao aceita PDF como imagem.
Os numeros saem com virgula decimal, como no texto.
"""

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from edh_recommender.archidekt import carregar_deck, ler_amostra
from edh_recommender.db import get_conn
from edh_recommender.recomendador import REFERENCIA
from edh_recommender.tags import categorias

PASTA = Path("figuras")

AZUL, LARANJA = "#2a78d6", "#eb6834"
SUPERFICIE = "#fcfcfb"
TINTA, TINTA_FRACA = "#0b0b0b", "#52514e"
GRADE = "#e0dfdb"

ACASO = 0.059


def _decimal(valor, casas=3):
    """0.387 -> '0,387': numero com virgula decimal, como no texto."""
    return f"{valor:.{casas}f}".replace(".", ",")


VIRGULA = FuncFormatter(lambda valor, _: f"{valor:g}".replace(".", ","))


def _estilo(eixo):
    """Aplica a grade horizontal, remove as molduras e poe virgula nos eixos."""
    eixo.xaxis.set_major_formatter(VIRGULA)
    eixo.yaxis.set_major_formatter(VIRGULA)
    eixo.set_facecolor(SUPERFICIE)
    eixo.grid(True, axis="y", color=GRADE, linewidth=1, zorder=0)
    eixo.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        eixo.spines[lado].set_visible(False)
    eixo.spines["bottom"].set_color(GRADE)
    eixo.tick_params(colors=TINTA_FRACA, length=0, labelsize=9)


def _salvar(figura, nome):
    """Grava a figura em PNG e PDF dentro de `figuras/`."""
    PASTA.mkdir(exist_ok=True)
    for extensao in ("png", "pdf"):
        figura.savefig(PASTA / f"{nome}.{extensao}", dpi=300,
                       bbox_inches="tight", facecolor=SUPERFICIE)
    plt.close(figura)
    print(f"   figuras/{nome}.pdf  e  .png")


def precisao_por_peso(dados_do_csv):
    """Um painel por k, com a curva do sistema e a linha de base como linha."""
    dados = dados_do_csv[dados_do_csv.perfil == "principal"]
    valores_de_k = sorted(dados.k.unique())
    figura, eixos = plt.subplots(1, len(valores_de_k), figsize=(11, 3.6), sharey=True)
    figura.patch.set_facecolor(SUPERFICIE)

    for eixo, k in zip(eixos, valores_de_k):
        dados_do_k = dados[dados.k == k]
        media_por_peso = dados_do_k.groupby("peso").precisao_sistema.mean()
        referencia = dados_do_k.precisao_baseline.mean()

        eixo.axhline(ACASO, color="#b8b6ae", linewidth=1.5, zorder=1)
        eixo.axhline(referencia, color=TINTA_FRACA, linewidth=1.5,
                     linestyle=(0, (6, 3)), zorder=2)
        eixo.plot(media_por_peso.index, media_por_peso.values, color=AZUL, linewidth=2,
                  marker="o", markersize=4, markeredgecolor=SUPERFICIE, markeredgewidth=1.5,
                  solid_capstyle="round", zorder=3)

        peso_do_pico = media_por_peso.idxmax()
        eixo.plot([peso_do_pico], [media_por_peso[peso_do_pico]], "o", color=AZUL,
                  markersize=9, markeredgecolor=SUPERFICIE, markeredgewidth=2, zorder=4)
        pico_espremido = 0 <= referencia - media_por_peso[peso_do_pico] < 0.04
        eixo.annotate(_decimal(media_por_peso[peso_do_pico]),
                      (peso_do_pico, media_por_peso[peso_do_pico]),
                      textcoords="offset points",
                      xytext=(0, -18 if pico_espremido else 12),
                      ha="center", fontsize=9, color=TINTA)
        eixo.annotate(f"linha de base {_decimal(referencia)}", (0, referencia),
                      textcoords="offset points", xytext=(0, 6),
                      ha="left", fontsize=8, color=TINTA_FRACA)

        _estilo(eixo)
        eixo.set_title(f"k = {k}", fontsize=10, color=TINTA, pad=10)
        eixo.set_xlabel("α", fontsize=9, color=TINTA_FRACA)
        eixo.set_xticks([0, 0.5, 0.7, 1.0])

    eixos[0].set_ylabel("precisão média", fontsize=9, color=TINTA_FRACA)
    eixos[0].set_ylim(0, 0.46)
    eixos[0].annotate("acaso", (0, ACASO), textcoords="offset points",
                      xytext=(0, 5), ha="left", fontsize=8, color=TINTA_FRACA)
    figura.suptitle("Precisão do sistema em função de α", fontsize=11,
                    color=TINTA, y=1.04, x=0.5)
    _salvar(figura, "precisao_por_peso")


def por_arquetipo(dados_do_csv, k=10, peso=0.8):
    """Barras agrupadas: sistema e linha de base lado a lado, por arquetipo.

    O peso padrao e o de maior precisao media em k = 10 (secao 5.2 do texto).
    """
    dados_do_k = dados_do_csv[(dados_do_csv.perfil == "principal") & (dados_do_csv.k == k)]
    do_peso = dados_do_k[dados_do_k.peso == peso]
    sistema = do_peso.groupby("arquetipo").precisao_sistema.mean()
    referencia = do_peso.groupby("arquetipo").precisao_baseline.mean()
    ordem = ["Aggro", "Midrange", "Control"]
    rotulos = {"Aggro": "agressivo", "Midrange": "intermediário", "Control": "controle"}

    figura, eixo = plt.subplots(figsize=(7, 3.8))
    figura.patch.set_facecolor(SUPERFICIE)
    posicoes = range(len(ordem))
    largura = 0.17

    for deslocamento, valores, cor, nome in [
            (-largura / 2 - 0.012, sistema, AZUL, f"sistema (α = {_decimal(peso, 1)})"),
            (+largura / 2 + 0.012, referencia, LARANJA, "linha de base")]:
        barras = eixo.bar([posicao + deslocamento for posicao in posicoes],
                          [valores[arquetipo] for arquetipo in ordem],
                          largura, color=cor, label=nome, zorder=3)
        for barra in barras:
            eixo.annotate(_decimal(barra.get_height()),
                          (barra.get_x() + barra.get_width() / 2, barra.get_height()),
                          textcoords="offset points", xytext=(0, 4),
                          ha="center", fontsize=9, color=TINTA)

    _estilo(eixo)
    eixo.set_xticks(list(posicoes))
    eixo.set_xticklabels([rotulos[arquetipo] for arquetipo in ordem],
                         fontsize=10, color=TINTA)
    eixo.set_ylabel("precisão média", fontsize=9, color=TINTA_FRACA)
    eixo.set_ylim(0, 0.52)
    eixo.legend(frameon=False, fontsize=9, labelcolor=TINTA_FRACA,
                loc="upper left", ncols=2)
    eixo.set_title(f"Precisão por arquétipo (k = {k})", fontsize=11,
                   color=TINTA, pad=14, loc="left")
    _salvar(figura, "por_arquetipo")


def sensibilidade(dados_do_csv, k=10):
    """Duas curvas no mesmo k: um perfil de alvos de cobertura em cada."""
    dados_do_k = dados_do_csv[dados_do_csv.k == k]
    figura, eixo = plt.subplots(figsize=(7, 3.8))
    figura.patch.set_facecolor(SUPERFICIE)

    for perfil, cor, nome, marca in [
            ("principal", AZUL, "perfil principal", "o"),
            ("sensibilidade", LARANJA, "perfil alternativo", "s")]:
        media_por_peso = (dados_do_k[dados_do_k.perfil == perfil]
                          .groupby("peso").precisao_sistema.mean())
        eixo.plot(media_por_peso.index, media_por_peso.values, color=cor, linewidth=2,
                  marker=marca, markersize=6, markeredgecolor=SUPERFICIE, markeredgewidth=2,
                  solid_capstyle="round", label=nome, zorder=3)
        eixo.annotate(nome, (media_por_peso.index[0], media_por_peso.iloc[0]),
                      textcoords="offset points",
                      xytext=(6, -12 if cor == LARANJA else 6),
                      fontsize=9, color=TINTA_FRACA)

    referencia = dados_do_k.precisao_baseline.mean()
    eixo.axhline(referencia, color=TINTA_FRACA, linewidth=1.5,
                 linestyle=(0, (6, 3)), zorder=2)
    eixo.annotate(f"linha de base {_decimal(referencia)}", (1.0, referencia),
                  textcoords="offset points", xytext=(0, 6), ha="right",
                  fontsize=8, color=TINTA_FRACA)
    _estilo(eixo)
    eixo.set_xlabel("α", fontsize=9, color=TINTA_FRACA)
    eixo.set_ylabel("precisão média", fontsize=9, color=TINTA_FRACA)
    eixo.set_ylim(0, 0.42)
    eixo.legend(frameon=False, fontsize=9, labelcolor=TINTA_FRACA, loc="lower right")
    eixo.set_title(f"Sensibilidade aos alvos de cobertura (k = {k})",
                   fontsize=11, color=TINTA, pad=14, loc="left")
    _salvar(figura, "sensibilidade")


def cobertura_da_amostra(dados_do_csv):
    """Uma barra por deck com o teto de revocacao, em ordem crescente."""
    por_deck = (dados_do_csv[(dados_do_csv.perfil == "principal")
                             & (dados_do_csv.peso == 0) & (dados_do_csv.k == 5)]
                .sort_values("teto_revocacao"))

    figura, eixo = plt.subplots(figsize=(8, 3.6))
    figura.patch.set_facecolor(SUPERFICIE)
    eixo.bar(range(len(por_deck)), por_deck.teto_revocacao, color=AZUL, width=0.7, zorder=3)
    media = por_deck.teto_revocacao.mean()
    eixo.axhline(media, color=TINTA_FRACA, linewidth=1.5, linestyle=(0, (6, 3)), zorder=4)
    eixo.annotate(f"média {media:.0%}", (len(por_deck) - 1, media),
                  textcoords="offset points", xytext=(0, 6),
                  ha="right", fontsize=9, color=TINTA)

    _estilo(eixo)
    eixo.set_xticks([])
    eixo.set_xlabel("os 30 decks, ordenados", fontsize=9, color=TINTA_FRACA)
    eixo.set_ylabel("teto de revocação", fontsize=9, color=TINTA_FRACA)
    eixo.set_ylim(0, 1.05)
    eixo.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    eixo.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    eixo.set_title("Fração das cartas removidas que o sistema pode alcançar",
                   fontsize=11, color=TINTA, pad=14, loc="left")
    _salvar(figura, "teto_revocacao")


def cartas_por_categoria(conn):
    """Diagrama de caixa: quantas cartas de cada categoria os 30 decks tem.

    Conta como `lacunas`, com o comandante, e marca o alvo de cada categoria.
    Le os decks e as categorias do cache em `data/`.
    """
    nomes = {"ramp": "aceleração\nde mana", "remocao": "remoção",
             "compra": "compra\nde cartas", "board_wipe": "limpeza\nde campo",
             "tutor": "tutores", "protecao": "proteção"}
    contagens = {categoria: [] for categoria in REFERENCIA}
    for deck_id, _ in ler_amostra():
        deck = carregar_deck(deck_id, conn)
        quantidade = {categoria: 0 for categoria in REFERENCIA}
        for carta in deck.todas_as_cartas():
            for categoria in categorias(carta.oracle_id, conn):
                if categoria in quantidade:
                    quantidade[categoria] += 1
        for categoria in REFERENCIA:
            contagens[categoria].append(quantidade[categoria])

    figura, eixo = plt.subplots(figsize=(8, 3.8))
    figura.patch.set_facecolor(SUPERFICIE)
    ordem = list(REFERENCIA)
    eixo.boxplot([contagens[categoria] for categoria in ordem], widths=0.45,
                 patch_artist=True, zorder=3,
                 boxprops=dict(facecolor=AZUL + "33", edgecolor=AZUL, linewidth=1.5),
                 whiskerprops=dict(color=AZUL, linewidth=1.5),
                 capprops=dict(color=AZUL, linewidth=1.5),
                 medianprops=dict(color=TINTA, linewidth=1.5),
                 flierprops=dict(marker="o", markersize=4, markerfacecolor=AZUL,
                                 markeredgecolor=SUPERFICIE))
    for posicao, categoria in enumerate(ordem, start=1):
        eixo.plot([posicao - 0.3, posicao + 0.3], [REFERENCIA[categoria]] * 2,
                  color=LARANJA, linewidth=2.5, solid_capstyle="round", zorder=4)
    eixo.plot([], [], color=LARANJA, linewidth=2.5, label="alvo de cobertura")

    _estilo(eixo)
    eixo.set_xticks(range(1, len(ordem) + 1))
    eixo.set_xticklabels([nomes[categoria] for categoria in ordem], fontsize=9, color=TINTA)
    eixo.set_ylabel("cartas no deck", fontsize=9, color=TINTA_FRACA)
    eixo.set_ylim(0, None)
    eixo.legend(frameon=False, fontsize=9, labelcolor=TINTA_FRACA, loc="upper right")
    eixo.set_title("Cartas por categoria funcional nos 30 decks", fontsize=11,
                   color=TINTA, pad=14, loc="left")
    _salvar(figura, "cartas_por_categoria")
    return contagens


if __name__ == "__main__":
    resultados = pd.read_csv("resultados.csv")
    print(f"{len(resultados)} linhas lidas de resultados.csv")
    precisao_por_peso(resultados)
    por_arquetipo(resultados)
    sensibilidade(resultados)
    cobertura_da_amostra(resultados)
    cartas_por_categoria(get_conn())
