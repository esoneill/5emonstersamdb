#!/usr/bin/env python3
"""
json_to_csv.py  ––  v2.1  (2025-04-29)
--------------------------------------
Convert a JSON array of monster objects (from html_to_json.py) to CSV.

• Ensures a **Gear** column (taken from the “gear” key) is always present
  and is appended as the final column in the output CSV.

Usage:
    python json_to_csv.py monstersfromhtml.json [monsters.csv]
"""

import csv
import json
import pathlib
import sys
from typing import Union


# ---------------------------------------------------------------------------

def build_fieldnames(records):
    """Return header list with *gear* column guaranteed to be last."""
    keys = {k for r in records for k in r}
    if "gear" in keys:
        keys.remove("gear")
        return sorted(keys) + ["gear"]
    return sorted(keys)


def json_to_csv(json_path: Union[str, pathlib.Path],
                csv_path: Union[str, pathlib.Path, None] = None) -> None:
    json_path = pathlib.Path(json_path)
    csv_path = pathlib.Path(csv_path) if csv_path else json_path.with_suffix(".csv")

    # 1. Load JSON -----------------------------------------------------------
    with json_path.open(encoding="utf-8") as fp:
        data = json.load(fp)

    if not isinstance(data, list):
        raise ValueError("JSON must be a top-level array of objects")

    # 2. Prepare header ------------------------------------------------------
    fieldnames = build_fieldnames(data)

    # 3. Write CSV -----------------------------------------------------------
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)

    print(f"✅  Wrote {len(data):,} rows to {csv_path}")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not 2 <= len(sys.argv) <= 3:
        prog = pathlib.Path(sys.argv[0]).name
        sys.exit(f"Usage:  python {prog} input.json [output.csv]")
    json_to_csv(*sys.argv[1:])
