"""Data loading and parsing helpers shared across the GUI."""

import json
import os
import time
from typing import List

import pandas as pd


def parse_comma_list(text: str, cast=float) -> list:
    """Parse a comma-separated string into a list.  Returns [] for empty input."""
    text = text.strip()
    if not text:
        return []
    return [cast(x.strip()) for x in text.split(",")]


def format_comma_list(items) -> str:
    """Format a list into a comma-separated string."""
    if not items:
        return ""
    return ", ".join(str(i) for i in items)


def load_fixture_info() -> pd.DataFrame:
    """Load fixture_info.csv and return the DataFrame."""
    return pd.read_csv("data/fixture_info.csv")


def id_to_code_map() -> dict:
    """Return a dict mapping fixture id -> gameday code string (e.g. '3.2')."""
    fi = load_fixture_info()
    return fi.set_index("id")["code"].to_dict()


def code_to_id_map() -> dict:
    """Return a dict mapping gameday code (float) -> fixture id (int)."""
    fi = load_fixture_info()
    return dict(zip(fi["code"].astype(float), fi["id"].astype(int)))


def load_projections() -> pd.DataFrame:
    """Load the best available projections CSV."""
    if os.path.exists("data/projections_overwrite.csv"):
        return pd.read_csv("data/projections_overwrite.csv")
    return pd.read_csv("data/projections.csv")


def load_xmins() -> pd.DataFrame:
    """Load the xmins CSV."""
    return pd.read_csv("data/xmins.csv")


def load_fixture_ticker() -> pd.DataFrame:
    """Load the fixture ticker CSV."""
    return pd.read_csv("data/fixture_ticker.csv")


def load_mins_changes() -> List[dict]:
    """Load saved xMins override entries, or empty list."""
    path = "data/mins_changes.json"
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return canonicalize_mins_changes(json.load(f))


def save_mins_changes(changes: List[dict]):
    """Persist xMins override entries to JSON."""
    os.makedirs("data", exist_ok=True)
    canonical = canonicalize_mins_changes(changes)
    with open("data/mins_changes.json", "w") as f:
        json.dump(canonical, f, indent=4)


def rename_columns_to_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Rename numeric column headers from fixture IDs to gameday codes."""
    mapping = id_to_code_map()
    df = df.rename(
        columns=lambda x: str(mapping[int(x)]) if x.isdigit() and int(x) in mapping else x
    )
    return df


def normalize_mins_column(column, code_to_id: dict | None = None) -> str:
    """Normalize xMins edit columns to a canonical persisted key."""
    col = str(column).strip()
    lowered = col.lower()
    if lowered in {"min", "xmins"}:
        return "MIN"

    if code_to_id is not None:
        try:
            code = float(col)
            mapped = code_to_id.get(code)
            if mapped is not None:
                return str(int(mapped))
        except (TypeError, ValueError):
            pass

    if col.isdigit():
        return str(int(col))
    return col


def canonicalize_mins_changes(changes: List[dict], code_to_id: dict | None = None) -> List[dict]:
    """Collapse override records to last-write-wins canonical entries."""
    if not changes:
        return []

    canonical: dict[tuple[str, str], dict] = {}
    ordered: list[dict] = []
    for idx, raw in enumerate(changes):
        if not isinstance(raw, dict):
            continue

        name = raw.get("name")
        if isinstance(name, (list, tuple)):
            name = name[0] if name else ""
        if not name:
            continue

        try:
            value = float(raw.get("value"))
        except (TypeError, ValueError):
            continue

        column = normalize_mins_column(raw.get("column", ""), code_to_id)
        timestamp = raw.get("timestamp")
        try:
            timestamp = float(timestamp)
        except (TypeError, ValueError):
            timestamp = float(idx) if idx else time.time()

        edit_type = raw.get("edit_type")
        if edit_type not in {"full_row", "single_day"}:
            edit_type = "full_row" if column == "MIN" else "single_day"

        record = {
            "name": str(name),
            "column": column,
            "value": value,
            "timestamp": timestamp,
            "edit_type": edit_type,
        }
        canonical[(record["name"], record["column"])] = record
        ordered.append(record)

    deduped = list(canonical.values())
    deduped.sort(key=lambda item: (item["timestamp"], item["name"], item["column"]))
    return deduped
