import sys
from pathlib import Path
import os

print(f"Initial sys.path: {sys.path}")
print(f"Current working directory: {os.getcwd()}")

project_root = Path(__file__).resolve().parents[2]
print(f"Calculated project_root: {project_root}")

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"Modified sys.path: {sys.path}")
else:
    print(f"project_root '{project_root}' already in sys.path")

print(f"Attempting to import card_generator.models...")
try:
    from card_generator import models
    print("Successfully imported card_generator.models")
    print(f"Location of models: {models.__file__}")
    from card_generator.models import Config
    print("Successfully imported Config from card_generator.models")
except Exception as e:
    print(f"Error importing: {e}")

print("\nListing /app/card_generator:")
# Use ls tool instead of os.system
# os.system("ls -l /app/card_generator")
