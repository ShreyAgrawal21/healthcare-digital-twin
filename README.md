Healthcare Digital Twin Platform -- Kidney Pilot

A proof-of-concept (POC) longitudinal healthcare data intelligence
engine focused on kidney deterioration patterns.

Overview

The Kidney Pilot is designed to understand how patient measurements
change over time across repeated visits. Instead of acting as a
standalone kidney-risk calculator, the prototype builds a longitudinal
patient timeline, calculates changes between visits, detects parameter
trends, identifies multiple worsening signals occurring together, and
provides a structured explanation of the observed pattern.

POC scope: This prototype is intended for synthetic/test data and
demonstration purposes. It is not a clinical decision-support system
and does not provide diagnosis, treatment recommendations, or future
clinical predictions.

Problem

Longitudinal healthcare data can contain several measurements whose
individual changes are difficult to interpret together. For example, a
patient's eGFR may decrease while UACR and systolic blood pressure
increase over several visits.

The prototype is intended to answer:

What changed over time?

Which parameters are moving consistently?

Which signals are worsening together?

Why was a patient flagged?

Current POC Capabilities

Data ingestion

CSV upload

Excel .xlsx upload

Excel .xls upload

Required-column validation

Date validation

Numeric-field validation

Empty-file validation

Longitudinal analysis

Patient-wise grouping

Chronological patient timeline

Previous value

Absolute change

Percentage change

Direction of change

Rate of change per day

Parameter-level trend detection

Pattern detection

Consistent worsening-signal detection

Concurrent/co-worsening detection across the same visit transition

Patient-level classification:

Multiple Worsening Signals

Stable Pattern

Mixed / Inconsistent Pattern

Explainability

Patient summary

Contributing parameters

Observed changes

Concurrent worsening evidence

Parameter evidence over time

Explicit clinical-rules disclaimer

Technology Stack

Backend

Python

FastAPI

Pandas

Pydantic

Uvicorn

openpyxl

Frontend

Next.js

React

TypeScript

CSS

Project Structure

healthcare-digital-twin/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── analyzer.py
│   │   └── config.py
│   │
│   ├── data/
│   │   └── kidney_patients.csv
│   │
│   ├── requirements.txt
│   └── README.md
│
└── frontend/
    ├── src/
    │   └── app/
    │       ├── page.tsx
    │       └── globals.css
    └── package.json

Data Schema

The current Kidney Pilot expects the following canonical fields:

Field            Description

patient_id     Unique patient identifier
date           Visit/measurement date
visit          Visit number
egfr           eGFR measurement
creatinine     Serum creatinine
uacr           UACR measurement
systolic_bp    Systolic blood pressure
diastolic_bp   Diastolic blood pressure
hba1c          HbA1c measurement

Additional variables can be incorporated in future disease modules
without changing the overall longitudinal-engine architecture.

Example Longitudinal Pattern

Example patient:

eGFR:          72 → 65 → 58 → 50
UACR:          30 → 55 → 100 → 160
Systolic BP:  132 → 139 → 146 → 151

The engine can identify that:

eGFR is decreasing

UACR is increasing

systolic BP is increasing

multiple signals are moving in their configured worsening directions

some of these changes occur concurrently across visit transitions

The system reports the observed pattern rather than making a diagnosis
or predicting a clinical outcome.

Running the Backend

From the backend directory:

Create virtual environment

python -m venv venv

Activate on Windows

venv\Scripts\activate

Install dependencies

pip install -r requirements.txt

If openpyxl is not already present:

pip install openpyxl

Start FastAPI

uvicorn app.main:app --reload

Backend:

http://127.0.0.1:8000

Swagger documentation:

http://127.0.0.1:8000/docs

Running the Frontend

From the frontend directory:

npm install
npm run dev

Frontend:

http://localhost:3000

The frontend sends uploaded patient files to:

POST http://127.0.0.1:8000/analyze

How to Use

Start the FastAPI backend.

Start the Next.js frontend.

Open the frontend in a browser.

Select a CSV or Excel patient dataset.

Click Analyze Patient Data.

Select a patient from the patient list.

Review:

patient status

longitudinal timeline

parameter trends

worsening signals

concurrent worsening

explanation

parameter evidence

clinical-rules status

Testing

The prototype has been tested with synthetic longitudinal patient data
containing:

P001 -- Worsening pattern

Multiple parameters progressively move in configured worsening
directions.

P002 -- Stable pattern

Tracked measurements remain unchanged across visits.

P003 -- Mixed/inconsistent pattern

Parameters fluctuate across visits without a consistent multi-parameter
worsening pattern.

Both CSV and Excel ingestion have been tested through the backend and
frontend.

Architecture

              CSV / Excel
                   │
                   ▼
          ┌─────────────────┐
          │ Data Ingestion  │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Data Validation │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Patient Timeline│
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Change Engine   │
          │ Δ / % / Rate    │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Trend Detection │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Multi-Signal    │
          │ Pattern Engine  │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Explainability  │
          └────────┬────────┘
                   │
                   ▼
                Frontend

Design Approach

The prototype separates reusable longitudinal analysis functions from
disease-specific configuration.

Core engine responsibilities include:

ingestion

timeline construction

change calculation

trend detection

structured pattern detection

explanation

Kidney-specific parameters and worsening-direction configuration are
currently provided through configuration.

This structure is intended to support future disease modules without
rebuilding the entire engine.

Clinical Safety / Scope

This POC deliberately does not:

diagnose disease

recommend treatment

predict future clinical outcomes

simulate treatment effects

apply unvalidated clinical thresholds

function as a complete clinical digital twin

Clinical thresholds and clinical decision rules require domain/clinical
validation before they are introduced.

Future Development

The broader platform can later support:

risk prediction

model validation

3/6/12-month trajectory estimation

explainable AI / feature contribution

scenario simulation

additional disease modules

clinical and HEOR-oriented modules

These are outside the current first-stage POC.

Disclaimer

This software is a prototype for synthetic/test healthcare data and
technical demonstration. It should not be used for patient care,
diagnosis, treatment decisions, or clinical decision-making.

Author / Project

Healthcare Digital Twin Platform -- Kidney Pilot

Developed as a proof-of-concept longitudinal healthcare data
intelligence engine.