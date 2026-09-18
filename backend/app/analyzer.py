import pandas as pd

from .config import (
    PARAMETERS,
    MIN_WORSENING_CONSISTENCY,
    MIN_WORSENING_PARAMETERS
)

def normalize_visit_number(visit):
    """
    Convert visit labels such as:
    1, 2, 3
    V1, V2, V3
    into numeric visit numbers.
    """

    if pd.isna(visit):
        return None

    visit_str = str(visit).strip()

    if visit_str.upper().startswith("V"):
        visit_str = visit_str[1:]

    try:
        return int(float(visit_str))
    except (ValueError, TypeError):
        return None
    
# ============================================================
# LONGITUDINAL FEATURE MINIMUM OBSERVATION REQUIREMENTS
# ============================================================

MIN_OBSERVATIONS = {
    "baseline": 1,
    "latest": 1,
    "absolute_change": 1,
    "percentage_change": 1,
    "slope": 2,
    "average_rate": 2,
    "variability": 2,
    "trend": 2,
    "acceleration": 4,
}
    
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

    Missing parameter observations are skipped rather than
    converted into NaN output values. Transitions are calculated
    between consecutive valid observations for that parameter.

    IMPORTANT:
    This function performs longitudinal pattern detection only.
    It does NOT apply clinical thresholds.
    """

    worsening = []

    for parameter, metadata in PARAMETERS.items():

        # Keep only valid observations for this parameter.
        # This supports partial-parameter test cases without
        # producing non-JSON-compliant NaN values.
        valid = patient_df[
            ["date", "visit", parameter]
        ].copy()

        valid[parameter] = pd.to_numeric(
            valid[parameter],
            errors="coerce"
        )

        valid = (
            valid
            .dropna(subset=[parameter])
            .sort_values("date")
            .reset_index(drop=True)
        )

        # At least two valid observations are needed for
        # a visit-to-visit worsening pattern.
        if len(valid) < 2:
            continue

        changes = (
            valid[parameter]
            .diff()
            .dropna()
        )

        if len(changes) == 0:
            continue

        expected_direction = metadata[
            "worsening_direction"
        ]

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

        consistency = (
            worsening_steps
            / len(changes)
        )

        # Both values are guaranteed to be valid because
        # they come from the filtered parameter series.
        overall_change = (
            float(valid[parameter].iloc[-1])
            - float(valid[parameter].iloc[0])
        )

        if consistency >= MIN_WORSENING_CONSISTENCY:
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
                        overall_change,
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
                normalize_visit_number(
                    previous["visit"]
                ),

            "to_visit":
                normalize_visit_number(
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
                normalize_visit_number(row["visit"])
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
                normalize_visit_number(row["visit"]),

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
    
def feature_not_calculable(reason):
    """
    Return a consistent representation for a longitudinal
    feature that cannot be calculated from the available history.
    """
    return {
        "value": None,
        "status": "not_calculable",
        "reason": reason,
    }


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
# 11.5 BUILD LONGITUDINAL FEATURES
# ============================================================

def calculate_longitudinal_features(patient_df: pd.DataFrame):
    """
    Generate reusable patient-level longitudinal features
    for downstream prediction and explainability models.

    Features include:
    - Baseline value
    - Latest value
    - Absolute change
    - Percentage change
    - Visit-to-visit rate
    - Longitudinal slope
    - Variability
    - Acceleration
    - Overall trend

    IMPORTANT:
    These are statistical longitudinal features only.
    They do not represent clinical thresholds, diagnosis,
    prognosis, or causal relationships.
    """

    patient_df = (
        patient_df
        .sort_values("date")
        .reset_index(drop=True)
    )

    features = {}

    for parameter in PARAMETERS:

        values = pd.to_numeric(
            patient_df[parameter],
            errors="coerce"
        )

        valid = pd.DataFrame({
            "date": patient_df["date"],
            "value": values
        }).dropna()

        # ----------------------------------------------------
        # Not enough data
        # ----------------------------------------------------

        if len(valid) == 0:
            features[parameter] = {
                "baseline": None,
                "latest": None,
                "absolute_change": None,
                "percentage_change": None,
                "slope_per_day": None,
                "slope_per_year": None,
                "variability_std": None,
                "average_rate_per_day": None,
                "acceleration": None,
                "trend": "insufficient_data"
            }
            continue

        # ----------------------------------------------------
        # Basic values
        # ----------------------------------------------------

        baseline = float(valid["value"].iloc[0])
        latest = float(valid["value"].iloc[-1])

        absolute_change = latest - baseline

        if baseline != 0:
            percentage_change = (
                absolute_change / abs(baseline)
            ) * 100
        else:
            percentage_change = feature_not_calculable(
                "Baseline value is zero, "
                "percentage change is undefined."
            )

        # ----------------------------------------------------
        # Time in days from baseline
        # ----------------------------------------------------

        days = (
            valid["date"] - valid["date"].iloc[0]
        ).dt.days.astype(float)

        values_list = valid["value"].astype(float)

        # ----------------------------------------------------
        # Longitudinal slope
        #
        # Simple least-squares regression:
        # value = intercept + slope * time
        # ----------------------------------------------------

        if len(valid) >= 2 and days.iloc[-1] != 0:

            x_mean = days.mean()
            y_mean = values_list.mean()

            numerator = (
                (days - x_mean) *
                (values_list - y_mean)
            ).sum()

            denominator = (
                (days - x_mean) ** 2
            ).sum()

            if denominator != 0:
                slope_per_day = numerator / denominator
            else:
                slope_per_day = None

        else:
            slope_per_day = None

        # Convert slope to approximate yearly rate.
        if slope_per_day is not None:
            slope_per_year = slope_per_day * 365.25
        else:
            slope_per_year = None

        # ----------------------------------------------------
        # Variability
        # ----------------------------------------------------

        if len(values_list) >= 2:
            variability_std = values_list.std(ddof=1)
        else:
            variability_std = None

        # ----------------------------------------------------
        # Visit-to-visit rates
        # ----------------------------------------------------

        visit_rates = []

        for index in range(1, len(valid)):

            previous_value = float(
                valid["value"].iloc[index - 1]
            )

            current_value = float(
                valid["value"].iloc[index]
            )

            days_between = (
                valid["date"].iloc[index]
                - valid["date"].iloc[index - 1]
            ).days

            if days_between > 0:

                rate = (
                    current_value - previous_value
                ) / days_between

                visit_rates.append({
                    "rate": rate,
                    "midpoint_day": (
                        days.iloc[index - 1]
                        + days.iloc[index]
                    ) / 2
                })

        if visit_rates:
            average_rate_per_day = sum(
                item["rate"]
                for item in visit_rates
            ) / len(visit_rates)
        else:
            average_rate_per_day = None

        # ----------------------------------------------------
        # Acceleration
        #
        # Acceleration is the change in rate over time.
        #
        # Requires at least 3 transitions.
        # ----------------------------------------------------

        acceleration = None

        if len(visit_rates) >= 3:

            rate_x = pd.Series(
                [
                    item["midpoint_day"]
                    for item in visit_rates
                ],
                dtype=float
            )

            rate_y = pd.Series(
                [
                    item["rate"]
                    for item in visit_rates
                ],
                dtype=float
            )

            rate_x_mean = rate_x.mean()
            rate_y_mean = rate_y.mean()

            numerator = (
                (rate_x - rate_x_mean) *
                (rate_y - rate_y_mean)
            ).sum()

            denominator = (
                (rate_x - rate_x_mean) ** 2
            ).sum()

            if denominator != 0:
                acceleration = numerator / denominator

        # ----------------------------------------------------
        # Overall trend
        # ----------------------------------------------------

        changes = (
            values_list.diff()
            .dropna()
        )

        if len(changes) == 0:
            trend = "insufficient_data"

        else:
            increasing_steps = int(
                (changes > 0).sum()
            )

            decreasing_steps = int(
                (changes < 0).sum()
            )

            stable_steps = int(
                (changes == 0).sum()
            )

            # A dominant direction is only assigned when
            # one direction has more transitions than the other.
            if (
                increasing_steps > decreasing_steps
                and increasing_steps > stable_steps
            ):
                trend = "increasing"

            elif (
                decreasing_steps > increasing_steps
                and decreasing_steps > stable_steps
            ):
                trend = "decreasing"

            elif stable_steps > max(
                increasing_steps,
                decreasing_steps
            ):
                trend = "stable"

            else:
                trend = "fluctuating"

        # ----------------------------------------------------
        # Store features
        # ----------------------------------------------------

        features[parameter] = {
            "baseline": round(baseline, 4),
            "latest": round(latest, 4),

            "absolute_change": round(
                absolute_change,
                4
            ),

            "percentage_change": (
                percentage_change
                if isinstance(percentage_change, dict)
                else round(percentage_change, 4)
            ),

            "slope_per_day": (
                round(float(slope_per_day), 8)
                if slope_per_day is not None
                else feature_not_calculable(
                    "Insufficient observations: at least 2 valid observations "
                    "on distinct dates are required."
                )
            ),

            "slope_per_year": (
                round(float(slope_per_year), 4)
                if slope_per_year is not None
                else feature_not_calculable(
                    "Insufficient observations: at least 2 valid observations "
                    "on distinct dates are required."
                )
            ),

            "variability_std": (
                round(float(variability_std), 4)
                if variability_std is not None
                else feature_not_calculable(
                    "Insufficient observations: at least 2 valid observations "
                    "are required to calculate variability."
                )
            ),

            "average_rate_per_day": (
                round(
                    float(average_rate_per_day),
                    8
                )
                if average_rate_per_day is not None
                else feature_not_calculable(
                    "Insufficient observations: at least 2 valid observations "
                    "on distinct dates are required to calculate visit-to-visit rates."
                )
            ),

            "acceleration": (
                round(
                    float(acceleration),
                    10
                )
                if acceleration is not None
                else feature_not_calculable(
                    "Insufficient observations: at least 3 valid visit-to-visit rates "
                    "are required to calculate acceleration."
                )
            ),

            "trend": (
                trend
                if trend != "insufficient_data"
                else feature_not_calculable(
                    "Insufficient observations: at least 2 valid observations "
                    "on distinct dates are required to determine trend."
                )
            )
        }

    # --------------------------------------------------------
    # Patient-level multi-signal features
    # --------------------------------------------------------

    worsening_signals = detect_worsening_signals(
        patient_df
    )

    co_worsening = detect_co_worsening(
        patient_df
    )

    # --------------------------------------------------------
    # Patient-level history availability
    # --------------------------------------------------------
    # The current acceleration implementation requires three
    # valid visit-to-visit rates, which means four valid visits.
    # P070-P075 intentionally contain two visits each and are
    # therefore treated as incomplete-follow-up test cases.
    valid_visit_count = len(
        patient_df[["date"]].dropna()
    )

    incomplete_follow_up = valid_visit_count < 4

    insufficient_history_features = []

    if valid_visit_count < 4:
        insufficient_history_features.append("acceleration")

    features["_patient_level"] = {
        "worsening_signal_count": len(
            worsening_signals
        ),

        "worsening_parameters": [
            signal["parameter"]
            for signal in worsening_signals
        ],

        "multi_signal_deterioration": (
            len(worsening_signals)
            >= MIN_WORSENING_PARAMETERS
        ),

        "concurrent_worsening_detected": (
            co_worsening[
                "co_worsening_detected"
            ]
        ),

        "concurrent_worsening_transition_count": len(
            co_worsening[
                "co_worsening_transitions"
            ]
        ),

        "incomplete_follow_up": incomplete_follow_up,

        "insufficient_history_features": insufficient_history_features
    }

    return features


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
            "Mixed / fluctuating longitudinal pattern."
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
    # 11. Longitudinal feature generation
    # --------------------------------------------

    longitudinal_features = calculate_longitudinal_features(
        analyzed_df
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
        
        "longitudinal_features":
            longitudinal_features,

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