"""
test_api.py - Direct Integration Tests for Vulcan Melt-OS REST Endpoints
Tests Grade CRUD, Alloy CRUD, Spectrometer Import, Optimization, Simulation,
Heat Audit Logging, Verification Workflow, and PDF/CSV Export.
"""

import pytest
import asyncio
from fastapi import HTTPException
from backend.main import (
    get_grades, get_grade_detail, create_grade, update_grade_recipe, delete_grade_recipe,
    get_alloys, get_alloy_detail, update_alloy,
    import_spectrometer_reading, optimize_melt_chemistry, compare_what_if,
    simulate_manual_additions, create_heat_record, update_heat_approval_status,
    list_heat_records, get_heat_record, export_heat_document,
    OptimizationRequest, WhatIfRequest, SimulationRequest, SimulatedAdditionItem,
    HeatLogCreateRequest, HeatStatusUpdateRequest, GradeCreateOrUpdateRequest,
    GradeElementSpec, AlloyUpdateRequest, SpectrometerImportPayload
)
from backend.storage import reset_grades_to_defaults, reset_alloys_to_defaults


@pytest.fixture(autouse=True)
def clean_catalogs():
    reset_grades_to_defaults()
    reset_alloys_to_defaults()
    yield
    reset_grades_to_defaults()
    reset_alloys_to_defaults()


def test_get_grades_and_alloys():
    res_g = get_grades()
    assert "grades" in res_g
    assert len(res_g["grades"]) >= 6

    res_a = get_alloys()
    assert "alloys" in res_a
    assert len(res_a["alloys"]) >= 10


def test_grade_crud_and_validation():
    # 1. Invalid corridor: min > target
    invalid_req = GradeCreateOrUpdateRequest(
        id="bad_grade",
        name="Bad Grade Spec",
        elements={
            "C": GradeElementSpec(min=3.5, target=3.2, max=3.8)  # min > target!
        }
    )
    with pytest.raises(HTTPException) as excinfo:
        create_grade(invalid_req)
    assert excinfo.value.status_code == 422
    assert "violated" in excinfo.value.detail

    # 2. Valid creation
    valid_req = GradeCreateOrUpdateRequest(
        id="custom_iron_1",
        name="Custom Foundry Iron",
        category="Ductile Iron",
        default_weight_kg=3500.0,
        ce_formula="C + Si / 3.0",
        elements={
            "C": GradeElementSpec(min=3.40, target=3.60, max=3.80, step=0.01),
            "Si": GradeElementSpec(min=2.20, target=2.40, max=2.60, step=0.01),
            "Mn": GradeElementSpec(min=0.30, target=0.40, max=0.50, step=0.01)
        },
        demo_reading={"C": 3.30, "Si": 2.10, "Mn": 0.25}
    )
    res_create = create_grade(valid_req)
    assert res_create["grade"]["id"] == "custom_iron_1"

    # 3. Retrieve
    res_get = get_grade_detail("custom_iron_1")
    assert res_get["name"] == "Custom Foundry Iron"

    # 4. Delete
    res_del = delete_grade_recipe("custom_iron_1")
    assert "deleted successfully" in res_del["message"]

    with pytest.raises(HTTPException) as excinfo:
        get_grade_detail("custom_iron_1")
    assert excinfo.value.status_code == 404


def test_alloy_update_and_recovery_validation():
    # Invalid recovery > 1.0 (100%)
    with pytest.raises(HTTPException) as excinfo:
        update_alloy("fesi_75", AlloyUpdateRequest(recovery={"Si": 1.45}))
    assert excinfo.value.status_code == 422
    assert "Recovery factor" in excinfo.value.detail

    # Valid update
    res_ok = update_alloy("fesi_75", AlloyUpdateRequest(
        cost_inr_per_kg=165.0,
        recovery={"Si": 0.88}
    ))
    updated = res_ok["alloy"]
    assert updated["cost_inr_per_kg"] == 165.0
    assert updated["recovery"]["Si"] == 0.88


def test_spectrometer_payload_import():
    csv_data = "Element,Percent\nC,3.42\nSi,2.05\nMn,0.22\nMg,0.038\nP,0.028\nS,0.010\n"
    res = import_spectrometer_reading(
        payload=SpectrometerImportPayload(content=csv_data, filename="sample.csv")
    )
    assert res["success"] is True
    assert res["composition"]["C"] == 3.42
    assert res["composition"]["Si"] == 2.05
    assert res["composition"]["Mn"] == 0.22


def test_simulate_manual_additions():
    req = SimulationRequest(
        grade_id="ductile_iron_500_7",
        melt_weight_kg=4000.0,
        current_composition={
            "C": 3.42, "Si": 2.05, "Mn": 0.22, "Mg": 0.038, "P": 0.028, "S": 0.010
        },
        additions=[
            SimulatedAdditionItem(alloy_id="recarburizer_graphite", weight_kg=15.0),
            SimulatedAdditionItem(alloy_id="fesi_75", weight_kg=25.0)
        ]
    )
    res = simulate_manual_additions(req)
    assert res["success"] is True
    assert "predicted_composition" in res
    assert res["total_added_kg"] == 40.0
    assert res["total_cost_inr"] > 0


def test_heat_audit_trail_and_verification_workflow():
    # 1. Create heat
    heat_req = HeatLogCreateRequest(
        grade_id="ductile_iron_500_7",
        grade_name="SG Iron 500/7",
        melt_weight_kg=4000.0,
        mode="target",
        input_chemistry={"C": 3.42, "Si": 2.05, "Mn": 0.22, "Mg": 0.038, "P": 0.028, "S": 0.010},
        final_chemistry={"C": 3.65, "Si": 2.50, "Mn": 0.40, "Mg": 0.042, "P": 0.028, "S": 0.010},
        recommendations=[
            {"alloy_id": "fesi_75", "short_name": "FeSi 75", "weight_kg": 23.23, "cost_inr": 3716.8, "cost_usd": 44.14}
        ],
        total_cost_inr=8140.0,
        total_cost_usd=96.70,
        status="CALCULATED"
    )
    res_create = create_heat_record(heat_req)
    heat = res_create["heat"]
    heat_id = heat["id"]
    heat_number = heat["heat_number"]
    assert heat_number.startswith("H-")

    # 2. Update to OVERRIDDEN without justification -> expects 422
    with pytest.raises(HTTPException) as excinfo:
        update_heat_approval_status(heat_id, HeatStatusUpdateRequest(
            status="OVERRIDDEN",
            operator_name="R. Kumar"
        ))
    assert excinfo.value.status_code == 422
    assert "justification" in excinfo.value.detail.lower()

    # 3. Update to OVERRIDDEN with justification -> succeeds
    res_override = update_heat_approval_status(heat_id, HeatStatusUpdateRequest(
        status="OVERRIDDEN",
        operator_name="R. Kumar",
        override_reason="Furnace wall erosion: rounded FeSi to 25.0 kg full sack."
    ))
    assert res_override["heat"]["status"] == "OVERRIDDEN"

    # 4. List heats
    res_list = list_heat_records()
    assert len(res_list["heats"]) >= 1

    # 5. Export CSV
    res_csv = export_heat_document(heat_id, format="csv")
    assert res_csv.headers["content-disposition"].endswith(".csv")
    assert b"SAKTHI MELT-OS" in res_csv.body

    # 6. Export PDF
    res_pdf = export_heat_document(heat_id, format="pdf")
    assert res_pdf.headers["content-disposition"].endswith(".pdf")
    assert res_pdf.body.startswith(b"%PDF-")
