import os
import pandas as pd
from PIL import Image
import imagehash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
MANIFEST_PATH = os.path.join(BASE_DIR, "bovine_hard_negatives_index.csv")
DATASET_DIR = os.path.join(BASE_DIR, "dataset_bovine_hard_negatives")
DIR_TICKS = os.path.join(DATASET_DIR, "ticks_bovine_hide")
DIR_MUD = os.path.join(DATASET_DIR, "mud_bovine_coat")
DIR_SNOW = os.path.join(DATASET_DIR, "snow_bovine_coat")

print("BOVINE HARD-NEGATIVE DATASET VERIFICATION")

if not os.path.exists(MANIFEST_PATH):
    raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

df = pd.read_csv(MANIFEST_PATH)
required_cols = [
    "image_id",
    "file_path",
    "confounder_category",
    "resolution_width",
    "resolution_height",
    "assigned_label",
]
cols_match = df.columns.tolist() == required_cols
print(f"Manifest rows: {len(df)}")
print(f"Exact column match: {'PASS' if cols_match else 'FAIL'}")

print("\nCategory distribution:")
for cat, count in df["confounder_category"].value_counts().items():
    print(f"  {cat}: {count}")

print("\nAssigned labels:")
for label, count in df["assigned_label"].value_counts().items():
    print(f"  {label}: {count}")

if len(df) > 0:
    print("\nResolution summary:")
    print(
        f"  Width: min={df['resolution_width'].min()} px, "
        f"max={df['resolution_width'].max()} px, "
        f"mean={df['resolution_width'].mean():.1f} px"
    )
    print(
        f"  Height: min={df['resolution_height'].min()} px, "
        f"max={df['resolution_height'].max()} px, "
        f"mean={df['resolution_height'].mean():.1f} px"
    )

all_exist = True
all_rgb_jpeg = True
hashes = []
duplicate_pairs = []

for _, row in df.iterrows():
    path = row["file_path"]
    image_id = row["image_id"]

    if not os.path.exists(path):
        print(f"[ERROR] Missing file: {path}")
        all_exist = False
        continue

    try:
        with Image.open(path) as img:
            img.verify()

        with Image.open(path) as img:
            if img.format != "JPEG" or img.mode != "RGB":
                print(f"[ERROR] Format/mode issue: {path} ({img.format}, {img.mode})")
                all_rgb_jpeg = False

            width, height = img.size
            if width != row["resolution_width"] or height != row["resolution_height"]:
                print(f"[ERROR] Manifest dimension mismatch: {path}")

            ph = imagehash.phash(img)
            for previous_hash, previous_id in hashes:
                if ph - previous_hash == 0:
                    duplicate_pairs.append((image_id, previous_id))
            hashes.append((ph, image_id))

    except Exception as error:
        print(f"[ERROR] Failed reading {path}: {error}")
        all_exist = False

print("\nQuality checks:")
print(f"  File existence: {'PASS' if all_exist else 'FAIL'}")
print(f"  RGB JPEG format: {'PASS' if all_rgb_jpeg else 'FAIL'}")
print(f"  pHash duplicates: {'PASS' if not duplicate_pairs else f'FAIL ({len(duplicate_pairs)})'}")

print("\nDirectory counts:")
for label, directory in [
    ("ticks_bovine_hide", DIR_TICKS),
    ("mud_bovine_coat", DIR_MUD),
    ("snow_bovine_coat", DIR_SNOW),
]:
    count = len(os.listdir(directory)) if os.path.exists(directory) else 0
    print(f"  {label}: {count}")

print("\nFirst 5 manifest entries:")
print(df.head(5).to_string(index=False))
print("\nLast 5 manifest entries:")
print(df.tail(5).to_string(index=False))
