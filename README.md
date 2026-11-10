# edh_recommender

Recomendador de cartas para decks de Commander (EDH). Dado um deck, sugere
cartas combinando dois critérios:

- **popularidade**: o quanto a carta é jogada com aquele comandante, segundo a
  taxa de inclusão e a sinergia do EDHREC;
- **lacunas**: o quanto falta ao deck em cada categoria funcional (aceleração de
  mana, remoção, compra, limpeza de campo, tutores e proteção), com as
  categorias tiradas das oracle tags do Scryfall.

O peso (`--peso`, entre 0 e 1) equilibra os dois: 1 é só popularidade, 0 é só
lacunas. As cartas são escolhidas uma de cada vez, e cada escolha desconta a
lacuna que ela preenche.

A avaliação esconde parte das cartas de 30 decks do Archidekt e mede
precisão e revocação em k, comparando com a lista do EDHREC.

## Como executar

Requer Python 3.11 ou mais novo.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e . streamlit pandas matplotlib
```

Na primeira vez, monte a tabela de categorias. O comando baixa as oracle tags
do Scryfall para `data/`:

```powershell
python -c "from edh_recommender.db import get_conn; from edh_recommender.tags import montar_tags; print(montar_tags(get_conn()))"
```

### Recomendar cartas

O deck é um `.txt` com uma carta por linha e o comandante na primeira linha
(veja `deck_exemplo.txt`). Listas exportadas do Archidekt ou do Moxfield, no
formato `1 Sol Ring`, funcionam direto.

```powershell
python -m edh_recommender.cli deck_exemplo.txt
python -m edh_recommender.cli deck_exemplo.txt --peso 0.6 -n 15
```

### Interface

```powershell
streamlit run app.py
```

### Experimento e gráficos

```powershell
python -m edh_recommender.avaliacao
python graficos.py
```

A avaliação lê a amostra de decks de `decks_hold.txt` e grava
`resultados.csv`; os gráficos são gerados a partir dele, em `figuras/`.

## Fontes dos dados

Cartas, imagens e categorias vêm do [Scryfall](https://scryfall.com),
popularidade e sinergia do [EDHREC](https://edhrec.com), e os decks da avaliação
do [Archidekt](https://archidekt.com). O uso é acadêmico e não comercial; os
dados baixados ficam em `data/`, que não é versionada. A exceção é `data/decks/`:
uma cópia dos 30 decks da amostra, só com a lista de cartas e as categorias, sem
dados dos usuários. O projeto não é afiliado a nenhum desses serviços.

edh_recommender is unofficial Fan Content permitted under the
[Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy).
Not approved/endorsed by Wizards. Portions of the materials used are property of
Wizards of the Coast. ©Wizards of the Coast LLC.
