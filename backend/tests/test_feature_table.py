import pandas as pd

from app.feature_table import (
    build_patient_feature_row,
    build_patient_feature_table,
)


def make_patient_analysis(
    patient_id="P001",
    number_of_visits=4,
    co_worsening_detected=True,
):
    """
    Small representative analyzer output fixture.

    This mimics the structure returned by analyze_patient()
    without recalculating any longitudinal features.
    """

    return {
        "patient_id": patient_id,

        "number_of_visits": number_of_visits,

        "worsening_signal_count": 3,

        "worsening_signals": [
            {
                "parameter": "egfr",
                "name": "eGFR",
            },
            {
                "parameter": "uacr",
                "name": "UACR",
            },
            {
                "parameter": "systolic_bp",
                "name": "Systolic BP",
            },
        ],

        "co_worsening_analysis": {
            "transitions": [
                {
                    "from_visit": 1,
                    "to_visit": 2,
                    "worsening_parameters": [
                        {
                            "parameter": "egfr",
                            "change": -7,
                        },
                        {
                            "parameter": "uacr",
                            "change": 25,
                        },
                    ],
                    "worsening_parameter_count": 2,
                }
            ],

            "co_worsening_transitions": [
                {
                    "from_visit": 1,
                    "to_visit": 2,
                    "worsening_parameter_count": 2,
                }
            ],

            "co_worsening_detected":
                co_worsening_detected,
        },

        "longitudinal_features": {
            "egfr": {
                "baseline": 72,
                "latest": 50,
                "absolute_change": -22,
                "percentage_change": -30.5556,
                "slope_per_day": -0.078,
                "slope_per_year": -28.47,
                "variability_std": 9.32,
                "average_rate_per_day": -0.078,
                "acceleration": -0.0001,
                "trend": "decreasing",
            },

            "creatinine": {
                "baseline": 1.1,
                "latest": 1.6,
                "absolute_change": 0.5,
                "percentage_change": 45.4545,
                "slope_per_day": 0.0018,
                "slope_per_year": 0.657,
                "variability_std": 0.216,
                "average_rate_per_day": 0.0018,
                "acceleration": 0.00001,
                "trend": "increasing",
            },

            "uacr": {
                "baseline": 30,
                "latest": 160,
                "absolute_change": 130,
                "percentage_change": 433.3333,
                "slope_per_day": 0.462,
                "slope_per_year": 168.63,
                "variability_std": 56.86,
                "average_rate_per_day": 0.462,
                "acceleration": 0.0001,
                "trend": "increasing",
            },

            "systolic_bp": {
                "baseline": 132,
                "latest": 151,
                "absolute_change": 19,
                "percentage_change": 14.3939,
                "slope_per_day": 0.0675,
                "slope_per_year": 24.64,
                "variability_std": 8.06,
                "average_rate_per_day": 0.0675,
                "acceleration": 0.00001,
                "trend": "increasing",
            },

            "diastolic_bp": {
                "baseline": 82,
                "latest": 91,
                "absolute_change": 9,
                "percentage_change": 10.9756,
                "slope_per_day": 0.032,
                "slope_per_year": 11.68,
                "variability_std": 3.87,
                "average_rate_per_day": 0.032,
                "acceleration": 0.00001,
                "trend": "increasing",
            },

            "hba1c": {
                "baseline": 6.2,
                "latest": 7.1,
                "absolute_change": 0.9,
                "percentage_change": 14.5161,
                "slope_per_day": 0.0032,
                "slope_per_year": 1.17,
                "variability_std": 0.387,
                "average_rate_per_day": 0.0032,
                "acceleration": 0.00001,
                "trend": "increasing",
            },
        },
    }


def test_build_patient_feature_row_contains_core_fields():

    analysis = make_patient_analysis()

    row = build_patient_feature_row(
        patient_id="P001",
        patient_analysis=analysis,
        quality_flags=[],
    )

    assert row["patient_id"] == "P001"

    assert row["number_of_visits"] == 4

    assert row["worsening_signal_count"] == 3

    assert row["worsening_parameters"] == (
        "egfr; uacr; systolic_bp"
    )


def test_longitudinal_features_are_flattened():

    analysis = make_patient_analysis()

    row = build_patient_feature_row(
        patient_id="P001",
        patient_analysis=analysis,
    )

    assert row["egfr_baseline"] == 72

    assert row["egfr_latest"] == 50

    assert row["egfr_absolute_change"] == -22

    assert row["egfr_percentage_change"] == -30.5556

    assert row["egfr_slope_per_day"] == -0.078

    assert row["egfr_slope_per_year"] == -28.47

    assert row["egfr_variability_std"] == 9.32

    assert row["egfr_average_rate_per_day"] == -0.078

    assert row["egfr_acceleration"] == -0.0001

    assert row["egfr_trend"] == "decreasing"


def test_co_worsening_fields_are_flattened():

    analysis = make_patient_analysis(
        co_worsening_detected=True
    )

    row = build_patient_feature_row(
        patient_id="P001",
        patient_analysis=analysis,
    )

    assert row["co_worsening_detected"] is True

    assert row["co_worsening_transition_count"] == 1


def test_quality_flags_are_preserved():

    analysis = make_patient_analysis()

    row = build_patient_feature_row(
        patient_id="P001",
        patient_analysis=analysis,
        quality_flags=[
            "incomplete_follow_up",
            "missing_numeric_values",
        ],
    )

    assert row["quality_flag_count"] == 2

    assert row["quality_flags"] == (
        "incomplete_follow_up; missing_numeric_values"
    )


def test_unavailable_features_remain_none():

    analysis = make_patient_analysis()

    analysis["longitudinal_features"]["egfr"][
        "acceleration"
    ] = {
        "value": None,
        "status": "not_calculable",
        "reason": "insufficient_visits",
    }

    row = build_patient_feature_row(
        patient_id="P001",
        patient_analysis=analysis,
    )

    assert row["egfr_acceleration"] is None


def test_build_patient_feature_table_creates_one_row_per_patient():

    patient_results = {
        "P001": make_patient_analysis(
            patient_id="P001"
        ),
        "P002": make_patient_analysis(
            patient_id="P002",
            number_of_visits=2,
            co_worsening_detected=False,
        ),
    }

    quality_report = {
        "patient_flags": {
            "P001": {
                "flags": []
            },
            "P002": {
                "flags": [
                    "incomplete_follow_up"
                ]
            },
        }
    }

    table = build_patient_feature_table(
        patient_results=patient_results,
        quality_report=quality_report,
    )

    assert isinstance(
        table,
        pd.DataFrame
    )

    assert len(table) == 2

    assert set(
        table["patient_id"]
    ) == {
        "P001",
        "P002",
    }

    p002 = table[
        table["patient_id"] == "P002"
    ].iloc[0]

    assert p002[
        "number_of_visits"
    ] == 2

    assert p002[
        "quality_flags"
    ] == "incomplete_follow_up"