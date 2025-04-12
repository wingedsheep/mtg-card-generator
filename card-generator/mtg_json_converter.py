import json
from pathlib import Path
from typing import Dict, List

from models import Config, Card


class MTGJSONConverter:
    def __init__(self, config: Config = None):
        self.config = config
        self.client = config.openai_client if config else None

    def convert_to_rendering_format(self, input_json: Dict, max_retries: int = 3) -> Dict:
        """Convert input JSON to rendering format using OpenRouter with retries."""
        # Extract card data
        card_data = input_json["card"]

        # Create example prompt
        prompt = self._create_conversion_prompt(card_data)

        for attempt in range(max_retries):
            try:
                # Get conversion from OpenRouter
                completion = self.client.chat.completions.create(
                    extra_headers=self.config.api_headers,
                    model=self.config.json_model,  # Use Gemini model from config
                    messages=[
                        {"role": "system",
                         "content": "You are a JSON converter that converts MTG card data to rendering format. Return only the JSON object with no additional text."},
                        {"role": "user", "content": prompt}
                    ]
                )

                response_text = completion.choices[0].message.content
                # Extract JSON from response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    json_text = response_text[start_idx:end_idx + 1]
                    converted_json = json.loads(json_text)

                    # Add original_name field for basic lands with variation numbers
                    if any(land_type in card_data["name"] for land_type in
                           ["Plains", "Island", "Swamp", "Mountain", "Forest"]) and " " in card_data["name"]:
                        converted_json["original_name"] = card_data["name"]

                    return converted_json
                raise ValueError("No valid JSON object found in response")

            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    print(f"Error converting JSON after {max_retries} attempts: {e}")
                    print("Raw response:", response_text)
                    raise
                print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                import time
                time.sleep(2)  # Wait 2 seconds before retrying

    def _create_conversion_prompt(self, card_data: Dict) -> str:
        """Create the prompt for JSON conversion."""
        example_pairs = [
            {
                "input": {
                    "name": "Ancient Grovekeeper",
                    "mana_cost": "{2}{G}{W}",
                    "type": "Creature — Treefolk Druid",
                    "rarity": "Uncommon",
                    "power": 3,
                    "toughness": 5,
                    "text": "Whenever you Stabilize, create a 1/1 green Saproling creature token.\nCreatures you "
                            "control with toughness 4 or greater have vigilance.",
                    "flavor": "The Dissenting Ancients believe Yros must regrow from destruction, one root at a time.",
                    "colors": ["G", "W"],
                    "image_path": "output/20250208_152032/Ancient_Grovekeeper.png",
                    "collector_number": "87"
                },
                "output": {
                    "name": "Ancient Grovekeeper",
                    "layout": "normal",
                    "collector_number": "87",
                    "image_uris": {
                        "art_crop": "../card-generator/output/20250208_152032/Ancient_Grovekeeper.png"
                    },
                    "mana_cost": "{2}{G}{W}",
                    "type_line": "Creature - Treefolk Druid",
                    "oracle_text": "Whenever you Stabilize, create a 1/1 green Saproling creature token.\n\nCreatures "
                                   "you control with toughness 4 or greater have vigilance.",
                    "colors": ["WG"],
                    "set": "thb",
                    "rarity": "uncommon",
                    "artist": "Vincent Bons",
                    "power": "3",
                    "toughness": "5",
                    "flavor_text": "The Dissenting Ancients believe Yros must regrow from destruction, one root at a time."
                }
            },
            {
                "input": {
                    "name": "Cindershard Raider",
                    "mana_cost": "{3}{B}{R}",
                    "type": "Creature — Spirit Warrior",
                    "rarity": "Uncommon",
                    "power": 4,
                    "toughness": 3,
                    "text": "Haste\nWhenever Cindershard Raider attacks, you may sacrifice an artifact. If you do, "
                            "it gains first strike and 'When this creature dies, it deals 3 damage to any target' "
                            "until end of turn.",
                    "flavor": "The rift-touched burn twice—once in battle, once in the memory of the dead.",
                    "colors": ["B", "R"],
                    "image_path": "output/20250208_152032/Cindershard_Raider.png",
                    "collector_number": "88"
                },
                "output": {
                    "name": "Cindershard Raider",
                    "layout": "normal",
                    "collector_number": "88",
                    "image_uris": {
                        "art_crop": "../card-generator/output/20250208_152032/Cindershard_Raider.png"
                    },
                    "mana_cost": "{3}{B}{R}",
                    "type_line": "Creature - Spirit Warrior",
                    "oracle_text": "Haste\n\nWhenever Cindershard Raider attacks, you may sacrifice an artifact. If "
                                   "you do, it gains first strike and \"When this creature dies, it deals 3 damage to "
                                   "any target\" until end of turn.",
                    "colors": ["BR"],
                    "set": "thb",
                    "rarity": "uncommon",
                    "artist": "Vincent Bons",
                    "power": "4",
                    "toughness": "3",
                    "flavor_text": "The rift-touched burn twice—once in battle, once in the memory of the dead."
                }
            },
            {
                "input": {
                    "name": "Molten Cataclysm",
                    "mana_cost": "{2}{R}{R}{G}",
                    "type": "Sorcery",
                    "rarity": "Rare",
                    "power": None,
                    "toughness": None,
                    "text": "Destroy all artifacts, then destroy target land for each artifact destroyed this "
                            "way.\nIf Molten Cataclysm had three or more colors spent to cast it, create a 5/5 red "
                            "Elemental creature token with trample.",
                    "flavor": "The Scavenger Tribes see opportunity in fire and ruin.",
                    "colors": ["R", "G"],
                    "image_path": "output/20250208_152032/Molten_Cataclysm.png",
                    "collector_number": "89"
                },
                "output": {
                    "name": "Molten Cataclysm",
                    "layout": "normal",
                    "collector_number": "89",
                    "image_uris": {
                        "art_crop": "../card-generator/output/20250208_152032/Molten_Cataclysm.png"
                    },
                    "mana_cost": "{2}{R}{R}{G}",
                    "type_line": "Sorcery",
                    "oracle_text": "Destroy all artifacts, then destroy target land for each artifact destroyed this "
                                   "way.\n\nIf Molten Cataclysm had three or more colors spent to cast it, "
                                   "create a 5/5 red Elemental creature token with trample.",
                    "colors": ["RG"],
                    "set": "thb",
                    "authority": None,
                    "rarity": "rare",
                    "artist": "Vincent Bons",
                    "flavor_text": "The Scavenger Tribes see opportunity in fire and ruin."
                }
            },
            {
                "input": {
                    "name": "Plains 1",  # Example of a basic land with variation number
                    "mana_cost": "",
                    "type": "Basic Land — Plains",
                    "rarity": "Common",
                    "power": None,
                    "toughness": None,
                    "text": "",
                    "flavor": "",
                    "colors": ["W"],
                    "image_path": "output/20250208_152032/Plains_1.png",
                    "collector_number": "201"
                },
                "output": {
                    "name": "Plains",  # Note: The renderer expects just "Plains" without the variation number
                    "layout": "normal",
                    "collector_number": "201",
                    "image_uris": {
                        "art_crop": "../card-generator/output/20250208_152032/Plains_1.png"
                    },
                    "mana_cost": "",
                    "type_line": "Basic Land - Plains",
                    "oracle_text": "",
                    "colors": ["W"],
                    "set": "thb",
                    "rarity": "common",
                    "artist": "Vincent Bons",
                    "flavor_text": ""
                }
            }
        ]

        prompt = f"""Convert the following MTG card data to the rendering format following these rules:

        # Valid Color Values (based on file structure)
        Single colors: W, U, B, R, G
        Dual colors: WU, WB, WR, WG, UB, UR, UG, BR, BG, RG
        Special types: Artifact, Vehicle, Land, Gold
        Icon values: 0, 1, 2, 2B, 2G, 2R, 2U, 2W, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 100, 1000000, A, B, BG, BGP, BP, BR, BRP, C, CB, CG, CHAOS, CP, CR, CU, CW, D, E, G, GP, GU, GUP, GW, GWP, H, HALF, HR, HW, INFINITY, L, P, PW, Q, R, RG, RGP, RP, RW, RWP, S, T, TK, U, UB, UBP, UP, UR, URP, W, WB, WBP, WP, WU, WUP, X, Y, Z

        # Transformation Rules
        1. Use the image_path from input, but prepend "../card-generator/" to the path
        2. Convert colors from individual letters to paired format (e.g., ["G", "W"] becomes ["WG"])
        3. Set 'layout' to "normal"
        4. Set 'set' to "thb"
        5. Set 'artist' to "Vincent Bons"
        6. Convert all power/toughness values to strings, when they exist. Otherwise don't include them
        7. Replace "—" with "-" in type_line
        8. Add double newlines between separate rules in oracle_text
        9. Include the collector_number from the input exactly as provided
        10. Convert the card text to oracle_text, handling line breaks and quotes properly
        11. Convert type to type_line
        12. Convert flavor to flavor_text (when present)
        13. Make rarity lowercase in the output, and use only from values: common, uncommon, rare, mythic
        14. Add an authority field for Planeswalker cards
        15. Basic land cards have no text, so set text to "".
        16. For basic lands (Plains, Island, Swamp, Mountain, Forest), if the name includes a variation number (e.g., "Plains 1"), 
            remove the variation number in the output name, but keep the image path as is.

        Here are some examples:

        Example 1:
        Input: {json.dumps(example_pairs[0]["input"], indent=2)}

        Output: {json.dumps(example_pairs[0]["output"], indent=2)}

        Example 2:
        Input: {json.dumps(example_pairs[1]["input"], indent=2)}

        Output: {json.dumps(example_pairs[1]["output"], indent=2)}

        Example 3:
        Input: {json.dumps(example_pairs[2]["input"], indent=2)}

        Output: {json.dumps(example_pairs[2]["output"], indent=2)}

        Example 4 (Basic Land):
        Input: {json.dumps(example_pairs[3]["input"], indent=2)}

        Output: {json.dumps(example_pairs[3]["output"], indent=2)}

        Now convert this card data to the same format:
        {json.dumps(card_data, indent=2)}

        Return only the JSON object with no additional text."""

        return prompt

    def convert_file(self, input_path: Path, max_retries: int = 3) -> Dict:
        """Convert a single JSON file with retries."""
        with open(input_path, 'r', encoding='utf-8') as f:
            input_json = json.load(f)

        return self.convert_to_rendering_format(input_json, max_retries=max_retries)

    def convert_directory(self, input_dir: Path, output_dir: Path, max_retries: int = 3) -> None:
        """Convert all JSON files in a directory with retries, excluding mtg_set_output.json."""
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create a separate directory for rendering format
        render_dir = output_dir / "render_format"
        render_dir.mkdir(parents=True, exist_ok=True)

        for json_file in input_dir.glob("*.json"):
            # Skip mtg_set_output.json
            if json_file.name == "mtg_set_output.json" or json_file.name == "mtg_set_complete.json":
                continue

            print(f"\nConverting {json_file.name}...")
            try:
                converted_json = self.convert_file(json_file, max_retries=max_retries)

                # Save to new directory with _render suffix
                output_filename = json_file.stem + "_render.json"
                output_path = render_dir / output_filename
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(converted_json, f, indent=2)

                print(f"Successfully saved to {output_path}")
            except Exception as e:
                print(f"Failed to convert {json_file.name} after {max_retries} attempts: {e}")

    def convert_cards(self, cards: List[Card], output_dir: Path, max_retries: int = 3) -> List[Path]:
        """Convert a list of cards to rendering format and save to output directory.

        Returns:
            List of paths to the generated render JSON files
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create a separate directory for rendering format
        render_dir = output_dir / "render_format"
        render_dir.mkdir(parents=True, exist_ok=True)

        render_paths = []

        for card in cards:
            # Skip cards without JSON files
            card_json_path = output_dir / f"{card.name.replace(' ', '_')}.json"
            if not card_json_path.exists():
                print(f"Warning: JSON file for {card.name} not found at {card_json_path}")
                continue

            print(f"\nConverting {card.name}...")
            try:
                converted_json = self.convert_file(card_json_path, max_retries=max_retries)

                # Save to new directory with _render suffix
                output_filename = card_json_path.stem + "_render.json"
                output_path = render_dir / output_filename
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(converted_json, f, indent=2)

                render_paths.append(output_path)
                print(f"Successfully saved to {output_path}")
            except Exception as e:
                print(f"Failed to convert {card.name} after {max_retries} attempts: {e}")

        return render_paths
