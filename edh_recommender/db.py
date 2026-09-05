import sqlite3
from pathlib import Path

from edh_recommender.config import DB_PATH

SCHEMA = """
    CREATE TABLE IF NOT EXISTS card_tags (
        oracle_id TEXT,
        category  TEXT,
        PRIMARY KEY (oracle_id, category)
    );
    CREATE TABLE IF NOT EXISTS cards (
        name TEXT,
        oracle_id TEXT,
        cmc REAL,
        type_line TEXT,
        color_identity TEXT,
        PRIMARY KEY (name)
    );
"""

def cores_para_texto(cores) -> str:
    """('R', 'B') -> 'R,B'"""
    return ','.join(cores)


def texto_para_cores(texto: str | None) -> tuple[str, ...]:
    """'R,B' -> ('R', 'B')"""
    if texto is not None:
        return tuple(texto.replace(",", ""))
    return ()

def get_conn(path=DB_PATH) -> sqlite3.Connection:
    """Abre o banco e cria as tabelas que faltarem"""
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(path)
    conexao.row_factory = sqlite3.Row
    conexao.executescript(SCHEMA)
    conexao.commit()
    return conexao