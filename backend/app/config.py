PARAMETERS = {
    "egfr": {
        "name": "eGFR",
        "worsening_direction": "decreasing"
    },
    "creatinine": {
        "name": "Serum Creatinine",
        "worsening_direction": "increasing"
    },
    "uacr": {
        "name": "UACR",
        "worsening_direction": "increasing"
    },
    "systolic_bp": {
        "name": "Systolic Blood Pressure",
        "worsening_direction": "increasing"
    },
    "diastolic_bp": {
        "name": "Diastolic Blood Pressure",
        "worsening_direction": "increasing"
    },
    "hba1c": {
        "name": "HbA1c",
        "worsening_direction": "increasing"
    }
}


# --------------------------------------------------
# Pattern Detection Configuration
# --------------------------------------------------

# Minimum proportion of observed transitions that
# must move in the worsening direction for a
# parameter to be considered consistently worsening.
#
# This is an ENGINE setting, NOT a clinical threshold.
MIN_WORSENING_CONSISTENCY = 0.67

# Minimum number of parameters required to form
# a multi-parameter worsening pattern.
MIN_WORSENING_PARAMETERS = 2