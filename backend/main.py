"""
main.py - FastAPI Application for Automated Corrective Alloy Addition
Provides high-performance REST APIs for melt chemistry optimization,
traceability explainability, digital heat audit logging, spectrometer import,
and interactive alloy/grade recipe configuration.
"""

from typing import Dict, List, Any, Optional, Literal
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import os

from backend.catalog import ELEMENT_METADATA
from backend.storage import (
    get_all_grades, get_grade, save_grade, delete_grade, reset_grades_to_defaults,
    get_all_alloys, get_alloy, save_alloy, reset_alloys_to_defaults,
    log_heat, get_heat, get_heat_by_number, list_heats, update_heat_status,
    generate_next_heat_number, get_heat_events
)
from backend.optimizer import solve_alloy_addition, validate_ce_formula
from backend.explainability import generate_alloy_explanations, compute_heuristic_comparison
from backend.spectrometer import parse_spectrometer_file
from backend.export_service import export_heat_csv, export_heat_pdf
from backend.config import DEFAULT_FX_RATE, OPTIMIZER_VERSION

app = FastAPI(
    title="VULCAN Melt-OS - Foundry Decision Support System",
    description="Automated Corrective Alloy Addition from Spectrometer Results using Constrained Linear Programming",
    version="2.0.0"
)


# ==========================================
# PYDANTIC REQUEST & RESPONSE SCHEMAS
# ==========================================

class OptimizationRequest(BaseModel):
    grade_id: str
    melt_weight_kg: float = Field(..., ge=100.0, le=50000.0, description="Melt weight in kg (100 to 50,000 kg)")
    current_composition: Dict[str, float]
    disabled_alloy_ids: Optional[List[str]] = None
    mode: Literal["target", "lean"] = "target"
    custom_alloy_costs: Optional[Dict[str, float]] = None


class WhatIfRequest(BaseModel):
    grade_id: str
    melt_weight_kg: float = Field(..., ge=100.0, le=50000.0, description="Melt weight in kg (100 to 50,000 kg)")
    current_composition: Dict[str, float]
    disabled_alloy_ids: Optional[List[str]] = None
    custom_alloy_costs: Optional[Dict[str, float]] = None
    mode: Literal["target", "lean"] = "target"
    heats_per_day: Optional[float] = Field(12.0, ge=1.0, le=100.0)
    working_days_per_year: Optional[float] = Field(300.0, ge=1.0, le=366.0)


class SpectrometerImportPayload(BaseModel):
    content: str
    filename: Optional[str] = "spectro_input.csv"


class GradeElementSpec(BaseModel):
    min: float = Field(..., ge=0.0, le=100.0)
    target: float = Field(..., ge=0.0, le=100.0)
    max: float = Field(..., ge=0.0, le=100.0)
    step: Optional[float] = 0.01


class GradeCreateOrUpdateRequest(BaseModel):
    id: str
    name: str
    casting_part: Optional[str] = ""
    category: Optional[str] = "Cast Iron"
    default_weight_kg: Optional[float] = Field(4000.0, ge=100.0, le=50000.0)
    ce_formula: Optional[str] = None
    elements: Dict[str, GradeElementSpec]
    demo_reading: Optional[Dict[str, float]] = None
    description: Optional[str] = ""


class AlloyUpdateRequest(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    cost_per_kg: Optional[float] = Field(None, ge=0.0)
    cost_inr_per_kg: Optional[float] = Field(None, ge=0.0)
    bag_size_kg: Optional[float] = Field(None, ge=1.0)
    charge_order: Optional[int] = Field(None, ge=1)
    composition: Optional[Dict[str, float]] = None
    recovery: Optional[Dict[str, float]] = None
    description: Optional[str] = None


class SimulatedAdditionItem(BaseModel):
    alloy_id: str
    weight_kg: float = Field(..., ge=0.0)


class SimulationRequest(BaseModel):
    grade_id: str
    melt_weight_kg: float = Field(..., ge=100.0, le=50000.0)
    current_composition: Dict[str, float]
    additions: List[SimulatedAdditionItem]


class HeatLogCreateRequest(BaseModel):
    heat_number: Optional[str] = None
    grade_id: str
    grade_name: Optional[str] = None
    melt_weight_kg: float = Field(..., ge=100.0, le=50000.0)
    mode: Literal["target", "lean"] = "target"
    input_chemistry: Dict[str, float]
    final_chemistry: Dict[str, float]
    recoveries_snapshot: Optional[Dict[str, Any]] = None
    alloy_prices_snapshot: Optional[Dict[str, Any]] = None
    recommendations: List[Dict[str, Any]]
    actual_additions: Optional[List[Dict[str, Any]]] = None
    violations: Optional[List[Dict[str, Any]]] = None
    total_cost_inr: float = 0.0
    total_cost_usd: float = 0.0
    status: Literal["CALCULATED", "UNDER_REVIEW", "APPROVED", "REJECTED", "OVERRIDDEN"] = "CALCULATED"
    operator_name: Optional[str] = None
    override_reason: Optional[str] = None
    notes: Optional[str] = None


class HeatStatusUpdateRequest(BaseModel):
    status: Literal["CALCULATED", "UNDER_REVIEW", "APPROVED", "REJECTED", "OVERRIDDEN"]
    operator_name: Optional[str] = None
    override_reason: Optional[str] = None
    actual_additions: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None


# ==========================================
# VALIDATION HELPER
# ==========================================

def validate_heat_input(
    grade_id: str,
    melt_weight_kg: float,
    current_composition: Dict[str, float],
    disabled_alloy_ids: Optional[List[str]] = None,
    custom_alloy_costs: Optional[Dict[str, float]] = None
):
    """Enforces strict input validation rules per technical requirements."""
    grades = get_all_grades()
    if grade_id not in grades:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown grade_id: '{grade_id}'. Valid grades: {list(grades.keys())}"
        )

    grade_spec = grades[grade_id]
    required_elements = list(grade_spec["elements"].keys())
    missing_elements = [el for el in required_elements if el not in current_composition]
    if missing_elements:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required elements for grade '{grade_id}': {missing_elements}. Spectrometer readings must include all specified elements."
        )

    for elem, val in current_composition.items():
        if val < 0.0 or val > 100.0:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid concentration for {elem}: {val}%. Must be between 0.0% and 100.0%."
            )

    alloys = get_all_alloys()
    valid_alloy_ids = {a["id"] for a in alloys}
    if disabled_alloy_ids:
        invalid_alloys = [aid for aid in disabled_alloy_ids if aid not in valid_alloy_ids]
        if invalid_alloys:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown alloy ID(s) in disabled_alloy_ids: {invalid_alloys}."
            )

    if custom_alloy_costs:
        for aid, cost in custom_alloy_costs.items():
            if aid not in valid_alloy_ids:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unknown alloy ID in custom_alloy_costs: '{aid}'."
                )
            if cost < 0.0:
                raise HTTPException(
                    status_code=422,
                    detail=f"Cost for alloy '{aid}' cannot be negative: {cost}."
                )


def check_implausible_chemistry(grade_spec: Dict[str, Any], current_composition: Dict[str, float]) -> List[str]:
    """Returns soft warnings (non-fatal advisory notices) for implausible or extreme spectrometer readings."""
    warnings = []
    category = grade_spec.get("category", "")
    is_steel = "steel" in category.lower() or "stainless" in category.lower()
    c_val = current_composition.get("C", 0.0)

    if is_steel and c_val > 5.0:
        warnings.append(
            f"Implausible reading: Carbon is {c_val:.2f}% in a steel grade (normal steel is < 2.0% C). Verify spectrometer calibration or sample contamination."
        )
    elif c_val > 6.0:
        warnings.append(
            f"Implausible reading: Carbon is {c_val:.2f}% (exceeds theoretical iron-carbon eutectic ceiling of 4.3%-5.0%)."
        )

    for el, val in current_composition.items():
        if val > 80.0 and el != "Fe":
            warnings.append(f"Implausible reading: {el} concentration is {val:.2f}%, unusually high for foundry melts.")

    return warnings


# ==========================================
# 1. GRADE RECIPE APIS (Configurable Grades)
# ==========================================

@app.get("/api/grades")
def get_grades():
    """Returns all active metallurgical grade recipes."""
    grades = get_all_grades()
    return {"grades": list(grades.values())}


@app.get("/api/grades/{grade_id}")
def get_grade_detail(grade_id: str):
    """Returns specific target grade details and demo spectrometer reading."""
    grade = get_grade(grade_id)
    if not grade:
        raise HTTPException(status_code=404, detail=f"Grade '{grade_id}' not found")
    return grade


@app.post("/api/grades")
def create_grade(payload: GradeCreateOrUpdateRequest):
    """Creates a new user-configured metallurgical grade with element corridor and CE formula validation."""
    if payload.ce_formula and not validate_ce_formula(payload.ce_formula):
        raise HTTPException(
            status_code=422,
            detail="Invalid Carbon Equivalent formula. Only element symbols (C, Si, P, Mn, Cr, Mo, Ni, Cu, V), numbers, and + - * / () are allowed."
        )

    for el_name, spec in payload.elements.items():
        if not (spec.min <= spec.target <= spec.max):
            raise HTTPException(
                status_code=422,
                detail=f"Element '{el_name}' has invalid corridor: min ({spec.min}) <= target ({spec.target}) <= max ({spec.max}) violated."
            )

    grade_dict = payload.model_dump()
    save_grade(payload.id, grade_dict)
    return {"message": f"Grade '{payload.id}' created successfully", "grade": grade_dict}


@app.put("/api/grades/{grade_id}")
def update_grade_recipe(grade_id: str, payload: GradeCreateOrUpdateRequest):
    """Updates an existing metallurgical grade recipe with validation."""
    if payload.ce_formula and not validate_ce_formula(payload.ce_formula):
        raise HTTPException(
            status_code=422,
            detail="Invalid Carbon Equivalent formula. Only element symbols (C, Si, P, Mn, Cr, Mo, Ni, Cu, V), numbers, and + - * / () are allowed."
        )

    for el_name, spec in payload.elements.items():
        if not (spec.min <= spec.target <= spec.max):
            raise HTTPException(
                status_code=422,
                detail=f"Element '{el_name}' has invalid corridor: min ({spec.min}) <= target ({spec.target}) <= max ({spec.max}) violated."
            )

    grade_dict = payload.model_dump()
    grade_dict["id"] = grade_id
    save_grade(grade_id, grade_dict)
    return {"message": f"Grade '{grade_id}' updated successfully", "grade": grade_dict}


@app.delete("/api/grades/{grade_id}")
def delete_grade_recipe(grade_id: str):
    """Deletes a custom metallurgical grade recipe."""
    grades = get_all_grades()
    if grade_id not in grades:
        raise HTTPException(status_code=404, detail="Grade not found")
    if len(grades) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the only remaining grade in the catalog.")
    delete_grade(grade_id)
    return {"message": f"Grade '{grade_id}' deleted successfully"}


@app.post("/api/grades/reset")
def reset_grades():
    """Resets grades catalog back to factory defaults."""
    seeded = reset_grades_to_defaults()
    return {"message": "Grades reset to factory standard defaults", "count": len(seeded)}


# ==========================================
# 2. ALLOY INVENTORY APIS (Editable Recoveries)
# ==========================================

@app.get("/api/alloys")
def get_alloys():
    """Returns active ferroalloy inventory, compositions, recovery factors, and unit costs."""
    alloys = get_all_alloys()
    return {"alloys": alloys}


@app.get("/api/alloys/{alloy_id}")
def get_alloy_detail(alloy_id: str):
    """Returns details of a specific ferroalloy."""
    alloy = get_alloy(alloy_id)
    if not alloy:
        raise HTTPException(status_code=404, detail=f"Alloy '{alloy_id}' not found")
    return alloy


@app.put("/api/alloys/{alloy_id}")
def update_alloy(alloy_id: str, payload: AlloyUpdateRequest):
    """Updates an alloy's recovery factors, composition percentages, unit costs, or bag sizing."""
    current = get_alloy(alloy_id)
    if not current:
        raise HTTPException(status_code=404, detail=f"Alloy '{alloy_id}' not found")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    
    # Validate recoveries <= 1.0 (100%) and >= 0.0
    if "recovery" in update_data and update_data["recovery"]:
        for el, rec in update_data["recovery"].items():
            if rec < 0.0 or rec > 1.0:
                raise HTTPException(
                    status_code=422,
                    detail=f"Recovery factor for {el} must be between 0.0 (0%) and 1.0 (100%). Received {rec}."
                )

    # Validate compositions <= 1.0 (100%) and >= 0.0
    if "composition" in update_data and update_data["composition"]:
        for el, frac in update_data["composition"].items():
            if frac < 0.0 or frac > 1.0:
                raise HTTPException(
                    status_code=422,
                    detail=f"Alloy composition fraction for {el} must be between 0.0 and 1.0. Received {frac}."
                )

    updated = save_alloy(alloy_id, update_data)
    return {"message": f"Alloy '{alloy_id}' updated successfully", "alloy": updated}


@app.post("/api/alloys/reset")
def reset_alloys():
    """Resets alloys catalog back to factory defaults."""
    seeded = reset_alloys_to_defaults()
    return {"message": "Alloys inventory reset to factory standard defaults", "count": len(seeded)}


# ==========================================
# 3. SPECTROMETER IMPORT APIS
# ==========================================

@app.post("/api/spectrometer/import")
def import_spectrometer_reading(
    file: Optional[UploadFile] = File(None),
    payload: Optional[SpectrometerImportPayload] = None
):
    """
    Parses an uploaded OES spectrometer file (CSV, TSV, JSON) or direct JSON payload.
    Extracts element compositions and suggests the closest matching grade.
    """
    content = ""
    filename = "spectro_input"

    # Check if a real file was uploaded
    is_real_file = file is not None and hasattr(file, "file") and hasattr(file, "filename") and file.filename

    if is_real_file:
        filename = file.filename or "spectro_file"
        raw_bytes = file.file.read()
        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = raw_bytes.decode("latin-1")
    elif payload and payload.content:
        content = payload.content
        filename = payload.filename or "direct_input.csv"
    else:
        raise HTTPException(status_code=400, detail="Provide either a file upload or JSON payload with 'content'.")

    result = parse_spectrometer_file(content, filename=filename)
    if not result.get("success") or not result.get("composition"):
        raise HTTPException(
            status_code=422,
            detail="Could not parse spectrometer channels from provided file. Ensure CSV has 'Element,Percent' or JSON has 'readings'."
        )

    return result


# ==========================================
# 4. ELEMENTS METADATA
# ==========================================

@app.get("/api/elements")
def get_elements():
    """Returns periodic table & metallurgical role metadata for spectrometer channels."""
    return {"elements": ELEMENT_METADATA}


# ==========================================
# 5. CORE OPTIMIZATION & WHAT-IF APIS
# ==========================================

@app.post("/api/optimize")
def optimize_melt_chemistry(req: OptimizationRequest):
    """
    Solves for cost-minimal alloy additions to bring spectrometer readings into grade spec.
    Includes dilution tracking, cross-contamination, bag breakdown, and explainability.
    """
    validate_heat_input(
        grade_id=req.grade_id,
        melt_weight_kg=req.melt_weight_kg,
        current_composition=req.current_composition,
        disabled_alloy_ids=req.disabled_alloy_ids,
        custom_alloy_costs=req.custom_alloy_costs
    )

    grade_spec = get_grade(req.grade_id)
    alloys = get_all_alloys()

    # Clone alloys and apply custom costs if provided
    alloys_copy = [dict(a) for a in alloys]
    if req.custom_alloy_costs:
        for a in alloys_copy:
            if a["id"] in req.custom_alloy_costs:
                a["cost_per_kg"] = float(req.custom_alloy_costs[a["id"]])

    # Solve LP
    result = solve_alloy_addition(
        melt_weight_kg=req.melt_weight_kg,
        current_composition=req.current_composition,
        grade_spec=grade_spec,
        alloys_catalog=alloys_copy,
        disabled_alloy_ids=req.disabled_alloy_ids,
        mode=req.mode
    )

    warnings = check_implausible_chemistry(grade_spec, req.current_composition)
    result["warnings"] = warnings
    result["fx_rate"] = DEFAULT_FX_RATE

    if not result.get("success"):
        return result

    # Attach explainability rationales
    explanations = generate_alloy_explanations(
        optimization_result=result,
        alloys_catalog=alloys_copy,
        grade_spec=grade_spec
    )
    result["explanations"] = explanations

    return result


@app.get("/api/config")
def get_app_config():
    """Returns system configuration constants including single-source FX rate and optimizer version."""
    return {
        "fx_rate": DEFAULT_FX_RATE,
        "optimizer_version": OPTIMIZER_VERSION,
        "currency": "INR"
    }


@app.post("/api/what-if")
def compare_what_if(req: WhatIfRequest):
    """
    Compares the LP joint optimizer against the traditional single-carrier manual spreadsheet heuristic.
    """
    validate_heat_input(
        grade_id=req.grade_id,
        melt_weight_kg=req.melt_weight_kg,
        current_composition=req.current_composition,
        disabled_alloy_ids=req.disabled_alloy_ids,
        custom_alloy_costs=req.custom_alloy_costs
    )

    grade_spec = get_grade(req.grade_id)
    alloys = get_all_alloys()

    comparison = compute_heuristic_comparison(
        melt_weight_kg=req.melt_weight_kg,
        current_composition=req.current_composition,
        grade_spec=grade_spec,
        alloys_catalog=alloys,
        disabled_alloy_ids=req.disabled_alloy_ids,
        custom_alloy_costs=req.custom_alloy_costs,
        mode=req.mode,
        heats_per_day=req.heats_per_day or 12.0,
        working_days_per_year=req.working_days_per_year or 300.0
    )

    return comparison


@app.post("/api/simulate-additions")
def simulate_manual_additions(req: SimulationRequest):
    """
    Recalculates melt chemistry when an operator manually overrides alloy additions.
    Performs full mass balance and returns predicted chemistry + spec violations.
    """
    grade_spec = get_grade(req.grade_id)
    if not grade_spec:
        raise HTTPException(status_code=404, detail=f"Grade '{req.grade_id}' not found")

    alloys_dict = {a["id"]: a for a in get_all_alloys()}
    m0 = req.melt_weight_kg
    total_added_kg = sum(item.weight_kg for item in req.additions)
    m_final = m0 + total_added_kg

    # Net retained mass per element
    retained_added_mass: Dict[str, float] = {}
    tot_cost_usd = 0.0
    tot_cost_inr = 0.0

    FX_RATE = 84.0

    for item in req.additions:
        alloy = alloys_dict.get(item.alloy_id)
        if not alloy:
            continue
        w = item.weight_kg
        tot_cost_usd += w * alloy.get("cost_per_kg", 0.0)
        inr_rate = alloy.get("cost_inr_per_kg") or (alloy.get("cost_per_kg", 0.0) * FX_RATE)
        tot_cost_inr += w * inr_rate

        comp = alloy.get("composition", {})
        rec = alloy.get("recovery", {})
        for el, frac in comp.items():
            eta = rec.get(el, 0.80)
            retained_added_mass[el] = retained_added_mass.get(el, 0.0) + w * frac * eta

    # Final composition
    predicted_comp: Dict[str, float] = {}
    all_elements = set(grade_spec["elements"].keys()).union(set(req.current_composition.keys()))

    violations = []
    for el in all_elements:
        c0 = req.current_composition.get(el, 0.0)
        base_mass = m0 * (c0 / 100.0)
        added_retained = retained_added_mass.get(el, 0.0)
        c_fin = ((base_mass + added_retained) / m_final) * 100.0
        predicted_comp[el] = round(c_fin, 4)

        # Check against grade spec
        spec = grade_spec["elements"].get(el)
        if spec:
            if c_fin < spec["min"] - 1e-4:
                violations.append({
                    "element": el,
                    "side": "under",
                    "amount_pct": round(spec["min"] - c_fin, 4),
                    "reason": f"{el} final ({c_fin:.4f}%) is below minimum requirement ({spec['min']}%)"
                })
            elif c_fin > spec["max"] + 1e-4:
                violations.append({
                    "element": el,
                    "side": "over",
                    "amount_pct": round(c_fin - spec["max"], 4),
                    "reason": f"{el} final ({c_fin:.4f}%) exceeds maximum limit ({spec['max']}%)"
                })

    return {
        "success": True,
        "is_in_spec": len(violations) == 0,
        "predicted_composition": predicted_comp,
        "violations": violations,
        "total_added_kg": round(total_added_kg, 2),
        "final_melt_weight_kg": round(m_final, 2),
        "total_cost_usd": round(tot_cost_usd, 2),
        "total_cost_inr": round(tot_cost_inr, 2)
    }


# ==========================================
# 6. DIGITAL HEAT AUDIT TRAIL & VERIFICATION APIS
# ==========================================

@app.get("/api/heats/next-number")
def get_next_heat_number():
    """Generates the next sequential foundry heat number."""
    return {"next_heat_number": generate_next_heat_number()}


@app.get("/api/heats")
def list_heat_records(
    search: Optional[str] = Query(None, description="Search by heat #, grade, operator, status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Returns past heat logs with search, filtering, and approval status."""
    clean_search = search if isinstance(search, str) else None
    clean_limit = int(getattr(limit, "default", limit) or 50)
    clean_offset = int(getattr(offset, "default", offset) or 0)
    records = list_heats(search=clean_search, limit=clean_limit, offset=clean_offset)
    return {"heats": records, "count": len(records)}


@app.get("/api/heats/{heat_id}")
def get_heat_record(heat_id: int):
    """Retrieves full metallurgical record and snapshot for a specific heat."""
    record = get_heat(heat_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Heat record #{heat_id} not found")
    return record


@app.post("/api/heats")
def create_heat_record(payload: HeatLogCreateRequest):
    """Logs a new heat calculation and verification state into the SQLite audit trail."""
    status = payload.status
    op_name = (payload.operator_name or "").strip()
    reason = (payload.override_reason or "").strip()

    if status in ("APPROVED", "OVERRIDDEN", "REJECTED"):
        if not op_name:
            raise HTTPException(
                status_code=422,
                detail=f"operator_name is mandatory when recording heat with status '{status}'."
            )

    if status in ("OVERRIDDEN", "REJECTED"):
        if not reason:
            raise HTTPException(
                status_code=422,
                detail=f"override_reason is mandatory when recording heat with status '{status}'."
            )

    record = log_heat(payload.model_dump())
    return {"message": "Heat record logged successfully", "heat": record}


@app.put("/api/heats/{heat_id}/status")
def update_heat_approval_status(heat_id: int, payload: HeatStatusUpdateRequest):
    """
    Updates the verification workflow status (Calculated -> Under review -> Approved / Rejected / Overridden).
    Mandates operator_name for APPROVED, OVERRIDDEN, REJECTED and override_reason for OVERRIDDEN and REJECTED.
    """
    current = get_heat(heat_id)
    if not current:
        raise HTTPException(status_code=404, detail=f"Heat record #{heat_id} not found")

    status = payload.status
    op_name = (payload.operator_name or "").strip()
    reason = (payload.override_reason or "").strip()

    if status in ("APPROVED", "OVERRIDDEN", "REJECTED"):
        if not op_name:
            raise HTTPException(
                status_code=422,
                detail=f"operator_name is mandatory when updating heat to status '{status}'."
            )

    if status in ("OVERRIDDEN", "REJECTED"):
        if not reason:
            raise HTTPException(
                status_code=422,
                detail=f"override_reason is mandatory when updating heat to status '{status}'."
            )

    updated = update_heat_status(
        heat_id=heat_id,
        status=payload.status,
        operator_name=op_name,
        override_reason=reason,
        actual_additions=payload.actual_additions,
        notes=payload.notes
    )
    return {"message": f"Heat #{heat_id} updated to '{payload.status}'", "heat": updated}


@app.get("/api/heats/{heat_id}/events")
def get_heat_audit_events(heat_id: int):
    """
    Retrieves the complete append-only audit trail and lifecycle transitions for a specific heat.
    Includes timestamps, actor signatures, previous/new states, justifications, and cryptographic hashes.
    """
    record = get_heat(heat_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Heat record #{heat_id} not found")
    events = get_heat_events(heat_id)
    return {
        "heat_id": heat_id,
        "heat_number": record.get("heat_number"),
        "grade_version_hash": record.get("grade_version_hash"),
        "optimizer_version": record.get("optimizer_version"),
        "snapshot_hash": record.get("snapshot_hash"),
        "events": events
    }


@app.get("/api/heats/{heat_id}/export")
def export_heat_document(heat_id: int, format: Literal["csv", "pdf"] = "pdf"):
    """
    Exports official foundry charging dispatch ticket in CSV or high-resolution vector PDF.
    """
    heat = get_heat(heat_id)
    if not heat:
        raise HTTPException(status_code=404, detail=f"Heat record #{heat_id} not found")

    heat_num = heat.get("heat_number", f"heat_{heat_id}")

    if format == "csv":
        csv_text = export_heat_csv(heat)
        return Response(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={heat_num}_report.csv"}
        )
    else:
        pdf_bytes = export_heat_pdf(heat)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={heat_num}_ticket.pdf"}
        )


# ==========================================
# 7. STATIC FILES & FRONTEND MOUNT
# ==========================================

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "VULCAN Melt-OS API running. Mount static/index.html to view dashboard."}
