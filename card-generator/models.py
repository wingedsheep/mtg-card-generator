from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

@dataclass
class Config:
    """Configuration for MTG card generation."""
    csv_file_path: str = "./assets/mtg_cards_english.csv"
    inspiration_cards_count: int = 100
    batches_count: int = 20
    theme_prompt: Optional[str] = None
    set_id: str = None
    output_dir: Path = None

    # Rarity distribution per batch
    mythics_per_batch: int = 1
    rares_per_batch: int = 3
    uncommons_per_batch: int = 4
    commons_per_batch: int = 5

    # Color balance target (percentage)
    color_distribution: Dict[str, float] = None

    def __post_init__(self):
        if self.color_distribution is None:
            self.color_distribution = {
                "W": 0.2, "U": 0.2, "B": 0.2, "R": 0.2, "G": 0.2
            }
        if self.set_id is None:
            self.set_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.output_dir is None:
            self.output_dir = Path("output") / self.set_id
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_output_path(self, filename: str) -> Path:
        """Get the full path for an output file."""
        return self.output_dir / filename


@dataclass
class Card:
    """Represents a Magic: The Gathering card."""
    name: str
    mana_cost: str
    type: str
    rarity: str
    text: str
    flavor: str
    colors: List[str]
    power: Optional[str] = None
    toughness: Optional[str] = None
    authority: Optional[str] = None
    set_name: str = ""
    art_prompt: Optional[str] = None
    image_path: Optional[str] = None
    collector_number: Optional[str] = None
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict) -> 'Card':
        """Create a Card instance from a dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            mana_cost=data.get("mana_cost", ""),
            type=data.get("type", ""),
            rarity=data.get("rarity", ""),
            power=data.get("power", None),
            toughness=data.get("toughness", None),
            authority=data.get("authority", None),
            text=data.get("text", ""),
            flavor=data.get("flavor", ""),
            colors=data.get("colors", []),
            set_name=data.get("set_name", ""),
            art_prompt=data.get("art_prompt"),
            image_path=data.get("image_path"),
            collector_number=data.get("collector_number"),
            description=data.get("description", "")
        )

    def to_dict(self) -> Dict:
        """Convert the card to a dictionary."""
        return {
            "name": self.name,
            "mana_cost": self.mana_cost,
            "type": self.type,
            "rarity": self.rarity,
            "power": self.power,
            "toughness": self.toughness,
            "authority": self.authority,
            "text": self.text,
            "flavor": self.flavor,
            "colors": self.colors,
            "set_name": self.set_name,
            "art_prompt": self.art_prompt,
            "image_path": self.image_path,
            "collector_number": self.collector_number,
            "description": self.description
        }

    def __str__(self) -> str:
        return f"{self.name} ({self.rarity}) - {self.mana_cost}"