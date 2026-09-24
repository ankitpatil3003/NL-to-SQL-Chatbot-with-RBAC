"""Execution-accuracy comparison: does the assistant's result contain the reference result?

Relaxed for a conversational assistant (unlike strict Spider/BIRD EX): column names and order are
ignored and extra columns are allowed (the assistant may add a percentage next to a count), but
every reference value must be present in the matching row. Numbers match within rounding
tolerance; strings match case-insensitively.
"""

import datetime as dt
from decimal import Decimal
from typing import Any

RTOL = 0.005  # 0.5% relative, for large sums rounded differently
ATOL = 0.051  # absolute, for percentages rounded to 1 decimal


def _number(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int | float | Decimal):
        return float(v)
    return None


def value_matches(ref: Any, act: Any) -> bool:
    if ref is None:
        return act is None
    r, a = _number(ref), _number(act)
    if r is not None:
        return a is not None and abs(a - r) <= max(ATOL, RTOL * abs(r))
    if isinstance(ref, dt.date):
        ref = ref.isoformat()
    return str(ref).strip().casefold() == str(act).strip().casefold()


def row_covered(ref_row: list[Any], act_row: list[Any]) -> bool:
    """Each reference value is matched by a distinct value in the actual row."""
    unused = list(act_row)
    for ref in ref_row:
        idx = next((i for i, act in enumerate(unused) if value_matches(ref, act)), None)
        if idx is None:
            return False
        unused.pop(idx)
    return True


def compare(
    ref_rows: list[list[Any]],
    act_rows: list[list[Any]],
    *,
    ordered: bool = False,
    extra_rows_ok: bool = False,
) -> tuple[bool, str]:
    if not ref_rows:
        return (not act_rows, "reference is empty" + ("" if not act_rows else "; actual is not"))
    if not extra_rows_ok and len(act_rows) != len(ref_rows):
        return False, f"row count {len(act_rows)} != reference {len(ref_rows)}"
    if len(act_rows) < len(ref_rows):
        return False, f"only {len(act_rows)} rows, reference has {len(ref_rows)}"
    if ordered:
        for i, ref in enumerate(ref_rows):
            if not row_covered(ref, act_rows[i]):
                return False, f"row {i + 1}: expected {ref}, got {act_rows[i]}"
        return True, "ok"
    remaining = list(act_rows)
    for ref in ref_rows:
        idx = next((i for i, act in enumerate(remaining) if row_covered(ref, act)), None)
        if idx is None:
            return False, f"no row matches reference {ref}"
        remaining.pop(idx)
    return True, "ok"
