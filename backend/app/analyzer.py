import pandas as pd

from .config import (
    PARAMETERS,
    MIN_WORSENING_CONSISTENCY,
    MIN_WORSENING_PARAMETERS
)


# ============================================================
# 1. CALCULATE LONGITUDINAL CHANGES
# ============================================================

def calculate_changes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate longitudinal changes for every patient
    and every configured parameter.

    Calculations:
    - Previous value
    - Absolute change
    - Percentage change
    - Direction
    - Days since previous visit
    - Rate of change per day
    """

    df = df.copy()

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"])

    # Sort patients chronologically
    df = (
        df.sort_values(
            ["patient_id", "date"]
        )
        .reset_index(drop=True)
    )

    # Days between visits
    df["days_since_previous_visit"] = (
        df.groupby("patient_id")["date"]
        .diff()
        .dt.days
    )

    # Calculate changes for every parameter
    for parameter in PARAMETERS:

        previous_column = (
            f"{parameter}_previous"
        )

        change_column = (
            f"{parameter}_change"
        )

        percentage_column = (
            f"{parameter}_change_percent"
        )

        direction_column = (
            f"{parameter}_direction"
        )

        rate_column = (
            f"{parameter}_rate"
        )

        # ----------------------------------------
        # Previous value
        # ----------------------------------------

        df[previous_column] = (
            df.groupby("patient_id")[parameter]
            .shift(1)
        )

        # ----------------------------------------
        # Absolute change
        # ----------------------------------------

        df[change_column] = (
            df[parameter]
            - df[previous_column]
        )

        # ----------------------------------------
        # Percentage change
        # ----------------------------------------

        df[percentage_column] = (
            df[change_column]
            / df[previous_column].abs()
        ) * 100

        # ----------------------------------------
        # Direction
        # ----------------------------------------

        df[direction_column] = (
            df[change_column]
            .apply(determine_direction)
        )

        # ----------------------------------------
        # Rate of change per day
        # ----------------------------------------

        df[rate_column] = (
            df[change_column]
            / df["days_since_previous_visit"]
        )

    return df


# ============================================================
# 2. DETERMINE DIRECTION
# ============================================================

def determine_direction(change):
    """
    Determine the direction of a measurement change.

    Returns:
        baseline
        increasing
        decreasing
        stable
    """

    if pd.isna(change):
        return "baseline"

    if change > 0:
        return "increasing"

    if change < 0:
        return "decreasing"

    return "stable"


# ============================================================
# 3. DETECT OVERALL PARAMETER TRENDS
# ============================================================

def detect_parameter_trends(
    patient_df: pd.DataFrame
):
    """
    Determine the overall longitudinal trend
    for every configured parameter.

    The function counts:
    - Increasing transitions
    - Decreasing transitions
    - Stable transitions
    """

    trends = {}

    for parameter in PARAMETERS:

        changes = (
            patient_df[parameter]
            .diff()
            .dropna()
        )

        # No transitions available
        if len(changes) == 0:

            trends[parameter] = {

                "trend":
                    "insufficient_data",

                "increasing_steps":
                    0,

                "decreasing_steps":
                    0,

                "stable_steps":
                    0
            }

            continue

        # Count directions
        increasing = int(
            (changes > 0).sum()
        )

        decreasing = int(
            (changes < 0).sum()
        )

        stable = int(
            (changes == 0).sum()
        )

        # Determine dominant trend
        if increasing > decreasing:

            trend = "increasing"

        elif decreasing > increasing:

            trend = "decreasing"

        else:

            trend = "stable"

        trends[parameter] = {

            "trend":
                trend,

            "increasing_steps":
                increasing,

            "decreasing_steps":
                decreasing,

            "stable_steps":
                stable
        }

    return trends


# ============================================================
# 4. DETECT CONSISTENTLY WORSENING SIGNALS
# ============================================================

def detect_worsening_signals(
    patient_df: pd.DataFrame
):
    """
    Identify parameters that consistently move
    in their configured worsening direction.

    IMPORTANT:
    This function performs longitudinal pattern
    detection only.

    It does NOT apply clinical thresholds.
    """

    worsening = []

    # Number of possible transitions
    total_transitions = (
        len(patient_df) - 1
    )

    if total_transitions <= 0:
        return worsening

    for parameter, metadata in PARAMETERS.items():

        # Visit-to-visit changes
        changes = (
            patient_df[parameter]
            .diff()
            .dropna()
        )

        # Remove missing changes
        changes = changes.dropna()

        if len(changes) == 0:
            continue

        expected_direction = metadata[
            "worsening_direction"
        ]

        # ----------------------------------------
        # Count worsening transitions
        # ----------------------------------------

        if expected_direction == "decreasing":

            worsening_steps = int(
                (changes < 0).sum()
            )

        elif expected_direction == "increasing":

            worsening_steps = int(
                (changes > 0).sum()
            )

        else:

            continue

        # ----------------------------------------
        # Calculate consistency
        # ----------------------------------------

        consistency = (
            worsening_steps
            / len(changes)
        )

        # ----------------------------------------
        # Overall change
        # ----------------------------------------

        overall_change = (
            patient_df[parameter].iloc[-1]
            -
            patient_df[parameter].iloc[0]
        )

        # ----------------------------------------
        # Add worsening signal
        # ----------------------------------------

        if (
            consistency
            >= MIN_WORSENING_CONSISTENCY
        ):

            worsening.append({

                "parameter":
                    parameter,

                "name":
                    metadata["name"],

                "expected_worsening_direction":
                    expected_direction,

                "worsening_steps":
                    worsening_steps,

                "total_transitions":
                    len(changes),

                "consistency":
                    round(
                        consistency,
                        3
                    ),

                "overall_change":
                    round(
                        float(
                            overall_change
                        ),
                        4
                    )
            })

    return worsening


# ============================================================
# 5. DETECT CONCURRENT / CO-WORSENING SIGNALS
# ============================================================

def detect_co_worsening(
    patient_df: pd.DataFrame
):
    """
    Detect whether multiple parameters move in their
    configured worsening directions during the same
    visit-to-visit transition.

    This is a longitudinal pattern detector.

    It does NOT make a clinical diagnosis.
    """

    patient_df = (
        patient_df
        .sort_values("date")
        .reset_index(drop=True)
    )

    transition_results = []

    # Compare every visit with the previous visit
    for index in range(
        1,
        len(patient_df)
    ):

        previous = patient_df.iloc[
            index - 1
        ]

        current = patient_df.iloc[
            index
        ]

        worsening_parameters = []

        # ----------------------------------------
        # Check every parameter
        # ----------------------------------------

        for parameter, metadata in PARAMETERS.items():

            previous_value = previous[
                parameter
            ]

            current_value = current[
                parameter
            ]

            # Skip missing values
            if (
                pd.isna(previous_value)
                or
                pd.isna(current_value)
            ):
                continue

            # Calculate change
            change = (
                current_value
                - previous_value
            )

            expected_direction = metadata[
                "worsening_direction"
            ]

            is_worsening = False

            # ------------------------------------
            # Check worsening direction
            # ------------------------------------

            if (
                expected_direction
                == "decreasing"
                and change < 0
            ):

                is_worsening = True

            elif (
                expected_direction
                == "increasing"
                and change > 0
            ):

                is_worsening = True

            # ------------------------------------
            # Store worsening parameter
            # ------------------------------------

            if is_worsening:

                worsening_parameters.append({

                    "parameter":
                        parameter,

                    "name":
                        metadata["name"],

                    "change":
                        round(
                            float(change),
                            4
                        )
                })

        # ----------------------------------------
        # Store transition
        # ----------------------------------------

        transition_results.append({

            "from_visit":
                int(
                    previous["visit"]
                ),

            "to_visit":
                int(
                    current["visit"]
                ),

            "from_date":
                previous[
                    "date"
                ].strftime(
                    "%Y-%m-%d"
                ),

            "to_date":
                current[
                    "date"
                ].strftime(
                    "%Y-%m-%d"
                ),

            "worsening_parameters":
                worsening_parameters,

            "worsening_parameter_count":
                len(
                    worsening_parameters
                )
        })

    # --------------------------------------------
    # Identify transitions with multiple
    # simultaneous worsening signals
    # --------------------------------------------

    co_worsening_transitions = [

        transition

        for transition
        in transition_results

        if transition[
            "worsening_parameter_count"
        ]
        >= MIN_WORSENING_PARAMETERS
    ]

    return {

        "transitions":
            transition_results,

        "co_worsening_transitions":
            co_worsening_transitions,

        "co_worsening_detected":
            len(
                co_worsening_transitions
            ) > 0
    }


# ============================================================
# 6. BUILD PATIENT TIMELINE
# ============================================================

def build_patient_timeline(
    patient_df: pd.DataFrame
):
    """
    Build a clean chronological timeline
    for the patient.
    """

    patient_df = (
        patient_df
        .sort_values("date")
        .reset_index(drop=True)
    )

    timeline = []

    for _, row in patient_df.iterrows():

        visit_data = {

            "date":
                row["date"].strftime(
                    "%Y-%m-%d"
                ),

            "visit":
                int(row["visit"])
        }

        # Add configured parameters
        for parameter in PARAMETERS:

            value = row[
                parameter
            ]

            if pd.isna(value):

                visit_data[
                    parameter
                ] = None

            else:

                visit_data[
                    parameter
                ] = float(value)

        timeline.append(
            visit_data
        )

    return timeline


# ============================================================
# 7. BUILD CHANGE HISTORY
# ============================================================

def build_change_history(
    patient_df: pd.DataFrame
):
    """
    Build detailed visit-to-visit change history
    for every parameter.
    """

    history = []

    for _, row in patient_df.iterrows():

        visit = {

            "date":
                row["date"].strftime(
                    "%Y-%m-%d"
                ),

            "visit":
                int(row["visit"]),

            "changes": {}
        }

        for parameter in PARAMETERS:

            previous = row[
                f"{parameter}_previous"
            ]

            current = row[
                parameter
            ]

            change = row[
                f"{parameter}_change"
            ]

            percentage = row[
                f"{parameter}_change_percent"
            ]

            direction = row[
                f"{parameter}_direction"
            ]

            rate = row[
                f"{parameter}_rate"
            ]

            visit[
                "changes"
            ][parameter] = {

                "current_value":
                    safe_float(
                        current
                    ),

                "previous_value":
                    safe_float(
                        previous
                    ),

                "absolute_change":
                    safe_float(
                        change
                    ),

                "percentage_change":
                    safe_float(
                        percentage
                    ),

                "direction":
                    direction,

                "rate_per_day":
                    safe_float(
                        rate
                    )
            }

        history.append(
            visit
        )

    return history


# ============================================================
# 8. SAFE FLOAT CONVERSION
# ============================================================

def safe_float(value):
    """
    Convert pandas/numpy values to JSON-safe floats.
    """

    if pd.isna(value):

        return None

    return round(
        float(value),
        4
    )


# ============================================================
# 9. BUILD STRUCTURED EXPLANATION
# ============================================================

def build_explanation(
    worsening_signals,
    co_worsening
):
    """
    Generate structured explanations using only
    calculated longitudinal evidence.

    No diagnosis or clinical prediction is generated.
    """

    explanations = []

    # --------------------------------------------
    # Individual trend explanations
    # --------------------------------------------

    for signal in worsening_signals:

        consistency_percent = round(
            signal["consistency"] * 100,
            1
        )

        direction = signal[
            "expected_worsening_direction"
        ]

        explanations.append({

            "type":
                "individual_trend",

            "parameter":
                signal["name"],

            "message":
                (
                    f"{signal['name']} shows a "
                    f"{direction} trend across "
                    f"{consistency_percent}% of "
                    f"observed transitions."
                ),

            "evidence": {

                "worsening_steps":
                    signal[
                        "worsening_steps"
                    ],

                "total_transitions":
                    signal[
                        "total_transitions"
                    ],

                "consistency":
                    signal[
                        "consistency"
                    ],

                "overall_change":
                    signal[
                        "overall_change"
                    ]
            }
        })

    # --------------------------------------------
    # Concurrent worsening explanations
    # --------------------------------------------

    for transition in (
        co_worsening[
            "co_worsening_transitions"
        ]
    ):

        parameter_names = [

            item["name"]

            for item
            in transition[
                "worsening_parameters"
            ]
        ]

        explanations.append({

            "type":
                "co_worsening",

            "from_visit":
                transition[
                    "from_visit"
                ],

            "to_visit":
                transition[
                    "to_visit"
                ],

            "message":
                (
                    "Multiple parameters moved "
                    "in their configured worsening "
                    "directions between "
                    f"Visit {transition['from_visit']} "
                    f"and Visit {transition['to_visit']}: "
                    +
                    ", ".join(
                        parameter_names
                    )
                    +
                    "."
                )
        })

    return explanations


# ============================================================
# 10. BUILD HUMAN-READABLE PATIENT SUMMARY
# ============================================================

def build_patient_summary(
    patient_df: pd.DataFrame,
    worsening_signals,
    co_worsening
):
    """
    Build a concise human-readable summary.

    This summarizes observed longitudinal data.
    It does not make a clinical diagnosis.
    """

    patient_id = patient_df[
        "patient_id"
    ].iloc[0]

    summary_lines = []

    # --------------------------------------------
    # Overall assessment
    # --------------------------------------------

    if (
        len(worsening_signals)
        >= MIN_WORSENING_PARAMETERS
        and
        co_worsening[
            "co_worsening_detected"
        ]
    ):

        summary_lines.append(
            "Multiple worsening signals were "
            "detected across the patient's "
            "longitudinal timeline."
        )

    elif (
        len(worsening_signals)
        >= MIN_WORSENING_PARAMETERS
    ):

        summary_lines.append(
            "Multiple parameters show "
            "worsening longitudinal trends, "
            "but concurrent worsening was not "
            "consistently observed."
        )

    elif len(worsening_signals) == 1:

        summary_lines.append(
            "One parameter shows a worsening "
            "longitudinal trend."
        )

    else:

        summary_lines.append(
            "No multi-parameter worsening "
            "pattern was detected."
        )

    # --------------------------------------------
    # Main contributing signals
    # --------------------------------------------

    if worsening_signals:

        summary_lines.append(
            "Main contributing signals:"
        )

        for signal in worsening_signals:

            consistency = round(
                signal["consistency"] * 100,
                1
            )

            overall_change = signal[
                "overall_change"
            ]

            direction = signal[
                "expected_worsening_direction"
            ]

            summary_lines.append(

                f"- {signal['name']} is "
                f"{direction} across "
                f"{consistency}% of observed "
                f"transitions "
                f"(overall change: "
                f"{overall_change})."
            )

    # --------------------------------------------
    # Concurrent worsening
    # --------------------------------------------

    if co_worsening[
        "co_worsening_detected"
    ]:

        summary_lines.append(
            "Concurrent worsening was observed "
            "between the following visits:"
        )

        for transition in (
            co_worsening[
                "co_worsening_transitions"
            ]
        ):

            names = [

                item["name"]

                for item
                in transition[
                    "worsening_parameters"
                ]
            ]

            summary_lines.append(

                f"- Visit "
                f"{transition['from_visit']} "
                f"→ Visit "
                f"{transition['to_visit']}: "
                +
                ", ".join(names)
            )

    # --------------------------------------------
    # Clinical rules note
    # --------------------------------------------

    summary_lines.append(
        "Clinical thresholds and clinical "
        "decision rules have not been applied. "
        "These require input from the DSC team."
    )

    return {

        "patient_id":
            patient_id,

        "summary":
            "\n".join(
                summary_lines
            )
    }


# ============================================================
# 11. BUILD PARAMETER EVIDENCE
# ============================================================

def build_parameter_evidence(
    patient_df: pd.DataFrame,
    worsening_signals
):
    """
    Build detailed evidence for every parameter
    contributing to the longitudinal flag.
    """

    evidence = []

    # Create a set for quick lookup
    worsening_parameters = {

        signal["parameter"]

        for signal
        in worsening_signals
    }

    for parameter in PARAMETERS:

        # Only include contributing parameters
        if parameter not in worsening_parameters:
            continue

        metadata = PARAMETERS[
            parameter
        ]

        values = []

        # ----------------------------------------
        # Collect values over time
        # ----------------------------------------

        for value in patient_df[
            parameter
        ]:

            if pd.isna(value):

                values.append(
                    None
                )

            else:

                values.append(
                    float(value)
                )

        # ----------------------------------------
        # First and last values
        # ----------------------------------------

        first_value = (
            values[0]
            if values
            else None
        )

        last_value = (
            values[-1]
            if values
            else None
        )

        # ----------------------------------------
        # Overall change
        # ----------------------------------------

        if (
            first_value is not None
            and
            last_value is not None
        ):

            overall_change = (
                last_value
                - first_value
            )

        else:

            overall_change = None

        evidence.append({

            "parameter":
                parameter,

            "name":
                metadata["name"],

            "configured_worsening_direction":
                metadata[
                    "worsening_direction"
                ],

            "values_over_time":
                values,

            "first_value":
                first_value,

            "last_value":
                last_value,

            "overall_change":
                (
                    round(
                        overall_change,
                        4
                    )

                    if overall_change
                    is not None

                    else None
                )
        })

    return evidence


# ============================================================
# 12. COMPLETE PATIENT ANALYSIS
# ============================================================

def analyze_patient(
    patient_df: pd.DataFrame
):
    """
    Complete longitudinal analysis pipeline.

    Pipeline:
        1. Sort timeline
        2. Calculate changes
        3. Detect parameter trends
        4. Detect worsening signals
        5. Detect concurrent worsening
        6. Build timeline
        7. Build change history
        8. Generate explanations
        9. Generate patient summary
        10. Generate parameter evidence
    """

    # --------------------------------------------
    # Sort patient timeline
    # --------------------------------------------

    patient_df = (
        patient_df
        .sort_values("date")
        .reset_index(drop=True)
    )

    patient_id = patient_df[
        "patient_id"
    ].iloc[0]

    # --------------------------------------------
    # 1. Calculate changes
    # --------------------------------------------

    analyzed_df = calculate_changes(
        patient_df
    )

    # --------------------------------------------
    # 2. Detect overall trends
    # --------------------------------------------

    trends = detect_parameter_trends(
        analyzed_df
    )

    # --------------------------------------------
    # 3. Detect consistently worsening signals
    # --------------------------------------------

    worsening_signals = (
        detect_worsening_signals(
            analyzed_df
        )
    )

    # --------------------------------------------
    # 4. Detect concurrent worsening
    # --------------------------------------------

    co_worsening = detect_co_worsening(
        analyzed_df
    )

    # --------------------------------------------
    # 5. Build timeline
    # --------------------------------------------

    timeline = build_patient_timeline(
        analyzed_df
    )

    # --------------------------------------------
    # 6. Build change history
    # --------------------------------------------

    change_history = build_change_history(
        analyzed_df
    )

    # --------------------------------------------
    # 7. Determine overall status
    # --------------------------------------------

    if (
        len(worsening_signals)
        >= MIN_WORSENING_PARAMETERS

        and

        co_worsening[
            "co_worsening_detected"
        ]
    ):

        overall_status = (
            "Multiple parameters show a "
            "co-worsening longitudinal pattern."
        )

    elif (
        len(worsening_signals)
        >= MIN_WORSENING_PARAMETERS
    ):

        overall_status = (
            "Multiple parameters show "
            "worsening longitudinal trends, "
            "but concurrent worsening was "
            "not consistently observed."
        )

    elif len(worsening_signals) == 1:

        overall_status = (
            "One parameter shows a "
            "worsening longitudinal trend."
        )

    else:

        overall_status = (
            "No multi-parameter worsening "
            "pattern detected."
        )

    # --------------------------------------------
    # 8. Structured explanation
    # --------------------------------------------

    explanations = build_explanation(
        worsening_signals,
        co_worsening
    )

    # --------------------------------------------
    # 9. Human-readable summary
    # --------------------------------------------

    patient_summary = build_patient_summary(
        analyzed_df,
        worsening_signals,
        co_worsening
    )

    # --------------------------------------------
    # 10. Parameter evidence
    # --------------------------------------------

    parameter_evidence = (
        build_parameter_evidence(
            analyzed_df,
            worsening_signals
        )
    )

    # --------------------------------------------
    # 11. Final structured response
    # --------------------------------------------

    return {

        "patient_id":
            patient_id,

        "number_of_visits":
            len(analyzed_df),

        "timeline":
            timeline,

        "change_history":
            change_history,

        "trends":
            trends,

        "worsening_signal_count":
            len(worsening_signals),

        "worsening_signals":
            worsening_signals,

        "co_worsening_analysis":
            co_worsening,

        "overall_status":
            overall_status,

        "patient_summary":
            patient_summary,

        "parameter_evidence":
            parameter_evidence,

        "explanation":
            explanations,

        "clinical_rules_status": {

            "applied":
                False,

            "message":
                "Clinical thresholds and "
                "clinical decision rules have "
                "not been applied. These require "
                "input from the DSC team."
        }
    }