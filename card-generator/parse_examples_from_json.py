import csv
import os

# Define the path to the CSV file
CSV_FILE_PATH = "./assets/mtg_cards_english.csv"


# Function to parse the CSV and extract relevant data
def parse_mtg_cards(file_path, num_cards=10):
    """Reads and parses MTG cards from a CSV file."""

    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    parsed_cards = []

    with open(file_path, newline='', encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)  # Read CSV into a dictionary format

        for row in reader:
            card_data = {
                "name": row.get("name", "Unknown"),
                "mana_cost": row.get("mana_cost", "N/A"),
                "type": row.get("type", "Unknown"),
                "rarity": row.get("rarity", "Unknown"),
                "power_toughness": f"{row.get('power', '?')}/{row.get('toughness', '?')}" if row.get(
                    'power') and row.get('toughness') else "N/A",
                "abilities": row.get("text", "No abilities listed."),
                "flavor_text": row.get("flavor", "No flavor text."),
                "colors": row.get("colors", "Colorless"),
                "set_name": row.get("set_name", "Unknown Set")
            }

            parsed_cards.append(card_data)

            if len(parsed_cards) >= num_cards:
                break  # Stop after fetching `num_cards` cards

    return parsed_cards


# Function to display card details in a readable format
def display_cards(cards):
    """Prints parsed card details in a structured format."""
    for card in cards:
        print(f"\n**Basic Card Information**")
        print(f"* Name: {card['name']}")
        print(f"* Mana Cost: {card['mana_cost']}")
        print(f"* Type: {card['type']}")
        print(f"* Rarity: {card['rarity']}")
        print(f"* Colors: {card['colors']}")
        print(f"* Set: {card['set_name']}")

        if card["power_toughness"] != "N/A":
            print(f"* Power / Toughness: {card['power_toughness']}")

        print("\n**Rules Text (Abilities and Effects)**")
        print(f"{card['abilities']}\n")

        print("**Flavor Text**")
        print(f"*{card['flavor_text']}*")
        print("-" * 50)  # Separator between cards


# Main execution
if __name__ == "__main__":
    cards = parse_mtg_cards(CSV_FILE_PATH, num_cards=5)  # Change num_cards as needed
    if cards:
        display_cards(cards)