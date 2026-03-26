from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import project  # noqa: E402


def _write_pipeline_fixture(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    players = pd.DataFrame(
        [
            {"id": 1, "name": "Player A", "web name": "PA", "team": "AAA", "price": 10.0, "position": "BACK"},
            {"id": 2, "name": "Player B", "web name": "PB", "team": "BBB", "price": 9.0, "position": "FRONT"},
        ]
    )
    fixture_ticker = pd.DataFrame(
        [
            {"team": "AAA", "1": "BBB", "2": "CCC", "3": None},
            {"team": "BBB", "1": None, "2": "AAA", "3": "CCC"},
        ]
    )
    fixture_info = pd.DataFrame(
        [
            {"id": 1, "code": 1.0, "deadline": "2025-01-01T00:00:00Z"},
            {"id": 2, "code": 2.0, "deadline": "2025-01-02T00:00:00Z"},
            {"id": 3, "code": 3.0, "deadline": "2025-01-04T00:00:00Z"},
        ]
    )
    injuries = pd.DataFrame([{"Player": "Player B", "Status": "Out", "Est. Return": "2025-01-02"}])
    projected_stats = pd.DataFrame([{"NAME": "Player A", "MIN": 30.0}, {"NAME": "Player B", "MIN": 28.0}])

    players.to_csv(data_dir / "players.csv", index=False)
    fixture_ticker.to_csv(data_dir / "fixture_ticker.csv", index=False)
    fixture_info.to_csv(data_dir / "fixture_info.csv", index=False)
    injuries.to_csv(data_dir / "nba-injury-report.csv", index=False)
    (data_dir / "name_exceptions.json").write_text("{}")
    (tmp_path / "solver_settings.json").write_text(json.dumps({"b2b_decay": [0.9, 0.8]}))
    return projected_stats


def test_availability_and_mins_projection_are_vectorized_and_correct(monkeypatch, tmp_path):
    projected_stats = _write_pipeline_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)

    avail = project.availability(projected_stats)
    mins = project.mins_projection(projected_stats)

    avail = avail.set_index("name")
    mins = mins.set_index("name")

    assert avail.loc["Player B", "1"] == 0
    assert avail.loc["Player B", "2"] == 0
    assert mins.loc["Player A", "1"] == 27.0
    assert mins.loc["Player A", "2"] == 24.0
    assert mins.loc["Player B", "1"] == 0.0
    assert mins.loc["Player B", "2"] == 0.0
    assert mins.loc["Player B", "3"] == 0.0
