# MTG Card Generator

# Default: list available recipes
default:
    @just --list

# Install Python dependencies
install:
    pip install -r requirements.txt

# Install Playwright browsers (needed for card rendering)
install-browsers:
    playwright install chromium

# Generate a complete MTG set
generate:
    cd card-generator && python main.py

# Resume the latest incomplete set
resume:
    cd card-generator && python main.py --resume

# Resume a specific incomplete set by ID
resume-set SET_ID:
    cd card-generator && python main.py --resume "{{SET_ID}}"

# Re-render cards from an existing output folder (opens folder picker)
rerender:
    cd card-generator && python tools/batch_rerender.py

# Re-render cards from a specific folder
rerender-folder folder:
    cd card-generator && python tools/batch_rerender.py --folder "{{folder}}"

# Generate booster packs (opens GUI)
boosters:
    cd card-generator && python mtg_booster_generator.py

# Convert cards to Tabletop Simulator format (opens GUI)
tts:
    cd card-generator && python tts_deck_converter.py

# Start Ollama via Docker (for local LLM)
ollama-up:
    docker compose up -d ollama

# Start Ollama + Web UI via Docker
ollama-up-all:
    docker compose up -d

# Stop Docker services
ollama-down:
    docker compose down

# Run tests
test:
    cd card-generator && python -m pytest tests/ -v
