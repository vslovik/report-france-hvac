from datetime import date


def last_n_quarters(n: int, at_date = None) -> list[str]:
    """Returns a list of the last N quarters in 'YYYY MM' format."""
    if at_date is None:
        at_date = date.today()
    # Find the current quarter's start month (1, 4, 7, or 10)
    current_quarter_month = ((at_date.month - 1) // 3) * 3 + 1
    year, month = at_date.year, current_quarter_month

    quarters = []
    for _ in range(n):
        quarters.append(f"{year} {month:02d}")
        # Step back one quarter
        month -= 3
        if month <= 0:
            month += 12
            year -= 1

    return quarters[::-1]


def last_n_quarters_label(n: int, at_date = None) -> list[str]:
    """Returns a list of the last N quarters in 'YYYY QQ' format."""
    if at_date is None:
        at_date = date.today()
    current_quarter = (at_date.month - 1) // 3 + 1
    year, quarter = at_date.year, current_quarter

    quarters = []
    for _ in range(n):
        quarters.append(f"{year} Q{quarter}")
        quarter -= 1
        if quarter <= 0:
            quarter = 4
            year -= 1

    return quarters[::-1]


def mm_to_quarter_label(quarters: list[str]) -> list[str]:
    """Converts 'YYYY MM' quarter strings to 'YYYY QQ' format."""
    return [f"{y} Q{(int(m) - 1) // 3 + 1}" for y, m in (q.split() for q in quarters)]