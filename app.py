"""Interface web local do recomendador."""

import json
from urllib.parse import quote

import streamlit as st

from edh_recommender.cli import QUANTIDADE
from edh_recommender.config import DATA_DIR
from edh_recommender.db import get_conn
from edh_recommender.models import Deck, nome_da_frente
from edh_recommender.recomendador import REFERENCIA, lacunas, recomendar
from edh_recommender.scryfall import _client, _pedir, cartas_por_nome
from edh_recommender.tags import categorias

ARQUIVO_IMAGENS = DATA_DIR / "imagens.json"
VERSOES = ("normal", "art_crop")

PALETAS = {
    "light": {"acento": "#2a78d6", "tinta": "#0b0b0b", "fraca": "#52514e",
              "trilho": "#e6e5e0", "borda": "#e4e3dd", "cheio": "#b8b6ae",
              "chip_fundo": "#e4eefb", "chip_texto": "#1d5ea8",
              "outro_fundo": "#f0efeb", "outro_texto": "#6d6b64",
              "superficie": "#ffffff", "veu": "#fcfcfb", "arte": "0.30",
              "vidro": "rgba(0,0,0,.035)", "realce": "rgba(42,120,214,.07)",
              "sombra": "0 8px 24px rgba(0,0,0,.10)",
              "sombra_forte": "0 16px 44px rgba(0,0,0,.22)"},
    "dark":  {"acento": "#3987e5", "tinta": "#ffffff", "fraca": "#c3c2b7",
              "trilho": "#33322f", "borda": "#2f2e2b", "cheio": "#5c5b56",
              "chip_fundo": "#16304d", "chip_texto": "#8cbcf0",
              "outro_fundo": "#2b2a28", "outro_texto": "#a3a199",
              "superficie": "#212120", "veu": "#1a1a19", "arte": "0.45",
              "vidro": "rgba(255,255,255,.06)", "realce": "rgba(57,135,229,.12)",
              "sombra": "0 10px 30px rgba(0,0,0,.45)",
              "sombra_forte": "0 20px 50px rgba(0,0,0,.65)"},
}


def paleta() -> dict:
    """A paleta do tema que o usuario escolheu no menu do Streamlit."""
    try:
        tipo = st.context.theme.get("type", "light")
    except Exception:
        tipo = "light"
    return PALETAS.get(tipo, PALETAS["light"])


CORES_MTG = {"W": "#f5eeda", "U": "#3d7dd4", "B": "#4a4a52",
             "R": "#d8503c", "G": "#3f9160"}
NOMES_CORES = {"W": "Branco", "U": "Azul", "B": "Preto",
               "R": "Vermelho", "G": "Verde"}

ROTULOS = {"ramp": "aceleração", "remocao": "remoção", "compra": "compra",
           "board_wipe": "limpeza", "tutor": "tutores", "protecao": "proteção"}

st.set_page_config(page_title="Recomendador EDH", page_icon="🎴", layout="wide")

CORES = paleta()
VEU = CORES["veu"]

st.markdown(f"""
<style>
  .block-container {{ padding-top: 1.9rem; max-width: 1160px; }}
  footer, [data-testid="stAppDeployButton"] {{ display: none; }}
  header {{ background: transparent !important; }}

  .cabecalho {{ position: relative; overflow: hidden; border-radius: 18px;
                border: 1px solid {CORES["borda"]}; background: {CORES["superficie"]};
                margin: 0 0 1.6rem; }}
  .cab-arte  {{ position: absolute; inset: -60px; background-size: cover;
                background-position: center 28%; opacity: {CORES["arte"]}; }}
  .cab-veu   {{ position: absolute; inset: 0;
                background: linear-gradient(100deg, {VEU}fa 0%, {VEU}f2 38%,
                                            {VEU}d4 64%, {VEU}8a 100%); }}
  .cab-corpo {{ position: relative; display: flex; align-items: center;
                gap: 1.7rem; padding: 1.4rem 1.7rem; }}
  .cab-carta {{ width: 180px; flex: none; display: block; border-radius: 11px;
                box-shadow: {CORES["sombra"]};
                transition: transform .3s cubic-bezier(.2,.8,.3,1); }}
  .cab-carta:hover {{ transform: translateY(-6px) scale(1.03) rotate(-.5deg); }}
  .cab-texto {{ min-width: 0; }}

  .etiqueta  {{ font-size: .7rem; letter-spacing: .17em; text-transform: uppercase;
                color: {CORES["fraca"]}; margin-bottom: .3rem; }}
  .titulo    {{ font-size: clamp(1.5rem, 2.7vw, 2rem); font-weight: 700;
                letter-spacing: -.025em; line-height: 1.12; margin: 0 0 .35rem;
                color: {CORES["tinta"]}; }}
  .tipo      {{ color: {CORES["fraca"]}; font-size: .93rem; margin: 0 0 .95rem; }}
  .cab-fatos {{ display: flex; flex-wrap: wrap; gap: .45rem; }}
  .fato      {{ font-size: .8rem; color: {CORES["fraca"]}; background: {CORES["vidro"]};
                border: 1px solid {CORES["borda"]}; border-radius: 999px;
                padding: .22rem .7rem; white-space: nowrap; }}

  .pip {{ display:inline-block; width:13px; height:13px; border-radius:50%;
          margin-right:4px; vertical-align:-1px;
          border:1px solid rgba(128,128,128,.35);
          box-shadow: inset 0 -2px 4px rgba(0,0,0,.2); }}

  .painel        {{ background: {CORES["superficie"]}; border: 1px solid {CORES["borda"]};
                    border-radius: 16px; padding: 1.15rem 1.3rem; }}
  .painel-titulo {{ display: flex; justify-content: space-between; align-items: baseline;
                    font-size: .72rem; letter-spacing: .14em; text-transform: uppercase;
                    color: {CORES["fraca"]}; margin-bottom: 1rem; }}
  .painel-alfa   {{ letter-spacing: 0; text-transform: none; font-size: .8rem;
                    color: {CORES["acento"]}; font-variant-numeric: tabular-nums; }}
  .painel-nota   {{ font-size: .82rem; color: {CORES["fraca"]}; margin-top: .9rem; }}

  .medidor      {{ margin-bottom: .95rem; }}
  .medidor:last-child {{ margin-bottom: 0; }}
  .medidor-topo {{ display:flex; justify-content:space-between; font-size:.87rem;
                   margin-bottom:.35rem; }}
  .medidor-nome {{ color:{CORES["tinta"]}; }}
  .medidor-num  {{ color:{CORES["fraca"]}; font-variant-numeric: tabular-nums; }}
  .trilho       {{ height:8px; background:{CORES["trilho"]}; border-radius:999px;
                   overflow:hidden; }}
  .preenchido   {{ height:100%; background:{CORES["acento"]}; border-radius:999px;
                   transition: width .45s cubic-bezier(.4,0,.2,1); }}
  .completo     {{ background:{CORES["cheio"]}; }}

  .linha  {{ position: relative; display:flex; align-items:center; gap:.85rem;
             padding:.5rem .6rem; border-radius: 10px;
             border-bottom:1px solid {CORES["borda"]};
             transition: background .16s ease, border-color .16s ease; }}
  .linha:last-child {{ border-bottom-color: transparent; }}
  .linha:hover {{ background:{CORES["realce"]}; border-bottom-color: transparent; }}

  .posic  {{ flex:none; width:1.75rem; height:1.75rem; line-height:1.75rem;
             border-radius:50%; text-align:center; font-size:.78rem;
             font-variant-numeric: tabular-nums; color:{CORES["fraca"]};
             background:{CORES["trilho"]};
             transition: background .16s ease, color .16s ease; }}
  .linha:hover .posic {{ background:{CORES["acento"]}; color:#fff; }}

  .carta  {{ flex:1; min-width:0; font-size:.98rem; color:{CORES["tinta"]};
             cursor: default; text-decoration: underline dotted transparent;
             text-underline-offset: 3px; transition: text-decoration-color .16s ease; }}
  .linha:hover .carta {{ text-decoration-color: {CORES["fraca"]}; }}

  .chips  {{ flex:none; display:flex; gap:.3rem; }}
  .chip   {{ font-size:.71rem; font-weight:500; padding:.18rem .55rem;
             border-radius:999px; white-space:nowrap; }}
  .chip-lacuna {{ background:{CORES["chip_fundo"]}; color:{CORES["chip_texto"]}; }}
  .chip-outra  {{ background:{CORES["outro_fundo"]}; color:{CORES["outro_texto"]}; }}

  .lista  {{ overflow: visible; }}
  .carta  {{ position: relative; }}
  .previa {{ position:absolute; left:0; top:calc(100% + 10px); z-index:999;
             width:244px; max-width:none; border-radius:12px; box-shadow:{CORES["sombra_forte"]};
             opacity:0; visibility:hidden; pointer-events:none;
             transform: translateY(-6px) scale(.96); transform-origin: top left;
             transition: opacity .18s ease, transform .18s ease,
                         visibility 0s linear .18s; }}
  .linha:hover .previa {{ opacity:1; visibility:visible;
                          transform: translateY(0) scale(1);
                          transition: opacity .18s ease, transform .18s ease,
                                      visibility 0s; }}
  .linha:nth-last-child(-n+3) .previa {{ top:auto; bottom:calc(100% + 10px);
                                         transform-origin: bottom left;
                                         transform: translateY(6px) scale(.96); }}
  .linha:nth-last-child(-n+3):hover .previa {{ transform: translateY(0) scale(1); }}
</style>
""", unsafe_allow_html=True)


def conexao():
    """Abre uma conexao nova a cada execucao do script."""
    return get_conn()


@st.cache_data(show_spinner="Consultando Scryfall e EDHREC...")
def resolver(texto: str) -> tuple[str, list[str]]:
    """Texto colado -> (comandante, demais cartas), so com os nomes."""
    nomes = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith(("//", "#")):
            continue
        nomes.append(QUANTIDADE.sub("", linha).strip())
    if not nomes:
        raise ValueError("cole ao menos uma carta")

    cartas = cartas_por_nome(nomes, conexao())
    if nomes[0] not in cartas:
        raise ValueError(f"comandante não encontrado: {nomes[0]!r} — "
                         "confira a grafia na primeira linha")
    return nomes[0], [nome for nome in nomes[1:] if nome in cartas]


def imagens(nomes: list[str]) -> dict[str, dict[str, str]]:
    """{nome em minusculas: {versao: URL}}, do disco ou de /cards/collection."""
    guardadas = {}
    if ARQUIVO_IMAGENS.exists():
        guardadas = json.loads(ARQUIVO_IMAGENS.read_text(encoding="utf-8"))

    faltando = list(dict.fromkeys(nome_da_frente(nome) for nome in nomes
                                  if nome_da_frente(nome).casefold() not in guardadas))
    for inicio in range(0, len(faltando), 75):
        lote = faltando[inicio:inicio + 75]
        resposta = _pedir(_client.post, "/cards/collection",
                          json={"identifiers": [{"name": nome} for nome in lote]})
        resposta.raise_for_status()
        for carta in resposta.json()["data"]:
            faces = carta.get("card_faces") or [{}]
            uris = carta.get("image_uris") or faces[0].get("image_uris")
            if uris:
                guardadas[nome_da_frente(carta["name"]).casefold()] = {
                    versao: uris[versao] for versao in VERSOES}

    if faltando:
        ARQUIVO_IMAGENS.parent.mkdir(parents=True, exist_ok=True)
        ARQUIVO_IMAGENS.write_text(json.dumps(guardadas), encoding="utf-8")
    return guardadas


def imagem_da_carta(nome: str, enderecos: dict, versao: str = "normal") -> str:
    """URL da imagem da carta no servidor de imagens do Scryfall."""
    guardada = enderecos.get(nome_da_frente(nome).casefold())
    if guardada:
        return guardada[versao]
    return ("https://api.scryfall.com/cards/named"
            f"?exact={quote(nome)}&format=image&version={versao}")


def leitura_do_alfa(peso: float) -> str:
    """A frase que descreve o valor de alfa, exibida junto do controle."""
    if peso >= 0.95:
        return "só popularidade: as cartas mais jogadas com este comandante"
    if peso >= 0.7:
        return "sobretudo popularidade, com as lacunas ajustando a ordem"
    if peso > 0.3:
        return "equilíbrio entre popularidade e o que falta no deck"
    if peso > 0.05:
        return "sobretudo as lacunas, com a popularidade como desempate"
    return "só as lacunas: o que falta funcionalmente, por mais raro que seja"


def medidor(categoria: str, tem: int, alvo: int) -> str:
    """O HTML de uma barra de cobertura: rotulo, contagem e trilho preenchido."""
    falta = max(0, alvo - tem)
    fracao = min(1.0, tem / alvo) if alvo else 1.0
    classe = "preenchido" if falta else "preenchido completo"
    direita = f"faltam {falta}" if falta else "✓ completo"
    dica = f"alvo de referência: {alvo} cartas de {ROTULOS[categoria]}"
    return (f'<div class="medidor" title="{dica}">'
            f'<div class="medidor-topo"><span class="medidor-nome">{ROTULOS[categoria]}</span>'
            f'<span class="medidor-num">{tem} de {alvo} · {direita}</span></div>'
            f'<div class="trilho"><div class="{classe}" style="width:{fracao:.0%}"></div></div>'
            f'</div>')


with st.sidebar:
    st.markdown("#### Seu deck")
    st.caption("Comandante na primeira linha. Quantidade e comentários são ignorados.")

    texto = st.text_area("deck", height=300,
                         label_visibility="collapsed",
                         placeholder="Krenko, Mob Boss\n1 Sol Ring\n1 Goblin Warchief")
    st.divider()
    peso = st.slider("α — o que pesa mais", 0.0, 1.0, 0.6, 0.05)
    st.caption(f"**{leitura_do_alfa(peso)}**")
    st.caption("**1** = só popularidade · **0** = só as lacunas do deck")
    quantidade_de_sugestoes = st.slider("Sugestões", 5, 30, 10, 5)

    st.divider()
    with st.expander("Como ler esta tela"):
        st.markdown(
            "- **O comandante no topo** define tudo: as cartas candidatas são as "
            "que o EDHREC associa a ele.\n"
            "- **Cobertura funcional** — quantas cartas o deck tem de cada função "
            "diante do alvo de referência. A barra azul é o que já existe.\n"
            "- **Sugestões** — a etiqueta azul marca a categoria que preenche uma "
            "lacuna; a cinza, a função que já está completa.\n"
            "- Passe o mouse sobre o nome para ver a carta."
        )

    tema = "escuro" if CORES is PALETAS["dark"] else "claro"
    st.caption(f"Tema **{tema}** · troque no menu **⋮** no canto superior direito. "
               "Para projetor, o claro costuma render melhor.")

if not texto.strip():
    st.info("Cole um deck na barra lateral para ver as recomendações.")
    st.stop()

try:
    comandante, demais_cartas = resolver(texto)
except ValueError as erro:
    st.error(str(erro))
    st.stop()

conn = conexao()
cartas_resolvidas = cartas_por_nome([comandante] + demais_cartas, conn)
deck = Deck(name="ui", commander=cartas_resolvidas[comandante],
            cards=[cartas_resolvidas[nome] for nome in demais_cartas
                   if nome in cartas_resolvidas])
faltando = lacunas(deck, conn)
recomendadas = recomendar(deck, conn, peso=peso, quantidade=quantidade_de_sugestoes)
enderecos = imagens([comandante] + [nome for nome, _nota in recomendadas])

pips ="".join(f'<span class="pip" style="background:{CORES_MTG[cor]}"'
               f' title="{NOMES_CORES[cor]}"></span>'
               for cor in deck.commander.color_identity) or \
       '<span class="pip" style="background:#d9d7cf" title="Incolor"></span>'

vagas = sum(faltando.values())
categorias_em_falta = sum(1 for quanto in faltando.values() if quanto)
resumo = (f"faltam {vagas} em {categorias_em_falta} de {len(REFERENCIA)} categorias"
          if vagas else "cobertura funcional completa")

st.markdown(
    '<div class="cabecalho">'
    f'<div class="cab-arte" style="background-image:url({imagem_da_carta(comandante, enderecos, "art_crop")})"></div>'
    '<div class="cab-veu"></div>'
    '<div class="cab-corpo">'
    f'<img class="cab-carta" src="{imagem_da_carta(comandante, enderecos)}" alt="{comandante}">'
    '<div class="cab-texto">'
    '<div class="etiqueta">Comandante</div>'
    f'<div class="titulo">{deck.commander.name}</div>'
    f'<div class="tipo">{pips} {deck.commander.type_line}</div>'
    '<div class="cab-fatos">'
    f'<span class="fato">{len(deck.cards) + 1} cartas</span>'
    f'<span class="fato">{resumo}</span>'
    '</div></div></div></div>',
    unsafe_allow_html=True)

esquerda, direita = st.columns([2, 3], gap="large")

with esquerda:
    quantas_o_deck_tem = {categoria: REFERENCIA[categoria] - quanto
                          for categoria, quanto in faltando.items()}
    medidores = "".join(
        medidor(categoria, quantas_o_deck_tem[categoria], REFERENCIA[categoria])
        for categoria in sorted(faltando, key=lambda cat: -faltando[cat]))
    aviso = ("" if vagas else
             '<div class="painel-nota">Sem lacunas — o sistema recomenda só por '
             'popularidade.</div>')
    st.markdown('<div class="painel">'
                '<div class="painel-titulo"><span>Cobertura funcional</span></div>'
                f'{medidores}{aviso}</div>', unsafe_allow_html=True)

with direita:
    linhas = []
    for posicao, (nome, _nota) in enumerate(recomendadas, 1):
        carta = cartas_por_nome([nome], conn)[nome]
        categorias_da_carta = sorted(categorias(carta.oracle_id, conn))
        chips = "".join(
            f'<span class="chip {"chip-lacuna" if faltando.get(categoria) else "chip-outra"}"'
            f' title="{"preenche uma lacuna do deck" if faltando.get(categoria) else "esta função já está completa"}">'
            f'{ROTULOS.get(categoria, categoria)}</span>'
            for categoria in categorias_da_carta)
        linhas.append(
            f'<div class="linha"><span class="posic">{posicao}</span>'
            f'<span class="carta">{nome}<img class="previa" loading="lazy"'
            f' src="{imagem_da_carta(nome, enderecos)}" alt="{nome}"></span>'
            f'<span class="chips">{chips}</span></div>')

    st.markdown('<div class="painel">'
                f'<div class="painel-titulo"><span>{quantidade_de_sugestoes} sugestões</span>'
                f'<span class="painel-alfa">α = {peso:g}</span></div>'
                f'<div class="lista">{"".join(linhas)}</div></div>',
                unsafe_allow_html=True)

    st.caption("A ordem é o que o ranqueamento garante. A nota não é comparável "
               "entre posições: a normalização é refeita a cada escolha. "
               "Passe o mouse sobre a carta para ver a imagem.")

st.divider()
st.caption("Dados de cartas e imagens: [Scryfall](https://scryfall.com) · "
           "popularidade e sinergia: [EDHREC](https://edhrec.com). "
           "Este projeto não é afiliado nem endossado por eles.")
st.caption("Recomendador EDH is unofficial Fan Content permitted under the "
           "[Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy). "
           "Not approved/endorsed by Wizards. Portions of the materials used are "
           "property of Wizards of the Coast. ©Wizards of the Coast LLC.")
