import pandas as pd

from app.analyzer import (
    calculate_longitudinal_features,
    detect_worsening_signals,
)


def make_patient(rows):
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def base_row(
    date,
    visit,
    egfr,
    creatinine=1.0,
    uacr=30,
    systolic_bp=130,
    diastolic_bp=80,
    hba1c=6.0,
):
    return {
        "patient_id": "TEST",
        "date": date,
        "visit": visit,
        "egfr": egfr,
        "creatinine": creatinine,
        "uacr": uacr,
        "systolic_bp": systolic_bp,
        "diastolic_bp": diastolic_bp,
        "hba1c": hba1c,
    }


def test_stable_patient():
    """
    All parameter values remain unchanged across visits.

    Expected:
        trend = stable
    """

    df = make_patient([
        base_row("2026-01-10", "V1", 70, 1.1, 40, 130, 80, 6.2),
        base_row("2026-04-10", "V2", 70, 1.1, 40, 130, 80, 6.2),
        base_row("2026-07-10", "V3", 70, 1.1, 40, 130, 80, 6.2),
        base_row("2026-10-10", "V4", 70, 1.1, 40, 130, 80, 6.2),
    ])

    result = calculate_longitudinal_features(df)

    assert result["egfr"]["trend"] == "stable"
    assert result["creatinine"]["trend"] == "stable"
    assert result["uacr"]["trend"] == "stable"
    assert result["systolic_bp"]["trend"] == "stable"


def test_improving_patient():
    """
    eGFR increases while creatinine, UACR and systolic BP decrease.

    Expected:
        eGFR       -> increasing
        creatinine -> decreasing
        UACR       -> decreasing
        SBP        -> decreasing
    """

    df = make_patient([
        base_row(
            "2026-01-10",
            "V1",
            50,
            1.6,
            160,
            150,
            90,
            7.2,
        ),
        base_row(
            "2026-04-10",
            "V2",
            58,
            1.4,
            120,
            142,
            87,
            6.8,
        ),
        base_row(
            "2026-07-10",
            "V3",
            66,
            1.2,
            80,
            135,
            84,
            6.4,
        ),
        base_row(
            "2026-10-10",
            "V4",
            72,
            1.1,
            50,
            130,
            81,
            6.1,
        ),
    ])

    result = calculate_longitudinal_features(df)

    assert result["egfr"]["trend"] == "increasing"
    assert result["creatinine"]["trend"] == "decreasing"
    assert result["uacr"]["trend"] == "decreasing"
    assert result["systolic_bp"]["trend"] == "decreasing"


def test_mixed_direction_with_dominant_decreasing_trend():
    """
    The eGFR values are:

        70 -> 65 -> 69 -> 64

    Transitions:

        decreasing
        increasing
        decreasing

    The longitudinal feature calculation should identify
    the dominant overall direction as decreasing.
    """

    df = make_patient([
        base_row(
            "2026-01-10",
            "V1",
            70,
            1.1,
            40,
            130,
            80,
            6.2,
        ),
        base_row(
            "2026-04-10",
            "V2",
            65,
            1.2,
            60,
            138,
            84,
            6.5,
        ),
        base_row(
            "2026-07-10",
            "V3",
            69,
            1.1,
            45,
            134,
            82,
            6.3,
        ),
        base_row(
            "2026-10-10",
            "V4",
            64,
            1.2,
            65,
            140,
            85,
            6.6,
        ),
    ])

    result = calculate_longitudinal_features(df)

    assert result["egfr"]["trend"] == "decreasing"

def test_gradual_directional_worsening():
    """
    Consistent directional worsening.

    Expected:
        eGFR       -> decreasing
        creatinine -> increasing
        UACR       -> increasing
        SBP        -> increasing
    """

    df = make_patient([
        base_row(
            "2026-01-10",
            "V1",
            72,
            1.1,
            30,
            132,
            82,
            6.2,
        ),
        base_row(
            "2026-04-10",
            "V2",
            68,
            1.2,
            55,
            137,
            84,
            6.4,
        ),
        base_row(
            "2026-07-10",
            "V3",
            64,
            1.3,
            80,
            142,
            86,
            6.6,
        ),
        base_row(
            "2026-10-10",
            "V4",
            60,
            1.4,
            105,
            147,
            88,
            6.8,
        ),
    ])

    result = calculate_longitudinal_features(df)

    assert result["egfr"]["trend"] == "decreasing"
    assert result["creatinine"]["trend"] == "increasing"
    assert result["uacr"]["trend"] == "increasing"
    assert result["systolic_bp"]["trend"] == "increasing"

    worsening = detect_worsening_signals(df)

    assert isinstance(worsening, list)

    worsening_parameters = {
        item["parameter"]
        for item in worsening
    }

    assert "egfr" in worsening_parameters
    assert "creatinine" in worsening_parameters
    assert "uacr" in worsening_parameters
    assert "systolic_bp" in worsening_parameters


def test_rapid_directional_worsening():
    """
    Rapid directional worsening.

    Expected:
        eGFR       -> decreasing
        creatinine -> increasing
        UACR       -> increasing
        SBP        -> increasing
    """

    df = make_patient([
        base_row(
            "2026-01-10",
            "V1",
            80,
            1.0,
            20,
            125,
            78,
            5.8,
        ),
        base_row(
            "2026-04-10",
            "V2",
            65,
            1.3,
            70,
            140,
            84,
            6.4,
        ),
        base_row(
            "2026-07-10",
            "V3",
            45,
            1.7,
            140,
            155,
            90,
            7.0,
        ),
        base_row(
            "2026-10-10",
            "V4",
            30,
            2.1,
            250,
            170,
            96,
            7.8,
        ),
    ])

    result = calculate_longitudinal_features(df)

    assert result["egfr"]["trend"] == "decreasing"
    assert result["creatinine"]["trend"] == "increasing"
    assert result["uacr"]["trend"] == "increasing"
    assert result["systolic_bp"]["trend"] == "increasing"

    assert result["egfr"]["slope_per_day"] < 0
    assert result["creatinine"]["slope_per_day"] > 0
    assert result["uacr"]["slope_per_day"] > 0
    assert result["systolic_bp"]["slope_per_day"] > 0

    worsening = detect_worsening_signals(df)

    assert isinstance(worsening, list)

    worsening_parameters = {
        item["parameter"]
        for item in worsening
    }

    assert "egfr" in worsening_parameters
    assert "creatinine" in worsening_parameters
    assert "uacr" in worsening_parameters
    assert "systolic_bp" in worsening_parameters


def test_expected_vs_actual_trend_behavior():
    """
    Regression test based on the canonical worsening example.

    Expected:
        eGFR       -> decreasing
        creatinine -> increasing
        UACR       -> increasing
        SBP        -> increasing
    """

    df = make_patient([
        base_row(
            "2026-01-10",
            "V1",
            72,
            1.1,
            30,
            132,
            82,
            6.2,
        ),
        base_row(
            "2026-04-10",
            "V2",
            65,
            1.2,
            55,
            139,
            85,
            6.5,
        ),
        base_row(
            "2026-07-10",
            "V3",
            58,
            1.4,
            100,
            146,
            88,
            6.8,
        ),
        base_row(
            "2026-10-10",
            "V4",
            50,
            1.6,
            160,
            151,
            91,
            7.1,
        ),
    ])

    result = calculate_longitudinal_features(df)

    expected_trends = {
        "egfr": "decreasing",
        "creatinine": "increasing",
        "uacr": "increasing",
        "systolic_bp": "increasing",
    }

    for parameter, expected in expected_trends.items():
        actual = result[parameter]["trend"]

        assert actual == expected, (
            f"{parameter}: expected '{expected}', got '{actual}'"
        )