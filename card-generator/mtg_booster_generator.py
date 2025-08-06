#!/usr/bin/env python3
"""
MTG Booster Generator — PyQt6 Edition
=============================================
* 15-card draft boosters (1 rare/mythic · 3 uncommons · 11 commons; no basic lands)
* One land-only booster per basic type with all art variants
* Modern PyQt6 UI that works reliably on all platforms including macOS dark mode
"""

import json
import math
import os
import random
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFileDialog,
                             QMessageBox, QProgressBar, QSpinBox, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont

# Check for required dependencies without using QMessageBox (since QApplication doesn't exist yet)
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    print("Error: Missing Dependencies")
    print("This program requires Pillow.")
    print("Please install it using: pip install Pillow")
    print(f"Import error details: {e}")
    sys.exit(1)

# Basic land types
BASIC_TYPES = ("Plains", "Island", "Swamp", "Mountain", "Forest")


def create_card_sheets(image_files, max_rows, max_columns, card_width, card_height, sort_files=False):
    """Create one or more card sheets from the provided image files.
    This function is adapted from tts_deck_converter to avoid tkinter dependency."""
    if sort_files:
        image_files.sort()

    # Calculate how many cards can fit in one sheet
    cards_per_sheet = max_rows * max_columns

    # Calculate how many sheets we'll need
    num_sheets = math.ceil(len(image_files) / cards_per_sheet)

    sheets = []
    for sheet_idx in range(num_sheets):
        # Calculate which images go on this sheet
        start_idx = sheet_idx * cards_per_sheet
        end_idx = min(start_idx + cards_per_sheet, len(image_files))
        sheet_images = image_files[start_idx:end_idx]

        # Calculate actual rows needed for this sheet (might be less than max for the last sheet)
        actual_rows = math.ceil(len(sheet_images) / max_columns)

        # Create a new blank image for the card sheet
        sheet_width = max_columns * card_width
        sheet_height = actual_rows * card_height
        card_sheet = Image.new('RGB', (sheet_width, sheet_height), (255, 255, 255))

        # Place each card on the sheet
        for i, file_path in enumerate(sheet_images):
            try:
                # Open and resize the card image
                with Image.open(file_path) as img:
                    # Convert to RGB mode if necessary (for PNG transparency, etc.)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    # Resize image to fit card dimensions
                    img = img.resize((card_width, card_height), Image.LANCZOS)

                    # Calculate position in the grid
                    row = i // max_columns
                    col = i % max_columns
                    x = col * card_width
                    y = row * card_height

                    # Paste the card onto the sheet
                    card_sheet.paste(img, (x, y))

                print(f"Processed: {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

        sheets.append((card_sheet, actual_rows, max_columns))

    return sheets


class WorkerSignals(QObject):
    """Signals for worker thread communication."""
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)
    error = pyqtSignal(str)


class BoosterGenerator(QThread):
    """Worker thread for booster generation."""

    def __init__(self, set_dir: Path, booster_count: int):
        super().__init__()
        self.set_dir = set_dir
        self.booster_count = booster_count
        self.signals = WorkerSignals()

        # Initialize card pools
        self._mythics: List[dict] = []
        self._rares: List[dict] = []
        self._uncommons: List[dict] = []
        self._commons: List[dict] = []
        self._basics_by_type: Dict[str, List[dict]] = {t: [] for t in BASIC_TYPES}
        self._image_paths: Dict[str, str] = {}

        # Constants
        self.RARE_MYTHIC_RATIO = 7
        self.RARES_PER_PACK = 1
        self.UNCOMMONS_PER_PACK = 3
        self.COMMONS_PER_PACK = 11

        # Temp file for empty card placeholder
        self.blank_card_path = None

    @staticmethod
    def _card_uid(card: dict) -> str:
        """Generate a unique ID for a card."""
        return f"{card.get('collector_number', '0')}_{card.get('name')}"

    def _load_set(self) -> bool:
        """Load cards from the set directory."""
        render_dir = self.set_dir / "render_format"
        images_dir = self.set_dir / "rendered_cards"

        if not render_dir.exists():
            self.signals.error.emit(f"'render_format' folder not found in {self.set_dir}")
            return False

        self.signals.progress.emit(f"Loading cards from {render_dir}...", 0)

        # Reset card pools
        self._mythics = []
        self._rares = []
        self._uncommons = []
        self._commons = []
        self._basics_by_type = {t: [] for t in BASIC_TYPES}
        self._image_paths = {}

        # Load cards from render_format
        card_count = 0
        for jf in render_dir.glob("*_render.json"):
            try:
                card = json.loads(jf.read_text(encoding="utf-8"))
                if card.get("layout") != "normal":
                    continue

                card_count += 1
                rarity = card.get("rarity", "").lower()
                name = card.get("name", "")

                # Handle basic lands
                if "Basic Land" in card.get("type_line", ""):
                    for btype in BASIC_TYPES:
                        if btype in name:
                            self._basics_by_type[btype].append(card)
                            break
                # Handle other cards by rarity
                elif rarity == "mythic":
                    self._mythics.append(card)
                elif rarity == "rare":
                    self._rares.append(card)
                elif rarity == "uncommon":
                    self._uncommons.append(card)
                elif rarity == "common":
                    self._commons.append(card)

                # Find the image path
                if "image_uris" in card and "art_crop" in card["image_uris"]:
                    art_path = card["image_uris"]["art_crop"]
                    # Remove "../card-generator/" prefix if present
                    clean_path = art_path.replace("../card-generator/", "")

                    # Check if it's an absolute path or relative
                    img_path = Path(clean_path)
                    if not img_path.is_absolute():
                        img_path = self.set_dir / clean_path

                    # If the direct path from JSON exists, use it
                    if img_path.exists():
                        self._image_paths[self._card_uid(card)] = str(img_path)
                    # Otherwise check card_images folder
                    elif images_dir.exists():
                        # Try with name variants
                        base_name = name.replace(" ", "_")
                        for img in images_dir.glob(f"{base_name}.*"):
                            self._image_paths[self._card_uid(card)] = str(img)
                            break
            except Exception as exc:
                print(f"⚠ Skipping {jf.name}: {exc}")

        # Perform sanity checks
        errors = []
        if len(self._commons) < self.COMMONS_PER_PACK:
            errors.append(f"Not enough commons ({len(self._commons)}). Need at least {self.COMMONS_PER_PACK}.")
        if len(self._uncommons) < self.UNCOMMONS_PER_PACK:
            errors.append(f"Not enough uncommons ({len(self._uncommons)}). Need at least {self.UNCOMMONS_PER_PACK}.")
        if not (self._rares or self._mythics):
            errors.append("No rares or mythics in set.")

        if errors:
            self.signals.error.emit("\n".join(errors))
            return False

        # Signal success
        summary = (f"Loaded {card_count} cards:\n"
                   f"• {len(self._commons)} commons\n"
                   f"• {len(self._uncommons)} uncommons\n"
                   f"• {len(self._rares)} rares\n"
                   f"• {len(self._mythics)} mythics")

        for land_type, cards in self._basics_by_type.items():
            if cards:
                summary += f"\n• {len(cards)} {land_type}"

        self.signals.progress.emit(summary, 10)
        return True

    def _make_booster(self) -> List[dict]:
        """Create a booster pack with the right card distribution."""
        booster: List[dict] = []
        # 1 rare/mythic (1/7 chance of mythic if available)
        booster.append(
            random.choice(self._mythics) if self._mythics and random.randint(1, self.RARE_MYTHIC_RATIO) == 1
            else random.choice(self._rares)
        )
        # 3 uncommons
        booster.extend(random.sample(self._uncommons, self.UNCOMMONS_PER_PACK))
        # 11 commons
        booster.extend(random.sample(self._commons, self.COMMONS_PER_PACK))
        return booster

    def _images_for(self, cards: List[dict]) -> List[str]:
        """Get image paths for each card."""
        return [self._image_paths[self._card_uid(c)]
                for c in cards if self._card_uid(c) in self._image_paths]

    def _images_for_land_variants(self, land_type: str) -> List[str]:
        """Get image paths for each land variant, ensuring no duplicates."""
        images_dir = self.set_dir / "card_images"
        variant_images = []

        # First check if we have direct land variant files in card_images
        if images_dir.exists():
            base_name = land_type.lower()

            # Look for specifically named variants (forest_1.png, forest_2.png, etc)
            for i in range(1, 20):  # Look for up to 20 variants
                variant_path = images_dir / f"{base_name}_{i}.png"
                if variant_path.exists():
                    variant_images.append(str(variant_path))

            # If we found variants this way, return them
            if variant_images:
                return variant_images

        # If no direct variants found, use the ones from the basics_by_type collection
        return [self._image_paths[self._card_uid(c)]
                for c in self._basics_by_type[land_type]
                if self._card_uid(c) in self._image_paths]

    def _create_blank_card_image(self) -> str:
        """Create a blank card image to use for padding."""
        # Find a sample card to get dimensions
        sample_path = None
        for images in self._image_paths.values():
            sample_path = images
            break

        if not sample_path:
            # Create a default sized blank card
            blank_card = Image.new('RGB', (1000, 1452), (240, 240, 240))
        else:
            # Create a blank card with the same dimensions as the sample
            sample_img = Image.open(sample_path)
            sample_width, sample_height = sample_img.size
            blank_card = Image.new('RGB', (sample_width * 2, sample_height * 2), (240, 240, 240))

        # Add some minimal text
        try:
            draw = ImageDraw.Draw(blank_card)
            # Try to use a system font, fall back to default if not available
            try:
                font = ImageFont.truetype("Arial", 40)
            except:
                font = ImageFont.load_default()

            text_pos = (blank_card.width // 2, blank_card.height // 2)
            draw.text(text_pos, "Empty", fill=(120, 120, 120), anchor="mm")
        except:
            # If text drawing fails, just use the blank image
            pass

        # Save to a temporary file
        fd, filepath = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        blank_card.save(filepath)
        self.blank_card_path = filepath
        return filepath

    def _save_sheet(self, name: str, images: List[str], out_dir: Path) -> None:
        """Save a card sheet image for TTS. Uses empty spaces instead of duplicates."""
        if not images:
            return

        # Calculate the minimum number of cards needed
        n = len(images)

        # Set minimum rows to 2 as required
        min_rows = 2

        # Calculate grid size to be as square as possible
        # Square means rows ≈ columns, so we target sqrt(n)
        target_dimension = math.sqrt(n)

        # But ensure we have at least 2 rows
        rows = max(min_rows, math.ceil(target_dimension))

        # Calculate columns needed based on rows to fit all cards
        cols = math.ceil(n / rows)

        # Adjust for maximum size (10x10)
        if cols > 10:
            cols = 10
            rows = math.ceil(n / cols)

        # Make more square if possible by balancing rows and columns
        # Try to get closer to a square by increasing rows if it would reduce columns significantly
        if cols > rows + 1 and rows < 10:
            new_rows = rows + 1
            new_cols = math.ceil(n / new_rows)
            # If this makes it more square, use the new dimensions
            if abs(new_rows - new_cols) < abs(rows - cols):
                rows = new_rows
                cols = new_cols

        # Create a blank card if needed
        if len(images) < rows * cols and not self.blank_card_path:
            self.blank_card_path = self._create_blank_card_image()

        # Prepare images list with padding
        all_images = list(images)
        if self.blank_card_path and len(all_images) < rows * cols:
            # Add enough blank cards to fill the grid
            all_images.extend([self.blank_card_path] * (rows * cols - len(all_images)))

        # Use the embedded create_card_sheets function
        sheets = create_card_sheets(
            all_images,
            max_rows=rows,
            max_columns=cols,
            card_width=1000,
            card_height=1452,
            sort_files=False,
        )

        # Save the sheet
        sheet, *_ = sheets[0]
        output_path = out_dir / f"booster_{name}.jpg"
        sheet.save(output_path, "JPEG", quality=80)

    def _cleanup(self):
        """Clean up temporary files."""
        if self.blank_card_path and os.path.exists(self.blank_card_path):
            try:
                os.unlink(self.blank_card_path)
            except:
                pass

    def run(self):
        """Run the booster generation process."""
        try:
            # Load the set
            if not self._load_set():
                self.signals.finished.emit(False, "Failed to load set")
                return

            # Create boosters directory
            boosters_dir = self.set_dir / "boosters"
            boosters_dir.mkdir(exist_ok=True)

            # Calculate total number of boosters (including basic land boosters)
            total_boosters = self.booster_count + len([t for t, cards in self._basics_by_type.items() if cards])
            boosters_created = 0

            # Generate regular boosters
            for i in range(1, self.booster_count + 1):
                # Calculate progress percentage (0-100), allocating 10% for loading and 90% for generation
                progress = 10 + int((boosters_created / total_boosters) * 90)

                # Update progress
                self.signals.progress.emit(f"Generating booster {i} of {self.booster_count}...", progress)

                # Generate booster
                booster_cards = self._make_booster()
                card_images = self._images_for(booster_cards)
                self._save_sheet(str(i), card_images, boosters_dir)
                boosters_created += 1

            # Generate land boosters
            for land_type, cards in self._basics_by_type.items():
                if cards:
                    # Calculate progress
                    progress = 10 + int((boosters_created / total_boosters) * 90)

                    # Update progress
                    self.signals.progress.emit(f"Generating {land_type} booster...", progress)

                    # Generate land booster using land variants method
                    land_images = self._images_for_land_variants(land_type)
                    if land_images:
                        self._save_sheet(land_type.lower(), land_images, boosters_dir)
                        boosters_created += 1

            # Compile results
            result_message = f"Created {self.booster_count} regular boosters"
            basic_lands = []
            for land_type, cards in self._basics_by_type.items():
                if cards:
                    variant_count = len(self._images_for_land_variants(land_type))
                    basic_lands.append(f"{land_type} ({variant_count} variants)")

            if basic_lands:
                result_message += f" and {len(basic_lands)} basic land boosters:\n• " + "\n• ".join(basic_lands)

            result_message += f"\n\nAll boosters saved to:\n{boosters_dir}"

            # Signal successful completion
            self.signals.finished.emit(True, result_message)

        except Exception as e:
            # Signal error
            error_msg = f"Error generating boosters: {str(e)}"
            print(error_msg)
            self.signals.error.emit(error_msg)
            self.signals.finished.emit(False, str(e))
        finally:
            # Clean up any temporary files
            self._cleanup()


class BoosterGeneratorApp(QMainWindow):
    """PyQt6 GUI for MTG Booster Generator."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MTG Booster Generator")
        self.setMinimumSize(600, 400)

        # Set up the user interface
        self.initUI()

        # Initialize variables
        self.set_dir = None
        self.generator = None

    def initUI(self):
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("MTG Booster Generator")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # Description
        desc_label = QLabel("Generate booster packs from MTG sets for Tabletop Simulator")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(desc_label)

        # Set folder selection - Using cleaner layout
        folder_layout = QGridLayout()
        folder_layout.setColumnStretch(1, 1)  # Make the middle column stretch
        folder_layout.setVerticalSpacing(15)

        folder_label = QLabel("MTG Set Folder:")
        folder_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.folder_path_label = QLabel("No folder selected")
        # The stylesheet will be set based on dark/light mode
        self.folder_path_label.setProperty("class", "path-display")
        self.folder_path_label.setMinimumWidth(300)
        self.folder_path_label.setMinimumHeight(30)
        self.folder_path_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.folder_path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        browse_btn = QPushButton("Browse...")
        browse_btn.setMinimumWidth(120)
        browse_btn.clicked.connect(self.browse_folder)

        folder_layout.addWidget(folder_label, 0, 0)
        folder_layout.addWidget(self.folder_path_label, 0, 1)
        folder_layout.addWidget(browse_btn, 0, 2)

        # Number of boosters
        booster_label = QLabel("Number of Boosters:")
        booster_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.booster_count = QSpinBox()
        self.booster_count.setRange(1, 100)
        self.booster_count.setValue(6)
        self.booster_count.setFixedWidth(100)
        self.booster_count.setMinimumHeight(30)

        folder_layout.addWidget(booster_label, 1, 0)
        folder_layout.addWidget(self.booster_count, 1, 1, 1, 1, Qt.AlignmentFlag.AlignLeft)

        main_layout.addLayout(folder_layout)

        # Status area - no hard-coded colors
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setProperty("class", "status-display")
        self.status_label.setMinimumHeight(130)
        self.status_label.setTextFormat(Qt.TextFormat.RichText)
        main_layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.generate_btn = QPushButton("Generate Boosters")
        self.generate_btn.setMinimumHeight(40)
        self.generate_btn.clicked.connect(self.generate_boosters)
        button_layout.addWidget(self.generate_btn)

        quit_btn = QPushButton("Quit")
        quit_btn.clicked.connect(self.close)
        button_layout.addWidget(quit_btn)

        main_layout.addLayout(button_layout)

    def browse_folder(self):
        """Browse for MTG set folder."""
        # Force non-native dialog which works better across platforms
        dialog = QFileDialog(self, "Select MTG Set Folder")
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)

        # Set a reasonable size for the dialog
        dialog.resize(800, 500)

        # Important: this enables double-clicking in the dialog
        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            selected_files = dialog.selectedFiles()
            if selected_files:
                folder = selected_files[0]
                self.set_dir = Path(folder)
                self.folder_path_label.setText(str(self.set_dir))
                self.update_status_ready()

    def update_status_ready(self):
        """Update the status with ready information."""
        if self.set_dir:
            self.status_label.setText(f"Ready to generate boosters from:<br><b>{self.set_dir}</b>")
        else:
            self.status_label.setText("Please select an MTG set folder first")

    def generate_boosters(self):
        """Start the booster generation process."""
        if not self.set_dir:
            QMessageBox.warning(self, "No Folder Selected", "Please select an MTG set folder first.")
            return

        # Check for required directories
        render_dir = self.set_dir / "render_format"
        if not render_dir.exists():
            QMessageBox.critical(self, "Invalid Set",
                                 f"No 'render_format' folder found in {self.set_dir}\n\n"
                                 "Please select a valid MTG set folder.")
            return

        # Get number of boosters
        booster_count = self.booster_count.value()

        # Disable UI while generating
        self.generate_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Loading card data from {self.set_dir}...")

        # Create and start the generator thread
        self.generator = BoosterGenerator(self.set_dir, booster_count)

        # Connect signals
        self.generator.signals.progress.connect(self.update_progress)
        self.generator.signals.finished.connect(self.generation_finished)
        self.generator.signals.error.connect(self.generation_error)

        # Start the generator
        self.generator.start()

    def update_progress(self, message, percent):
        """Update the UI with progress information."""
        self.status_label.setText(message.replace("\n", "<br>"))
        self.progress_bar.setValue(percent)

    def generation_finished(self, success, message):
        """Handle completion of booster generation."""
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText(message.replace("\n", "<br>"))
            QMessageBox.information(self, "Success", message)
        else:
            self.status_label.setText(f"Error: {message}")
            QMessageBox.critical(self, "Error", f"Failed to generate boosters: {message}")

        # Re-enable UI
        self.generate_btn.setEnabled(True)

    def generation_error(self, message):
        """Handle errors during booster generation."""
        self.status_label.setText(f"Error: {message}")
        QMessageBox.critical(self, "Error", message)
        self.generate_btn.setEnabled(True)
        self.progress_bar.setValue(0)


if __name__ == "__main__":
    # Seed the random number generator
    random.seed()

    # Create and run the application
    app = QApplication(sys.argv)

    # Use fusion style which works well in dark mode
    app.setStyle("fusion")

    # Detect if we're in dark mode and apply appropriate stylesheet
    is_dark_mode = False
    palette = app.palette()
    bg_color = palette.color(palette.ColorRole.Window)
    is_dark_mode = bg_color.lightness() < 128

    # Apply stylesheet based on mode
    if is_dark_mode:
        # Dark mode stylesheet
        app.setStyleSheet("""
            QMainWindow {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QWidget {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
            QLabel[class="path-display"] {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 6px;
            }
            QLabel[class="status-display"] {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 10px;
            }
            QPushButton {
                background-color: #505050;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 6px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #606060;
                border-color: #888888;
            }
            QPushButton:pressed {
                background-color: #707070;
            }
            QPushButton:disabled {
                background-color: #3a3a3a;
                color: #888888;
            }
            QSpinBox {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 4px;
                min-height: 20px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #505050;
                width: 16px;
                border: 1px solid #666666;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #606060;
            }
            QProgressBar {
                border: 1px solid #666666;
                border-radius: 3px;
                background-color: #3a3a3a;
                text-align: center;
                color: #ffffff;
                min-height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4d7cbe;
                width: 10px;
                margin: 0.5px;
            }
            QFileDialog {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QFileDialog QListView, QFileDialog QTreeView, QFileDialog QComboBox {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #666666;
            }
            QFileDialog QPushButton {
                min-width: 80px;
            }
        """)

    window = BoosterGeneratorApp()
    window.show()
    sys.exit(app.exec())
