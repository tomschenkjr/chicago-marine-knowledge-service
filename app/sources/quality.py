BAD_NUMERIC_SENTINELS = {-100000.0, -99999.992, 999.9, -99.0}


def parse_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed in BAD_NUMERIC_SENTINELS:
        return None
    return parsed


def quality_flags(raw_values: dict[str, object]) -> list[str]:
    flags: list[str] = []
    for field, value in raw_values.items():
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if parsed in BAD_NUMERIC_SENTINELS:
            flags.append(f"{field}:bad_sentinel")
    return flags

