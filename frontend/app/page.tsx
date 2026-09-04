"use client";

import { useState } from "react";

interface TimelineItem {
  date: string;
  visit: number;
  [key: string]: string | number | null;
}

interface TrendData {
  trend: string;
  increasing_steps: number;
  decreasing_steps: number;
  stable_steps: number;
}

interface WorseningSignal {
  parameter: string;
  name: string;
  expected_worsening_direction: string;
  worsening_steps: number;
  total_transitions: number;
  consistency: number;
  overall_change: number;
}

interface Explanation {
  type: string;
  parameter?: string;
  message: string;
  from_visit?: number;
  to_visit?: number;
}

interface PatientResult {
  patient_id: string;
  number_of_visits: number;
  timeline: TimelineItem[];
  trends: Record<string, TrendData>;

  worsening_signal_count: number;
  worsening_signals: WorseningSignal[];

  co_worsening_analysis: {
    co_worsening_detected: boolean;
    co_worsening_transitions: {
      from_visit: number;
      to_visit: number;
      from_date: string;
      to_date: string;
      worsening_parameters: {
        parameter: string;
        name: string;
        change: number;
      }[];
      worsening_parameter_count: number;
    }[];
  };

  overall_status: string;

  patient_summary: {
    patient_id: string;
    summary: string;
  };

  parameter_evidence: {
    parameter: string;
    name: string;
    configured_worsening_direction: string;
    values_over_time: number[];
    first_value: number;
    last_value: number;
    overall_change: number;
  }[];

  explanation: Explanation[];

  clinical_rules_status: {
    applied: boolean;
    message: string;
  };
}

interface AnalysisResponse {
  patients_analyzed: number;
  records_processed?: number;
  file_name?: string;
  results: PatientResult[];
}

const parameterNames: Record<string, string> = {
  egfr: "eGFR",
  creatinine: "Serum Creatinine",
  uacr: "UACR",
  systolic_bp: "Systolic BP",
  diastolic_bp: "Diastolic BP",
  hba1c: "HbA1c",
};

const parameterUnits: Record<string, string> = {
  egfr: "mL/min/1.73m²",
  creatinine: "mg/dL",
  uacr: "mg/g",
  systolic_bp: "mmHg",
  diastolic_bp: "mmHg",
  hba1c: "%",
};

function formatParameter(parameter: string) {
  return (
    parameterNames[parameter] ||
    parameter.replaceAll("_", " ")
  );
}

function getTrendSymbol(trend: string) {
  if (trend === "increasing") return "↑";
  if (trend === "decreasing") return "↓";
  if (trend === "stable") return "→";
  return "—";
}

function getTrendClass(trend: string) {
  if (trend === "increasing") return "trend-up";
  if (trend === "decreasing") return "trend-down";
  if (trend === "stable") return "trend-stable";
  return "";
}

/*
 * ---------------------------------------------------------
 * Patient classification
 * ---------------------------------------------------------
 *
 * This classification is intentionally based on the
 * longitudinal pattern detected by the engine.
 *
 * Multiple worsening signals:
 *   - At least 2 consistently worsening parameters
 *   - AND concurrent worsening detected
 *
 * Stable:
 *   - Every tracked parameter has a stable trend
 *
 * Mixed / inconsistent:
 *   - Changes exist, but there is no consistent
 *     multi-parameter worsening pattern
 */
function getPatientClassification(patient: PatientResult) {
  if (
    patient.worsening_signal_count >= 2 &&
    patient.co_worsening_analysis.co_worsening_detected
  ) {
    return {
      label: "Multiple Worsening Signals",
      shortLabel: "Worsening pattern",
      className: "warning-badge",
      icon: "⚠",
    };
  }

  const trendValues = Object.values(patient.trends);

  const isStable =
    trendValues.length > 0 &&
    trendValues.every(
      (trend) => trend.trend === "stable"
    );

  if (isStable) {
    return {
      label: "Stable Pattern",
      shortLabel: "Stable pattern",
      className: "stable-badge",
      icon: "✓",
    };
  }

  return {
    label: "Mixed / Inconsistent Pattern",
    shortLabel: "Mixed / inconsistent",
    className: "stable-badge",
    icon: "↔",
  };
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);

  const [data, setData] =
    useState<AnalysisResponse | null>(null);

  const [selectedPatient, setSelectedPatient] =
    useState<string>("");

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");

  /*
   * -------------------------------------------------------
   * File selection
   * -------------------------------------------------------
   */

  function handleFileChange(
    event: React.ChangeEvent<HTMLInputElement>
  ) {
    const selectedFile =
      event.target.files?.[0] || null;

    if (!selectedFile) {
      setFile(null);
      return;
    }

    const allowedExtensions = [
      ".csv",
      ".xlsx",
      ".xls",
    ];

    const fileName =
      selectedFile.name.toLowerCase();

    const isValidFile =
      allowedExtensions.some((extension) =>
        fileName.endsWith(extension)
      );

    if (!isValidFile) {
      setFile(null);

      setError(
        "Please upload a CSV or Excel file (.csv, .xlsx, .xls)."
      );

      return;
    }

    setFile(selectedFile);
    setError("");
  }

  /*
   * -------------------------------------------------------
   * Analyze file
   * -------------------------------------------------------
   */

  async function analyzeFile() {
    if (!file) {
      setError(
        "Please select a CSV or Excel file first."
      );

      return;
    }

    setLoading(true);
    setError("");

    const formData = new FormData();

    formData.append("file", file);

    try {
      const response = await fetch(
        "https://YOUR-RENDER-URL.onrender.com/analyze",
        {
          method: "POST",
          body: formData,
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.detail?.message ||
            result.detail ||
            "Analysis failed."
        );
      }

      setData(result);

      if (result.results.length > 0) {
        setSelectedPatient(
          result.results[0].patient_id
        );
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to backend."
      );
    } finally {
      setLoading(false);
    }
  }

  /*
   * -------------------------------------------------------
   * Selected patient
   * -------------------------------------------------------
   */

  const patient = data?.results.find(
    (item) =>
      item.patient_id === selectedPatient
  );

  /*
   * -------------------------------------------------------
   * Render
   * -------------------------------------------------------
   */

  return (
    <main className="page">

      {/* =================================================
          HEADER
      ================================================= */}

      <header className="header">

        <div>
          <p className="eyebrow">
            DIGITAL TWIN PLATFORM
          </p>

          <h1>
            Healthcare Digital Twin
          </h1>

          <p className="subtitle">
            Kidney Deterioration Pilot
          </p>
        </div>

        <div className="status-badge">
          <span className="status-dot" />
          Prototype
        </div>

      </header>


      {/* =================================================
          DATA UPLOAD
      ================================================= */}

      <section className="card upload-card">

        <div className="section-heading">

          <div>

            <p className="section-label">
              DATA INGESTION
            </p>

            <h2>
              Upload Patient Data
            </h2>

            <p>
              Upload synthetic longitudinal
              patient data in CSV or Excel format.
            </p>

          </div>

        </div>


        <div className="upload-area">

          <input
            id="file-upload"
            type="file"
            accept=".csv, .xlsx, .xls"
            onChange={handleFileChange}
          />

          <label htmlFor="file-upload">

            <span className="upload-icon">
              ↑
            </span>

            <strong>
              {file
                ? file.name
                : "Choose a CSV or Excel file"}
            </strong>

            <span>
              {file
                ? "File selected"
                : "Supported formats: .csv, .xlsx, .xls"}
            </span>

          </label>

        </div>


        {error && (
          <div className="error-box">
            {error}
          </div>
        )}


        <button
          className="primary-button"
          onClick={analyzeFile}
          disabled={loading}
        >
          {loading
            ? "Analyzing..."
            : "Analyze Patient Data"}
        </button>

      </section>


      {/* =================================================
          RESULTS
      ================================================= */}

      {data && (
        <>

          {/* ===============================================
              OVERVIEW
          =============================================== */}

          <section className="overview-grid">

            <div className="stat-card">

              <span>
                Patients Analyzed
              </span>

              <strong>
                {data.patients_analyzed}
              </strong>

            </div>


            <div className="stat-card">

              <span>
                Selected Patient
              </span>

              <strong>
                {selectedPatient}
              </strong>

            </div>


            <div className="stat-card">

              <span>
                Visits
              </span>

              <strong>
                {patient?.number_of_visits || 0}
              </strong>

            </div>


            <div className="stat-card">

              <span>
                Worsening Signals
              </span>

              <strong>
                {patient?.worsening_signal_count || 0}
              </strong>

            </div>

          </section>


          {/* ===============================================
              PATIENT SELECTOR
          =============================================== */}

          <section className="card">

            <div className="section-heading">

              <div>

                <p className="section-label">
                  PATIENT SELECTION
                </p>

                <h2>
                  Patients
                </h2>

              </div>

            </div>


            <div className="patient-list">

              {data.results.map(
                (result) => {

                  const classification =
                    getPatientClassification(
                      result
                    );

                  return (
                    <button
                      key={result.patient_id}
                      className={
                        selectedPatient ===
                        result.patient_id
                          ? "patient-button selected"
                          : "patient-button"
                      }
                      onClick={() =>
                        setSelectedPatient(
                          result.patient_id
                        )
                      }
                    >

                      <span>
                        {result.patient_id}
                      </span>

                      <small>
                        {
                          classification.shortLabel
                        }
                      </small>

                    </button>
                  );
                }
              )}

            </div>

          </section>


          {/* ===============================================
              SELECTED PATIENT
          =============================================== */}

          {patient && (
            <>

              {/* =============================================
                  PATIENT STATUS
              ============================================= */}

              <section className="card">

                <div className="patient-header">

                  <div>

                    <p className="section-label">
                      PATIENT ANALYSIS
                    </p>

                    <h2>
                      Patient{" "}
                      {patient.patient_id}
                    </h2>

                  </div>


                  {(() => {

                    const classification =
                      getPatientClassification(
                        patient
                      );

                    return (
                      <div
                        className={
                          classification.className
                        }
                      >

                        <span>
                          {classification.icon}
                        </span>

                        {classification.label}

                      </div>
                    );

                  })()}

                </div>


                <div className="status-message">
                  {patient.overall_status}
                </div>

              </section>


              {/* =============================================
                  TIMELINE
              ============================================= */}

              <section className="card">

                <div className="section-heading">

                  <div>

                    <p className="section-label">
                      LONGITUDINAL HISTORY
                    </p>

                    <h2>
                      Patient Timeline
                    </h2>

                    <p>
                      Measurements organized
                      chronologically by visit.
                    </p>

                  </div>

                </div>


                <div className="table-wrapper">

                  <table>

                    <thead>

                      <tr>

                        <th>
                          Parameter
                        </th>

                        {patient.timeline.map(
                          (visit) => (

                            <th
                              key={visit.visit}
                            >

                              <span>
                                Visit{" "}
                                {visit.visit}
                              </span>

                              <small>
                                {visit.date}
                              </small>

                            </th>

                          )
                        )}

                      </tr>

                    </thead>


                    <tbody>

                      {Object.keys(
                        parameterNames
                      ).map(
                        (parameter) => (

                          <tr
                            key={parameter}
                          >

                            <td>

                              <strong>
                                {formatParameter(
                                  parameter
                                )}
                              </strong>

                              <small>
                                {
                                  parameterUnits[
                                    parameter
                                  ]
                                }
                              </small>

                            </td>


                            {patient.timeline.map(
                              (visit) => (

                                <td
                                  key={visit.visit}
                                >

                                  {
                                    visit[
                                      parameter
                                    ] !== null &&
                                    visit[
                                      parameter
                                    ] !== undefined
                                      ? String(
                                          visit[
                                            parameter
                                          ]
                                        )
                                      : "—"
                                  }

                                </td>

                              )
                            )}

                          </tr>

                        )
                      )}

                    </tbody>

                  </table>

                </div>

              </section>


              {/* =============================================
                  TRENDS
              ============================================= */}

              <section className="card">

                <div className="section-heading">

                  <div>

                    <p className="section-label">
                      TREND ANALYSIS
                    </p>

                    <h2>
                      Parameter Trends
                    </h2>

                    <p>
                      Longitudinal direction
                      detected by the engine.
                    </p>

                  </div>

                </div>


                <div className="trend-grid">

                  {Object.entries(
                    patient.trends
                  ).map(
                    ([parameter, trend]) => (

                      <div
                        className="trend-card"
                        key={parameter}
                      >

                        <div>

                          <span className="trend-name">
                            {formatParameter(
                              parameter
                            )}
                          </span>

                          <span className="trend-unit">
                            {
                              parameterUnits[
                                parameter
                              ]
                            }
                          </span>

                        </div>


                        <div
                          className={
                            "trend-value " +
                            getTrendClass(
                              trend.trend
                            )
                          }
                        >

                          <span>
                            {getTrendSymbol(
                              trend.trend
                            )}
                          </span>

                          <span>
                            {trend.trend}
                          </span>

                        </div>


                        <div className="trend-details">

                          <span>
                            ↑{" "}
                            {
                              trend.increasing_steps
                            } increasing
                          </span>

                          <span>
                            ↓{" "}
                            {
                              trend.decreasing_steps
                            } decreasing
                          </span>

                          <span>
                            →{" "}
                            {
                              trend.stable_steps
                            } stable
                          </span>

                        </div>

                      </div>

                    )
                  )}

                </div>

              </section>


              {/* =============================================
                  WORSENING SIGNALS
              ============================================= */}

              <section className="card">

                <div className="section-heading">

                  <div>

                    <p className="section-label">
                      INTELLIGENCE ENGINE
                    </p>

                    <h2>
                      Worsening Signals
                    </h2>

                    <p>
                      Parameters consistently
                      moving in their configured
                      worsening direction.
                    </p>

                  </div>

                </div>


                {patient.worsening_signals
                  .length === 0 ? (

                  <div className="empty-state">
                    No consistently worsening
                    parameters detected.
                  </div>

                ) : (

                  <div className="signal-list">

                    {patient.worsening_signals.map(
                      (signal) => (

                        <div
                          className="signal-card"
                          key={signal.parameter}
                        >

                          <div className="signal-top">

                            <strong>
                              {signal.name}
                            </strong>

                            <span>
                              {Math.round(
                                signal.consistency *
                                  100
                              )}
                              % consistent
                            </span>

                          </div>


                          <div className="signal-details">

                            <span>
                              Direction:{" "}
                              {
                                signal.expected_worsening_direction
                              }
                            </span>

                            <span>
                              Worsening steps:{" "}
                              {
                                signal.worsening_steps
                              }
                              /
                              {
                                signal.total_transitions
                              }
                            </span>

                            <span>
                              Overall change:{" "}
                              {
                                signal.overall_change
                              }
                            </span>

                          </div>

                        </div>

                      )
                    )}

                  </div>

                )}

              </section>


              {/* =============================================
                  CONCURRENT WORSENING
              ============================================= */}

              <section className="card">

                <div className="section-heading">

                  <div>

                    <p className="section-label">
                      PATTERN DETECTION
                    </p>

                    <h2>
                      Concurrent Worsening
                    </h2>

                    <p>
                      Multiple parameters
                      moving in worsening
                      directions during the
                      same transition.
                    </p>

                  </div>

                </div>


                {patient
                  .co_worsening_analysis
                  .co_worsening_detected ? (

                  <div className="transition-list">

                    {patient
                      .co_worsening_analysis
                      .co_worsening_transitions
                      .map(
                        (transition) => (

                          <div
                            className="transition-card"
                            key={`${transition.from_visit}-${transition.to_visit}`}
                          >

                            <div className="transition-header">

                              <strong>
                                Visit{" "}
                                {
                                  transition.from_visit
                                }{" "}
                                →
                                Visit{" "}
                                {
                                  transition.to_visit
                                }
                              </strong>

                              <span>
                                {
                                  transition.worsening_parameter_count
                                }{" "}
                                parameters
                              </span>

                            </div>


                            <div className="signal-tags">

                              {transition
                                .worsening_parameters
                                .map(
                                  (item) => (

                                    <span
                                      key={
                                        item.parameter
                                      }
                                    >

                                      {item.name}{" "}
                                      (
                                      {item.change >
                                      0
                                        ? "+"
                                        : ""}
                                      {
                                        item.change
                                      }
                                      )

                                    </span>

                                  )
                                )}

                            </div>

                          </div>

                        )
                      )}

                  </div>

                ) : (

                  <div className="empty-state">
                    No concurrent multi-parameter
                    worsening transitions detected.
                  </div>

                )}

              </section>


              {/* =============================================
                  EXPLANATION
              ============================================= */}

              <section className="card explanation-card">

                <div className="section-heading">

                  <div>

                    <p className="section-label">
                      EXPLAINABILITY
                    </p>

                    <h2>
                      Why Was This Patient Flagged?
                    </h2>

                  </div>

                </div>


                <div className="summary-box">

                  {patient.patient_summary.summary
                    .split("\n")
                    .map(
                      (line, index) => (

                        <p key={index}>
                          {line}
                        </p>

                      )
                    )}

                </div>


                <div className="explanation-list">

                  {patient.explanation.map(
                    (item, index) => (

                      <div
                        className="explanation-item"
                        key={index}
                      >

                        <span className="explanation-icon">
                          ✓
                        </span>


                        <div>

                          <strong>
                            {item.parameter ||
                              "Pattern Evidence"}
                          </strong>

                          <p>
                            {item.message}
                          </p>

                        </div>

                      </div>

                    )
                  )}

                </div>

              </section>


              {/* =============================================
                  PARAMETER EVIDENCE
              ============================================= */}

              <section className="card">

                <div className="section-heading">

                  <div>

                    <p className="section-label">
                      EVIDENCE
                    </p>

                    <h2>
                      Parameter Evidence
                    </h2>

                  </div>

                </div>


                <div className="evidence-grid">

                  {patient.parameter_evidence.map(
                    (item) => (

                      <div
                        className="evidence-card"
                        key={item.parameter}
                      >

                        <strong>
                          {item.name}
                        </strong>


                        <div className="evidence-values">

                          {item.values_over_time.map(
                            (value, index) => (

                              <span
                                key={index}
                              >
                                {value}
                              </span>

                            )
                          )}

                        </div>


                        <div className="evidence-footer">

                          <span>
                            First:{" "}
                            {item.first_value}
                          </span>

                          <span>
                            Last:{" "}
                            {item.last_value}
                          </span>

                          <span>
                            Change:{" "}
                            {item.overall_change}
                          </span>

                        </div>

                      </div>

                    )
                  )}

                </div>

              </section>


              {/* =============================================
                  CLINICAL RULES
              ============================================= */}

              <section className="clinical-note">

                <div className="clinical-icon">
                  i
                </div>


                <div>

                  <strong>
                    Clinical Rules & Thresholds
                  </strong>

                  <p>
                    {
                      patient
                        .clinical_rules_status
                        .message
                    }
                  </p>

                </div>

              </section>

            </>
          )}

        </>
      )}

    </main>
  );
}