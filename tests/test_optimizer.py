"""
test_optimizer.py - Comprehensive Unit & Metallurgical Integrity Tests for Vulcan Melt-OS
Verifies LP formulations, independent mass balance verification, soft constraints,
dilution tracking, and fuzz testing across automotive and industrial casting grades.
"""

import pytest
import numpy as np
from backend.storage import get_all_grades, get_all_alloys
from backend.optimizer import solve_alloy_addition, evaluate_ce, validate_ce_formula


def calculate_independent_mass_balance(melt_weight_kg, c0_dict, recommendations, alloys_catalog):
    """
    Independent 1st-principles metallurgical mass-balance calculation.
    Used to independently verify the HiGHS LP solver results.
    """
    alloys_map = {a["id"]: a for a in alloys_catalog}
    total_added_kg = sum(r["quantity_kg"] for r in recommendations)
    final_weight_kg = melt_weight_kg + total_added_kg

    retained_added_mass = {}
    for r in recommendations:
        alloy = alloys_map[r["alloy_id"]]
        w = r["quantity_kg"]
        for el, frac in alloy.get("composition", {}).items():
            eta = alloy.get("recovery", {}).get(el, 0.80)
            retained_added_mass[el] = retained_added_mass.get(el, 0.0) + w * frac * eta

    computed_final = {}
    all_elements = set(c0_dict.keys()).union(set(retained_added_mass.keys()))
    for el in all_elements:
        base_mass = melt_weight_kg * (c0_dict.get(el, 0.0) / 100.0)
        added_mass = retained_added_mass.get(el, 0.0)
        c_fin = ((base_mass + added_mass) / final_weight_kg) * 100.0
        computed_final[el] = c_fin

    return computed_final, final_weight_kg


def test_all_standard_grades_feasibility():
    """Verifies that all 6 preconfigured industrial grades solve with 100% success."""
    grades = get_all_grades()
    alloys = get_all_alloys()

    for gid, gspec in grades.items():
        res = solve_alloy_addition(
            melt_weight_kg=gspec.get("default_weight_kg", 4000.0),
            current_composition=gspec["demo_reading"],
            grade_spec=gspec,
            alloys_catalog=alloys,
            mode="target"
        )
        assert res["success"] is True, f"Grade {gid} failed optimization: {res.get('message')}"
        assert res["total_added_kg"] >= 0.0
        assert res["total_cost"] >= 0.0
        assert res["total_cost_inr"] >= 0.0
        assert len(res["violations"]) == 0, f"Grade {gid} produced unexpected violations: {res['violations']}"


def test_independent_mass_balance_accuracy():
    """
    Verifies that the LP solver's reported final_composition matches
    independent 1st-principles mass balance to within 1e-3%.
    """
    grades = get_all_grades()
    alloys = get_all_alloys()

    for gid, gspec in grades.items():
        m0 = gspec.get("default_weight_kg", 4000.0)
        c0 = gspec["demo_reading"]
        res = solve_alloy_addition(
            melt_weight_kg=m0,
            current_composition=c0,
            grade_spec=gspec,
            alloys_catalog=alloys,
            mode="target"
        )
        assert res["success"] is True

        computed_final, final_wt = calculate_independent_mass_balance(
            melt_weight_kg=m0,
            c0_dict=c0,
            recommendations=res["recommendations"],
            alloys_catalog=alloys
        )

        for el in gspec["elements"].keys():
            solver_val = res["final_composition"][el]
            indep_val = computed_final[el]
            diff = abs(solver_val - indep_val)
            assert diff < 0.001, f"Grade {gid} element {el} mass-balance mismatch: solver={solver_val:.4f}%, indep={indep_val:.4f}%, diff={diff:.6f}"


def test_fesimg_gated_on_magnesium():
    """Ensures FeSiMg nodulizer is never recommended for non-ductile iron grades."""
    grades = get_all_grades()
    alloys = get_all_alloys()

    # Grey iron FG 260 has NO magnesium requirement
    grey_spec = grades["grey_iron_fg260"]
    res = solve_alloy_addition(
        melt_weight_kg=5000.0,
        current_composition=grey_spec["demo_reading"],
        grade_spec=grey_spec,
        alloys_catalog=alloys,
        mode="target"
    )
    assert res["success"] is True
    added_alloy_ids = [r["alloy_id"] for r in res["recommendations"]]
    assert "fesimg_nodulizer" not in added_alloy_ids, "FeSiMg was incorrectly added to Grey Cast Iron!"


def test_dilution_protection():
    """
    Verifies that when a large addition is made, elements that start in spec
    are constrained to prevent dilution below grade minimum.
    """
    grades = get_all_grades()
    alloys = get_all_alloys()

    # Hadfield manganese steel requires large manganese addition (~250 kg)
    hadfield_spec = grades["hadfield_manganese"]
    res = solve_alloy_addition(
        melt_weight_kg=4000.0,
        current_composition=hadfield_spec["demo_reading"],
        grade_spec=hadfield_spec,
        alloys_catalog=alloys,
        mode="target"
    )
    assert res["success"] is True
    for el, spec in hadfield_spec["elements"].items():
        if spec["min"] > 0:
            assert res["final_composition"][el] >= spec["min"] - 1e-4, (
                f"Element {el} diluted below minimum ({spec['min']}%): got {res['final_composition'][el]}%"
            )


def test_soft_constraints_on_over_spec_input():
    """
    When an input already exceeds the maximum ceiling, the solver should NOT crash
    or fail with bare 'infeasible', but return a best-effort plan with soft violations.
    """
    grades = get_all_grades()
    alloys = get_all_alloys()

    spec = grades["ductile_iron_500_7"]
    bad_reading = dict(spec["demo_reading"])
    bad_reading["Si"] = 3.20  # Max is 2.70%, already way over spec

    res = solve_alloy_addition(
        melt_weight_kg=4000.0,
        current_composition=bad_reading,
        grade_spec=spec,
        alloys_catalog=alloys,
        mode="target"
    )
    assert res["success"] is True
    # Should report violation or over_spec_alert
    assert len(res["violations"]) > 0 or len(res.get("over_spec_alerts", [])) > 0
    # Recommendations should not crash
    assert "recommendations" in res


def test_lean_mode_vs_target_mode():
    """Verifies that lean mode targets the lower bound and yields equal or lower cost than target mode."""
    grades = get_all_grades()
    alloys = get_all_alloys()

    gspec = grades["ductile_iron_500_7"]
    res_target = solve_alloy_addition(
        melt_weight_kg=4000.0,
        current_composition=gspec["demo_reading"],
        grade_spec=gspec,
        alloys_catalog=alloys,
        mode="target"
    )
    res_lean = solve_alloy_addition(
        melt_weight_kg=4000.0,
        current_composition=gspec["demo_reading"],
        grade_spec=gspec,
        alloys_catalog=alloys,
        mode="lean"
    )

    assert res_target["success"] is True
    assert res_lean["success"] is True
    # Lean mode cost should be <= target mode cost
    assert res_lean["total_cost"] <= res_target["total_cost"] + 0.01


def test_fuzz_random_inputs():
    """
    Fuzz testing: tests 50 randomized spectrometer readings per grade (300 total)
    to confirm solver robustness with zero unhandled exceptions.
    """
    grades = get_all_grades()
    alloys = get_all_alloys()
    rng = np.random.default_rng(42)

    total_runs = 0
    for gid, gspec in grades.items():
        base = gspec["demo_reading"]
        for _ in range(50):
            noisy_reading = {}
            for el, val in base.items():
                # Perturb between -30% and +30%
                noise = rng.uniform(0.70, 1.30)
                noisy_reading[el] = max(0.001, round(val * noise, 4))

            # Vary melt weight between 500 and 10000 kg
            w = float(rng.uniform(500, 10000))

            res = solve_alloy_addition(
                melt_weight_kg=w,
                current_composition=noisy_reading,
                grade_spec=gspec,
                alloys_catalog=alloys,
                mode="target"
            )
            assert res is not None
            assert "success" in res
            assert "recommendations" in res
            total_runs += 1

    assert total_runs == 300


def test_safe_ce_evaluator_security_and_accuracy():
    """
    Verifies that the AST-based Carbon Equivalent evaluator strictly enforces
    allowed symbols and operators, and rejects code injection attempts.
    """
    # 1. Reject malicious code injection payloads
    exploit_payloads = [
        "().__class__.__base__.__subclasses__()",
        "__import__('os').system('calc')",
        "eval('1+1')",
        "open('/etc/passwd').read()",
        "exec('import sys')",
        "C.__class__",
        "C + [1, 2, 3]",
        "lambda: C",
    ]
    for payload in exploit_payloads:
        assert validate_ce_formula(payload) is False, f"Failed to reject exploit: {payload}"
        res = evaluate_ce(payload, {"C": 3.5, "Si": 2.0})
        assert res is None, f"evaluate_ce should return None for exploit: {payload}"

    # 2. Reject disallowed identifiers and syntax
    invalid_formulas = [
        "C + Fe / 2",  # Fe is not in ALLOWED_CE_SYMBOLS
        "C + Titanium * 2",
        "C + +",
        "1 / 0",  # Div zero handled safely
    ]
    assert validate_ce_formula("C + Fe / 2") is False
    assert validate_ce_formula("C + Titanium * 2") is False
    assert evaluate_ce("1 / 0", {"C": 3.0}) is None

    # 3. Valid formulas calculate correctly
    valid_formula = "C + (Si + P) / 3"
    assert validate_ce_formula(valid_formula) is True
    comp = {"C": 3.60, "Si": 2.40, "P": 0.03}
    expected = round(3.60 + (2.40 + 0.03) / 3, 3)
    assert evaluate_ce(valid_formula, comp) == expected

    # Steel / Stainless (None formula) returns None
    assert evaluate_ce(None, comp) is None


def test_calculation_trace_slag_loss_and_recovery_notices():
    """Verifies that the optimizer produces calculation trace with slag/oxidation losses and recovery notices."""
    grades = get_all_grades()
    alloys = get_all_alloys()
    gspec = grades["ductile_iron_500_7"]

    # Normal solve produces calculation trace
    res = solve_alloy_addition(
        melt_weight_kg=4000.0,
        current_composition=gspec["demo_reading"],
        grade_spec=gspec,
        alloys_catalog=alloys,
        mode="target"
    )
    assert "calculation_trace" in res
    trace = res["calculation_trace"]
    assert trace["optimizer_version"] == "2.1.0-scipy-highs"
    assert trace["fx_rate"] == 84.0
    assert trace["estimated_slag_loss_kg"] >= 0.0
    assert trace["slag_loss_pct_of_additions"] >= 0.0
    assert "Estimated" in trace["oxidation_loss_note"]

    # When an alloy lacks explicit recovery for an element, notice is recorded
    custom_alloys = [dict(a) for a in alloys]
    # Remove Si recovery from fesi_75
    fesi = next(a for a in custom_alloys if a["id"] == "fesi_75")
    fesi_rec = dict(fesi["recovery"])
    del fesi_rec["Si"]
    fesi["recovery"] = fesi_rec

    res2 = solve_alloy_addition(
        melt_weight_kg=4000.0,
        current_composition=gspec["demo_reading"],
        grade_spec=gspec,
        alloys_catalog=custom_alloys,
        mode="target"
    )
    trace2 = res2["calculation_trace"]
    assert any("Default recovery (0.80) used for Si" in n for n in trace2["notices"])
