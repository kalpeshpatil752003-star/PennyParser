import re

def is_footnote_marker(raw: str) -> bool:
    """Checks if a cell is an isolated footnote/reference marker like (1), [1], (a), [a], *, †."""
    if not raw:
        return False
    s = str(raw).strip()
    # Standalone footnote markers: (1)-(9), [1]-[9], (a)-(z), [a]-[z], (i)-(iv), *, **, etc.
    if re.match(r"^(\([0-9a-zA-Z]\)|\[[0-9a-zA-Z]\]|\([ivxIVX]+\)|\[[ivxIVX]+\]|\*+|[\u2020\u2021\u00a7])$", s):
        return True
    return False

def parse_number(raw: str) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s in ("-", "—", "–", "−", "N/A", "n/a", "NA", "na", "nil", "null", "none", "...", "…"):
        return None

    # Check for isolated footnote reference cells
    if is_footnote_marker(s):
        return None

    # Replace unicode minus signs with standard hyphen-minus
    s = s.replace("—", "-").replace("–", "-").replace("−", "-")

    # Strip currency signs at start or end
    s = re.sub(r"^[\$\€\£\₹\s]+", "", s).strip()
    s = re.sub(r"[\$\€\£\₹\s]+$", "", s).strip()

    # Strip trailing footnote markers like *, **, (1), (a), [1], or letters like 'a', 'b' right after digits
    s = re.sub(r"\s*\*+$", "", s).strip()
    s = re.sub(r"\s*(\([0-9a-zA-Z]\)|\[[0-9a-zA-Z]\]|\([ivxIVX]+\)|\[[ivxIVX]+\])$", "", s).strip()
    # Also trailing footnote letter attached directly to digits e.g. "1,234a" -> "1,234"
    s = re.sub(r"(?<=\d)[a-zA-Z]$", "", s).strip()

    # Handle percentage
    is_percent = False
    if s.endswith("%"):
        is_percent = True
        s = s[:-1].strip()

    # Clean currency symbols that might still be present
    s = s.replace("$", "").replace("€", "").replace("£", "").replace("₹", "").strip()

    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()
    elif s.startswith("-"):
        negative = True
        s = s[1:].strip()

    # Clean remaining spaces and thousands separators
    s = s.replace(",", "").replace(" ", "").strip()

    if not re.match(r"^\d+(\.\d+)?$", s):
        return None

    try:
        value = float(s)
        return -value if negative else value
    except ValueError:
        return None