import pandas as pd

from app.analyzer import calculate_longitudinal_features


def make_patient(rows):
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def assert_not_calculable(feature):
    """
    Structured unavailable feature.
    """
    assert isinstance(feature, dict)
    assert feature["value"] is None
    assert feature["status"] == "not_calculable"
    assert feature["reason"]


def test_duplicate_dates_are_handled_without_crashing():
    df = make_patient([
        {
            "patient_id": "DUP",
            "date": "2026-01-10",
            "visit": "V1",
            "egfr": 72,
            "creatinine": 1.1,
            "uacr": 30,
            "systolic_bp": 132,
            "diastolic_bp": 82,
            "hba1c": 6.2,
        },
        {
            "patient_id": "DUP",
            "date": "2026-01-10",
            "visit": "V2",
            "egfr": 68,
            "creatinine": 1.2,
            "uacr": 45,
            "systolic_bp": 136,
            "diastolic_bp": 84,
            "hba1c": 6.4,
        },
        {
            "patient_id": "DUP",
            "date": "2026-04-10",
            "visit": "V3",
            "egfr": 64,
            "creatinine": 1.3,
            "uacr": 60,
            "systolic_bp": 140,
            "diastolic_bp": 86,
            "hba1c": 6.6,
        },
    ])

    result = calculate_longitudinal_features(df)
    egfr = result["egfr"]

    # Duplicate dates must not crash longitudinal calculations.
    assert egfr["slope_per_day"] is not None
    assert egfr["average_rate_per_day"] is not None
    assert pd.notna(egfr["slope_per_day"])
    assert pd.notna(egfr["average_rate_per_day"])


def test_irregular_intervals_use_actual_elapsed_days():
    df = make_patient([
        {
            "patient_id": "IRR",
            "date": "2026-01-10",
            "visit": "V1",
            "egfr": 80,
            "creatinine": 1.0,
            "uacr": 20,
            "systolic_bp": 128,
            "diastolic_bp": 80,
            "hba1c": 6.0,
        },
        {
            "patient_id": "IRR",
            "date": "2026-02-09",
            "visit": "V2",
            "egfr": 70,
            "creatinine": 1.1,
            "uacr": 40,
            "systolic_bp": 135,
            "diastolic_bp": 83,
            "hba1c": 6.3,
        },
        {
            "patient_id": "IRR",
            "date": "2026-06-09",
            "visit": "V3",
            "egfr": 60,
            "creatinine": 1.3,
            "uacr": 70,
            "systolic_bp": 142,
            "diastolic_bp": 86,
            "hba1c": 6.6,
        },
    ])

    result = calculate_longitudinal_features(df)
    egfr = result["egfr"]

    # Actual elapsed intervals:
    # Jan 10 -> Feb 9 = 30 days
    # Feb 9 -> Jun 9 = 120 days
    expected_average_rate = ((-10 / 30) + (-10 / 120)) / 2

    # Analyzer rounds rate values, so use a practical tolerance.
    assert abs(
        egfr["average_rate_per_day"] - expected_average_rate
    ) < 1e-7

    assert egfr["slope_per_day"] < 0
    assert egfr["trend"] == "decreasing"


def test_zero_baseline_percentage_change_is_not_calculable():
    df = make_patient([
        {
            "patient_id": "ZERO",
            "date": "2026-01-10",
            "visit": "V1",
            "egfr": 0,
            "creatinine": 1.0,
            "uacr": 20,
            "systolic_bp": 128,
            "diastolic_bp": 80,
            "hba1c": 6.0,
        },
        {
            "patient_id": "ZERO",
            "date": "2026-04-10",
            "visit": "V2",
            "egfr": 10,
            "creatinine": 1.1,
            "uacr": 30,
            "systolic_bp": 130,
            "diastolic_bp": 82,
            "hba1c": 6.2,
        },
    ])

    result = calculate_longitudinal_features(df)
    egfr = result["egfr"]

    assert egfr["absolute_change"] == 10
    assert_not_calculable(egfr["percentage_change"])


def test_missing_parameter_values_use_available_observations():
    df = make_patient([
        {
            "patient_id": "MISS",
            "date": "2026-01-10",
            "visit": "V1",
            "egfr": 70,
            "creatinine": 1.1,
            "uacr": 40,
            "systolic_bp": 130,
            "diastolic_bp": 82,
            "hba1c": 6.3,
        },
        {
            "patient_id": "MISS",
            "date": "2026-04-10",
            "visit": "V2",
            "egfr": None,
            "creatinine": 1.2,
            "uacr": None,
            "systolic_bp": 136,
            "diastolic_bp": 84,
            "hba1c": 6.5,
        },
        {
            "patient_id": "MISS",
            "date": "2026-07-10",
            "visit": "V3",
            "egfr": 60,
            "creatinine": None,
            "uacr": 80,
            "systolic_bp": 142,
            "diastolic_bp": 86,
            "hba1c": 6.7,
        },
    ])

    result = calculate_longitudinal_features(df)

    # eGFR has two valid observations.
    assert result["egfr"]["slope_per_day"] is not None
    assert result["egfr"]["baseline"] == 70
    assert result["egfr"]["latest"] == 60

    # Creatinine actually has TWO valid observations:
    # 1.1 on V1 and 1.2 on V2.
    # Therefore its slope and variability ARE calculable.
    assert result["creatinine"]["slope_per_day"] is not None
    assert result["creatinine"]["variability_std"] is not None

    # UACR also has two valid observations.
    assert result["uacr"]["slope_per_day"] is not None
    assert result["uacr"]["baseline"] == 40
    assert result["uacr"]["latest"] == 80

def test_missing_all_observations_for_parameter_is_not_calculable():
    df = make_patient([
        {
            "patient_id": "ALLMISS",
            "date": "2026-01-10",
            "visit": "V1",
            "egfr": None,
            "creatinine": 1.1,
            "uacr": None,
            "systolic_bp": 130,
            "diastolic_bp": 82,
            "hba1c": 6.3,
        },
        {
            "patient_id": "ALLMISS",
            "date": "2026-04-10",
            "visit": "V2",
            "egfr": None,
            "creatinine": 1.2,
            "uacr": None,
            "systolic_bp": 136,
            "diastolic_bp": 84,
            "hba1c": 6.5,
        },
    ])

    result = calculate_longitudinal_features(df)

    # No valid eGFR observations exist.
    # The analyzer represents unavailable features as None.
    assert result["egfr"]["baseline"] is None
    assert result["egfr"]["latest"] is None
    assert result["egfr"]["absolute_change"] is None
    assert result["egfr"]["percentage_change"] is None
    assert result["egfr"]["slope_per_day"] is None
    assert result["egfr"]["slope_per_year"] is None
    assert result["egfr"]["variability_std"] is None
    assert result["egfr"]["average_rate_per_day"] is None
    assert result["egfr"]["acceleration"] is None
    assert result["egfr"]["trend"] == "insufficient_data"

    # No valid UACR observations exist.
    assert result["uacr"]["baseline"] is None
    assert result["uacr"]["latest"] is None
    assert result["uacr"]["absolute_change"] is None
    assert result["uacr"]["percentage_change"] is None
    assert result["uacr"]["slope_per_day"] is None
    assert result["uacr"]["slope_per_year"] is None
    assert result["uacr"]["variability_std"] is None
    assert result["uacr"]["average_rate_per_day"] is None
    assert result["uacr"]["acceleration"] is None
    assert result["uacr"]["trend"] == "insufficient_data"