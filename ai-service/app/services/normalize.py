import re

def parse_number(raw: str) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s in ("-", "—", "–", "−", "N/A", "n/a", "NA", "na", "nil", "null", "none", "..."):
        return None

    # Replace unicode minus signs with standard hyphen-minus
    s = s.replace("—", "-").replace("–", "-").replace("−", "-")

    # Handle footnote markers like *, **, (1) at the end
    s = re.sub(r"\s*\*+$", "", s).strip()

    # Clean currency symbols and leading spaces before checking brackets
    s = re.sub(r"^[\$\€\£\₹\s]+", "", s).strip()

    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()
    elif s.startswith("-"):
        negative = True
        s = s[1:].strip()

    # Handle percentage
    if s.endswith("%"):
        s = s[:-1].strip()

    # Clean remaining currency symbols and thousands separators
    s = s.replace("$", "").replace(",", "").strip()

    if not re.match(r"^\d+(\.\d+)?$", s):
        return None

    try:
        value = float(s)
        return -value if negative else value
    except ValueError:
        return None