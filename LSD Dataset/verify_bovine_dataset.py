"""
Independent Verification Script for Curated Bovine Hard-Negative Dataset
"""

import os
import pandas as pd
from PIL import Image
import imagehash

MANIFEST_PATH = r"E:\LSD Dataset\bovine_hard_negatives_index.csv"
DATASET_DIR = r"E:\LSD Dataset\dataset_bovine_hard_negatives"
DIR_TICKS = os.path.join(DATASET_DIR, "ticks_bovine_hide")
DIR_MUD = os.path.join(DATASET_DIR, "mud_bovine_coat")

print("=" * 75)
print("       MANUAL CURATED BOVINE DATASET INDEPENDENT VERIFICATION")
print("=" * 75)

# 1. Manifest Structure & Integrity
df = pd.read_csv(MANIFEST_PATH)
print(f"Total Rows in Manifest: {len(df)}")
print(f"Manifest Columns: {df.columns.tolist()}")

required_cols = ["image_id", "file_path", "confounder_category", "resolution_width", "resolution_height", "assigned_label"]
cols_match = df.columns.tolist() == required_cols
print(f"Columns Exact Match: {'PASS' if cols_match else 'FAIL'}")

# Category Breakdown
print("\nCategory Distribution:")
for cat, count in df["confounder_category"].value_counts().items():
    print(f"  - {cat}: {count} images")

# Assigned Label
print("\nAssigned Labels:")
for label, count in df["assigned_label"].value_counts().items():
    print(f"  - {label}: {count}")

# 2. Resolution Statistics
min_w, max_w, mean_w = df["resolution_width"].min(), df["resolution_width"].max(), df["resolution_width"].mean()
min_h, max_h, mean_h = df["resolution_height"].min(), df["resolution_height"].max(), df["resolution_height"].mean()
print(f"\nResolution Summary:")
print(f"  - Width:  min={min_w} px, max={max_w} px, mean={mean_w:.1f} px")
print(f"  - Height: min={min_h} px, max={max_h} px, mean={mean_h:.1f} px")

# 3. Physical File Integrity & Zero-Mistake Guardrails
all_exist = True
all_rgb_jpeg = True
hashes = []
duplicate_pairs = []

for idx, row in df.iterrows():
    p = row["file_path"]
    img_id = row["image_id"]
    if not os.path.exists(p):
        print(f"  [ERROR] Missing file: {p}")
        all_exist = False
        continue
    try:
        with Image.open(p) as img:
            img.verify()
        with Image.open(p) as img:
            if img.format != "JPEG" or img.mode != "RGB":
                print(f"  [ERROR] Format/Mode issue: {p} (format={img.format}, mode={img.mode})")
                all_rgb_jpeg = False
            w, h = img.size
            if w != row["resolution_width"] or h != row["resolution_height"]:
                print(f"  [ERROR] Manifest dimension mismatch: {p}")
            
            ph = imagehash.phash(img)
            for prev_ph, prev_id in hashes:
                if ph - prev_ph == 0:
                    duplicate_pairs.append((img_id, prev_id))
            hashes.append((ph, img_id))
    except Exception as e:
        print(f"  [ERROR] Failed reading {p}: {e}")
        all_exist = False

print("\nQuality Guardrail Checks:")
print(f"  - Physical File Existence:         {'PASS' if all_exist else 'FAIL'}")
print(f"  - Uniform 24-bit RGB JPEG Format:  {'PASS' if all_rgb_jpeg else 'FAIL'}")
print(f"  - Zero Duplicate Files (pHash):    {'PASS' if len(duplicate_pairs) == 0 else f'FAIL ({len(duplicate_pairs)} dupes)'}")

print("\nSubdirectory File Counts:")
print(f"  - ticks_bovine_hide: {len(os.listdir(DIR_TICKS))} files")
print(f"  - mud_bovine_coat:   {len(os.listdir(DIR_MUD))} files")

print("\nFirst 5 Manifest Entries:")
print(df.head(5).to_string(index=False))
print("\nLast 5 Manifest Entries:")
print(df.tail(5).to_string(index=False))
print("=" * 75)
