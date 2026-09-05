"""
Os modelos do dominio: uma carta e um deck.
"""

from dataclasses import dataclass, field


def nome_da_frente(nome: str) -> str:
    """'Altar of Bhaal // Bone Offering' -> 'Altar of Bhaal'."""
    nome_array = nome.split()
    if ("//" in nome_array):
        primeiro_nome_array = slice(nome_array.index("//"))
        primeiro_nome = ' '.join(nome_array[primeiro_nome_array]).strip()
        return primeiro_nome
    return nome.strip()


@dataclass(frozen=True)
class Card:
    """Uma carta do Magic, imutavel."""
    oracle_id: str
    name: str
    cmc: float
    type_line: str
    color_identity: tuple[str, ...]
    

    @classmethod
    def from_scryfall(cls, dados: dict) -> "Card":
        """Cria uma Card a partir do JSON do Scryfall."""
        return cls(
            oracle_id=dados["oracle_id"],
            name=nome_da_frente(dados["name"]),
            color_identity=tuple(dados.get("color_identity") or ()),
            cmc=float(dados.get("cmc") or 0.0),
            type_line=dados.get("type_line", ""),
        )

@dataclass
class Deck:
    """Um deck: o comandante mais as outras 99 cartas."""

    name: str = ""
    cards: list[Card] = field(default_factory=list)
    commander: Card | None = None

    def todas_as_cartas(self) -> list["Card"]:
        if self.commander is None:
            return list(self.cards)
        return [self.commander] + self.cards