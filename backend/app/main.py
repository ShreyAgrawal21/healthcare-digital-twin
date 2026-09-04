from io import BytesIO

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.analyzer import calculate_changes, analyze_patient


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

            df = pd.read_excel(
                BytesIO(file_bytes),
                engine="openpyxl"
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

    # Remove accidental spaces from column names
    df.columns = [
        str(column).strip().lower()
        for column in df.columns
    ]

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
    # Convert numeric columns
    # -----------------------------------------------------

    numeric_columns = [
        "visit",
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
    # Check missing numeric values
    # -----------------------------------------------------

    missing_numeric = {}

    for column in numeric_columns:

        missing_count = int(
            df[column].isna().sum()
        )

        if missing_count > 0:

            missing_numeric[column] = missing_count

    if missing_numeric:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing or invalid numeric values found",
                "columns": missing_numeric,
            }
        )

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