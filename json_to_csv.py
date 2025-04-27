#!/usr/bin/env python3
"""
json_to_csv.py  ––  Convert a list-of-objects JSON file to CSV
(works on Python 3.7+)
"""

import json
import csv
import pathlib
import sys
from typing import Union   # <— new import

def json_to_csv(json_path: Union[str, pathlib.Path],
                csv_path: Union[str, pathlib.Path, None] = None) -> None:
    json_path = pathlib.Path(json_path)
    csv_path = pathlib.Path(csv_path) if csv_path else json_path.with_suffix(".csv")

    # 1. Load
    with json_path.open(encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, list):
        raise ValueError("JSON must be a top-level array of objects")

    # 2. Header
    fieldnames = sorted({k for obj in data for k in obj})

    # 3. Write CSV
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)      # blank cells for missing keys

    print(f"✅  Wrote {len(data):,} rows to {csv_path}")

if __name__ == "__main__":
    if not 2 <= len(sys.argv) <= 3:
        this = pathlib.Path(sys.argv[0]).name
        sys.exit(f"Usage:  python {this} input.json [output.csv]")
    json_to_csv(*sys.argv[1:])