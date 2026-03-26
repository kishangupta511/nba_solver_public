"""Typed dataclass for all solver inputs with validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class SolverOptions:
    """All parameters the solver needs, with defaults matching the template."""

    # Team
    team_id: int = 148

    # Main options
    horizon: int = 5
    tm: int = 0
    solve_time: int = 300
    preseason: bool = False
    captain_played: bool = False

    # Chip options
    wc_day: float = 0
    wc_days: List[float] = field(default_factory=list)
    wc_range: List[float] = field(default_factory=list)
    all_star_day: float = 0
    all_star_days: List[float] = field(default_factory=list)
    all_star_range: List[float] = field(default_factory=list)

    # Forced options
    banned_players: List[str] = field(default_factory=list)
    forced_players: List[str] = field(default_factory=list)
    forced_players_days: Dict[str, list] = field(default_factory=dict)

    # Advanced options
    decay_base: float = 0.98
    bench_weight: float = 0.1
    trf_last_gw: int = 0
    ft_value: float = 10
    ft_increment: float = 2.5
    threshold_value: float = 2.8
    no_sols: int = 1
    alternative_solution: str = "1week_buy"

    # Back-to-back decay
    b2b_decay: List[float] = field(default_factory=lambda: [0.975, 0.95])
    current_season: str = "2024-25"
    fixture_weight: str = "low"
    use_daily_mins: bool = False

    # Solver paths (from settings file, not editable in GUI)
    solver: str = "cbc"
    cbc_path: Optional[str] = None
    highs_path: Optional[str] = None

    # ------------------------------------------------------------------
    @classmethod
    def from_json(cls, path: str) -> "SolverOptions":
        """Load options from a JSON settings file."""
        with open(path) as f:
            data = json.load(f)
        # Only pass keys that match dataclass fields
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def to_solver_dict(self) -> dict:
        """Return a plain dict suitable for passing to solve_multi_period_NBA."""
        return {
            "team_id": self.team_id,
            "horizon": self.horizon,
            "tm": self.tm,
            "solve_time": self.solve_time,
            "preseason": self.preseason,
            "captain_played": self.captain_played,
            "wc_day": self.wc_day,
            "wc_days": self.wc_days,
            "wc_range": self.wc_range,
            "all_star_day": self.all_star_day,
            "all_star_days": self.all_star_days,
            "all_star_range": self.all_star_range,
            "banned_players": self.banned_players,
            "forced_players": self.forced_players,
            "forced_players_days": self.forced_players_days,
            "decay_base": self.decay_base,
            "bench_weight": self.bench_weight,
            "trf_last_gw": self.trf_last_gw,
            "ft_value": self.ft_value,
            "ft_increment": self.ft_increment,
            "threshold_value": self.threshold_value,
            "no_sols": self.no_sols,
            "alternative_solution": self.alternative_solution,
            "solver": self.solver,
            "cbc_path": self.cbc_path,
            "highs_path": self.highs_path,
        }

    def validate(self) -> Tuple[List[str], List[str]]:
        """Validate the options.

        Returns (errors, warnings) where each is a list of strings.
        Errors prevent solving; warnings are informational.
        """
        errors: List[str] = []
        warnings: List[str] = []

        if self.horizon < 1:
            errors.append("Horizon must be at least 1.")
        if self.horizon > 30:
            warnings.append(f"Horizon of {self.horizon} is very large and may take a long time.")

        if self.no_sols < 1:
            errors.append("Number of solutions must be at least 1.")

        if self.decay_base <= 0 or self.decay_base > 1:
            errors.append("Decay base must be between 0 (exclusive) and 1 (inclusive).")

        if self.bench_weight < 0 or self.bench_weight > 1:
            errors.append("Bench weight must be between 0 and 1.")

        if self.wc_range and len(self.wc_range) != 2:
            errors.append("Wildcard range must have exactly 2 values (start, end).")

        if self.all_star_range and len(self.all_star_range) != 2:
            errors.append("All Star range must have exactly 2 values (start, end).")

        return errors, warnings
