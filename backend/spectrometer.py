"""
spectrometer.py - Spectrometer (OES) File Parser for Vulcan / Sakthi Melt-OS
Parses optical emission spectrometer exports in CSV, TSV, and JSON formats
from instruments such as Spectro MAXx, Thermo ARL, and Bruker Magellan.
"""

import csv
import io
import json
import re
from typing import Dict, Any, Tuple, Optional
from backend.storage import get_all_grades

STANDARD_ELEMENTS = {"C", "Si", "Mn", "Cr", "Mo", "Ni", "Mg", "P", "S", "Al", "Cu", "Ti", "V", "Fe"}


def parse_spectrometer_file(file_content: str, filename: str = "") -> Dict[str, Any]:
    """
    Parses a spectrometer export string into a clean composition dictionary.
    Supports:
    1. Key-value JSON (direct or nested under "readings" / "composition")
    2. Vertical two-column CSV / TSV (Element, Percent)
    3. Horizontal table CSV / TSV with element headers
    4. Spectro MAXx / Thermo OES raw text reports
    """
    composition: Dict[str, float] = {}
    metadata: Dict[str, Any] = {"filename": filename}

    clean_text = file_content.strip()

    # Case 1: Try JSON
    if clean_text.startswith("{"):
        try:
            data = json.loads(clean_text)
            if "readings" in data and isinstance(data["readings"], dict):
                readings = data["readings"]
            elif "composition" in data and isinstance(data["composition"], dict):
                readings = data["composition"]
            else:
                readings = data

            for k, v in readings.items():
                el = k.strip().capitalize()
                # Special handle for 2-char elements like Si, Mn, Cr, Mo, Ni, Mg
                el_match = _normalize_element_symbol(el)
                if el_match and isinstance(v, (int, float)):
                    composition[el_match] = float(v)

            if "heat_number" in data:
                metadata["heat_number"] = data["heat_number"]
            if "grade_id" in data:
                metadata["suggested_grade_id"] = data["grade_id"]

            return _finalize_result(composition, metadata)
        except Exception:
            pass  # Fall back to CSV/text parsing

    # Case 2: Delimited CSV / TSV
    # Check delimiter
    sample_line = clean_text.splitlines()[0] if clean_text.splitlines() else ""
    delimiter = ";" if ";" in sample_line else ("\t" if "\t" in sample_line else ",")

    lines = [line.strip() for line in clean_text.splitlines() if line.strip() and not line.strip().startswith("#")]

    # Check if vertical (Element, Value) or horizontal (header of elements)
    # Check vertical first
    vertical_parsed = {}
    reader = csv.reader(lines, delimiter=delimiter)
    for row in reader:
        if len(row) >= 2:
            first_col = row[0].strip()
            # Clean possible channel prefix, e.g. "C (247.8nm)" or "Si %"
            el = re.split(r"[\s\(\[\_]", first_col)[0].strip()
            el_norm = _normalize_element_symbol(el)
            if el_norm:
                try:
                    # Look for numerical value in row[1] or last row item
                    val_str = row[1].strip().replace("%", "")
                    val = float(val_str)
                    if 0.0 <= val <= 100.0:
                        vertical_parsed[el_norm] = val
                except ValueError:
                    # Maybe header row or metadata line
                    continue

    if len(vertical_parsed) >= 2:
        composition.update(vertical_parsed)
        return _finalize_result(composition, metadata)

    # Case 3: Horizontal tabular CSV
    try:
        reader = csv.reader(lines, delimiter=delimiter)
        rows = list(reader)
        if len(rows) >= 2:
            header_row = rows[0]
            val_row = rows[1]
            for col_idx, col_name in enumerate(header_row):
                el = col_name.strip()
                el_norm = _normalize_element_symbol(el)
                if el_norm and col_idx < len(val_row):
                    try:
                        v = float(val_row[col_idx].strip().replace("%", ""))
                        if 0.0 <= v <= 100.0:
                            composition[el_norm] = v
                    except ValueError:
                        pass
    except Exception:
        pass

    if len(composition) >= 2:
        return _finalize_result(composition, metadata)

    # Case 4: Regex scanner for key-value tokens (e.g. "C: 3.45 Si: 2.10")
    for match in re.finditer(r"\b([A-Za-z]{1,2})\s*[:=]\s*([0-9]+\.?[0-9]*)\b", clean_text):
        symbol = match.group(1).strip()
        el_norm = _normalize_element_symbol(symbol)
        if el_norm:
            try:
                v = float(match.group(2))
                if 0.0 <= v <= 100.0:
                    composition[el_norm] = v
            except ValueError:
                pass

    return _finalize_result(composition, metadata)


def _normalize_element_symbol(raw: str) -> Optional[str]:
    """Matches raw strings to metallurgical symbols (e.g., 'si', 'SI', 'Silicon' -> 'Si')"""
    s = raw.strip()
    if not s:
        return None
    # 2-letter uppercase check
    if len(s) == 2:
        candidate = s[0].upper() + s[1].lower()
        if candidate in STANDARD_ELEMENTS:
            return candidate
    elif len(s) == 1:
        candidate = s.upper()
        if candidate in STANDARD_ELEMENTS:
            return candidate

    # Common full names
    name_map = {
        "carbon": "C", "silicon": "Si", "manganese": "Mn", "chromium": "Cr",
        "molybdenum": "Mo", "nickel": "Ni", "magnesium": "Mg", "phosphorus": "P",
        "sulfur": "S", "sulphur": "S", "aluminum": "Al", "copper": "Cu"
    }
    return name_map.get(s.lower())


def _detect_best_matching_grade(composition: Dict[str, float]) -> Optional[str]:
    """Matches the composition to the closest grade specification."""
    grades = get_all_grades()
    best_grade = None
    min_dist = float("inf")

    for gid, gspec in grades.items():
        g_elems = gspec.get("elements", {})
        # Check overlap
        overlap = set(g_elems.keys()).intersection(set(composition.keys()))
        if len(overlap) < 3:
            continue

        dist = 0.0
        # If Mg is present > 0.01 and grade has no Mg, penalize
        if composition.get("Mg", 0) > 0.02 and "Mg" not in g_elems:
            dist += 100.0
        # If Cr is high > 10% and grade has Cr < 2%, penalize
        if composition.get("Cr", 0) > 10.0 and g_elems.get("Cr", {}).get("max", 0) < 5.0:
            dist += 200.0

        for el in overlap:
            c = composition[el]
            target = g_elems[el].get("target", 0.0)
            dist += abs(c - target)

        if dist < min_dist:
            min_dist = dist
            best_grade = gid

    return best_grade


def _finalize_result(composition: Dict[str, float], metadata: Dict[str, Any]) -> Dict[str, Any]:
    suggested_grade = metadata.get("suggested_grade_id") or _detect_best_matching_grade(composition)
    return {
        "success": len(composition) > 0,
        "composition": composition,
        "channels_read": len(composition),
        "detected_grade_id": suggested_grade,
        "metadata": metadata
    }
