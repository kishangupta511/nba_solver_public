from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
GUI_SRC = REPO_ROOT / "public_solver" / "src"
if str(GUI_SRC) not in sys.path:
    sys.path.insert(0, str(GUI_SRC))

from gui.services import XminsService  # noqa: E402


def _write_service_fixture(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    xmins = pd.DataFrame(
        [
            {"id": 1, "name": "Player A", "team": "AAA", "price": 10.0, "position": "BACK", "MIN": 30.0, "1": 30.0, "2": 30.0, "3": 0.0},
            {"id": 2, "name": "Player B", "team": "BBB", "price": 9.0, "position": "FRONT", "MIN": 28.0, "1": 0.0, "2": 28.0, "3": 28.0},
        ]
    )
    projections36 = pd.DataFrame(
        [
            {"id": 1, "name": "Player A", "team": "AAA", "price": 10.0, "position": "BACK", "1": 36.0, "2": 54.0, "3": 72.0},
            {"id": 2, "name": "Player B", "team": "BBB", "price": 9.0, "position": "FRONT", "1": 40.0, "2": 50.0, "3": 60.0},
        ]
    )
    fixture_info = pd.DataFrame(
        [
            {"id": 1, "code": 1.0, "deadline": "2025-01-01T00:00:00Z"},
            {"id": 2, "code": 2.0, "deadline": "2025-01-02T00:00:00Z"},
            {"id": 3, "code": 3.0, "deadline": "2025-01-04T00:00:00Z"},
        ]
    )
    fixture_ticker = pd.DataFrame(
        [
            {"team": "AAA", "1": "BBB", "2": "CCC", "3": None},
            {"team": "BBB", "1": None, "2": "AAA", "3": "CCC"},
        ]
    )

    xmins.to_csv(data_dir / "xmins.csv", index=False)
    projections36.to_csv(data_dir / "projections36.csv", index=False)
    fixture_info.to_csv(data_dir / "fixture_info.csv", index=False)
    fixture_ticker.to_csv(data_dir / "fixture_ticker.csv", index=False)
    (tmp_path / "solver_settings.json").write_text(json.dumps({"b2b_decay": [0.9, 0.8]}))


def test_full_row_and_single_day_overrides(monkeypatch, tmp_path):
    _write_service_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)

    service = XminsService()
    result = service.apply_edits(
        [
            {"player_name": "Player A", "column": "Xmins", "value": 20.0, "timestamp": 1.0, "edit_type": "full_row"},
            {"player_name": "Player A", "column": "2.0", "value": 17.0, "timestamp": 2.0, "edit_type": "single_day"},
        ]
    )

    xmins = result.xmins_df.set_index("name")
    projections = result.projections_df.set_index("name")
    assert xmins.loc["Player A", "MIN"] == 20.0
    assert xmins.loc["Player A", "1"] == 18.0
    assert xmins.loc["Player A", "2"] == 17.0
    assert xmins.loc["Player A", "3"] == 0.0
    assert projections.loc["Player A", "1"] == 18.0
    assert projections.loc["Player A", "2"] == 25.5
    assert result.changed_players == ["Player A"]


def test_last_write_wins_and_legacy_changes_are_canonicalized(monkeypatch, tmp_path):
    _write_service_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "mins_changes.json").write_text(
        json.dumps(
            [
                {"name": "Player B", "column": "2.0", "value": 10, "timestamp": 1},
                {"name": "Player B", "column": "2", "value": 12, "timestamp": 2},
            ]
        )
    )

    service = XminsService()
    xmins = service.current_xmins_df().set_index("name")
    assert xmins.loc["Player B", "2"] == 12

    saved = json.loads((tmp_path / "data" / "mins_changes.json").read_text())
    assert len(saved) == 1
    assert saved[0]["column"] == "2"
    assert saved[0]["value"] == 12.0
