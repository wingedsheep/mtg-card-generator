Looking at the code more carefully, I can see the actual model IDs. Here's the corrected README:

# MTG Card Generator

Generate complete Magic: The Gathering card sets using AI. Creates thematically cohesive sets with synergistic mechanics, unique artwork, and proper card balance.

## Generated Example Cards

![Example Card 1](example-cards/example1.png)
![Example Card 2](example-cards/example2.png)
![Example Card 3](example-cards/example3.png)

## What It Does

- **Complete Set Generation**: Creates 260 cards by default (20 batches × 13 cards each)
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
2. Create 260 cards with proper color/rarity distribution
3. Generate AI artwork for each card
4. Render cards as high-quality images
5. Save everything to `output_sets/[timestamp]/`

## Configuration Guide

Edit `settings.json` to customize your setup:

### API Keys Section

The `api_keys` section stores your authentication credentials:
- **openrouter**: Your OpenRouter API key for text generation
- **replicate**: Your Replicate API key for image generation

### Image Generation Settings

The `image_generation` section controls how card artwork is created:

**strategy**: Choose between "replicate" (cloud-based, recommended) or "diffusers" (local generation)

**Replicate Configuration** (when strategy is "replicate"):
- **selected_model_type**: Which model to use - "imagen" (default, Google Imagen 4) or "flux" (Black Forest Labs FLUX 1.1 Pro)
- **models**: Contains configuration for each model type:
  - **id**: The specific model version (e.g., "google/imagen-4" or "black-forest-labs/flux-1.1-pro")
  - **params**: Model-specific parameters like output format, aspect ratios, and safety settings
- **cropping**: Options to crop images to specific aspect ratios after generation

**Diffusers Configuration** (when strategy is "diffusers" for local generation):
- **model_id**: The Hugging Face model to use (default: "stabilityai/stable-diffusion-xl-base-1.0")
- **device**: Hardware to use - "auto" (automatic detection), "cuda" (NVIDIA GPU), "mps" (Apple Silicon), or "cpu"
- **dtype**: Precision setting - "auto", "float32", or "float16"
- **params**: Generation parameters like number of inference steps and guidance scale
- **dimensions**: Image sizes for standard cards and saga cards

### Language Model Settings

The `language_model` section configures text generation:

**strategy**: Choose between "openrouter" (cloud-based, recommended) or "ollama" (local models)

**OpenRouter Configuration**:
- **base_url**: API endpoint (default: "https://openrouter.ai/api/v1")
- **models**: Different models for different tasks:
  - **default_main**: General text generation (default: "openai/gpt-4o-mini")
  - **default_json**: JSON-specific tasks
  - **art_prompt_generation**: Creating image prompts
  - **theme_generation**: Developing set themes
  - **card_batch_generation**: Creating card mechanics
  - **json_conversion_from_text**: Converting text to JSON
  - **render_format_conversion**: Converting to rendering format
- **params**: Default parameters like temperature and max_tokens
- **json_params**: Special parameters for JSON generation tasks

**Ollama Configuration** (for local models):
- **host**: URL where Ollama is running. Use "http://localhost:11434" for native installation or Docker
- **models**: Same task-specific model selection as OpenRouter
- **params**: Generation parameters
- **json_params**: Parameters for JSON tasks, including format: "json" for structured output
- **stream**: Whether to stream responses (default: false)

### Operational Settings

The `operational_settings` section controls the generation process:

- **inspiration_cards_count**: Number of real MTG cards to analyze for inspiration (default: 50)
- **batches_count**: How many batches of cards to generate (default: 20)
- **theme_prompt**: A prompt to guide theme generation, like "Varied set with many creature types"
- **complete_theme_override**: Provide a complete custom theme instead of generating one (null to disable)
- **generate_basic_lands**: Whether to create basic land variations (default: true)
- **land_variations_per_type**: Number of art variants per basic land type (default: 3)
- **rarities_per_batch**: Card distribution per batch:
  - mythic: 1 card
  - rare: 3 cards
  - uncommon: 4 cards
  - common: 5 cards
  - Total: 13 cards per batch × 20 batches = 260 cards
- **color_distribution_targets**: Target percentage for each color (W/U/B/R/G each at 0.2 = 20%)

### Other Settings

- **output_directory_base**: Where to save generated sets (default: "output_sets")
- **api_headers**: Additional HTTP headers for API requests

## Running Models Locally

Local generation provides complete control and no API costs, though quality may be lower than cloud services.

### Local Image Generation with Diffusers

Requires a GPU with 8GB+ VRAM for best results. The system will automatically download the selected Stable Diffusion model (2-7GB) on first use. Generation takes 10-60 seconds per image depending on your hardware.

### Local Text Generation with Ollama

Two options for running Ollama:

**Option 1: Docker (Recommended)**
```bash
# Start Ollama with Docker Compose
docker-compose up -d

# Download a model (4-40GB depending on choice)
docker exec mtg-ollama ollama pull llama3

# In settings.json, set host to "http://localhost:11434"
```

**Option 2: Native Installation**
```bash
# Install from https://ollama.com/
# Then download models
ollama pull llama3
ollama pull mistral  # Good for JSON tasks

# In settings.json, set host to "http://localhost:11434"
```

Popular model choices:
- **llama3**: Best general purpose (4.7GB)
- **mistral**: Excellent for JSON tasks (4.1GB)
- **llama3.2:1b**: Fast but lower quality (1.3GB)
- **llama3:70b**: Highest quality but requires 40GB+ RAM

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
- Expect to spend $10-15 in API costs for a complete 260-card set (mostly image generation at ~$0.05 per card)
- First-time local setup downloads 2-7GB for image models, 4-40GB for language models
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