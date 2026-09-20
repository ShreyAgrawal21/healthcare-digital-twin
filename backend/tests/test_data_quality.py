import pandas as pd

from app.main import build_data_quality_report


def make_dataframe(rows):
    return pd.DataFrame(rows)


def valid_row(
    patient_id="P001",
    date="2026-01-10",
    visit="V1",
    egfr=72,
    creatinine=1.1,
    uacr=30,
    systolic_bp=132,
    diastolic_bp=82,
    hba1c=6.2,
):
    return {
        "patient_id": patient_id,
        "date": date,
        "visit": visit,
        "egfr": egfr,
        "creatinine": creatinine,
        "uacr": uacr,
        "systolic_bp": systolic_bp,
        "diastolic_bp": diastolic_bp,
        "hba1c": hba1c,
    }


def test_valid_dataset_has_no_quality_warnings():
    df = make_dataframe([
        valid_row(
            patient_id="P001",
            date="2026-01-10",
            visit="V1",
        ),
        valid_row(
            patient_id="P001",
            date="2026-04-10",
            visit="V2",
        ),
        valid_row(
            patient_id="P002",
            date="2026-01-15",
            visit="V1",
        ),
    ])

    report = build_data_quality_report(df)

    assert report["status"] == "ok"

    assert report["summary"]["patient_count"] == 2
    assert report["summary"]["record_count"] == 3

    assert report["summary"]["patients_with_quality_warnings"] == 0

    assert report["checks"]["missing_or_invalid_patient_ids"] == 0
    assert report["checks"]["missing_visits"] == 0
    assert report["checks"]["invalid_visits"] == 0
    assert report["checks"]["invalid_dates"] == 0
    assert report["checks"]["duplicate_patient_date_records"] == 0
    assert report["checks"]["duplicate_patient_visit_records"] == 0
    assert report["checks"]["non_positive_intervals"] == 0

    assert report["checks"]["missing_numeric_values"] == {}
    assert report["checks"]["invalid_numeric_values"] == {}


def test_missing_patient_ids_are_reported():
    df = make_dataframe([
        valid_row(
            patient_id="P001",
            date="2026-01-10",
            visit="V1",
        ),
        valid_row(
            patient_id=None,
            date="2026-04-10",
            visit="V2",
        ),
        valid_row(
            patient_id="   ",
            date="2026-07-10",
            visit="V3",
        ),
    ])

    report = build_data_quality_report(df)

    assert report["status"] == "warning"

    assert report["checks"]["missing_or_invalid_patient_ids"] == 2

    assert report["summary"]["patient_count"] == 1
    assert report["summary"]["record_count"] == 3

    assert "MISSING_PATIENT_ID" in report["patient_flags"]

    missing_flag = report["patient_flags"]["MISSING_PATIENT_ID"]

    assert isinstance(missing_flag["flags"], list)


def test_invalid_and_missing_visits_are_reported():
    df = make_dataframe([
        valid_row(
            patient_id="P010",
            date="2026-01-10",
            visit="V1",
        ),
        valid_row(
            patient_id="P010",
            date="2026-04-10",
            visit=None,
        ),
        valid_row(
            patient_id="P010",
            date="2026-07-10",
            visit="INVALID",
        ),
    ])

    report = build_data_quality_report(df)

    assert report["status"] == "warning"

    assert report["checks"]["missing_visits"] == 1
    assert report["checks"]["invalid_visits"] == 1

    patient_flags = report["patient_flags"]["P010"]

    assert patient_flags["quality_status"] == "warning"
    assert "missing_visit" in patient_flags["flags"]
    assert "invalid_visit" in patient_flags["flags"]


def test_invalid_dates_are_reported():
    df = make_dataframe([
        valid_row(
            patient_id="P020",
            date="2026-01-10",
            visit="V1",
        ),
        valid_row(
            patient_id="P020",
            date="not-a-date",
            visit="V2",
        ),
    ])

    report = build_data_quality_report(df)

    assert report["status"] == "warning"

    assert report["checks"]["invalid_dates"] == 1

    patient_flags = report["patient_flags"]["P020"]

    assert patient_flags["quality_status"] == "warning"
    assert "invalid_date" in patient_flags["flags"]

    assert patient_flags["number_of_valid_dates"] == 1


def test_duplicate_patient_date_is_reported():
    df = make_dataframe([
        valid_row(
            patient_id="P030",
            date="2026-01-10",
            visit="V1",
        ),
        valid_row(
            patient_id="P030",
            date="2026-01-10",
            visit="V2",
        ),
        valid_row(
            patient_id="P030",
            date="2026-04-10",
            visit="V3",
        ),
    ])

    report = build_data_quality_report(df)

    assert report["status"] == "warning"

    assert report["checks"]["duplicate_patient_date_records"] == 2

    patient_flags = report["patient_flags"]["P030"]

    assert patient_flags["quality_status"] == "warning"
    assert "duplicate_patient_date" in patient_flags["flags"]


def test_duplicate_patient_visit_is_reported():
    df = make_dataframe([
        valid_row(
            patient_id="P040",
            date="2026-01-10",
            visit="V1",
        ),
        valid_row(
            patient_id="P040",
            date="2026-04-10",
            visit="V1",
        ),
        valid_row(
            patient_id="P040",
            date="2026-07-10",
            visit="V2",
        ),
    ])

    report = build_data_quality_report(df)

    assert report["status"] == "warning"

    assert report["checks"]["duplicate_patient_visit_records"] == 2

    patient_flags = report["patient_flags"]["P040"]

    assert patient_flags["quality_status"] == "warning"
    assert "duplicate_patient_visit" in patient_flags["flags"]


def test_non_positive_intervals_are_reported():
    df = make_dataframe([
        valid_row(
            patient_id="P050",
            date="2026-01-10",
            visit="V1",
        ),
        valid_row(
            patient_id="P050",
            date="2026-01-10",
            visit="V2",
        ),
        valid_row(
            patient_id="P050",
            date="2026-04-10",
            visit="V3",
        ),
    ])

    report = build_data_quality_report(df)

    assert report["status"] == "warning"

    assert report["checks"]["non_positive_intervals"] >= 1

    patient_flags = report["patient_flags"]["P050"]

    assert patient_flags["quality_status"] == "warning"
    assert "non_positive_interval" in patient_flags["flags"]


def test_missing_numeric_values_are_reported():
    df = make_dataframe([
        valid_row(
            patient_id="P060",
            date="2026-01-10",
            visit="V1",
            egfr=None,
            uacr=None,
        ),
        valid_row(
            patient_id="P060",
            date="2026-04-10",
            visit="V2",
        ),
    ])

    report = build_data_quality_report(df)

    assert report["status"] == "warning"

    missing_numeric = report["checks"]["missing_numeric_values"]

    assert missing_numeric["egfr"] == 1
    assert missing_numeric["uacr"] == 1

    patient_flags = report["patient_flags"]["P060"]

    assert patient_flags["quality_status"] == "warning"
    assert "missing_egfr" in patient_flags["flags"]
    assert "missing_uacr" in patient_flags["flags"]


def test_invalid_numeric_values_are_reported():
    df = make_dataframe([
        valid_row(
            patient_id="P070",
            date="2026-01-10",
            visit="V1",
            egfr="invalid",
            creatinine="not-a-number",
        ),
        valid_row(
            patient_id="P070",
            date="2026-04-10",
            visit="V2",
        ),
    ])

    report = build_data_quality_report(df)

    assert report["status"] == "warning"

    invalid_numeric = report["checks"]["invalid_numeric_values"]

    assert invalid_numeric["egfr"] == 1
    assert invalid_numeric["creatinine"] == 1

    patient_flags = report["patient_flags"]["P070"]

    assert patient_flags["quality_status"] == "warning"
    assert "invalid_egfr" in patient_flags["flags"]
    assert "invalid_creatinine" in patient_flags["flags"]


def test_visit_count_distribution_is_reported():
    df = make_dataframe([
        # P080 -> 2 records
        valid_row("P080", "2026-01-10", "V1"),
        valid_row("P080", "2026-04-10", "V2"),

        # P081 -> 3 records
        valid_row("P081", "2026-01-10", "V1"),
        valid_row("P081", "2026-04-10", "V2"),
        valid_row("P081", "2026-07-10", "V3"),

        # P082 -> 4 records
        valid_row("P082", "2026-01-10", "V1"),
        valid_row("P082", "2026-04-10", "V2"),
        valid_row("P082", "2026-07-10", "V3"),
        valid_row("P082", "2026-10-10", "V4"),
    ])

    report = build_data_quality_report(df)

    distribution = report["summary"]["visit_count_distribution"]

    assert distribution["2"] == 1
    assert distribution["3"] == 1
    assert distribution["4"] == 1

    assert report["summary"]["patient_count"] == 3
    assert report["summary"]["record_count"] == 9


def test_patient_level_quality_flags_are_visible():
    df = make_dataframe([
        valid_row(
            patient_id="P090",
            date="2026-01-10",
            visit="V1",
        ),
        valid_row(
            patient_id="P090",
            date="2026-01-10",
            visit="V1",
            egfr=None,
        ),
    ])

    report = build_data_quality_report(df)

    assert report["status"] == "warning"

    assert report["summary"]["patients_with_quality_warnings"] == 1

    assert "P090" in report["patient_flags"]

    patient = report["patient_flags"]["P090"]

    assert patient["quality_status"] == "warning"

    assert "duplicate_patient_date" in patient["flags"]
    assert "duplicate_patient_visit" in patient["flags"]
    assert "missing_egfr" in patient["flags"]

    assert patient["number_of_records"] == 2
    assert patient["number_of_valid_dates"] == 2
    assert patient["number_of_valid_visits"] == 2