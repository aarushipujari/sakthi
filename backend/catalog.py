"""
catalog.py - Metallurgical Grade Library and Ferroalloy Inventory
Engineered for industrial foundry operations (Sakthi Melt Shop & Automotive Castings).
"""

# Periodic Table & Channel Metadata for Spectrometer Channels
ELEMENT_METADATA = {
    "C":  {"name": "Carbon", "atomic": 6, "atomic_mass": 12.011, "role": "Matrix hardness & graphite formation", "color": "amber"},
    "Si": {"name": "Silicon", "atomic": 14, "atomic_mass": 28.085, "role": "Graphitizer & deoxidizer", "color": "cyan"},
    "Mn": {"name": "Manganese", "atomic": 25, "atomic_mass": 54.938, "role": "Pearlite stabilizer & sulfur scavenger", "color": "purple"},
    "Cr": {"name": "Chromium", "atomic": 24, "atomic_mass": 51.996, "role": "Carbide stabilizer & corrosion resistance", "color": "rose"},
    "Mo": {"name": "Molybdenum", "atomic": 42, "atomic_mass": 95.95, "role": "Hardenability & creep strength", "color": "indigo"},
    "Ni": {"name": "Nickel", "atomic": 28, "atomic_mass": 58.693, "role": "Austenite stabilizer & impact toughness", "color": "emerald"},
    "Mg": {"name": "Magnesium", "atomic": 12, "atomic_mass": 24.305, "role": "Graphite nodulizing spheroidizer", "color": "yellow"},
    "P":  {"name": "Phosphorus", "atomic": 15, "atomic_mass": 30.974, "role": "Impurity / embrittlement ceiling", "color": "red"},
    "S":  {"name": "Sulfur", "atomic": 16, "atomic_mass": 32.065, "role": "Impurity / nodule degenerate ceiling", "color": "orange"}
}

# Standard Metallurgical Grades (Specialized for Automotive & Industrial Melt Shops)
GRADES = {
    "ductile_iron_500_7": {
        "id": "ductile_iron_500_7",
        "name": "SG Iron 500/7 (ASTM 65-45-12)",
        "casting_part": "Crankshafts & Steering Knuckles",
        "category": "Ductile Iron",
        "default_weight_kg": 4000.0,
        "ce_formula": "C + (Si + P) / 3.0",
        "elements": {
            "C":  {"min": 3.50, "target": 3.65, "max": 3.80, "step": 0.01},
            "Si": {"min": 2.30, "target": 2.50, "max": 2.70, "step": 0.01},
            "Mn": {"min": 0.30, "target": 0.40, "max": 0.50, "step": 0.01},
            "Mg": {"min": 0.035, "target": 0.042, "max": 0.050, "step": 0.002},
            "P":  {"min": 0.00, "target": 0.030, "max": 0.050, "step": 0.005},
            "S":  {"min": 0.00, "target": 0.010, "max": 0.020, "step": 0.002}
        },
        "demo_reading": {
            "C": 3.42,
            "Si": 2.05,
            "Mn": 0.22,
            "Mg": 0.038,
            "P": 0.028,
            "S": 0.010
        },
        "description": "High-strength spheroidal graphite cast iron for heavy-duty safety components (crankshafts, steering knuckles)."
    },
    "ductile_iron_400_18": {
        "id": "ductile_iron_400_18",
        "name": "SG Iron 400/18 (High Impact Ferritic)",
        "casting_part": "Suspension Arms & Caliper Brackets",
        "category": "Ductile Iron",
        "default_weight_kg": 4500.0,
        "ce_formula": "C + (Si + P) / 3.0",
        "elements": {
            "C":  {"min": 3.60, "target": 3.75, "max": 3.90, "step": 0.01},
            "Si": {"min": 2.20, "target": 2.45, "max": 2.65, "step": 0.01},
            "Mn": {"min": 0.10, "target": 0.20, "max": 0.30, "step": 0.01},
            "Mg": {"min": 0.035, "target": 0.042, "max": 0.050, "step": 0.002},
            "P":  {"min": 0.00, "target": 0.025, "max": 0.040, "step": 0.002},
            "S":  {"min": 0.00, "target": 0.008, "max": 0.015, "step": 0.002}
        },
        "demo_reading": {
            "C": 3.52,
            "Si": 2.10,
            "Mn": 0.12,
            "Mg": 0.036,
            "P": 0.022,
            "S": 0.009
        },
        "description": "Fully ferritic ductile iron with 18% elongation and high sub-zero Charpy impact toughness for automotive suspension."
    },
    "grey_iron_fg260": {
        "id": "grey_iron_fg260",
        "name": "Grey Cast Iron FG 260 (ASTM Class 35)",
        "casting_part": "Ventilated Brake Rotors & Drums",
        "category": "Grey Iron",
        "default_weight_kg": 5000.0,
        "ce_formula": "C + (Si + P) / 3.0",
        "elements": {
            "C":  {"min": 3.10, "target": 3.25, "max": 3.40, "step": 0.01},
            "Si": {"min": 1.70, "target": 1.90, "max": 2.10, "step": 0.01},
            "Mn": {"min": 0.55, "target": 0.65, "max": 0.75, "step": 0.01},
            "Cr": {"min": 0.15, "target": 0.22, "max": 0.30, "step": 0.01},
            "P":  {"min": 0.00, "target": 0.05, "max": 0.08, "step": 0.005},
            "S":  {"min": 0.00, "target": 0.08, "max": 0.12, "step": 0.005}
        },
        "demo_reading": {
            "C": 3.12,
            "Si": 1.62,
            "Mn": 0.48,
            "Cr": 0.12,
            "P": 0.045,
            "S": 0.075
        },
        "description": "High thermal conductivity flake graphite iron engineered for thermal crack resistance in disc brake rotors."
    },
    "steel_aisi_4140": {
        "id": "steel_aisi_4140",
        "name": "Low-Alloy Steel 4140 (42CrMo4)",
        "casting_part": "Transmission Pinions & Turbine Shafts",
        "category": "Alloy Steel",
        "default_weight_kg": 5000.0,
        "ce_formula": None,
        "elements": {
            "C":  {"min": 0.38, "target": 0.41, "max": 0.43, "step": 0.005},
            "Si": {"min": 0.15, "target": 0.25, "max": 0.35, "step": 0.01},
            "Mn": {"min": 0.75, "target": 0.88, "max": 1.00, "step": 0.01},
            "Cr": {"min": 0.80, "target": 0.98, "max": 1.10, "step": 0.01},
            "Mo": {"min": 0.15, "target": 0.20, "max": 0.25, "step": 0.005},
            "P":  {"min": 0.00, "target": 0.02, "max": 0.035, "step": 0.002},
            "S":  {"min": 0.00, "target": 0.02, "max": 0.040, "step": 0.002}
        },
        "demo_reading": {
            "C": 0.33,
            "Si": 0.16,
            "Mn": 0.62,
            "Cr": 0.72,
            "Mo": 0.09,
            "P": 0.018,
            "S": 0.015
        },
        "description": "High-tensile Cr-Mo quench and temper steel for heavy-duty drive shafts, turbine studs, and steering gears."
    },
    "stainless_304": {
        "id": "stainless_304",
        "name": "Austenitic Stainless CF8 (AISI 304)",
        "casting_part": "Chemical Pump Impellers & Valves",
        "category": "Stainless Steel",
        "default_weight_kg": 6000.0,
        "ce_formula": None,
        "elements": {
            "C":  {"min": 0.00, "target": 0.04, "max": 0.08, "step": 0.005},
            "Si": {"min": 0.30, "target": 0.60, "max": 1.00, "step": 0.01},
            "Mn": {"min": 0.80, "target": 1.40, "max": 2.00, "step": 0.01},
            "Cr": {"min": 18.00, "target": 18.80, "max": 20.00, "step": 0.05},
            "Ni": {"min": 8.00, "target": 8.80, "max": 10.50, "step": 0.05},
            "P":  {"min": 0.00, "target": 0.03, "max": 0.045, "step": 0.002},
            "S":  {"min": 0.00, "target": 0.015, "max": 0.030, "step": 0.002}
        },
        "demo_reading": {
            "C": 0.038,
            "Si": 0.35,
            "Mn": 0.95,
            "Cr": 17.20,
            "Ni": 7.90,
            "P": 0.025,
            "S": 0.012
        },
        "description": "Corrosion-resistant 18Cr-8Ni stainless casting for sanitary pumps, petrochemical valves, and marine impellers."
    },
    "hadfield_manganese": {
        "id": "hadfield_manganese",
        "name": "Hadfield Wear Steel (ASTM A128 Gr B)",
        "casting_part": "Rock Crusher Jaws & Railway Frogs",
        "category": "Wear Steel",
        "default_weight_kg": 4000.0,
        "ce_formula": None,
        "elements": {
            "C":  {"min": 1.05, "target": 1.20, "max": 1.35, "step": 0.01},
            "Si": {"min": 0.30, "target": 0.50, "max": 0.80, "step": 0.01},
            "Mn": {"min": 11.50, "target": 12.80, "max": 14.00, "step": 0.10},
            "Cr": {"min": 0.00, "target": 0.80, "max": 1.50, "step": 0.05},
            "P":  {"min": 0.00, "target": 0.04, "max": 0.07, "step": 0.005},
            "S":  {"min": 0.00, "target": 0.02, "max": 0.04, "step": 0.002}
        },
        "demo_reading": {
            "C": 1.02,
            "Si": 0.32,
            "Mn": 9.80,
            "Cr": 0.40,
            "P": 0.042,
            "S": 0.018
        },
        "description": "Austenitic work-hardening steel with extreme impact abrasion resistance for primary stone crushers."
    }
}

# Standard Commercial Ferroalloys Catalog with USD & INR Market Rates
FERROALLOYS = [
    {
        "id": "recarburizer_graphite",
        "name": "Synthetic Graphite Recarburizer",
        "short_name": "Carburizer (C 98%)",
        "cost_per_kg": 0.85,
        "cost_inr_per_kg": 72.0,
        "bag_size_kg": 25.0,
        "charge_order": 1,
        "composition": {"C": 0.985, "S": 0.005},
        "recovery": {"C": 0.85, "S": 0.70},
        "description": "High-purity carbon raiser with low nitrogen for rapid bath dissolution onto cleared slag."
    },
    {
        "id": "fesi_75",
        "name": "Ferrosilicon 75% (FeSi 75)",
        "short_name": "FeSi 75 (Si 75%)",
        "cost_per_kg": 1.90,
        "cost_inr_per_kg": 160.0,
        "bag_size_kg": 25.0,
        "charge_order": 2,
        "composition": {"Si": 0.75, "Al": 0.012, "C": 0.001, "Fe": 0.237},
        "recovery": {"Si": 0.85, "Al": 0.70, "C": 0.85, "Fe": 1.00},
        "description": "Primary graphitizer and deoxidizer for cast iron and steel killing."
    },
    {
        "id": "hc_femn",
        "name": "High-Carbon Ferromanganese (HC FeMn)",
        "short_name": "HC FeMn (Mn 75%)",
        "cost_per_kg": 1.60,
        "cost_inr_per_kg": 135.0,
        "bag_size_kg": 50.0,
        "charge_order": 3,
        "composition": {"Mn": 0.75, "C": 0.068, "Si": 0.010, "Fe": 0.172},
        "recovery": {"Mn": 0.80, "C": 0.85, "Si": 0.80, "Fe": 1.00},
        "description": "Standard manganese addition for iron and steels where melt carbon has absorption headroom."
    },
    {
        "id": "lc_femn",
        "name": "Low-Carbon Ferromanganese (LC FeMn)",
        "short_name": "LC FeMn (Mn 80%)",
        "cost_per_kg": 2.40,
        "cost_inr_per_kg": 205.0,
        "bag_size_kg": 50.0,
        "charge_order": 3,
        "composition": {"Mn": 0.80, "C": 0.0075, "Si": 0.015, "Fe": 0.177},
        "recovery": {"Mn": 0.82, "C": 0.85, "Si": 0.80, "Fe": 1.00},
        "description": "Refined low-carbon manganese alloy for tight carbon ceilings (low-alloy & stainless)."
    },
    {
        "id": "simn",
        "name": "Silicomanganese (SiMn 65/17)",
        "short_name": "SiMn (Mn 65% / Si 17%)",
        "cost_per_kg": 1.45,
        "cost_inr_per_kg": 122.0,
        "bag_size_kg": 50.0,
        "charge_order": 2,
        "composition": {"Mn": 0.65, "Si": 0.17, "C": 0.018, "Fe": 0.162},
        "recovery": {"Mn": 0.82, "Si": 0.85, "C": 0.85, "Fe": 1.00},
        "description": "Simultaneous Mn + Si deoxidation carrier at lower combined cost than separate FeMn and FeSi."
    },
    {
        "id": "hc_fecr",
        "name": "High-Carbon Ferrochrome (HC FeCr 65%)",
        "short_name": "HC FeCr (Cr 65%)",
        "cost_per_kg": 2.10,
        "cost_inr_per_kg": 178.0,
        "bag_size_kg": 50.0,
        "charge_order": 3,
        "composition": {"Cr": 0.65, "C": 0.070, "Si": 0.015, "Fe": 0.265},
        "recovery": {"Cr": 0.88, "C": 0.85, "Si": 0.80, "Fe": 1.00},
        "description": "Economical chromium addition for pearlitic cast irons and steels with adequate carbon headroom."
    },
    {
        "id": "lc_fecr",
        "name": "Low-Carbon Ferrochrome (LC FeCr 68%)",
        "short_name": "LC FeCr (Cr 68%)",
        "cost_per_kg": 2.95,
        "cost_inr_per_kg": 250.0,
        "bag_size_kg": 50.0,
        "charge_order": 3,
        "composition": {"Cr": 0.68, "C": 0.001, "Si": 0.010, "Fe": 0.309},
        "recovery": {"Cr": 0.90, "C": 0.85, "Si": 0.80, "Fe": 1.00},
        "description": "Premium ultra-low carbon chromium carrier for CF8/304 stainless and critical alloys."
    },
    {
        "id": "femo_60",
        "name": "Ferromolybdenum (FeMo 60%)",
        "short_name": "FeMo (Mo 60%)",
        "cost_per_kg": 34.00,
        "cost_inr_per_kg": 2880.0,
        "bag_size_kg": 10.0,
        "charge_order": 3,
        "composition": {"Mo": 0.60, "C": 0.001, "Si": 0.010, "Fe": 0.389},
        "recovery": {"Mo": 0.94, "Si": 0.80, "Fe": 1.00},
        "description": "High-density molybdenum carrier for high-temperature creep strength and hardenability."
    },
    {
        "id": "pure_nickel",
        "name": "Pure Nickel Briquettes (Ni 99.5%)",
        "short_name": "Nickel (Ni 99.5%)",
        "cost_per_kg": 18.50,
        "cost_inr_per_kg": 1560.0,
        "bag_size_kg": 25.0,
        "charge_order": 3,
        "composition": {"Ni": 0.995, "C": 0.0005, "Fe": 0.004},
        "recovery": {"Ni": 0.96, "Fe": 1.00},
        "description": "Primary nickel for austenite stabilization and cryogenic impact toughness."
    },
    {
        "id": "fesimg_nodulizer",
        "name": "Ferrosilicon Magnesium Nodulizer (FeSiMg 6%)",
        "short_name": "FeSiMg Nodulizer (Mg 6%)",
        "cost_per_kg": 3.10,
        "cost_inr_per_kg": 260.0,
        "bag_size_kg": 25.0,
        "charge_order": 4,
        "composition": {"Mg": 0.060, "Si": 0.450, "Ca": 0.015, "Fe": 0.475},
        "recovery": {"Mg": 0.45, "Si": 0.85, "Fe": 1.00},
        "description": "Magnesium treatment alloy for graphite spheroidization in ductile cast iron."
    }
]
