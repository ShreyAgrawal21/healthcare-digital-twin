import pandas as pd

from app.analyzer import calculate_longitudinal_features


PARAMETERS = [
    "egfr",
    "creatinine",
    "uacr",
    "systolic_bp",
    "diastolic_bp",
    "hba1c",
]


def make_patient(values, dates=None):
    """Build the canonical analyzer input for one synthetic patient."""
    if dates is None:
        dates = [
            "2026-01-10",
            "2026-04-10",
            "2026-07-10",
            "2026-10-10",
        ][: len(values)]

    rows = []

    for index, row_values in enumerate(values):
        row = {
            "patient_id": "TEST",
            "date": dates[index],
            "visit": f"V{index + 1}",
        }

        for parameter, value in zip(PARAMETERS, row_values):
            row[parameter] = value

        rows.append(row)

    df = pd.DataFrame(rows)
    # The production longitudinal engine performs date arithmetic,
    # so tests must provide actual datetime values rather than strings.
    df["date"] = pd.to_datetime(df["date"])
    return df


def feature_status(feature):
    """Return the status when the feature uses structured availability."""
    if isinstance(feature, dict):
        return feature.get("status")
    return None


def assert_not_calculable(feature):
    assert isinstance(feature, dict)
    assert feature["value"] is None
    assert feature["status"] == "not_calculable"
    assert feature["reason"]


def test_one_visit_requires_two_observations_for_longitudinal_features():
    df = make_patient([
        [72, 1.1, 30, 132, 82, 6.2],
    ])

    result = calculate_longitudinal_features(df)
    egfr = result["egfr"]

    assert egfr["baseline"] == 72
    assert egfr["latest"] == 72
    assert egfr["absolute_change"] == 0
    assert egfr["percentage_change"] == 0

    assert_not_calculable(egfr["slope_per_day"])
    assert_not_calculable(egfr["slope_per_year"])
    assert_not_calculable(egfr["variability_std"])
    assert_not_calculable(egfr["average_rate_per_day"])
    assert_not_calculable(egfr["acceleration"])
    assert_not_calculable(egfr["trend"])

    patient_level = result["_patient_level"]
    assert patient_level["incomplete_follow_up"] is True
    assert "acceleration" in patient_level["insufficient_history_features"]


def test_two_visits_calculate_slope_rate_variability_but_not_acceleration():
    df = make_patient([
        [72, 1.1, 30, 132, 82, 6.2],
        [66, 1.2, 55, 138, 85, 6.5],
    ])

    result = calculate_longitudinal_features(df)
    egfr = result["egfr"]

    # 90 days between the two observations: (66 - 72) / 90.
    assert abs(egfr["slope_per_day"] - (-6 / 90)) < 1e-8
    assert abs(egfr["slope_per_year"] - ((-6 / 90) * 365.25)) < 1e-4

    assert egfr["variability_std"] is not None
    assert egfr["average_rate_per_day"] == egfr["slope_per_day"]

    assert_not_calculable(egfr["acceleration"])

    assert egfr["trend"] == "decreasing"

    patient_level = result["_patient_level"]
    assert patient_level["incomplete_follow_up"] is True
    assert "acceleration" in patient_level["insufficient_history_features"]


def test_three_visits_calculate_longitudinal_features_but_acceleration_remains_unavailable():
    df = make_patient([
        [72, 1.1, 30, 132, 82, 6.2],
        [66, 1.2, 55, 138, 85, 6.5],
        [60, 1.3, 80, 144, 88, 6.8],
    ])

    result = calculate_longitudinal_features(df)
    egfr = result["egfr"]

    assert egfr["baseline"] == 72
    assert egfr["latest"] == 60
    assert egfr["absolute_change"] == -12
    assert egfr["slope_per_day"] is not None
    assert egfr["slope_per_year"] is not None
    assert egfr["variability_std"] is not None
    assert egfr["average_rate_per_day"] is not None
    assert egfr["trend"] == "decreasing"

    # Three observations produce only two visit-to-visit rates.
    assert_not_calculable(egfr["acceleration"])

    patient_level = result["_patient_level"]
    assert patient_level["incomplete_follow_up"] is True
    assert "acceleration" in patient_level["insufficient_history_features"]


def test_four_visits_make_acceleration_calculable():
    df = make_patient([
        [72, 1.1, 30, 132, 82, 6.2],
        [66, 1.2, 55, 138, 85, 6.5],
        [60, 1.3, 80, 144, 88, 6.8],
        [50, 1.6, 160, 151, 91, 7.1],
    ])

    result = calculate_longitudinal_features(df)
    egfr = result["egfr"]

    assert egfr["slope_per_day"] is not None
    assert egfr["slope_per_year"] is not None
    assert egfr["variability_std"] is not None
    assert egfr["average_rate_per_day"] is not None
    assert egfr["acceleration"] is not None
    assert egfr["trend"] == "decreasing"

    patient_level = result["_patient_level"]
    assert patient_level["incomplete_follow_up"] is False
    assert patient_level["insufficient_history_features"] == []
