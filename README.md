# MTG Card Generator

Generate complete Magic: The Gathering card sets using AI. Creates thematically cohesive sets with synergistic mechanics, unique artwork, and proper card balance.

## Generated Example Cards

![Example Card 1](example-cards/example1.png)
![Example Card 2](example-cards/example2.png)
![Example Card 3](example-cards/example3.png)

## What It Does

- **Complete Set Generation**: Creates 100+ card sets with balanced rarities and colors
- **AI-Powered Content**: 
  - Generates unique card mechanics, abilities, and flavor text
  - Creates original artwork for every card
  - Develops cohesive set themes and lore
- **Professional Rendering**: Renders cards using authentic MTG frame styles
- **Play-Ready Output**:
  - Tabletop Simulator integration with properly formatted deck sheets
  - Booster draft packs with correct rarity distribution
  - High-resolution PNG exports for printing

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js and a modern web browser
- API keys from [OpenRouter](https://openrouter.ai/) and [Replicate](https://replicate.com/) (recommended)

### Installation

```bash
# Clone and setup
git clone https://github.com/yourusername/mtg-card-generator.git
cd mtg-card-generator
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
playwright install

# Configure
cp card-generator/settings.example.json card-generator/settings.json
# Edit settings.json with your API keys
```

### Generate Your First Set

```bash
cd card-generator
python main.py
```

The system will:
1. Generate a unique set theme
2. Create ~100 cards with proper color/rarity distribution
3. Generate AI artwork for each card
4. Render cards as high-quality images
5. Save everything to `output_sets/[timestamp]/`

## Configuration Guide

Edit `settings.json` to customize your setup:

### API Keys
- `openrouter`: Your OpenRouter API key for text generation
- `replicate`: Your Replicate API key for image generation

### Image Generation Settings

**Strategy Options:**
- `"replicate"` (recommended): Cloud-based, high quality, costs ~$0.05 per image
- `"diffusers"`: Local generation, free but requires GPU, slower

**Replicate Models:**
- `"imagen"` (default): Google Imagen 3 - excellent quality and fast
- `"flux"`: Black Forest Labs FLUX - alternative high-quality option

**Diffusers Settings (if using local):**
- `model_id`: Which Stable Diffusion model to use (default: `stabilityai/stable-diffusion-xl-base-1.0`)
- `device`: `"auto"`, `"cuda"` (NVIDIA), `"mps"` (Apple Silicon), or `"cpu"`
- `dimensions`: Image sizes for different card types

### Language Model Settings

**Strategy Options:**
- `"openrouter"` (recommended): Access to GPT-4, Claude, and other top models
- `"ollama"`: Local models, free but lower quality

**Model Selection:**
Different models can be used for different tasks:
- `default_main`: General text generation
- `art_prompt_generation`: Creating image prompts
- `theme_generation`: Developing set themes
- `card_batch_generation`: Creating card mechanics
- `json_conversion`: Converting between formats

### Operational Settings

- `inspiration_cards_count`: How many real MTG cards to use as inspiration (default: 50)
- `batches_count`: Number of card batches to generate (default: 20)
- `theme_prompt`: Guide the theme generation (e.g., "Epic fantasy with dragons")
- `complete_theme_override`: Provide your own complete theme instead of generating one
- `generate_basic_lands`: Whether to create basic land variations (default: true)
- `land_variations_per_type`: How many art variants per basic land (default: 3)
- `rarities_per_batch`: Card distribution per batch (1 mythic, 3 rares, 4 uncommons, 5 commons)
- `color_distribution_targets`: Target percentage for each color (default: 20% each)

## Local Generation Option

While cloud services provide better quality, you can run everything locally:

### Local Setup

1. **For Image Generation**: Install PyTorch with GPU support
   ```bash
   # NVIDIA GPU
   pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   
   # Apple Silicon
   pip3 install torch torchvision torchaudio
   ```

2. **For Text Generation**: Use Docker Compose
   ```bash
   docker-compose up -d
   docker exec mtg-ollama ollama pull llama3
   ```

3. **Configure for local**:
   ```json
   {
     "image_generation": { "strategy": "diffusers" },
     "language_model": { "strategy": "ollama" }
   }
   ```

## Additional Tools

### Tabletop Simulator Integration

Convert your cards into TTS-compatible deck sheets:
```bash
cd card-generator
python tts_deck_converter.py
```

### Booster Draft Generator

Create draft boosters with proper rarity distribution:
```bash
cd card-generator
python mtg_booster_generator.py
```

Features:
- 15-card boosters (1 rare/mythic, 3 uncommons, 11 commons)
- Special land packs with all art variations
- Ready for Tabletop Simulator import

## Output Structure

Generated sets are saved to `output_sets/[timestamp]/` containing:
- `mtg_set_complete.json`: Complete set data with statistics
- `card_images/`: Individual card artwork
- `rendered_cards/`: Final card images with frames
- `render_format/`: Cards formatted for the renderer
- `boosters/`: TTS-ready booster packs (if generated)

## Tips for Best Results

- **Cloud services** (OpenRouter + Replicate) produce the highest quality output
- **Local models** offer more control and no API costs but lower quality
- Expect to spend $5-8 in API costs for a complete 100+ card set (mostly image generation)
- First-time local setup downloads 2-7GB of model files
- GPU recommended for local image generation (8GB+ VRAM for best results)

## Acknowledgments

- Card rendering system based on [MTG Render](https://www.mtgrender.tk/) by Yoann 'Senryoku' Maret-Verdant
- Magic: The Gathering is a trademark of Wizards of the Coast LLC
- AI art generation powered by:
  - **Local**: Hugging Face Diffusers, Stability AI (Stable Diffusion)
  - **Cloud**: Replicate, Black Forest Labs (FLUX), Google (Imagen)
- Card generation powered by:
  - **Local**: Ollama with Llama, Mistral
  - **Cloud**: OpenRouter, OpenAI, Claude

Special thanks to Yoann 'Senryoku' Maret-Verdant for creating the original MTG card renderer ([GitHub](https://github.com/Senryoku)) which forms the foundation of our card rendering system.