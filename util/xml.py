from __future__ import annotations

from typing import Optional
from pathlib import Path
from typing import Union
import xml.etree.ElementTree as ET


# =============================================================================
# Numeric safety helpers
# =============================================================================

def safe_int(value: Optional[str], default: int = 0) -> int:
    """
    Safely parse an integer from XML attributes.

    X4 XML files sometimes store integers as floats (e.g. "93000.0")
    or omit attributes entirely.

    Examples:
        "42"      -> 42
        "42.0"    -> 42
        None      -> default
        "invalid" -> default
    """
    if value is None:
        return default
    try:
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Optional[str], default: float = 0.0) -> float:
    """
    Safely parse a float from XML attributes.

    Examples:
        "3.5"     -> 3.5
        None      -> default
        "invalid" -> default
    """
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default


# =============================================================================
# XML helper utilities
# =============================================================================

def parse_xml(path: str | Path) -> ET.ElementTree:
    """
    Parse an XML file and return the ElementTree.

    Callers may safely call .getroot() on the result.
    """
    return ET.parse(path)
    
    
def find_first(parent: ET.Element, xpath: str) -> Optional[ET.Element]:
    """
    Return the first matching XML element for an XPath query,
    or None if no element is found.

    This avoids repeated boilerplate like:
        elems = root.findall(...)
        if elems: ...

    Example:
        hull = find_first(root, ".//hull")
    """
    elem = parent.find(xpath)
    return elem


def get_attr(elem: Optional[ET.Element], name: str) -> Optional[str]:
    """
    Safely retrieve an attribute from an XML element.

    Returns None if the element or attribute does not exist.
    """
    if elem is None:
        return None
    return elem.get(name)
