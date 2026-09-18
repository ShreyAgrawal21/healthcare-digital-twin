from io import BytesIO

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.analyzer import calculate_changes, analyze_patient, normalize_visit_number


app = FastAPI(
    title="Healthcare Digital Twin - Kidney Pilot",
    description="Longitudinal healthcare data intelligence engine",
    version="1.0.0"
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://healthcare-digital-twin-blond.vercel.app",
        "https://healthcare-digital-twin-2xmbgn0dt-shreyagrawal21.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Required columns
# ---------------------------------------------------------

REQUIRED_COLUMNS = [
    "patient_id",
    "date",
    "visit",
    "egfr",
    "creatinine",
    "uacr",
    "systolic_bp",
    "diastolic_bp",
    "hba1c",
]


# ---------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Healthcare Digital Twin API is running",
        "status": "ok",
        "version": "1.0.0",
    }


# ---------------------------------------------------------
# File reader
# ---------------------------------------------------------

def read_uploaded_file(file_bytes: bytes, filename: str) -> pd.DataFrame:

    filename_lower = filename.lower()

    try:

        # CSV
        if filename_lower.endswith(".csv"):

            df = pd.read_csv(BytesIO(file_bytes))

        # Excel
        elif filename_lower.endswith(".xlsx"):

            excel_file = pd.ExcelFile(
                BytesIO(file_bytes),
                engine="openpyxl"
            )

            if "Longitudinal_Data" in excel_file.sheet_names:
                df = pd.read_excel(
                    excel_file,
                    sheet_name="Longitudinal_Data"
                )
            else:
                df = pd.read_excel(
                    excel_file,
                    sheet_name=excel_file.sheet_names[0]
                )

        # Old Excel format
        elif filename_lower.endswith(".xls"):

            df = pd.read_excel(BytesIO(file_bytes))

        else:

            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Unsupported file format",
                    "supported_formats": [
                        ".csv",
                        ".xlsx",
                        ".xls"
                    ]
                }
            )

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unable to read uploaded file",
                "error": str(e)
            }
        )

    return df


# ---------------------------------------------------------
# Validate columns
# ---------------------------------------------------------

def validate_columns(df: pd.DataFrame):

    # ---------------------------------------------------------
    # Normalize column names
    # ---------------------------------------------------------

    df.columns = [
        str(column).strip().lower()
        for column in df.columns
    ]

    # ---------------------------------------------------------
    # Map shared DSC dataset → canonical engine schema
    # ---------------------------------------------------------

    column_mapping = {
        "patient_id": "patient_id",
        "patient_id ": "patient_id",

        "date": "date",
        "visit": "visit",

        "egfr": "egfr",
        "creatinine": "creatinine",
        "uacr": "uacr",

        "sbp": "systolic_bp",
        "dbp": "diastolic_bp",

        "hba1c": "hba1c",

        "potassium": "potassium",
        "hemoglobin": "hemoglobin",
    }

    df.rename(
        columns=column_mapping,
        inplace=True
    )

    # ---------------------------------------------------------
    # Validate required columns
    # ---------------------------------------------------------

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing required columns",
                "columns": missing_columns,
            }
        )

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing required columns",
                "columns": missing_columns,
            }
        )



# ---------------------------------------------------------
# Data-quality checks
# ---------------------------------------------------------

QUALITY_NUMERIC_COLUMNS = [
    "egfr",
    "creatinine",
    "uacr",
    "systolic_bp",
    "diastolic_bp",
    "hba1c",
]


def build_data_quality_report(df: pd.DataFrame):
    """
    Build a visible, non-clinical data-quality report.

    These checks describe data completeness/structure only.
    They do not apply clinical thresholds or make clinical judgments.
    """
    work = df.copy()

    # Normalize patient IDs for checking while preserving original data.
    patient_id_text = work["patient_id"].astype("string").str.strip()
    missing_patient_id = patient_id_text.isna() | (patient_id_text == "")

    # Visit validation: supports 1, 2, 3 and V1, V2, V3 style labels.
    visit_numbers = work["visit"].apply(normalize_visit_number)
    invalid_visit = work["visit"].notna() & visit_numbers.isna()
    missing_visit = work["visit"].isna()

    # Date validation.
    parsed_dates = pd.to_datetime(work["date"], errors="coerce")
    invalid_date = parsed_dates.isna()

    # Numeric validation: original non-null values that cannot be converted.
    invalid_numeric = {}
    missing_numeric = {}

    for column in QUALITY_NUMERIC_COLUMNS:
        original = work[column]
        converted = pd.to_numeric(original, errors="coerce")

        invalid_mask = original.notna() & converted.isna()
        missing_mask = original.isna()

        invalid_numeric[column] = int(invalid_mask.sum())
        missing_numeric[column] = int(missing_mask.sum())

    # Duplicate checks.
    # Perform duplicate checks on a copy containing parsed dates.
    duplicate_check = work.copy()
    duplicate_check["_parsed_date"] = parsed_dates
    duplicate_patient_date_mask = duplicate_check.duplicated(
        subset=["patient_id", "_parsed_date"],
        keep=False
    ) & duplicate_check["patient_id"].notna() & duplicate_check["_parsed_date"].notna()

    duplicate_patient_visit_mask = (
        duplicate_check.duplicated(
            subset=["patient_id", "visit"],
            keep=False
        )
        & duplicate_check["patient_id"].notna()
        & duplicate_check["visit"].notna()
    )

    # Non-positive intervals after chronological sorting.
    interval_check = duplicate_check.sort_values(
        ["patient_id", "_parsed_date", "visit"],
        na_position="last"
    ).copy()

    interval_check["days_since_previous_visit"] = (
        interval_check.groupby("patient_id")["_parsed_date"].diff().dt.days
    )

    non_positive_interval_mask = (
        interval_check["days_since_previous_visit"].notna()
        & (interval_check["days_since_previous_visit"] <= 0)
    )

    # Patient-level visit counts.
    valid_patient_ids = patient_id_text[~missing_patient_id]
    visit_counts = valid_patient_ids.value_counts().sort_index()

    visit_count_distribution = {
        str(int(visit_count)): int((visit_counts == visit_count).sum())
        for visit_count in sorted(visit_counts.unique())
    }

    # Patient-level flags.
    patient_flags = {}
    for patient_id, group in duplicate_check.groupby("patient_id", dropna=False):
        patient_key = (
            str(patient_id).strip()
            if pd.notna(patient_id) and str(patient_id).strip()
            else "MISSING_PATIENT_ID"
        )

        flags = []

        group_dates = group["_parsed_date"]
        if group_dates.isna().any():
            flags.append("invalid_date")

        group_visits = group["visit"].apply(normalize_visit_number)
        if group["visit"].isna().any():
            flags.append("missing_visit")
        if group["visit"].notna().any() and group_visits[group["visit"].notna()].isna().any():
            flags.append("invalid_visit")

        if group.duplicated(
            subset=["patient_id", "_parsed_date"], keep=False
        ).any() and group["_parsed_date"].notna().any():
            flags.append("duplicate_patient_date")

        if group.duplicated(
            subset=["patient_id", "visit"], keep=False
        ).any() and group["visit"].notna().any():
            flags.append("duplicate_patient_visit")

        # Flag missing/invalid parameter values without making them fatal.
        for column in QUALITY_NUMERIC_COLUMNS:
            converted = pd.to_numeric(group[column], errors="coerce")
            if group[column].isna().any():
                flags.append(f"missing_{column}")
            if (group[column].notna() & converted.isna()).any():
                flags.append(f"invalid_{column}")

        sorted_group = group.sort_values(["_parsed_date", "visit"], na_position="last")
        intervals = sorted_group["_parsed_date"].diff().dt.days.dropna()
        if (intervals <= 0).any():
            flags.append("non_positive_interval")

        patient_flags[patient_key] = {
            "quality_status": "warning" if flags else "ok",
            "flags": sorted(set(flags)),
            "number_of_records": int(len(group)),
            "number_of_valid_dates": int(group["_parsed_date"].notna().sum()),
            "number_of_valid_visits": int(group["visit"].apply(normalize_visit_number).notna().sum()),
        }

    invalid_numeric_total = {
        column: count
        for column, count in invalid_numeric.items()
        if count > 0
    }
    missing_numeric_total = {
        column: count
        for column, count in missing_numeric.items()
        if count > 0
    }

    total_warning_patients = sum(
        1
        for item in patient_flags.values()
        if item["quality_status"] == "warning"
    )

    return {
        "status": "warning" if (
            missing_patient_id.any()
            or missing_visit.any()
            or invalid_visit.any()
            or invalid_date.any()
            or duplicate_patient_date_mask.any()
            or duplicate_patient_visit_mask.any()
            or non_positive_interval_mask.any()
            or invalid_numeric_total
            or missing_numeric_total
        ) else "ok",
        "summary": {
            "patient_count": int(valid_patient_ids.nunique()),
            "record_count": int(len(work)),
            "visit_count_distribution": visit_count_distribution,
            "patients_with_quality_warnings": int(total_warning_patients),
        },
        "checks": {
            "missing_or_invalid_patient_ids": int(missing_patient_id.sum()),
            "missing_visits": int(missing_visit.sum()),
            "invalid_visits": int(invalid_visit.sum()),
            "invalid_dates": int(invalid_date.sum()),
            "duplicate_patient_date_records": int(duplicate_patient_date_mask.sum()),
            "duplicate_patient_visit_records": int(duplicate_patient_visit_mask.sum()),
            "non_positive_intervals": int(non_positive_interval_mask.sum()),
            "missing_numeric_values": missing_numeric_total,
            "invalid_numeric_values": invalid_numeric_total,
        },
        "patient_flags": patient_flags,
    }


# ---------------------------------------------------------
# Analyze endpoint
# ---------------------------------------------------------

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):

    # -----------------------------------------------------
    # Validate filename
    # -----------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="File name is missing"
        )

    # -----------------------------------------------------
    # Read file
    # -----------------------------------------------------

    file_bytes = await file.read()

    if not file_bytes:

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )

    # -----------------------------------------------------
    # Convert CSV / Excel → DataFrame
    # -----------------------------------------------------

    df = read_uploaded_file(
        file_bytes,
        file.filename
    )

    # -----------------------------------------------------
    # Validate schema
    # -----------------------------------------------------

    validate_columns(df)

    # -----------------------------------------------------
    # Validate empty dataset
    # -----------------------------------------------------

    if df.empty:

        raise HTTPException(
            status_code=400,
            detail="Uploaded file contains no patient records"
        )

    # -----------------------------------------------------
    # Parse dates
    # -----------------------------------------------------

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    invalid_dates = df["date"].isna()

    if invalid_dates.any():

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid date values found",
                "invalid_rows": (
                    df.index[invalid_dates]
                    .tolist()
                ),
            }
        )

    # -----------------------------------------------------
    # Preserve raw values for data-quality validation
    # -----------------------------------------------------

    raw_df_for_quality = df.copy()

    # -----------------------------------------------------
    # Convert numeric columns
    # -----------------------------------------------------

    numeric_columns = [
        "egfr",
        "creatinine",
        "uacr",
        "systolic_bp",
        "diastolic_bp",
        "hba1c",
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # -----------------------------------------------------
    # Build visible data-quality report
    # -----------------------------------------------------

    data_quality = build_data_quality_report(raw_df_for_quality)

    # -----------------------------------------------------
    # Sort data
    # -----------------------------------------------------

    df = df.sort_values(
        by=[
            "patient_id",
            "date",
            "visit"
        ]
    ).reset_index(drop=True)

    # -----------------------------------------------------
    # Analyze each patient
    # -----------------------------------------------------

    results = []

    for patient_id, patient_df in df.groupby(
        "patient_id",
        sort=False
    ):

        patient_df = patient_df.copy()

        # Calculate longitudinal changes
        patient_df = calculate_changes(
            patient_df
        )

        # Analyze patient
        result = analyze_patient(
            patient_df
        )

        # Add patient ID explicitly
        result["patient_id"] = str(
            patient_id
        )

        # Attach patient-level data-quality flags.
        patient_key = str(patient_id).strip()
        patient_quality = data_quality["patient_flags"].get(
            patient_key,
            {
                "quality_status": "warning",
                "flags": ["patient_quality_record_not_found"],
            }
        )

        # P070-P075 are intentionally incomplete-follow-up test cases
        # with two visits. Keep the general data-quality checks intact,
        # while making the incomplete history visible to downstream users.
        visit_count = len(patient_df)
        if visit_count < 4:
            patient_quality = dict(patient_quality)
            patient_quality["flags"] = list(patient_quality.get("flags", []))
            if "incomplete_follow_up_test_case" not in patient_quality["flags"]:
                patient_quality["flags"].append("incomplete_follow_up_test_case")
            patient_quality["incomplete_follow_up"] = True
            patient_quality["insufficient_history_features"] = ["acceleration"]
            patient_quality["quality_status"] = "warning"
        else:
            patient_quality = dict(patient_quality)
            patient_quality["incomplete_follow_up"] = False
            patient_quality["insufficient_history_features"] = []

        result["data_quality"] = patient_quality

        results.append(result)

    # -----------------------------------------------------
    # Final response
    # -----------------------------------------------------

    return {
        "patients_analyzed": len(results),
        "records_processed": len(df),
        "file_name": file.filename,
        "results": results,
    }