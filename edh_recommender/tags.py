"""
As categorias funcionais, vindas das oracle tags do Scryfall.
"""

import gzip
import json

import httpx

from edh_recommender.config import DATA_DIR, SCRYFALL_HEADERS
from edh_recommender.scryfall import _client, _pedir

ARQUIVO_TAGS = DATA_DIR / "oracle-tags.jsonl.gz"

CATEGORIAS = {
    "ramp": ("ramp", "2f3e4ad7-5e60-41b4-bdbc-653f16869cf6"),
    "remocao": ("removal", "444f824c-f910-4530-9dbe-ede7a84cd7f9"),
    "compra": ("draw", "b6448c45-ce65-4848-aa98-2151e4e07437"),
    "board_wipe": ("sweeper", "3fb7e4fd-5304-4120-b7c4-8a89f70ad3f0"),
    "tutor": ("tutor", "c768d2ec-3264-4a90-a98f-bea8467857d3"),
    "protecao": ("protection", "6e2cdc7c-b02c-4b59-a171-f93723721b79"),
}

def _uri_do_bulk(indice: dict) -> str:
    """O endereco do bulk `oracle_tags` na lista do /bulk-data.
    """
    item = next((bulk for bulk in indice["data"] if bulk["type"] == "oracle_tags"), None)
    if item is None:
        disponiveis = [bulk["type"] for bulk in indice["data"]]
        raise RuntimeError(f"o Scryfall nao lista o bulk 'oracle_tags'. Tipos: {disponiveis}")
    return item["jsonl_download_uri"]


def _conferir_oracle(tags: list[dict]) -> None:
    """Levanta erro se o arquivo baixado nao for o bulk de oracle tags."""
    outros_tipos = {tag.get("type") for tag in tags} - {"oracle"}
    if outros_tipos:
        raise RuntimeError(
            f"{ARQUIVO_TAGS} nao e o bulk de oracle tags (achei type={outros_tipos})."
            f" Apague o arquivo e rode de novo."
        )


def baixar_tags() -> list[dict]:
    """Todas as oracle tags do Scryfall, do disco ou da rede.
    """
    if not ARQUIVO_TAGS.exists():
        indice = _pedir(_client.get, "/bulk-data").json()
        resposta = httpx.get(_uri_do_bulk(indice), headers=SCRYFALL_HEADERS,
                             timeout=300, follow_redirects=True)
        resposta.raise_for_status()
        ARQUIVO_TAGS.parent.mkdir(parents=True, exist_ok=True)
        ARQUIVO_TAGS.write_bytes(resposta.content)

    with gzip.open(ARQUIVO_TAGS, "rt", encoding="utf-8") as arquivo:
        tags = [json.loads(linha) for linha in arquivo]

    _conferir_oracle(tags)
    return tags


def _descendentes(id_raiz: str, tags_por_id: dict) -> set[str]:
    """Ids da tag-raiz e de todas as tags abaixo dela."""
    visitados: set[str] = set()
    fila = [id_raiz]
    while fila:
        tag_id = fila.pop()
        if tag_id in visitados or tag_id not in tags_por_id:
            continue
        visitados.add(tag_id)
        fila += tags_por_id[tag_id].get("child_ids") or []
    return visitados

def _achar_tag(slug: str, tag_id: str, tags_por_id: dict, tags_por_slug: dict) -> dict | None:
    """Procura a tag-pai pelo id e, se nao achar, pelo slug."""
    tag = tags_por_id.get(tag_id)
    if tag is not None:
        if tag["slug"] != slug:
            print(f"[aviso] a tag {tag_id} agora se chama '{tag['slug']}'"
                  f" (no codigo esta '{slug}') - vale atualizar CATEGORIAS")
        return tag

    tag = tags_por_slug.get(slug)
    if tag is not None:
        print(f"[aviso] a tag '{slug}' trocou de id: era {tag_id}, agora e {tag['id']}"
              f" - atualize CATEGORIAS")
    return tag


def montar_tags(conn) -> dict[str, int]:
    """Reconstroi a tabela `card_tags`. Devolve quantas cartas cada categoria tem.
    """
    tags = baixar_tags()
    tags_por_id = {tag["id"]: tag for tag in tags}
    tags_por_slug = {tag["slug"]: tag for tag in tags}

    linhas_para_gravar, cartas_por_categoria = [], {}
    for categoria, (slug_pai, id_pai) in CATEGORIAS.items():
        raiz = _achar_tag(slug_pai, id_pai, tags_por_id, tags_por_slug)
        if raiz is None:
            print(f"[aviso] a tag '{slug_pai}' ({id_pai}) nao existe mais no Scryfall")
            cartas_por_categoria[categoria] = 0
            continue

        oracle_ids = set()
        for tag_id in _descendentes(raiz["id"], tags_por_id):
            taggings = tags_por_id[tag_id].get("taggings") or []   
            for tagging in taggings:
                if tagging.get("oracle_id"):
                    oracle_ids.add(tagging["oracle_id"])

        linhas_para_gravar += [(oracle_id, categoria) for oracle_id in oracle_ids]
        cartas_por_categoria[categoria] = len(oracle_ids)

    conn.execute("DELETE FROM card_tags")
    conn.executemany("INSERT OR IGNORE INTO card_tags (oracle_id, category) VALUES (?,?)",
                     linhas_para_gravar)
    conn.commit()
    return cartas_por_categoria


def categorias(oracle_id: str, conn) -> set[str]:
    """As categorias de uma carta. Conjunto vazio se ela nao tiver nenhuma."""
    return {
        linha["category"]
        for linha in conn.execute("SELECT category FROM card_tags WHERE oracle_id = ?",
                                  (oracle_id,))
    }
