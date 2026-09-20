# Healthcare Digital Twin — Change Log

## Project
Healthcare Digital Twin Platform — Kidney Deterioration Pilot

## Current milestone
Reusable Longitudinal Healthcare Data & Intelligence Engine

## 1. Purpose

The prototype was developed as a reusable longitudinal healthcare data/intelligence engine using kidney deterioration as the first use case.

The engine focuses on understanding how patient measurements change across repeated observations rather than functioning as a standalone kidney-risk calculator.

Current tracked parameters:

- eGFR
- Serum Creatinine
- UACR
- Systolic BP
- Diastolic BP
- HbA1c

The architecture is designed so additional parameters and future disease modules can be added without rebuilding the longitudinal processing layer.

---

## 2. Data ingestion

Supported input formats:

- CSV
- XLSX
- XLS

The ingestion layer:

- maps supported source column names to the canonical schema;
- supports the DSC longitudinal workbook structure;
- sorts observations chronologically;
- preserves repeated patient observations;
- validates dates, visits, patient identifiers and numeric fields.

Canonical fields include:

```text
patient_id
date
visit
egfr
creatinine
uacr
systolic_bp
diastolic_bp
hba1c
```

---

## 3. Data-quality checks

The system now provides dataset-level and patient-level quality information.

Checks include:

- missing or invalid patient IDs;
- missing or invalid visit numbers;
- invalid dates;
- duplicate patient-date records;
- duplicate patient-visit records;
- non-positive intervals;
- missing numeric values;
- invalid numeric values;
- patient-level quality flags;
- incomplete follow-up.

Quality issues are surfaced rather than silently hidden.

For patients with insufficient longitudinal history, features that cannot be calculated are explicitly marked as unavailable.

---

## 4. Longitudinal change calculations

For each parameter, the engine calculates:

- previous value;
- absolute change;
- percentage change;
- direction;
- days since previous observation;
- rate of change per day.

Intervals are calculated using the actual observation dates rather than assuming equal spacing between visits.

Zero-baseline percentage changes are handled as unavailable rather than producing an invalid percentage.

---

## 5. Trend detection

The engine detects longitudinal directional behavior using repeated observations.

Supported trend states include:

- increasing;
- decreasing;
- stable;
- insufficient data where a trend cannot be calculated.

The engine counts:

- increasing steps;
- decreasing steps;
- stable steps;

and determines the dominant longitudinal direction.

---

## 6. Worsening signal detection

The prototype contains configurable worsening-direction assumptions for the current kidney pilot:

| Parameter | Configured prototype direction |
|---|---|
| eGFR | decreasing |
| Creatinine | increasing |
| UACR | increasing |
| Systolic BP | increasing |
| Diastolic BP | increasing |
| HbA1c | increasing |

These directions are prototype/domain configuration and are not presented as clinical decision rules.

Clinical thresholds and clinical decision rules require validation/input from the DSC team.

The engine reports:

- worsening parameter;
- expected worsening direction;
- number of worsening transitions;
- total transitions;
- consistency;
- overall change.

---

## 7. Concurrent / co-worsening detection

The engine checks whether multiple parameters move in their configured worsening directions during the same transition.

The output includes:

- detected concurrent worsening;
- transition information;
- affected parameters;
- number of worsening parameters per transition.

This allows the system to identify multi-signal longitudinal patterns rather than treating every parameter independently.

---

## 8. Longitudinal statistical feature engine

The feature engine now produces patient-level statistical features for each tracked parameter:

- baseline;
- latest;
- absolute change;
- percentage change;
- slope per day;
- slope per year;
- variability;
- average rate per day;
- acceleration;
- trend.

Feature availability is explicitly tied to the number of valid observations.

Unavailable features are represented with:

```text
value: null
status: not_calculable
reason: <explanation>
```

They are not converted to zero.

The feature calculations are statistical longitudinal features and should not be interpreted as diagnosis, prognosis, treatment effect, or causal inference.

---

## 9. Incomplete follow-up handling

Patients with fewer than the required number of observations are flagged for incomplete follow-up.

The system identifies longitudinal features that require more history.

For example:

- slope requires at least two valid observations;
- variability requires at least two valid observations;
- acceleration requires at least four valid observations.

This prevents insufficient history from being silently treated as a valid zero or stable value.

---

## 10. Reusable patient-level feature table

A dedicated feature-table module was added.

The table provides one row per patient and exposes longitudinal features in a flat structure suitable for downstream modules.

The table includes:

- patient ID;
- number of visits;
- longitudinal features for each tracked parameter;
- worsening signal count;
- worsening parameters;
- co-worsening status;
- co-worsening transition count;
- quality flag count;
- quality flags.

This table is intended to be consumed by later prediction, explainability and healthcare-economic modules without requiring those modules to recalculate the longitudinal features.

---

## 11. Test dataset

The revised synthetic dataset contains:

- 83 patients;
- 319 longitudinal records.

Additional test cases cover:

- stable trajectory;
- improving trajectory;
- fluctuating measurements;
- gradual directional worsening;
- rapid directional worsening;
- irregular observation intervals;
- missing visit;
- partial parameter data;
- incomplete follow-up cases.

The dataset was used to validate edge cases and longitudinal behavior.

---

## 12. Automated testing

Automated tests cover:

- longitudinal observation requirements;
- duplicate dates;
- irregular intervals;
- zero-baseline handling;
- missing parameter observations;
- missing all observations;
- stable behavior;
- improving behavior;
- mixed behavior;
- gradual worsening;
- rapid worsening;
- expected versus actual trend behavior;
- data-quality checks;
- patient feature-table construction.

Current test suite:

```text
32 passed
0 failed
```

---

## 13. API output

The `/analyze` endpoint now provides:

- patients analyzed;
- records processed;
- file name;
- dataset-level quality report;
- patient-level analysis results;
- patient-level feature table;
- analysis ID for feature-table export.

The feature table can therefore be consumed programmatically by later modules.

---

## 14. Feature-table export

The calculated patient-level feature table can be downloaded without recalculating the longitudinal analysis.

Available exports:

```text
GET /feature-table/{analysis_id}/csv
GET /feature-table/{analysis_id}/xlsx
```

The Excel export provides a patient-level table suitable for downstream analysis and integration.

The frontend now exposes:

- Download CSV;
- Download Excel.

The deployed frontend and backend have been tested together successfully.

---

## 15. Frontend integration

The frontend currently provides:

- dataset upload;
- patient selection;
- patient timeline;
- parameter trends;
- longitudinal technical feature summary;
- worsening signals;
- concurrent worsening;
- explanations;
- parameter evidence;
- incomplete follow-up warnings;
- patient feature-table export.

The frontend is connected to the deployed FastAPI backend.

---

## 16. Clinical-rule status

Clinical thresholds and clinical decision rules have deliberately not been hard-coded into the prototype.

Current API status:

```text
applied: false
```

The system explicitly communicates that clinical thresholds and decision rules require input from the DSC team.

This separation keeps the current engine focused on longitudinal data intelligence rather than making unsupported clinical decisions.

---

## 17. Known prototype limitations

1. Clinical thresholds and decision rules are not yet implemented.
2. The current worsening directions are configurable prototype assumptions and require DSC validation.
3. Statistical longitudinal features do not establish causality.
4. The current engine does not claim diagnosis or prognosis.
5. Prediction of future eGFR or deterioration probability is not yet part of this milestone.
6. The temporary export cache is in-memory and therefore is suitable for the current POC deployment rather than production-grade persistent storage.
7. The current dataset is synthetic/test data.

---

## 18. Ready for next module

The current milestone provides a reusable longitudinal intelligence layer that can serve as input to future modules.

The next development stage can build on the generated patient-level feature table for:

- future trajectory prediction;
- 3/6/12-month forecasting;
- deterioration probability modelling;
- explainable feature contribution;
- uncertainty reporting;
- scenario analysis;
- clinical and HEOR/resource-use modules.

These future modules should consume the existing longitudinal features rather than duplicate the underlying calculations.

---

## 19. Current completion summary

```text
Longitudinal ingestion                 DONE
Timeline generation                    DONE
Change calculations                    DONE
Trend detection                        DONE
Worsening signal detection             DONE
Concurrent worsening                  DONE
Longitudinal statistical features      DONE
Unavailable feature handling           DONE
Data-quality reporting                 DONE
Incomplete follow-up handling          DONE
Synthetic test dataset                 DONE
Automated tests                         DONE (32/32)
Patient-level feature table             DONE
CSV export                              DONE
Excel export                            DONE
Frontend export integration             DONE
Backend deployment                      DONE
Frontend/backend integration            DONE
```

## 20. Scope boundary

This milestone intentionally stops at the longitudinal intelligence layer.

It does not yet implement:

- clinical diagnosis;
- treatment recommendations;
- clinical decision thresholds;
- causal claims;
- validated future-risk prediction;
- a complete clinical digital twin.

Those capabilities require additional clinical validation, modelling, validation datasets and DSC-defined rules.
