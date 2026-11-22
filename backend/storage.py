"""
storage.py - Persistence Layer for Vulcan / Sakthi Melt-OS
Manages configurable grade recipes (data/grades.json), editable alloy inventory (data/alloys.json),
and the SQLite digital heat log & audit trail (data/heats.db).
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
from backend.catalog import GRADES as SEED_GRADES, FERROALLOYS as SEED_ALLOYS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
GRADES_FILE = os.path.join(DATA_DIR, "grades.json")
ALLOYS_FILE = os.path.join(DATA_DIR, "alloys.json")
DB_FILE = os.path.join(DATA_DIR, "heats.db")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


# ==========================================
# 1. GRADES REPOSITORY (data/grades.json)
# ==========================================

def init_grades():
    ensure_data_dir()
    if not os.path.exists(GRADES_FILE):
        with open(GRADES_FILE, "w", encoding="utf-8") as f:
            json.dump(SEED_GRADES, f, indent=2)


def get_all_grades() -> Dict[str, Any]:
    init_grades()
    try:
        with open(GRADES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return SEED_GRADES


def get_grade(grade_id: str) -> Optional[Dict[str, Any]]:
    grades = get_all_grades()
    return grades.get(grade_id)


def save_grade(grade_id: str, grade_data: Dict[str, Any]) -> Dict[str, Any]:
    ensure_data_dir()
    grades = get_all_grades()
    grades[grade_id] = grade_data
    with open(GRADES_FILE, "w", encoding="utf-8") as f:
        json.dump(grades, f, indent=2)
    return grade_data


def delete_grade(grade_id: str) -> bool:
    ensure_data_dir()
    grades = get_all_grades()
    if grade_id in grades:
        del grades[grade_id]
        with open(GRADES_FILE, "w", encoding="utf-8") as f:
            json.dump(grades, f, indent=2)
        return True
    return False


def reset_grades_to_defaults():
    ensure_data_dir()
    with open(GRADES_FILE, "w", encoding="utf-8") as f:
        json.dump(SEED_GRADES, f, indent=2)
    return SEED_GRADES


# ==========================================
# 2. ALLOYS REPOSITORY (data/alloys.json)
# ==========================================

def init_alloys():
    ensure_data_dir()
    if not os.path.exists(ALLOYS_FILE):
        with open(ALLOYS_FILE, "w", encoding="utf-8") as f:
            json.dump(SEED_ALLOYS, f, indent=2)


def get_all_alloys() -> List[Dict[str, Any]]:
    init_alloys()
    try:
        with open(ALLOYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return SEED_ALLOYS


def get_alloy(alloy_id: str) -> Optional[Dict[str, Any]]:
    alloys = get_all_alloys()
    for a in alloys:
        if a["id"] == alloy_id:
            return a
    return None


def save_alloy(alloy_id: str, alloy_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ensure_data_dir()
    alloys = get_all_alloys()
    found = False
    for i, a in enumerate(alloys):
        if a["id"] == alloy_id:
            alloys[i] = {**a, **alloy_data, "id": alloy_id}
            found = True
            break
    if not found:
        alloy_data["id"] = alloy_id
        alloys.append(alloy_data)
    with open(ALLOYS_FILE, "w", encoding="utf-8") as f:
        json.dump(alloys, f, indent=2)
    return get_alloy(alloy_id)


def reset_alloys_to_defaults():
    ensure_data_dir()
    with open(ALLOYS_FILE, "w", encoding="utf-8") as f:
        json.dump(SEED_ALLOYS, f, indent=2)
    return SEED_ALLOYS


# ==========================================
# 3. SQLITE DIGITAL HEAT AUDIT TRAIL (data/heats.db)
# ==========================================

def get_db_connection() -> sqlite3.Connection:
    ensure_data_dir()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    ensure_data_dir()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS heats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            heat_number TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            grade_id TEXT NOT NULL,
            grade_name TEXT NOT NULL,
            melt_weight_kg REAL NOT NULL,
            mode TEXT NOT NULL,
            input_chemistry TEXT NOT NULL,
            final_chemistry TEXT NOT NULL,
            recoveries_snapshot TEXT NOT NULL,
            alloy_prices_snapshot TEXT NOT NULL,
            recommendations TEXT NOT NULL,
            actual_additions TEXT,
            violations TEXT NOT NULL,
            total_cost_inr REAL NOT NULL,
            total_cost_usd REAL NOT NULL,
            status TEXT NOT NULL,
            operator_name TEXT,
            override_reason TEXT,
            notes TEXT
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_heats_number ON heats(heat_number);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_heats_created_at ON heats(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_heats_grade ON heats(grade_id);")
    conn.commit()
    conn.close()


def generate_next_heat_number() -> str:
    """Generates standard foundry heat sequence: H-YYYY-MMDD-NNN"""
    now = datetime.now()
    date_prefix = f"H-{now.strftime('%Y-%m%d')}"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT heat_number FROM heats WHERE heat_number LIKE ? ORDER BY id DESC LIMIT 1",
        (f"{date_prefix}-%",)
    )
    row = cursor.fetchone()
    conn.close()

    if row and row["heat_number"]:
        try:
            last_seq = int(row["heat_number"].split("-")[-1])
            next_seq = last_seq + 1
        except Exception:
            next_seq = 1
    else:
        next_seq = 1

    return f"{date_prefix}-{next_seq:03d}"


def log_heat(record: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    heat_number = record.get("heat_number") or generate_next_heat_number()
    created_at = record.get("created_at") or datetime.now().isoformat()
    status = record.get("status", "CALCULATED")

    cursor.execute("""
        INSERT INTO heats (
            heat_number, created_at, grade_id, grade_name, melt_weight_kg, mode,
            input_chemistry, final_chemistry, recoveries_snapshot, alloy_prices_snapshot,
            recommendations, actual_additions, violations, total_cost_inr, total_cost_usd,
            status, operator_name, override_reason, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        heat_number,
        created_at,
        record["grade_id"],
        record.get("grade_name", record["grade_id"]),
        float(record["melt_weight_kg"]),
        record.get("mode", "target"),
        json.dumps(record["input_chemistry"]),
        json.dumps(record["final_chemistry"]),
        json.dumps(record.get("recoveries_snapshot", {})),
        json.dumps(record.get("alloy_prices_snapshot", {})),
        json.dumps(record.get("recommendations", [])),
        json.dumps(record.get("actual_additions", record.get("recommendations", []))),
        json.dumps(record.get("violations", [])),
        float(record.get("total_cost_inr", 0.0)),
        float(record.get("total_cost_usd", 0.0)),
        status,
        record.get("operator_name"),
        record.get("override_reason"),
        record.get("notes")
    ))
    heat_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return get_heat(heat_id)


def get_heat(heat_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM heats WHERE id = ?", (heat_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    for k in ["input_chemistry", "final_chemistry", "recoveries_snapshot",
              "alloy_prices_snapshot", "recommendations", "actual_additions", "violations"]:
        if d.get(k):
            try:
                d[k] = json.loads(d[k])
            except Exception:
                pass
    return d


def get_heat_by_number(heat_number: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM heats WHERE heat_number = ?", (heat_number,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    for k in ["input_chemistry", "final_chemistry", "recoveries_snapshot",
              "alloy_prices_snapshot", "recommendations", "actual_additions", "violations"]:
        if d.get(k):
            try:
                d[k] = json.loads(d[k])
            except Exception:
                pass
    return d


def list_heats(search: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM heats"
    params = []
    if search:
        query += " WHERE heat_number LIKE ? OR grade_name LIKE ? OR operator_name LIKE ? OR status LIKE ?"
        s = f"%{search}%"
        params.extend([s, s, s, s])
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        d = dict(row)
        for k in ["input_chemistry", "final_chemistry", "recommendations", "actual_additions", "violations"]:
            if d.get(k):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    pass
        result.append(d)
    return result


def update_heat_status(
    heat_id: int,
    status: str,
    operator_name: Optional[str] = None,
    override_reason: Optional[str] = None,
    actual_additions: Optional[List[Dict[str, Any]]] = None,
    notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    updates = ["status = ?"]
    params = [status]

    if operator_name is not None:
        updates.append("operator_name = ?")
        params.append(operator_name)
    if override_reason is not None:
        updates.append("override_reason = ?")
        params.append(override_reason)
    if actual_additions is not None:
        updates.append("actual_additions = ?")
        params.append(json.dumps(actual_additions))
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)

    params.append(heat_id)
    cursor.execute(f"UPDATE heats SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()

    return get_heat(heat_id)


# Initialize files on module load
init_grades()
init_alloys()
init_db()
