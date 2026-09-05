from pathlib import Path

DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "edh.db"

SEED = 42

SCRYFALL_BASE = "https://api.scryfall.com"
SCRYFALL_HEADERS = {
    "User-Agent": "edh-recommender/1.0",
    "Accept": "application/json",
}

EDHREC_BASE = "https://json.edhrec.com/pages/commanders"

ARCHIDEKT_BASE = "https://archidekt.com/api/decks"

ARQUIVO_AMOSTRA = Path("../decks_hold.txt")
