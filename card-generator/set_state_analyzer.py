import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from models import Config, Card


@dataclass
class ResumeState:
    """Represents the state of an incomplete set for resumption."""
    theme: str
    cards: List[Card]
    batches_completed: int
    total_batches: int
    cards_needing_art: List[Card]
    cards_needing_render_format: List[Card]
    cards_needing_rendering: List[Card]
    has_lands: bool
    is_complete: bool
    collector_number_counter: int


class SetStateAnalyzer:
    """Scans an output directory and determines what work remains at each pipeline stage."""

    def __init__(self, config: Config):
        self.config = config
        self.output_dir = config.output_dir

    def analyze(self) -> ResumeState:
        """Analyze the set directory and return a ResumeState."""
        theme, cards = self._load_cards()
        cards = self._enrich_cards_from_individual_jsons(cards)

        cards_needing_art = self._find_cards_needing_art(cards)
        cards_needing_render_format = self._find_cards_needing_render_format(cards)
        cards_needing_rendering = self._find_cards_needing_rendering(cards)

        has_lands = self._check_has_lands(cards)
        is_complete = (self.output_dir / "mtg_set_complete.json").exists()

        # Calculate batches completed from non-land cards
        cards_per_batch = (
            self.config.mythics_per_batch +
            self.config.rares_per_batch +
            self.config.uncommons_per_batch +
            self.config.commons_per_batch
        )
        non_land_cards = [c for c in cards if "Basic Land" not in c.type]
        batches_completed = len(non_land_cards) // cards_per_batch if cards_per_batch > 0 else 0

        # Calculate collector number counter
        collector_number_counter = 1
        if cards:
            max_num = max(
                (int(c.collector_number) for c in cards if c.collector_number and c.collector_number.isdigit()),
                default=0
            )
            collector_number_counter = max_num + 1

        return ResumeState(
            theme=theme,
            cards=cards,
            batches_completed=batches_completed,
            total_batches=self.config.batches_count,
            cards_needing_art=cards_needing_art,
            cards_needing_render_format=cards_needing_render_format,
            cards_needing_rendering=cards_needing_rendering,
            has_lands=has_lands,
            is_complete=is_complete,
            collector_number_counter=collector_number_counter,
        )

    def _load_cards(self) -> tuple:
        """Load cards from the latest batch file or fall back to mtg_set_output.json."""
        # Find the highest batch file
        batch_files = sorted(self.output_dir.glob("mtg_set_batch_*.json"))
        source_file = None

        if batch_files:
            source_file = batch_files[-1]
        elif (self.output_dir / "mtg_set_output.json").exists():
            source_file = self.output_dir / "mtg_set_output.json"

        if not source_file:
            raise FileNotFoundError(
                f"No card data found in {self.output_dir}. "
                "Expected mtg_set_batch_N.json or mtg_set_output.json"
            )

        print(f"Loading cards from: {source_file.name}")
        with open(source_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Batch files have theme under set_info, output files have it at top level
        if "set_info" in data:
            theme = data["set_info"].get("theme", "")
        else:
            theme = data.get("theme", "")

        cards_data = data.get("cards", [])
        cards = [Card.from_dict(cd) for cd in cards_data]

        return theme, cards

    def _enrich_cards_from_individual_jsons(self, cards: List[Card]) -> List[Card]:
        """For each card, try to load its individual JSON file for art_prompt and image_path."""
        for card in cards:
            json_path = self.output_dir / f"{card.name.replace(' ', '_')}.json"
            if json_path.exists():
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    card_data = data.get("card", data)
                    if card_data.get("art_prompt"):
                        card.art_prompt = card_data["art_prompt"]
                    if card_data.get("image_path"):
                        card.image_path = card_data["image_path"]
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Warning: Could not read individual JSON for {card.name}: {e}")
        return cards

    def _find_cards_needing_art(self, cards: List[Card]) -> List[Card]:
        """Cards where the image file doesn't exist on disk."""
        needing_art = []
        for card in cards:
            if not card.image_path:
                needing_art.append(card)
                continue
            # Check if the image file actually exists
            image_path = Path(card.image_path)
            if not image_path.exists():
                # Also check relative to output_dir/card_images
                alt_path = self.output_dir / "card_images" / f"{card.name.replace(' ', '_')}.png"
                if not alt_path.exists():
                    needing_art.append(card)
        return needing_art

    def _find_cards_needing_render_format(self, cards: List[Card]) -> List[Card]:
        """Cards with images but no render_format JSON."""
        render_dir = self.output_dir / "render_format"
        needing = []
        for card in cards:
            if card in self._find_cards_needing_art(cards):
                continue  # Skip cards that still need art
            render_path = render_dir / f"{card.name.replace(' ', '_')}_render.json"
            if not render_path.exists():
                needing.append(card)
        return needing

    def _find_cards_needing_rendering(self, cards: List[Card]) -> List[Card]:
        """Cards with render format but no rendered PNG."""
        render_dir = self.output_dir / "render_format"
        rendered_dir = self.output_dir / "rendered_cards"
        needing = []
        for card in cards:
            render_path = render_dir / f"{card.name.replace(' ', '_')}_render.json"
            if not render_path.exists():
                continue  # Skip cards without render format
            rendered_path = rendered_dir / f"{card.name.replace(' ', '_')}.png"
            if not rendered_path.exists():
                needing.append(card)
        return needing

    def _check_has_lands(self, cards: List[Card]) -> bool:
        """Check if basic land cards exist in the set."""
        land_types = {"Plains", "Island", "Swamp", "Mountain", "Forest"}
        card_names = {card.name.split()[0] for card in cards}
        return bool(land_types & card_names)

    def print_status_report(self, state: ResumeState) -> None:
        """Print a human-readable status report."""
        print("\n" + "=" * 60)
        print(f"  Resume Status Report for set: {self.config.set_id}")
        print("=" * 60)

        print(f"\n  Cards generated:       {len(state.cards)}")
        print(f"  Batches completed:     {state.batches_completed}/{state.total_batches}")
        print(f"  Batches remaining:     {state.total_batches - state.batches_completed}")
        print(f"  Has basic lands:       {'Yes' if state.has_lands else 'No'}")
        print(f"  Set complete file:     {'Yes' if state.is_complete else 'No'}")

        print(f"\n  --- Pipeline Status ---")
        print(f"  Cards needing art:            {len(state.cards_needing_art)}")
        print(f"  Cards needing render format:  {len(state.cards_needing_render_format)}")
        print(f"  Cards needing rendering:      {len(state.cards_needing_rendering)}")

        total_work = (
            len(state.cards_needing_art) +
            len(state.cards_needing_render_format) +
            len(state.cards_needing_rendering) +
            (state.total_batches - state.batches_completed)
        )

        if total_work == 0 and state.has_lands and state.is_complete:
            print(f"\n  Set appears to be complete!")
        else:
            print(f"\n  Work remaining:")
            if state.cards_needing_art:
                print(f"    - Generate art for {len(state.cards_needing_art)} cards")
            if state.cards_needing_render_format:
                print(f"    - Convert {len(state.cards_needing_render_format)} cards to render format")
            if state.cards_needing_rendering:
                print(f"    - Render {len(state.cards_needing_rendering)} cards as images")
            remaining_batches = state.total_batches - state.batches_completed
            if remaining_batches > 0:
                print(f"    - Generate {remaining_batches} more batches of cards")
            if not state.has_lands and self.config.generate_basic_lands:
                print(f"    - Generate basic lands")

        print("=" * 60 + "\n")
