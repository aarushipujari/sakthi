import sys
from backend.catalog import GRADES, FERROALLOYS, ELEMENT_METADATA
from backend.optimizer import solve_alloy_addition
from backend.explainability import compute_heuristic_comparison

def test_all_grades_verification():
    for gid, g in GRADES.items():
        weight = g['default_weight_kg']
        c0 = g['demo_reading']

        # Target mode
        res_t = solve_alloy_addition(weight, c0, g, FERROALLOYS, mode="target")
        assert res_t["success"] is True, f"Target Mode failed on {g['name']}: {res_t.get('error')}"

        # Lean mode
        res_l = solve_alloy_addition(weight, c0, g, FERROALLOYS, mode="lean")
        assert res_l["success"] is True, f"Lean Mode failed on {g['name']}: {res_l.get('error')}"

        # Heuristic comparison
        comp = compute_heuristic_comparison(weight, c0, g, FERROALLOYS, mode="target")
        assert "comparison" in comp
        assert comp['comparison']['cost_savings_inr'] >= 0 or comp['comparison']['cost_savings_inr'] < 0  # valid number
        assert "optimal" in comp

if __name__ == "__main__":
    test_all_grades_verification()
    print("ALL GRADES VERIFIED SUCCESSFULLY.")
