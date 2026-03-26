"""Custom QValidators and form-level validation helpers."""

from __future__ import annotations

from typing import List, Tuple

from PySide6.QtGui import QValidator


class GamedayCodeValidator(QValidator):
    """Accepts gameday codes like 3.2, 17.4, or 0."""

    def validate(self, text: str, pos: int):
        text = text.strip()
        if not text or text == "-":
            return QValidator.State.Intermediate, text, pos
        try:
            val = float(text)
            if val < 0:
                return QValidator.State.Invalid, text, pos
            return QValidator.State.Acceptable, text, pos
        except ValueError:
            return QValidator.State.Invalid, text, pos


class CommaListValidator(QValidator):
    """Accepts comma-separated strings (names or numbers)."""

    def validate(self, text: str, pos: int):
        # Always acceptable - we validate at form level
        return QValidator.State.Acceptable, text, pos


def validate_squad_inputs(
    squad_text: str,
    prices_text: str,
    gd_text: str,
    itb_text: str,
    preseason: bool,
) -> Tuple[List[str], List[str]]:
    """Validate the squad-related form inputs.

    Returns (errors, warnings).
    """
    errors: List[str] = []
    warnings: List[str] = []

    if preseason:
        return errors, warnings

    # Squad
    squad = [s.strip() for s in squad_text.split(",") if s.strip()]
    if not squad:
        errors.append("Squad is empty. Retrieve your team or enter player names.")
    elif len(squad) != 10:
        errors.append(f"Squad must have exactly 10 players (found {len(squad)}).")

    # Sell prices
    prices = [s.strip() for s in prices_text.split(",") if s.strip()]
    if squad and len(prices) != len(squad):
        errors.append(
            f"Number of sell prices ({len(prices)}) does not match "
            f"number of players ({len(squad)})."
        )
    for p in prices:
        try:
            float(p)
        except ValueError:
            errors.append(f"Invalid sell price: '{p}'")
            break

    # Game day
    try:
        gd = float(gd_text)
        if gd <= 0:
            errors.append("Game day must be positive.")
    except (ValueError, TypeError):
        errors.append("Game day is not a valid number.")

    # ITB
    try:
        float(itb_text)
    except (ValueError, TypeError):
        errors.append("ITB is not a valid number.")

    return errors, warnings
