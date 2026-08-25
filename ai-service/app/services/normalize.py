import re

def parse_number(raw: str) -> float | None:
    if raw is None:
        return None
    s = raw.strip()
    if s == "" or s == "-":
        return None
    negative = s.startswith("(") and s.endswith(")")  # accounting negative notation
    s = s.strip("()").replace("$", "").replace(",", "").strip()
    if not re.match(r"^-?\d+(\.\d+)?$", s):
        return None  # not actually a number (e.g. a text cell)
    value = float(s)
    return -value if negative else value