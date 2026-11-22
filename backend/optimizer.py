"""
optimizer.py - Core Linear Optimization Engine for Metallurgical Corrective Additions
Uses SciPy HiGHS LP solver with recovery-adjusted mass conservation, dilution dynamics,
and soft penalty slack variables for guaranteed best-effort feasibility.
"""

from typing import Dict, List, Any, Optional
import numpy as np
from scipy.optimize import linprog


def evaluate_ce(formula: Optional[str], composition: Dict[str, float]) -> Optional[float]:
    """Safely evaluates Carbon Equivalent using the grade-specific CE formula."""
    if not formula:
        return None
    try:
        # Build safe context with allowed metallurgical element symbols
        allowed_keys = ("C", "Si", "P", "Mn", "Cr", "Mo", "Ni", "Cu", "V")
        context = {elem: float(composition.get(elem, 0.0)) for elem in allowed_keys}
        val = eval(formula, {"__builtins__": {}}, context)
        return round(float(val), 3)
    except Exception:
        return None


def solve_alloy_addition(
    melt_weight_kg: float,
    current_composition: Dict[str, float],
    grade_spec: Dict[str, Any],
    alloys_catalog: List[Dict[str, Any]],
    disabled_alloy_ids: Optional[List[str]] = None,
    mode: str = "target"  # "target" or "lean"
) -> Dict[str, Any]:
    """
    Computes cost-optimal ferroalloy additions using Constrained Linear Programming with Soft Slack Penalties.
    """
    disabled_set = set(disabled_alloy_ids or [])
    grade_elements = grade_spec.get("elements", {})
    all_elements = list(grade_elements.keys())

    # 1. ALLOY GATING (Phase 1, Item 3)
    # - Gate any alloy containing Mg on the grade having Mg.min > 0
    # - Gate other alloys on whether they contribute to a constrained element in this grade
    active_alloys = []
    has_mg_requirement = grade_elements.get("Mg", {}).get("min", 0.0) > 0.0

    for a in alloys_catalog:
        if a["id"] in disabled_set:
            continue

        # If alloy contains intentional Mg (>0.005), require grade to have Mg.min > 0
        if a["composition"].get("Mg", 0.0) > 0.005:
            if not has_mg_requirement:
                continue

        # Check if alloy contributes to any element constrained in this grade (excluding carrier Fe/Ash)
        contributes_to_grade = any(
            elem in grade_elements and a["composition"].get(elem, 0.0) > 0.005
            for elem in a["composition"]
            if elem not in ("Fe", "Ash")
        )
        if contributes_to_grade:
            active_alloys.append(a)

    if not active_alloys:
        return {
            "success": False,
            "error": "No relevant ferroalloys available in inventory for this grade's chemistry.",
            "violations": [{
                "element": "ALL",
                "side": "min",
                "amount_pct": 0.0,
                "reason": "No active ferroalloys available in inventory to correct melt chemistry."
            }],
            "recommendations": [],
            "over_spec_alerts": []
        }

    # 2. OVER-SPEC PRE-CHECK (Phase 1, Item 4)
    # If an element is already over max, do not add a hard upper row for it.
    # Keep it from getting worse (max(max_val, c0)) and report in over_spec_alerts.
    over_spec_alerts = []
    effective_max_bounds = {}
    for elem, bounds in grade_elements.items():
        c0 = float(current_composition.get(elem, 0.0))
        u_bound = float(bounds.get("max", 100.0))
        if c0 > u_bound:
            delta = c0 - u_bound
            over_spec_alerts.append({
                "element": elem,
                "current": c0,
                "max": u_bound,
                "excess": round(delta, 3),
                "message": f"{elem} is already +{delta:.3f}% over upper limit ({u_bound}%). Requires dilution or decarburization."
            })
            effective_max_bounds[elem] = c0  # Keep it from getting worse
        else:
            effective_max_bounds[elem] = u_bound

    # 3. BUILD LP CONSTRAINTS WITH DILUTION SAFEGUARD & SLACK VARIABLES
    # Decision variables:
    # x = [x_0, ..., x_{n-1}, s_0, ..., s_{m-1}]
    # where x_j are alloy addition kg, and s_k are soft slack penalties (kg deficit/excess).
    num_alloys = len(active_alloys)
    PENALTY_COST = 10000.0  # $10,000/kg penalty for constraint violation

    A_ub_base = []
    b_ub = []
    constraint_metadata = []

    for elem in all_elements:
        bounds = grade_elements[elem]
        c0 = float(current_composition.get(elem, 0.0))
        min_val = float(bounds.get("min", 0.0))
        target_val = float(bounds.get("target", min_val))
        eff_max = effective_max_bounds[elem]

        has_carrier = any(alloy["composition"].get(elem, 0.0) >= 0.05 for alloy in active_alloys)
        any_alloy_contains = any(alloy["composition"].get(elem, 0.0) > 0.001 for alloy in active_alloys)

        lower_threshold = target_val if mode == "target" else min_val

        # LOWER BOUND ROW (Phase 1, Item 2 - Dilution Bug Fix):
        # For every element with min > 0 and a carrier alloy, ALWAYS add a lower row.
        # Use lower_threshold if c0 < lower_threshold, otherwise the hard floor min_val.
        if min_val > 0 and has_carrier:
            eff_lower = lower_threshold if c0 < lower_threshold else min_val
            row_lower = []
            for alloy in active_alloys:
                comp = alloy["composition"].get(elem, 0.0)
                rec = alloy["recovery"].get(elem, 0.80)
                effective_yield = comp * rec
                row_lower.append((eff_lower / 100.0) - effective_yield)
            A_ub_base.append(row_lower)
            b_ub.append(melt_weight_kg * (c0 - eff_lower) / 100.0)
            constraint_metadata.append({
                "type": "lower",
                "element": elem,
                "bound_value": eff_lower,
                "is_floor": (eff_lower == min_val and c0 >= lower_threshold),
                "description": f"Enforce {elem} >= {eff_lower:.3f}% ({'target' if eff_lower == target_val else 'min floor'})"
            })

        # UPPER BOUND ROW:
        # Prevent additions from exceeding ceiling (or from worsening pre-existing excess)
        if any_alloy_contains:
            row_upper = []
            for alloy in active_alloys:
                comp = alloy["composition"].get(elem, 0.0)
                rec = alloy["recovery"].get(elem, 0.80)
                effective_yield = comp * rec
                row_upper.append(effective_yield - (eff_max / 100.0))
            A_ub_base.append(row_upper)
            b_ub.append(melt_weight_kg * (eff_max - c0) / 100.0)
            constraint_metadata.append({
                "type": "upper",
                "element": elem,
                "bound_value": eff_max,
                "description": f"Prevent {elem} from exceeding ceiling of {eff_max:.3f}%"
            })

    # Assemble full LP matrix with slack variables
    num_constraints = len(A_ub_base)
    cost_vector = [a["cost_per_kg"] for a in active_alloys] + [PENALTY_COST] * num_constraints
    bounds = [(0.0, None) for _ in range(num_alloys + num_constraints)]

    A_ub = []
    for k in range(num_constraints):
        slack_row = [0.0] * num_constraints
        slack_row[k] = -1.0  # sum(A_ij * x_j) - s_k <= b_k
        A_ub.append(A_ub_base[k] + slack_row)

    # 4. SOLVE VIA SCIPY HIGHS
    if num_constraints == 0:
        alloy_quantities = [0.0] * num_alloys
        total_cost = 0.0
        marginals = []
    else:
        lp_res = linprog(
            c=cost_vector,
            A_ub=A_ub,
            b_ub=b_ub,
            bounds=bounds,
            method="highs"
        )
        if lp_res.success:
            alloy_quantities = [max(0.0, float(q)) for q in lp_res.x[:num_alloys]]
            # Total purchase cost is based strictly on real alloy additions, excluding slack penalties
            total_cost = sum(qty * a["cost_per_kg"] for qty, a in zip(alloy_quantities, active_alloys))
            marginals = [float(m) for m in (lp_res.ineqlin.marginals if hasattr(lp_res, "ineqlin") and lp_res.ineqlin is not None else [])]
        else:
            # Absolute fallback if solver fails (should not happen with unbounded slacks)
            alloy_quantities = [0.0] * num_alloys
            total_cost = 0.0
            marginals = []

    # 5. POST-ADDITION METALLURGICAL MASS BALANCE & DILUTION
    total_added_kg = sum(alloy_quantities)
    final_weight_kg = melt_weight_kg + total_added_kg

    final_composition = {}
    element_audit = []

    for elem in all_elements:
        c0 = float(current_composition.get(elem, 0.0))
        initial_mass_kg = melt_weight_kg * (c0 / 100.0)

        added_mass_kg = 0.0
        contributions = []
        for i, alloy in enumerate(active_alloys):
            qty = alloy_quantities[i]
            if qty > 0.001 and elem in alloy["composition"]:
                elem_frac = alloy["composition"][elem]
                rec_frac = alloy["recovery"].get(elem, 0.80)
                retained_mass = qty * elem_frac * rec_frac
                added_mass_kg += retained_mass
                contributions.append({
                    "alloy_id": alloy["id"],
                    "alloy_name": alloy["short_name"],
                    "added_kg": round(qty, 2),
                    "retained_elem_kg": round(retained_mass, 3),
                    "pct_contribution": 0.0
                })

        final_mass_kg = initial_mass_kg + added_mass_kg
        final_pct = (final_mass_kg / final_weight_kg) * 100.0 if final_weight_kg > 0 else 0.0
        final_composition[elem] = round(final_pct, 4)

        if added_mass_kg > 0:
            for c in contributions:
                c["pct_contribution"] = round((c["retained_elem_kg"] / added_mass_kg) * 100.0, 1)

        b = grade_elements[elem]
        min_v = float(b.get("min", 0.0))
        tgt_v = float(b.get("target", min_v))
        max_v = float(b.get("max", 100.0))

        status = "IN_SPEC"
        if final_pct < min_v - 0.0001:
            status = "BELOW_SPEC"
        elif final_pct > max_v + 0.0001:
            status = "ABOVE_SPEC"

        element_audit.append({
            "element": elem,
            "initial_pct": c0,
            "final_pct": round(final_pct, 3),
            "delta_pct": round(final_pct - c0, 3),
            "target_pct": tgt_v,
            "min_pct": min_v,
            "max_pct": max_v,
            "added_mass_kg": round(added_mass_kg, 3),
            "status": status,
            "contributions": contributions
        })

    # 6. SHOP PACKAGING BREAKDOWN
    recommendations = []
    for i, alloy in enumerate(active_alloys):
        qty = alloy_quantities[i]
        if qty >= 0.05:  # Practical melt shop threshold (50 grams)
            bag_size = alloy.get("bag_size_kg", 25.0)
            full_bags = int(qty // bag_size)
            loose_kg = round(qty % bag_size, 2)
            cost_usd = round(qty * alloy["cost_per_kg"], 2)
            # Consistent INR pricing derived from USD with FX rate 84.0
            cost_inr = round(qty * (alloy.get("cost_inr_per_kg") or (alloy["cost_per_kg"] * 84.0)), 2)

            recommendations.append({
                "alloy_id": alloy["id"],
                "alloy_name": alloy["name"],
                "short_name": alloy["short_name"],
                "quantity_kg": round(qty, 2),
                "bag_size_kg": bag_size,
                "full_bags": full_bags,
                "loose_kg": loose_kg,
                "charge_order": alloy.get("charge_order", 2),
                "cost_per_kg": alloy["cost_per_kg"],
                "cost_inr_per_kg": round(alloy.get("cost_inr_per_kg") or (alloy["cost_per_kg"] * 84.0), 2),
                "total_cost": cost_usd,
                "total_cost_inr": cost_inr,
                "composition": alloy["composition"],
                "recovery": alloy["recovery"],
                "description": alloy.get("description", "")
            })

    # 7. VIOLATIONS DETECTION & DIAGNOSTIC REASONING (Phase 1, Item 4)
    violations = []
    for elem, bounds in grade_elements.items():
        min_v = float(bounds.get("min", 0.0))
        max_v = float(bounds.get("max", 100.0))
        c_fin = final_composition[elem]
        c_init = float(current_composition.get(elem, 0.0))

        # Check deficit below minimum specification
        if min_v > 0 and c_fin < min_v - 0.0001:
            deficit_pct = round(min_v - c_fin, 4)
            has_carrier = any(a["composition"].get(elem, 0.0) >= 0.05 for a in active_alloys)
            if not has_carrier:
                reason = f"No available ferroalloy in inventory supplies {elem}."
            else:
                reason = f"{elem} is below min spec {min_v:.3f}% by {deficit_pct:.3f}%; additions constrained by ceiling on carrier elements."
            violations.append({
                "element": elem,
                "side": "min",
                "amount_pct": deficit_pct,
                "reason": reason
            })

        # Check ceiling excess
        if c_fin > max_v + 0.0001:
            excess_pct = round(c_fin - max_v, 4)
            if c_init > max_v:
                reason = f"{elem} was already +{c_init - max_v:.3f}% over upper limit before additions. Dilution or decarburization required."
            elif elem == "Si" and any(r["alloy_id"] == "fesimg_nodulizer" for r in recommendations):
                reason = f"Si ceiling {max_v:.2f}% leaves no headroom for the Mg treatment (FeSiMg), which adds about 0.4% Si. Lower base Si or dilute."
            elif elem == "C" and any("hc_" in r["alloy_id"] for r in recommendations):
                reason = f"C ceiling {max_v:.3f}% was exceeded due to carbon carried by high-carbon ferroalloys. Switch to low-carbon alloys or dilute."
            else:
                reason = f"{elem} final level ({c_fin:.3f}%) exceeds ceiling of {max_v:.3f}% by +{excess_pct:.3f}%."
            violations.append({
                "element": elem,
                "side": "max",
                "amount_pct": excess_pct,
                "reason": reason
            })

    # 8. LIQUIDUS & CE EVALUATION (Phase 1, Item 5)
    # Only compute for grades whose ce_formula is not None (iron grades); return null for steels and stainless
    ce_formula = grade_spec.get("ce_formula")
    ce_initial = evaluate_ce(ce_formula, current_composition)
    ce_final = evaluate_ce(ce_formula, final_composition)
    liquidus_temp_c = round(1669.0 - (124.0 * ce_final), 1) if (ce_final is not None and "Iron" in grade_spec.get("category", "")) else None

    # 9. BINDING CONSTRAINTS & NUMERIC SHADOW PRICES (No pre-formatted string currency)
    binding_constraints = []
    if marginals and len(marginals) >= num_constraints:
        for meta, m in zip(constraint_metadata, marginals[:num_constraints]):
            if abs(m) > 1e-4:
                shadow_price_usd = round(abs(m), 2)
                shadow_price_inr = round(shadow_price_usd * 84.0, 2)
                binding_constraints.append({
                    "element": meta["element"],
                    "type": meta["type"],
                    "bound_value": meta["bound_value"],
                    "shadow_price_usd": shadow_price_usd,
                    "shadow_price_inr": shadow_price_inr,
                    "shadow_price_per_kg": shadow_price_usd,  # legacy compatibility
                    "description": meta["description"],
                    "explanation": f"Constraint '{meta['element']} ({meta['type']})' is actively binding. Relaxing this requirement saves {shadow_price_usd:.2f}/kg of metal deficit."
                })

    total_cost_inr = round(sum(r["total_cost_inr"] for r in recommendations), 2)

    return {
        "success": True,
        "all_in_spec": len(violations) == 0,
        "mode": mode,
        "initial_melt_weight_kg": melt_weight_kg,
        "total_added_kg": round(total_added_kg, 2),
        "final_melt_weight_kg": round(final_weight_kg, 2),
        "total_cost": round(total_cost, 2),
        "total_cost_inr": total_cost_inr,
        "recommendations": recommendations,
        "element_audit": element_audit,
        "final_composition": final_composition,
        "ce_initial": ce_initial,
        "ce_final": ce_final,
        "liquidus_temp_c": liquidus_temp_c,
        "binding_constraints": binding_constraints,
        "violations": violations,
        "over_spec_alerts": over_spec_alerts
    }
