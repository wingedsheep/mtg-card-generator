"""All prompt-building functions for the MTG card generator.

Each function is a pure function that returns a prompt string, keeping
the generator modules focused on orchestration and API calls.
"""

from typing import Dict, List, Optional


def build_theme_prompt(inspiration_summary: str, theme_prompt: Optional[str] = None) -> str:
    """Build the prompt for set theme generation.

    Extracted from MTGSetGenerator._get_theme_prompt().
    """
    base_prompt = f"""
        Some inspirational cards. These cards are not in the set and not part of the theme. You can just use them to get a feel for the mechanics, types etc.:
        {inspiration_summary}

        Create a detailed theme for a new Magic The Gathering set. The world should feel rich, layered, and diverse — NOT centered around a single concept or aesthetic.

        Build a world with:

        1. **Geography & Biomes** (at least 4-5 distinct regions):
           - The world should span contrasting environments (e.g. volcanic wastelands, deep ocean trenches, ancient forests, floating sky-islands, underground fungal networks, frozen tundra, etc.)
           - Each region has its own ecosystem, dangers, and resources
           - Describe how these regions interact — trade routes, contested borders, migration paths

        2. **Factions & Civilizations** (at least 3-4 major factions):
           - Each faction should have distinct goals, culture, and methods
           - Factions should span different colors — no faction should map to just one color
           - Include tensions, alliances, and rivalries BETWEEN factions
           - Some factions may span multiple regions; some regions may host competing factions

        3. **History & Lore**:
           - A deep backstory with at least one major historical event that shaped the current world
           - Notable characters/creatures tied to different factions and regions (not all on the same side)
           - Ongoing conflicts or mysteries that the set's story explores
           - The world should feel like it existed before this set and will continue after

        4. **Creature Types** (CRITICAL — maximize diversity):
           - Include a WIDE variety of creature types: humanoids, beasts, insects, oozes, horrors, elementals, spirits, constructs, fungi, plants, wurms, drakes, leviathans, nightmares, shapeshifters, etc.
           - Every region should have its own unique endemic creatures that couldn't exist anywhere else
           - Include bizarre, alien, and unsettling creatures — not everything should be conventionally cool or pretty
           - Describe small parasitic organisms, massive apex predators, hive-mind colonies, symbiotic pairs, and everything in between
           - Some creatures should be mysterious or defy easy categorization
           - Not all creatures should fit neatly into one theme — include oddities, neutral wildlife, and things that don't belong to any faction
           - INVENT new creature types unique to this world. Don't only use existing MTG creature types — come up with original species that feel native to this setting


        5. **Mechanical Themes & Gameplay**:
           - Main mechanical themes and gameplay elements. Don't introduce new mechanics, just describe how existing ones are used
           - Different regions or factions can emphasize different play patterns
           - Potential synergies between different card types and mechanics
           - How the theme supports different play styles (aggro, control, midrange, combo)

        6. **The In-Between**:
           - Wanderers, outcasts, and neutral parties that don't belong to any faction
           - Wild magic, ancient ruins, or natural phenomena that exist outside faction control
           - Moral ambiguity — no faction is purely good or evil
           - Strange phenomena, cursed locations, and unexplained occurrences

        Important guidelines:
        - Try to come up with original made-up names for characters, locations, and events. Not combinations of meaningful words like "Blooming Spire" or "Shadow Citadel", but rather unique, invented names.
        - The set should NOT feel like it revolves around one central gimmick or aesthetic. It should feel like a living world with many stories happening at once.
        - Keep the color distribution in mind — every color should have a strong presence with its own identity in this world.
        - Be as detailed as possible to create a rich and engaging world for the set.
        - Think about the TONE range: some parts of the world are whimsical, some are horrifying, some are melancholic, some are awe-inspiring. Not everything should have the same emotional register.

        """

    if theme_prompt:
        base_prompt = f"""Base the theme on the following prompt: {theme_prompt}

{base_prompt}"""

    return base_prompt


def _get_representation_level(diff: float) -> str:
    """Describe how far a color is from its target representation.

    Helper for build_batch_prompt().
    """
    percentage_diff = (diff / 0.2) * 100

    if abs(percentage_diff) < 10:
        return "well-balanced"
    elif abs(percentage_diff) < 25:
        return "slightly " + ("under" if diff > 0 else "over") + "-represented"
    elif abs(percentage_diff) < 50:
        return "significantly " + ("under" if diff > 0 else "over") + "-represented"
    else:
        return "severely " + ("under" if diff > 0 else "over") + "-represented"


def build_batch_prompt(
    inspiration_cards_text: str,
    set_theme: str,
    existing_cards_text: str,
    current_distribution: Dict[str, float],
    mythics_per_batch: int,
    rares_per_batch: int,
    uncommons_per_batch: int,
    commons_per_batch: int,
) -> str:
    """Build the prompt for batch card generation.

    Extracted from MTGSetGenerator._get_batch_prompt().
    """
    cards_per_batch = (mythics_per_batch + rares_per_batch +
                       uncommons_per_batch + commons_per_batch)

    color_analysis = f"""Color Distribution Analysis:
        - White (W): {abs(0.2 - current_distribution.get('W', 0)) * 100:.1f}% {_get_representation_level(0.2 - current_distribution.get('W', 0))}
        - Blue (U): {abs(0.2 - current_distribution.get('U', 0)) * 100:.1f}% {_get_representation_level(0.2 - current_distribution.get('U', 0))}
        - Black (B): {abs(0.2 - current_distribution.get('B', 0)) * 100:.1f}% {_get_representation_level(0.2 - current_distribution.get('B', 0))}
        - Red (R): {abs(0.2 - current_distribution.get('R', 0)) * 100:.1f}% {_get_representation_level(0.2 - current_distribution.get('R', 0))}
        - Green (G): {abs(0.2 - current_distribution.get('G', 0)) * 100:.1f}% {_get_representation_level(0.2 - current_distribution.get('G', 0))}

        Priority for upcoming cards:
        1. Colors that are severely under-represented should be highest priority
        2. Colors that are significantly under-represented should be high priority
        3. Colors that are over-represented should be generated less in this batch
        4. Maintain overall color balance"""

    return f"""Based on the following context for a Magic The Gathering set:

        Some inspirational cards. Just use these for mechanics, types etc. These cards are not in the set and not part of the theme:
        {inspiration_cards_text}

        Theme:
        {set_theme}

        # Card Rarity Guidelines

        ## Common
        - Simple, vanilla effects that work in multiples
        - Basic creature types and spells
        - Usually clean, short rules text, or no rules at all
        - Foundation of gameplay mechanics

        ## Uncommon
        - Moderately complex abilities
        - Support for specific strategies
        - Clear synergies with other cards

        ## Rare
        - Format-defining effects
        - Important characters or spells
        - Unique mechanics
        - Can shape deck strategies

        ## Mythic Rare
        - Game-changing effects
        - Major characters
        - Splashy, memorable designs
        - Build-around centerpieces

        Existing cards in the set:
        {existing_cards_text}

        Color analysis:
        {color_analysis}

        Instructions:

        - Create a batch of new cards that fit into the theme of the set.
        - Think of how this batch adds to the existing cards in the set.
        - Make sure this batch has some memorable cards.
        - Ensure that these cards are different enough from the cards already in the set. They should add to the variety and depth of the set.
        - Think about already existing cards, and how the cards in this batch complement those cards.
        - Cards in this batch are varied and different enough from the existing cards in the set.
        - Think about the color distribution analysis above and prioritize underrepresented colors.
        - Try to keep card types in the set well-balanced. Also, make sure the color distribution in the whole set is balanced. Artifacts and colorless cards are also important, if they fit the theme.
        - Make sure the color distribution in the whole set is balanced. Artifacts and colorless cards are also important, if they fit the theme.
        - ALWAYS include an explanation between brackets for less common mechanics.
        Well known mechanics like flying, haste, etc. do not need explanations.
        - Think about synergy in the set.
        - Look at the rarity instructions.
        - Multi color cards are fine, but they appear less frequently than mono color cards.\
        - No dual sided cards

        VARIETY IS CRITICAL — follow these rules to avoid sameness:
        - Look at the creature types already in the set. Actively pick DIFFERENT creature types for this batch. If the set has many Soldiers and Warriors, make an Ooze, a Fungus, a Wurm, or a Nightmare instead.
        - Include at least one creature with a weird or unusual creature type (e.g. Sliver, Crab, Jellyfish, Ooze, Eye, Homarid, Lhurgoyf, Treefolk, Scarecrow, Atog, Shapeshifter, Chimera).
        - Vary the TONE of cards: include at least one card that is humorous, eerie, tragic, or whimsical — not everything should feel epic and grand.
        - Vary card designs: include utility spells, combat tricks, build-around enchantments, equipment, and niche cards — not just efficient creatures and removal.
        - Don't make every creature a humanoid fighter or mage. Include animals, parasites, swarm creatures, animated objects, and alien beings.
        - Be original — invent new creature types that are unique to this set's world. Not every creature needs to use an existing MTG creature type.
        - Flavor text should vary in style: some poetic, some dialogue, some ominous, some matter-of-fact. Avoid a uniform "epic fantasy" voice.
        - Some cards should depict small, mundane, or overlooked aspects of the world — a pest, a common tool, a forgotten ruin, daily life.

        First make a plan for the rare and mythic cards of this batch, what are they going to be? (notable characters described in the theme are fine as long as they are not already in the set).
        Then think of what would be a good addition to add some variety to the set and make it more interesting. What could we add to the uncommon and common cards?
        Before finalizing the plan, review the existing cards and specifically ask: what creature types, card types, and tones are MISSING or underrepresented? Prioritize filling those gaps.
        Keeping in mind the number of rarities in this batch. These could inspire the cards in the batch.
        Make a short plan for the batch, write it down, and then start creating the cards.

        Then generate {cards_per_batch} new cards, fitting the theme, with the following rarity distribution:
        - {mythics_per_batch} Mythic Rare
        - {rares_per_batch} Rare
        - {uncommons_per_batch} Uncommon
        - {commons_per_batch} Common

        For each card, provide a complete description in this format:
        Card Name (Rarity)
        Mana Cost: [cost]
        Type: [type]
        Power/Toughness: [P/T] (if creature)
        Loyalty: [loyalty] (if planeswalker)
        Rules Text: [text]
        Flavor Text: [flavor]
        Colors: [colors]
        Description: [short lore + visual description]"""


def build_text_to_json_prompt(cards_text: str) -> str:
    """Build the prompt for converting card text descriptions to JSON.

    Extracted from MTGSetGenerator.convert_text_to_json().
    """
    return f"""Convert the following Magic: The Gathering card descriptions into a JSON array.
Each card has the following fields: name, mana_cost, type, rarity, power (null if not creature),
toughness (null if not creature), loyalty (null if not planeswalker), text, flavor, colors (array of W, U, B, R, G or none if colorless), description.

class Card:
    name: str
    mana_cost: str
    type: str
    rarity: str
    text: str
    colors: List[str]
    flavor: Optional[str] = None
    power: Optional[str] = None
    toughness: Optional[str] = None
    loyalty: Optional[str] = None
    set_name: str = ""
    art_prompt: Optional[str] = None
    image_path: Optional[str] = None
    collector_number: Optional[str] = None
    description: str = ""

Cards to convert:

{cards_text}

Return only the JSON array with no additional text or explanation."""


def build_art_prompt(
    card_name: str,
    card_type: str,
    card_rarity: str,
    card_text: str,
    card_flavor: Optional[str],
    card_colors: List[str],
    card_power: Optional[str],
    card_toughness: Optional[str],
    card_description: str,
    theme: str,
    is_diffusers: bool,
    attempt: int = 0,
) -> str:
    """Build the prompt for art generation for a card.

    Extracted from MTGArtGenerator.generate_art_prompt_text().
    """
    theme_context = f"""Set Theme Context:
{theme}

Consider this theme when creating the art prompt. The art should reflect both the card's individual characteristics and the overall set theme.""" if theme else ""

    saga_instructions = ""
    if "Saga" in card_type:
        saga_instructions = """
IMPORTANT: This is a Saga card which requires VERTICAL art composition (portrait orientation).
The art should be tall rather than wide. Saga cards display art along the right side of the card in a vertical format.
Create a VERTICAL composition that works well with the Saga card layout.
"""

    if is_diffusers:
        length_instructions = """
CRITICAL: This prompt will be used with Hugging Face Diffusers which has a 77-token limit.
Generate a concise, focused prompt that is MAXIMUM 70 tokens (approximately 50 words).
Focus on the most essential visual elements only. Be concise but vivid.
Prioritize the most important visual aspects of the card.
"""
    else:
        length_instructions = """
- Focus on vivid, detailed scenes reflecting mechanics and flavor.
- Specify composition, lighting, mood, and key details.
"""

    colors_str = ', '.join(card_colors) if card_colors else 'Colorless'

    return f"""Create a detailed art prompt for a Magic: The Gathering card.
{saga_instructions}
Theme: {theme_context}
Card Name: {card_name}
Type: {card_type}
Rarity: {card_rarity}
Card Text: {card_text}
Flavor Text: {card_flavor}
Colors: {colors_str}
P/T: {card_power}/{card_toughness} (if applicable)
Description: {card_description}

Instructions for prompt generation:
{length_instructions}
- Start with "Oil on canvas painting. Magic the gathering art. Rough brushstrokes."
- Ensure prompt is safe for work.
- If a character name is present, include their full name.
- Return only the prompt text.
{f"Retry attempt {attempt}: Focus on safety and clarity." if attempt > 0 else ""}
"""


def build_land_art_prompt(land_type: str, theme: str) -> str:
    """Build the prompt for basic land art generation.

    Extracted from MTGLandGenerator.generate_land_prompt().
    """
    return f"""Create a detailed art prompt for a {land_type} basic land card in Magic: The Gathering.

Set Theme Context:
{theme}

This is a variation of the {land_type} for this set. Make it unique and distinct from other variations while still fitting the overall set theme.

Create a vivid, detailed scene that captures the essence of a {land_type}. The art should reflect the color identity and mana characteristics of this land type, while incorporating elements from the set's theme.

The prompt should begin with "Oil on canvas painting. Magic the gathering art. Detailed landscape." and should include elements that make this land distinctly a {land_type} while fitting the theme.

Focus on:
- The landscape features typical of a {land_type}
- The mood and atmosphere that reflects the land's color identity
- How this landscape connects to the set's theme
- What makes this variation unique from other versions of the same land type
- Environmental details, weather conditions, time of day, and lighting that create a distinctive scene
- Any characteristic flora, fauna, or geographical elements associated with this land type

Example land art prompts:

Example 1 (Mountain): "Oil on canvas painting. Magic the gathering art. Detailed landscape. Jagged crimson peaks emerging from mist, with streams of molten lava creating veins of orange light down their faces. The mountain range extends into the distance, with storm clouds gathering above. Lightning strikes illuminate the rugged terrain, revealing ancient dwarven ruins carved into the cliffs. Towering obsidian formations jut from the mountainside, their surfaces reflecting the red glow of sunrise. Small geysers of steam and fire erupt periodically across the mountain face."

Example 2 (Island): "Oil on canvas painting. Magic the gathering art. Detailed landscape. A secluded cove surrounded by towering blue-crystal formations that rise from turquoise waters. Spiral-shaped coral formations emit an ethereal blue glow beneath the water's surface. A small rocky island at the center features a twisted, wind-sculpted tree with luminescent blue leaves. Mist hangs over the waters, creating an otherworldly atmosphere. The sky above displays unusual cloud formations that mirror the spiral patterns in the water below, with a faint blue sun visible through the haze."

Return only the art prompt text with no additional explanation."""
