import pandas as pd


PARAMETERS = [
    "egfr",
    "creatinine",
    "uacr",
    "systolic_bp",
    "diastolic_bp",
    "hba1c",
]


def _feature_value(feature):
    """
    Extract the actual value from a longitudinal feature.

    Structured unavailable features are represented as None
    in the integration-ready table.
    """
    if isinstance(feature, dict):
        return feature.get("value")

    return feature


def build_patient_feature_row(
    patient_id,
    patient_analysis,
    quality_flags=None,
):
    """
    Build one integration-ready row for a single patient.

    This function does not calculate longitudinal statistics.
    It only flattens the existing analyzer output.
    """

    row = {
        "patient_id": patient_id,

        # Patient-level metadata
        "number_of_visits": patient_analysis.get(
            "number_of_visits"
        ),

        # Existing overall analysis
        "worsening_signal_count": patient_analysis.get(
            "worsening_signal_count",
            0
        ),
    }

    # --------------------------------------------------
    # Longitudinal parameter features
    # --------------------------------------------------

    longitudinal_features = patient_analysis.get(
        "longitudinal_features",
        {}
    )

    for parameter in PARAMETERS:

        features = longitudinal_features.get(
            parameter,
            {}
        )

        prefix = parameter

        row[f"{prefix}_baseline"] = _feature_value(
            features.get("baseline")
        )

        row[f"{prefix}_latest"] = _feature_value(
            features.get("latest")
        )

        row[f"{prefix}_absolute_change"] = _feature_value(
            features.get("absolute_change")
        )

        row[f"{prefix}_percentage_change"] = _feature_value(
            features.get("percentage_change")
        )

        row[f"{prefix}_slope_per_day"] = _feature_value(
            features.get("slope_per_day")
        )

        row[f"{prefix}_slope_per_year"] = _feature_value(
            features.get("slope_per_year")
        )

        row[f"{prefix}_variability_std"] = _feature_value(
            features.get("variability_std")
        )

        row[f"{prefix}_average_rate_per_day"] = _feature_value(
            features.get("average_rate_per_day")
        )

        row[f"{prefix}_acceleration"] = _feature_value(
            features.get("acceleration")
        )

        row[f"{prefix}_trend"] = _feature_value(
            features.get("trend")
        )

    # --------------------------------------------------
    # Worsening parameters
    # --------------------------------------------------

    worsening_signals = patient_analysis.get(
        "worsening_signals",
        []
    )

    worsening_parameters = []

    for signal in worsening_signals:

        if isinstance(signal, dict):

            parameter = signal.get(
                "parameter"
            )

            if parameter:
                worsening_parameters.append(
                    parameter
                )

    row["worsening_parameters"] = (
        "; ".join(worsening_parameters)
    )

    # --------------------------------------------------
    # Co-worsening analysis
    # --------------------------------------------------

    co_worsening = patient_analysis.get(
        "co_worsening_analysis",
        {}
    )

    row["co_worsening_detected"] = co_worsening.get(
        "co_worsening_detected",
        False
    )

    co_worsening_transitions = co_worsening.get(
        "co_worsening_transitions",
        []
    )

    row["co_worsening_transition_count"] = len(
        co_worsening_transitions
    )

    # --------------------------------------------------
    # Data-quality flags
    # --------------------------------------------------

    quality_flags = quality_flags or []

    row["quality_flag_count"] = len(
        quality_flags
    )

    row["quality_flags"] = (
        "; ".join(
            str(flag)
            for flag in quality_flags
        )
    )

    return row


def build_patient_feature_table(
    patient_results,
    quality_report=None,
):
    """
    Build one row per patient from existing
    analyzer results.

    Parameters
    ----------
    patient_results : dict
        Dictionary containing analyze_patient()
        output keyed by patient ID.

    quality_report : dict, optional
        Existing data-quality report containing
        patient-level quality flags.

    Returns
    -------
    pandas.DataFrame
        Integration-ready patient-level feature table.
    """

    quality_report = quality_report or {}

    patient_flags = quality_report.get(
        "patient_flags",
        {}
    )

    rows = []

    for patient_id, analysis in patient_results.items():

        patient_quality = patient_flags.get(
            patient_id,
            {}
        )

        quality_flags = patient_quality.get(
            "flags",
            []
        )

        row = build_patient_feature_row(
            patient_id=patient_id,
            patient_analysis=analysis,
            quality_flags=quality_flags,
        )

        rows.append(row)

    return pd.DataFrame(rows)