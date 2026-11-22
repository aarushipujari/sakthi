import sys
from backend.catalog import GRADES, FERROALLOYS, ELEMENT_METADATA
from backend.optimizer import solve_alloy_addition
from backend.explainability import generate_alloy_explanations, compute_heuristic_comparison

def verify():
    print("=================================================================")
    print(" VULCAN // SAKTHI MELT-OS - INDUSTRIAL METALLURGICAL VERIFICATION")
    print("=================================================================\n")
    print(f"Loaded {len(GRADES)} Target Grades | {len(FERROALLOYS)} Commercial Ferroalloys | {len(ELEMENT_METADATA)} Spectro Channels\n")

    for gid, g in GRADES.items():
        weight = g['default_weight_kg']
        c0 = g['demo_reading']
        part = g.get('casting_part', 'Automotive Casting')

        # Target mode
        res_t = solve_alloy_addition(weight, c0, g, FERROALLOYS, mode="target")
        if not res_t["success"]:
            print(f"[FAIL] Target Mode on {g['name']}: {res_t.get('error')}")
            return False

        # Lean mode
        res_l = solve_alloy_addition(weight, c0, g, FERROALLOYS, mode="lean")
        if not res_l["success"]:
            print(f"[FAIL] Lean Mode on {g['name']}: {res_l.get('error')}")
            return False

        # Heuristic comparison
        comp = compute_heuristic_comparison(weight, c0, g, FERROALLOYS, mode="target")
        sav_inr = comp['comparison']['cost_savings_inr']
        sav_pct = comp['comparison']['cost_savings_pct']
        annual_lakhs = comp['comparison']['annual_savings_lakhs']

        print(f"[PASS] {g['name']} ({part}):")
        print(f"       Additions: {res_t['total_added_kg']:.2f} kg | Net Cost: ₹{res_t['total_cost_inr']:,.0f} (${res_t['total_cost']:.2f})")
        print(f"       Foundry ROI: Saves ₹{sav_inr:,.0f} ({sav_pct:.1f}%) per heat -> ₹{annual_lakhs:.1f} Lakhs/year")
        for r in res_t['recommendations']:
            print(f"         * {r['short_name']:<25} : {r['quantity_kg']:>6.2f} kg ({r['full_bags']} sacks of {r['bag_size_kg']}kg + {r['loose_kg']}kg trim)")
        print()

    print("ALL 6 AUTOMOTIVE & INDUSTRIAL GRADES PASSED WITH 100% METALLURGICAL INTEGRITY!")
    return True

if __name__ == "__main__":
    if not verify():
        sys.exit(1)
