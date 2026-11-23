"""
explainability.py - Decision Traceability & What-If Scenario Analysis
Provides human-readable metallurgical justifications, shadow price interpretation,
and side-by-side comparison between naive manual heuristics vs. optimal LP additions.
"""

from typing import Dict, List, Any, Optional
from backend.optimizer import solve_alloy_addition
from backend.config import DEFAULT_FX_RATE as FX_RATE


def generate_alloy_explanations(
    optimization_result: Dict[str, Any],
    alloys_catalog: List[Dict[str, Any]],
    grade_spec: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Produces clear metallurgical rationale for each recommended alloy in the solution:
    - Primary purpose / deficit addressed
    - Cross-contamination synergy (secondary elements delivered)
    - Effective unit cost comparison
    Numeric fields returned without pre-formatted currency symbols.
    """
    if not optimization_result.get("success"):
        return []

    recommendations = optimization_result.get("recommendations", [])
    binding_constraints = {b["element"]: b for b in optimization_result.get("binding_constraints", [])}
    explanations = []

    for rec in recommendations:
        alloy_id = rec["alloy_id"]
        alloy_def = next((a for a in alloys_catalog if a["id"] == alloy_id), None)
        if not alloy_def:
            continue

        comp = alloy_def["composition"]
        recov = alloy_def["recovery"]
        
        # Determine primary element (highest retained yield contribution)
        primary_elem = None
        max_effective_content = -1.0
        for elem, frac in comp.items():
            if elem in ("Fe", "Ash"):
                continue
            eff = frac * recov.get(elem, 0.80)
            if eff > max_effective_content:
                max_effective_content = eff
                primary_elem = elem

        # Calculate unit cost per kg of recovered primary element
        effective_cost_usd = rec["cost_per_kg"] / max_effective_content if max_effective_content > 0 else 0.0

        # Identify cross-contamination / secondary carriers
        secondary_contributions = []
        for elem, frac in comp.items():
            if elem != primary_elem and elem not in ("Fe", "Ash") and frac > 0.005:
                yielded_kg = rec["quantity_kg"] * frac * recov.get(elem, 0.80)
                secondary_contributions.append({
                    "element": elem,
                    "fraction_pct": round(frac * 100, 2),
                    "delivered_kg": round(yielded_kg, 2)
                })

        # Build natural language narrative without pre-formatted "$" strings
        reasons = []
        shadow_price_usd = 0.0
        if primary_elem in binding_constraints:
            shadow_price_usd = binding_constraints[primary_elem].get("shadow_price_usd", 0.0)
            reasons.append(
                f"Driven by the {primary_elem} requirement (Shadow price: {shadow_price_usd:.2f}/kg)."
            )
        else:
            reasons.append(f"Provides required {primary_elem} at {effective_cost_usd:.2f}/kg effective yield.")

        if secondary_contributions:
            sec_details = ", ".join([f"+{s['delivered_kg']}kg {s['element']}" for s in secondary_contributions])
            reasons.append(f"Delivers beneficial secondary elements ({sec_details}), offsetting separate additions.")

        if alloy_id == "simn":
            reasons.append("Multi-element synergy: Silicomanganese simultaneously corrects Mn and Si at a lower net cost than separate FeMn and FeSi.")
        elif alloy_id == "lc_femn":
            reasons.append("Selected over High-Carbon FeMn to prevent exceeding strict carbon specification ceilings.")
        elif alloy_id == "lc_fecr":
            reasons.append("Selected over High-Carbon FeCr because the melt carbon limit cannot absorb 7% alloy carbon.")
        elif alloy_id == "fesimg_nodulizer":
            reasons.append("Required magnesium treatment alloy for graphite nodule spheroidization in ductile cast iron.")

        explanations.append({
            "alloy_id": alloy_id,
            "alloy_name": rec["short_name"],
            "quantity_kg": rec["quantity_kg"],
            "primary_element": primary_elem,
            "effective_cost_usd": round(effective_cost_usd, 2),
            "effective_cost_inr": round(effective_cost_usd * FX_RATE, 2),
            "shadow_price_usd": round(shadow_price_usd, 2),
            "secondary_contributions": secondary_contributions,
            "rationale": " ".join(reasons)
        })

    return explanations


def compute_heuristic_comparison(
    melt_weight_kg: float,
    current_composition: Dict[str, float],
    grade_spec: Dict[str, Any],
    alloys_catalog: List[Dict[str, Any]],
    disabled_alloy_ids: Optional[List[str]] = None,
    custom_alloy_costs: Optional[Dict[str, float]] = None,
    mode: str = "target",
    heats_per_day: float = 12.0,
    working_days_per_year: float = 300.0
) -> Dict[str, Any]:
    """
    Simulates the traditional single-element rule-of-thumb heuristic calculation
    used on static spreadsheets in foundries (treating each element independently
    using single-carrier alloys), and compares it against the LP joint optimum.
    Evaluates whether the naive method lands in spec or produces scrap.
    """
    # Clone catalog and apply custom costs / overrides
    alloys = [dict(a) for a in alloys_catalog]
    if custom_alloy_costs:
        for a in alloys:
            if a["id"] in custom_alloy_costs:
                a["cost_per_kg"] = float(custom_alloy_costs[a["id"]])

    # 1. Run optimal LP
    optimal_solution = solve_alloy_addition(
        melt_weight_kg=melt_weight_kg,
        current_composition=current_composition,
        grade_spec=grade_spec,
        alloys_catalog=alloys,
        disabled_alloy_ids=disabled_alloy_ids,
        mode=mode
    )

    if not optimal_solution.get("success"):
        return {"error": "Optimal LP solver failed on this input."}

    # 2. Simulate Naive Heuristic (Typical manual shop practice)
    # Map elements to traditional single-carrier alloys
    element_to_alloy_map = {
        "C": "recarburizer_graphite",
        "Si": "fesi_75",
        "Mn": "lc_femn" if grade_spec["elements"].get("C", {}).get("max", 1.0) < 0.20 else "hc_femn",
        "Cr": "lc_fecr" if grade_spec["elements"].get("C", {}).get("max", 1.0) < 0.20 else "hc_fecr",
        "Mo": "femo_60",
        "Ni": "pure_nickel",
        "Mg": "fesimg_nodulizer"
    }

    disabled_set = set(disabled_alloy_ids or [])
    naive_additions = {}
    naive_total_cost = 0.0
    grade_elements = grade_spec.get("elements", {})

    for elem, bounds in grade_elements.items():
        min_v = bounds.get("min", 0.0)
        if min_v <= 0.0:
            continue  # Skip ceiling-only impurity elements like P, S

        c0 = float(current_composition.get(elem, 0.0))
        tgt = float(bounds.get("target" if mode == "target" else "min", min_v))
        deficit_pct = tgt - c0

        if deficit_pct > 0 and elem in element_to_alloy_map:
            alloy_id = element_to_alloy_map[elem]
            if alloy_id in disabled_set:
                continue
            alloy = next((a for a in alloys if a["id"] == alloy_id), None)
            if alloy:
                comp_pct = alloy["composition"].get(elem, 0.0)
                recov_pct = alloy["recovery"].get(elem, 0.80)
                eff_yield = comp_pct * recov_pct

                if eff_yield > 0:
                    # Naive flat formula: (Deficit% * W0) / (Effective Yield)
                    kg_needed = (deficit_pct / 100.0 * melt_weight_kg) / eff_yield
                    naive_additions[alloy_id] = naive_additions.get(alloy_id, 0.0) + kg_needed

    naive_recommendations = []
    total_naive_kg = 0.0
    for alloy_id, qty in naive_additions.items():
        alloy = next((a for a in alloys if a["id"] == alloy_id), None)
        if alloy and qty > 0.05:
            cost = qty * alloy["cost_per_kg"]
            naive_total_cost += cost
            total_naive_kg += qty
            naive_recommendations.append({
                "alloy_id": alloy_id,
                "short_name": alloy["short_name"],
                "quantity_kg": round(qty, 2),
                "cost_per_kg": alloy["cost_per_kg"],
                "total_cost": round(cost, 2),
                "total_cost_inr": round(cost * FX_RATE, 2)
            })

    # 3. COMPUTE NAIVE BASELINE FINAL CHEMISTRY & SPEC COMPLIANCE (Phase 1, Item 6)
    naive_final_weight = melt_weight_kg + total_naive_kg
    naive_final_comp = {}
    naive_violations = []

    for elem, bounds in grade_elements.items():
        c0 = float(current_composition.get(elem, 0.0))
        min_v = float(bounds.get("min", 0.0))
        max_v = float(bounds.get("max", 100.0))

        added_mass = 0.0
        for alloy_id, qty in naive_additions.items():
            alloy = next((a for a in alloys if a["id"] == alloy_id), None)
            if alloy and elem in alloy["composition"]:
                eff_y = alloy["composition"][elem] * alloy["recovery"].get(elem, 0.80)
                added_mass += qty * eff_y

        final_c = ((melt_weight_kg * (c0 / 100.0)) + added_mass) / naive_final_weight * 100.0 if naive_final_weight > 0 else c0
        naive_final_comp[elem] = round(final_c, 3)

        if min_v > 0 and final_c < min_v - 0.0001:
            naive_violations.append(f"{elem} {final_c:.3f}% < {min_v:.3f}% min")
        if final_c > max_v + 0.0001:
            naive_violations.append(f"{elem} {final_c:.3f}% > {max_v:.3f}% max")

    naive_in_spec = len(naive_violations) == 0
    opt_cost = optimal_solution.get("total_cost", 0.0)
    opt_cost_inr = round(opt_cost * FX_RATE, 2)
    opt_kg = optimal_solution.get("total_added_kg", 0.0)

    naive_total_cost = round(naive_total_cost, 2)
    naive_total_cost_inr = round(naive_total_cost * FX_RATE, 2)
    mass_diff_kg = round(total_naive_kg - opt_kg, 2)

    # If naive baseline is OUT OF SPEC, do not claim a cost advantage; flag scrap risk!
    if not naive_in_spec:
        cost_savings = 0.0
        cost_savings_inr = 0.0
        cost_savings_pct = 0.0
        annual_savings_lakhs = 0.0
        violation_str = ", ".join(naive_violations)
        status_message = f"Manual method: OUT OF SPEC ({violation_str})"
        key_takeaway = (
            f"Manual spreadsheet addition fails metallurgical specification: {violation_str}. "
            f"Cross-contamination or uncoordinated additions cause scrap heats. VULCAN's joint LP optimizer "
            f"is strictly required to produce a valid heat."
        )
    else:
        status_message = "Manual method: IN SPEC"
        cost_savings = round(max(0.0, naive_total_cost - opt_cost), 2)
        cost_savings_inr = round(cost_savings * FX_RATE, 2)
        cost_savings_pct = round((cost_savings / naive_total_cost * 100.0), 1) if naive_total_cost > 0 else 0.0
        total_heats_year = heats_per_day * working_days_per_year
        annual_savings_lakhs = round((cost_savings_inr * total_heats_year) / 100000.0, 2)
        key_takeaway = (
            f"Joint LP optimization saves ₹{cost_savings_inr:,.0f} (${cost_savings:.2f} / {cost_savings_pct:.1f}%) "
            f"and {mass_diff_kg:.1f} kg alloy per heat by exploiting multi-carrier synergies (e.g., SiMn) — "
            f"totaling ₹{annual_savings_lakhs:.1f} Lakhs/year at {heats_per_day:.0f} heats/day."
        )

    return {
        "mode": mode,
        "parameters": {
            "heats_per_day": heats_per_day,
            "working_days_per_year": working_days_per_year,
            "fx_rate": FX_RATE
        },
        "optimal": {
            "total_cost": opt_cost,
            "total_cost_inr": opt_cost_inr,
            "total_kg": opt_kg,
            "recommendations": optimal_solution.get("recommendations", [])
        },
        "naive_heuristic": {
            "in_spec": naive_in_spec,
            "status_message": status_message,
            "violations": naive_violations,
            "final_composition": naive_final_comp,
            "total_cost": naive_total_cost,
            "total_cost_inr": naive_total_cost_inr,
            "total_kg": round(total_naive_kg, 2),
            "recommendations": naive_recommendations
        },
        "comparison": {
            "naive_in_spec": naive_in_spec,
            "naive_is_in_spec": naive_in_spec,
            "status_message": status_message,
            "naive_out_of_spec_reason": ", ".join(naive_violations) if naive_violations else "",
            "lp_cost_usd": opt_cost,
            "lp_cost_inr": opt_cost_inr,
            "naive_cost_usd": naive_total_cost,
            "naive_cost_inr": naive_total_cost_inr,
            "cost_savings": cost_savings,
            "cost_savings_inr": cost_savings_inr,
            "cost_savings_pct": cost_savings_pct,
            "alloy_mass_saved_kg": mass_diff_kg,
            "annual_savings_lakhs": annual_savings_lakhs,
            "key_takeaway": key_takeaway
        }
    }
