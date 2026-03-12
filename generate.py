import json
import random
import hashlib
from pathlib import Path
from PIL import Image

# =========================
# CONFIG
# =========================
TOTAL_SUPPLY = 999
START_EDITION = 1
RANDOM_SEED = 42

LAYERS_DIR = Path("layers")
OUTPUT_DIR = Path("output")
IMAGES_DIR = OUTPUT_DIR / "images"
METADATA_DIR = OUTPUT_DIR / "metadata"

# Bottom -> Top
LAYER_ORDER = [
    "background",
    "skin",
    "base",
    "clothes",
    "visor",
    "hair",
    "headwear",
    "accessory",
    "companion",
]

# Add filenames and weights here.
# Any PNG not listed gets default weight = 1.
RARITY = {
    "background": {
        "beige.png": 20,
        "blue.png": 10,
        "purple.png": 10,
        "gray.png": 8,
    },
    "skin": {
        "orange.png": 20,
        "brown.png": 10,
        "pale.png": 8,
        "zombie_green.png": 3,
    },
    "clothes": {
        "hoodie_blue.png": 18,
        "hoodie_black.png": 14,
        "hoodie_purple.png": 10,
        "hoodie_orange.png": 10,
        "varsity_red.png": 6,
        "jacket_white.png": 5,
    },
    "visor": {
        "green.png": 20,
        "blue.png": 12,
        "red.png": 8,
        "purple.png": 7,
        "yellow.png": 4,
    },
    "hair": {
        "spiky_blue.png": 16,
        "spiky_white.png": 8,
        "dreads_black.png": 8,
        "buns_pink.png": 4,
        "twins_teal.png": 4,
    },
    "headwear": {
        "none.png": 30,
        "crown.png": 2,
        "bucket_hat.png": 6,
        "cap_backwards.png": 7,
        "robot_helmet.png": 2,
    },
    "accessory": {
        "none.png": 30,
        "chain.png": 8,
        "headphones.png": 4,
        "earring.png": 6,
        "choker.png": 5,
    },
    "companion": {
        "none.png": 36,
        "duck.png": 3,
        "pet.png": 2,
        "trophy.png": 2,
    }
}

# Optional compatibility rules
def is_valid_combo(selected: dict) -> bool:
    # Robot helmet should not combine with visible hair
    if selected.get("headwear") == "robot_helmet.png" and selected.get("hair") != "none.png":
        return False

    # Headphones conflict with large headwear
    if selected.get("accessory") == "headphones.png" and selected.get("headwear") in {
        "crown.png", "bucket_hat.png", "robot_helmet.png"
    }:
        return False

    return True


# =========================
# HELPERS
# =========================
def ensure_output_dirs() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)


def get_pngs(layer_name: str) -> list[Path]:
    layer_path = LAYERS_DIR / layer_name
    if not layer_path.exists():
        return []
    return sorted([p for p in layer_path.iterdir() if p.suffix.lower() == ".png"])


def weighted_pick(layer_name: str, files: list[Path]) -> Path | None:
    if not files:
        return None
    weights_map = RARITY.get(layer_name, {})
    weights = [weights_map.get(f.name, 1) for f in files]
    return random.choices(files, weights=weights, k=1)[0]


def build_dna(selection: dict) -> str:
    raw = "|".join(f"{layer}:{filename}" for layer, filename in selection.items())
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compose(selection: dict) -> Image.Image | None:
    canvas = None

    for layer_name in LAYER_ORDER:
        filename = selection.get(layer_name)
        if not filename or filename == "none.png":
            continue

        img_path = LAYERS_DIR / layer_name / filename
        if not img_path.exists():
            raise FileNotFoundError(f"Missing file: {img_path}")

        img = Image.open(img_path).convert("RGBA")

        if canvas is None:
            canvas = Image.new("RGBA", img.size, (0, 0, 0, 0))

        if canvas.size != img.size:
            raise ValueError(
                f"Size mismatch in {img_path}. Expected {canvas.size}, got {img.size}"
            )

        canvas.alpha_composite(img)

    return canvas


def pretty_value(filename: str) -> str:
    return Path(filename).stem.replace("_", " ").title()


def save_metadata(edition: int, selection: dict, dna: str) -> None:
    attributes = []

    for layer_name in LAYER_ORDER:
        filename = selection.get(layer_name)
        if not filename or filename == "none.png":
            continue

        attributes.append({
            "trait_type": layer_name.title(),
            "value": pretty_value(filename)
        })

    metadata = {
        "name": f"Chapter #{edition}",
        "description": "Pixel art Chapter collection generated from trait layers.",
        "image": f"{edition}.png",
        "edition": edition,
        "dna": dna,
        "attributes": attributes,
    }

    out_path = METADATA_DIR / f"{edition}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def load_layer_catalog() -> dict[str, list[Path]]:
    catalog = {}
    for layer_name in LAYER_ORDER:
        files = get_pngs(layer_name)
        if not files:
            print(f"Warning: no PNGs found in layers/{layer_name}")
        catalog[layer_name] = files
    return catalog


def generate_one(layer_catalog: dict[str, list[Path]]) -> dict:
    selection = {}

    for layer_name in LAYER_ORDER:
        files = layer_catalog[layer_name]

        if not files:
            selection[layer_name] = "none.png"
            continue

        picked = weighted_pick(layer_name, files)
        selection[layer_name] = picked.name if picked else "none.png"

    return selection


# =========================
# MAIN
# =========================
def main() -> None:
    random.seed(RANDOM_SEED)
    ensure_output_dirs()

    layer_catalog = load_layer_catalog()
    seen_dna = set()

    generated = 0
    edition = START_EDITION
    attempts = 0
    max_attempts = TOTAL_SUPPLY * 300

    while generated < TOTAL_SUPPLY and attempts < max_attempts:
        attempts += 1
        selection = generate_one(layer_catalog)

        if not is_valid_combo(selection):
            continue

        dna = build_dna(selection)
        if dna in seen_dna:
            continue

        try:
            final_image = compose(selection)
            if final_image is None:
                continue

            image_path = IMAGES_DIR / f"{edition}.png"
            final_image.save(image_path)

            save_metadata(edition, selection, dna)

            seen_dna.add(dna)
            print(f"Generated #{edition}")
            edition += 1
            generated += 1

        except Exception as e:
            print(f"Skipped #{edition}: {e}")

    print()
    print(f"Finished: {generated} unique editions created.")
    if generated < TOTAL_SUPPLY:
        print("Could not reach target supply. Add more traits or relax rules.")


if __name__ == "__main__":
    main()
