"""Cached read-mostly data used by the projections workspace."""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class ProjectionCache:
    """Immutable cache of base projection inputs."""

    xmins_base_df: pd.DataFrame
    projections36_df: pd.DataFrame
    fixture_info_df: pd.DataFrame
    fixture_ticker_df: pd.DataFrame
    solver_options: dict
    gameday_columns: list[str]
    gameday_codes: list[float]
    name_to_idx: dict[str, int]
    team_to_fixture_vector: dict[str, np.ndarray]
    availability_basis: np.ndarray
    fixture_code_to_id: dict[float, int]
    fixture_id_to_code: dict[int, float]
    b2b_pairs: list[tuple[int, int]]
    cache_version: int = 1

    @classmethod
    def load(cls) -> "ProjectionCache":
        xmins_base_df = pd.read_csv("data/xmins.csv").sort_values(by="id").reset_index(drop=True)
        projections36_df = pd.read_csv("data/projections36.csv").sort_values(by="id").reset_index(drop=True)
        fixture_info_df = pd.read_csv("data/fixture_info.csv").copy()
        fixture_ticker_df = pd.read_csv("data/fixture_ticker.csv").copy()
        with open("solver_settings.json") as f:
            solver_options = json.load(f)

        gameday_columns = [str(col) for col in xmins_base_df.columns[6:]]
        gameday_codes = [float(col) for col in gameday_columns]
        name_to_idx = {str(name): int(idx) for idx, name in enumerate(xmins_base_df["name"].tolist())}

        fixture_block = fixture_ticker_df.iloc[:, 1:].copy()
        fixture_numeric = fixture_block.notna().astype(float)
        fixture_numeric.columns = [str(col) for col in fixture_numeric.columns]
        team_to_fixture_vector = {
            str(team): fixture_numeric.iloc[idx].to_numpy(dtype=float, copy=True)
            for idx, team in enumerate(fixture_ticker_df.iloc[:, 0].tolist())
        }

        base_numeric = xmins_base_df.iloc[:, 6:].to_numpy(dtype=float, copy=True)
        availability_basis = (base_numeric > 0).astype(float)

        fixture_info_df["deadline"] = pd.to_datetime(fixture_info_df["deadline"], errors="coerce")
        fixture_info_df["code"] = fixture_info_df["code"].astype(float)
        fixture_info_df["id"] = fixture_info_df["id"].astype(int)
        fixture_code_to_id = dict(zip(fixture_info_df["code"], fixture_info_df["id"]))
        fixture_id_to_code = dict(zip(fixture_info_df["id"], fixture_info_df["code"]))

        deadline_by_id = dict(zip(fixture_info_df["id"], fixture_info_df["deadline"]))
        b2b_pairs: list[tuple[int, int]] = []
        for idx in range(len(gameday_columns) - 1):
            current_id = int(float(gameday_columns[idx]))
            next_id = int(float(gameday_columns[idx + 1]))
            current_date = deadline_by_id.get(current_id)
            next_date = deadline_by_id.get(next_id)
            if current_date is None or next_date is None or pd.isna(current_date) or pd.isna(next_date):
                continue
            if (next_date - current_date).days == 1:
                b2b_pairs.append((idx, idx + 1))

        return cls(
            xmins_base_df=xmins_base_df,
            projections36_df=projections36_df,
            fixture_info_df=fixture_info_df,
            fixture_ticker_df=fixture_ticker_df,
            solver_options=solver_options,
            gameday_columns=gameday_columns,
            gameday_codes=gameday_codes,
            name_to_idx=name_to_idx,
            team_to_fixture_vector=team_to_fixture_vector,
            availability_basis=availability_basis,
            fixture_code_to_id=fixture_code_to_id,
            fixture_id_to_code=fixture_id_to_code,
            b2b_pairs=b2b_pairs,
        )


_CACHE: ProjectionCache | None = None


def get_projection_cache(force_reload: bool = False) -> ProjectionCache:
    """Return a cached ProjectionCache instance."""
    global _CACHE
    if force_reload or _CACHE is None:
        _CACHE = ProjectionCache.load()
    return _CACHE


def invalidate_projection_cache():
    """Drop the cached ProjectionCache instance."""
    global _CACHE
    _CACHE = None
