"""Color interpolation utilities."""

from PySide6.QtGui import QColor


def ryg_color(value: float, min_val: float, max_val: float) -> QColor:
    """Return a red-yellow-green interpolated QColor for *value*.

    *value* is clamped to [min_val, max_val].  The gradient goes:
        min  -> red (#FF0000)
        mid  -> yellow (#FFFF00)
        max  -> green (#00FF00)
    """
    if max_val == min_val:
        return QColor("#FFFFE0")

    norm = max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

    if norm < 0.5:
        t = norm * 2
        r = int(255 * (1 - t) + 255 * t)
        g = int(0 * (1 - t) + 255 * t)
        b = 0
    else:
        t = (norm - 0.5) * 2
        r = int(255 * (1 - t))
        g = 255
        b = 0

    return QColor(r, g, b)


def xp_color(xp: float) -> QColor:
    """Return a color for an xP value -- desaturated, clean palette."""
    if xp == 0:
        return QColor("#EF4444")  # red-500
    elif xp < 20:
        return QColor("#EAB308")  # yellow-500
    return QColor("#22C55E")  # green-500
