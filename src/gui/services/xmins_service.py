"""Shared backend for xMins edits and overwrite projection generation."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from gui.services.projection_cache import ProjectionCache, get_projection_cache
from gui.utils.data_utils import (
    canonicalize_mins_changes,
    load_mins_changes,
    normalize_mins_column,
    rename_columns_to_codes,
    save_mins_changes,
)


@dataclass(slots=True)
class XminsEdit:
    """Normalized xMins edit payload."""

    player_name: str
    column: str
    value: float
    timestamp: float
    edit_type: str

    @classmethod
    def from_payload(cls, payload: dict, cache: ProjectionCache) -> "XminsEdit":
        column = normalize_mins_column(payload.get("column", ""), cache.fixture_code_to_id)
        edit_type = payload.get("edit_type")
        if edit_type not in {"full_row", "single_day"}:
            edit_type = "full_row" if column == "MIN" else "single_day"
        return cls(
            player_name=str(payload["player_name"]),
            column=column,
            value=float(payload["value"]),
            timestamp=float(payload.get("timestamp", time.time())),
            edit_type=edit_type,
        )


@dataclass(slots=True)
class XminsApplyResult:
    """Result returned after applying a batch of xMins edits."""

    xmins_df: pd.DataFrame
    projections_df: pd.DataFrame
    override_cells: set[tuple[int, int]]
    changed_players: list[str]
    errors: list[str]


class XminsService:
    """Manage canonical xMins overrides and derived overwrite projections."""

    def __init__(self, cache: ProjectionCache | None = None):
        self.cache = cache or get_projection_cache()
        self._xmins_df = self.cache.xmins_base_df.copy()
        self._projections_df = self._build_projection_df(self._xmins_df)
        self._overrides: dict[tuple[str, str], XminsEdit] = {}
        self._load_existing_overrides()

    def _load_existing_overrides(self):
        for record in canonicalize_mins_changes(load_mins_changes(), self.cache.fixture_code_to_id):
            edit = XminsEdit(
                player_name=str(record["name"]),
                column=str(record["column"]),
                value=float(record["value"]),
                timestamp=float(record["timestamp"]),
                edit_type=str(record["edit_type"]),
            )
            self._overrides[(edit.player_name, edit.column)] = edit
        if self._overrides:
            changed = sorted({name for name, _ in self._overrides})
            self._rebuild_players(changed)
            self.persist()

    def invalidate_cache(self):
        """Reload all base inputs from disk."""
        self.cache = get_projection_cache(force_reload=True)
        self._xmins_df = self.cache.xmins_base_df.copy()
        self._projections_df = self._build_projection_df(self._xmins_df)
        existing = list(self._overrides.values())
        self._overrides = {}
        for edit in existing:
            self._overrides[(edit.player_name, edit.column)] = edit
        if existing:
            self._rebuild_players(sorted({edit.player_name for edit in existing}))

    def has_overrides(self) -> bool:
        return bool(self._overrides)

    def current_xmins_df(self) -> pd.DataFrame:
        return self._xmins_df.copy()

    def current_projections_df(self) -> pd.DataFrame:
        return self._projections_df.copy()

    def apply_edits(self, edits: list[dict]) -> XminsApplyResult:
        """Apply a batch of xMins edits and persist canonical outputs."""
        errors: list[str] = []
        normalized: list[XminsEdit] = []
        for payload in edits:
            try:
                edit = XminsEdit.from_payload(payload, self.cache)
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(str(exc))
                continue
            if edit.player_name not in self.cache.name_to_idx:
                errors.append(f"Unknown player: {edit.player_name}")
                continue
            if edit.column != "MIN" and edit.column not in self.cache.gameday_columns:
                errors.append(f"Unknown xMins column: {payload.get('column')}")
                continue
            normalized.append(edit)

        changed_players: set[str] = set()
        for edit in normalized:
            self._overrides[(edit.player_name, edit.column)] = edit
            changed_players.add(edit.player_name)

        if changed_players:
            self._rebuild_players(sorted(changed_players))
            self.persist()

        return XminsApplyResult(
            xmins_df=self.current_xmins_df(),
            projections_df=self.current_projections_df(),
            override_cells=self.override_cells_for_display_df(self.display_xmins_df()),
            changed_players=sorted(changed_players),
            errors=errors,
        )

    def delete_overrides(self):
        """Clear all persisted overrides and restore base data."""
        self._overrides.clear()
        self._xmins_df = self.cache.xmins_base_df.copy()
        self._projections_df = self._build_projection_df(self._xmins_df)
        for path in ("data/mins_changes.json", "data/xmins_overwrite.csv", "data/projections_overwrite.csv"):
            if os.path.exists(path):
                os.remove(path)

    def persist(self):
        """Persist canonical override records and overwrite CSVs."""
        records = [
            {
                "name": edit.player_name,
                "column": edit.column,
                "value": edit.value,
                "timestamp": edit.timestamp,
                "edit_type": edit.edit_type,
            }
            for edit in self._overrides.values()
        ]
        if records:
            save_mins_changes(records)
            self._xmins_df.round(2).to_csv("data/xmins_overwrite.csv", index=False)
            self._projections_df.round(1).to_csv("data/projections_overwrite.csv", index=False)
        else:
            for path in ("data/mins_changes.json", "data/xmins_overwrite.csv", "data/projections_overwrite.csv"):
                if os.path.exists(path):
                    os.remove(path)

    def display_xmins_df(self) -> pd.DataFrame:
        """Return current xMins in GUI display format."""
        data = self._xmins_df.copy()
        data = data.drop(columns=["id"], errors="ignore")
        data.columns = data.columns.str.lower().str.capitalize()
        data.rename(columns={"Min": "Xmins"}, inplace=True)
        data = rename_columns_to_codes(data)
        data.sort_values(by=["Price", "Name"], ascending=[False, True], inplace=True)
        data.reset_index(drop=True, inplace=True)
        return data

    def display_projections_df(self) -> pd.DataFrame:
        """Return current xPoints in GUI display format."""
        data = self._projections_df.copy()
        if "G" in data.columns:
            data = data.drop(columns=["G"])
        data = data.drop(columns=["id"], errors="ignore")
        data.columns = data.columns.str.lower().str.capitalize()
        data = rename_columns_to_codes(data)
        data.sort_values(by=["Price", "Name"], ascending=[False, True], inplace=True)
        data.reset_index(drop=True, inplace=True)
        return data

    def override_cells_for_display_df(self, display_df: pd.DataFrame) -> set[tuple[int, int]]:
        """Return persisted override cell positions for the display dataframe."""
        name_to_row = {str(name): idx for idx, name in enumerate(display_df.iloc[:, 0].tolist())}
        columns = list(display_df.columns)
        override_cells: set[tuple[int, int]] = set()
        for edit in sorted(self._overrides.values(), key=lambda item: item.timestamp):
            row_idx = name_to_row.get(edit.player_name)
            if row_idx is None:
                continue
            if edit.column == "MIN":
                for col_name in ("Xmins", "Min", "MIN"):
                    if col_name in columns:
                        override_cells.add((row_idx, columns.index(col_name)))
                        break
            else:
                code = self.cache.fixture_id_to_code.get(int(edit.column))
                col_key = str(code) if code is not None else str(edit.column)
                if col_key in columns:
                    override_cells.add((row_idx, columns.index(col_key)))
        return override_cells

    def _build_projection_df(self, xmins_df: pd.DataFrame) -> pd.DataFrame:
        projections = self.cache.projections36_df.copy()
        projections.iloc[:, 5:] = (
            self.cache.projections36_df.iloc[:, 5:].to_numpy(dtype=float) * xmins_df.iloc[:, 6:].to_numpy(dtype=float)
        ) / 36.0
        return projections.round(1)

    def _rebuild_players(self, player_names: list[str]):
        for player_name in player_names:
            row_idx = self.cache.name_to_idx[player_name]
            rebuilt_row = self._rebuild_player_row(player_name, row_idx)
            self._xmins_df.iloc[row_idx, 5:] = rebuilt_row
            proj_row = (
                self.cache.projections36_df.iloc[row_idx, 5:].to_numpy(dtype=float) * rebuilt_row[1:]
            ) / 36.0
            self._projections_df.iloc[row_idx, 5:] = np.round(proj_row, 1)

    def _rebuild_player_row(self, player_name: str, row_idx: int) -> np.ndarray:
        base_row = self.cache.xmins_base_df.iloc[row_idx, 5:].to_numpy(dtype=float, copy=True)
        current_min = float(base_row[0])
        gameday_values = base_row[1:].copy()

        player_edits = sorted(
            [edit for edit in self._overrides.values() if edit.player_name == player_name],
            key=lambda item: item.timestamp,
        )
        for edit in player_edits:
            if edit.column == "MIN":
                current_min = float(edit.value)
                gameday_values = self.cache.availability_basis[row_idx].astype(float, copy=True) * current_min
                gameday_values = self._apply_b2b_decay_to_row(gameday_values)
            else:
                try:
                    gd_idx = self.cache.gameday_columns.index(str(edit.column))
                except ValueError:
                    continue
                gameday_values[gd_idx] = float(edit.value)

        row = np.concatenate(([current_min], np.round(gameday_values, 2)))
        return row

    def _apply_b2b_decay_to_row(self, values: np.ndarray) -> np.ndarray:
        decayed = values.astype(float, copy=True)
        b2b_decay = self.cache.solver_options.get("b2b_decay", [0.975, 0.95])
        if len(b2b_decay) < 2:
            return decayed
        for left_idx, right_idx in self.cache.b2b_pairs:
            if decayed[left_idx] != 0 and decayed[right_idx] != 0:
                decayed[left_idx] *= float(b2b_decay[0])
                decayed[right_idx] *= float(b2b_decay[1])
        return decayed
