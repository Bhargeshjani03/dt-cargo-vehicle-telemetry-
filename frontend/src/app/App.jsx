import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";
import AnomalyPage from "../features/anomalies/AnomalyPage";
import "../App.css";
import ValidationPage from "../features/regression/ValidationPage";
import TrackAnalyticsPage from "../features/tracks/TrackAnalyticsPage";
import OperationalInsightsPage from "../features/insights/OperationalInsightsPage";
import VehicleIntelligencePage from "../features/vehicles/VehicleIntelligencePage";
import MethodologyPage from "../features/methodology/MethodologyPage";
// ==========================================
// FLEET DATA
// ==========================================

const fleetTests = [
  { id: 1, tracks: 40048, vehicles: 18, tours: 2976 },
  { id: 2, tracks: 12089, vehicles: 5, tours: 1362 },
  { id: 3, tracks: 22933, vehicles: 12, tours: 2326 },
  { id: 4, tracks: 26860, vehicles: 18, tours: 1654 },
  { id: 5, tracks: 25020, vehicles: 13, tours: 4517 },
  { id: 6, tracks: 24648, vehicles: 97, tours: 611 },
];

const formatNumber = (number) => number.toLocaleString("en-IN");

// ==========================================
// REUSABLE COMPONENTS
// ==========================================

function StatCard({ label, value, detail, icon }) {
  return (
    <div className="dt-stat-card">
      <div className="dt-stat-top">
        <span className="dt-stat-label">{label}</span>
        <span className="dt-stat-icon">{icon}</span>
      </div>

      <div className="dt-stat-value">{value}</div>
      <div className="dt-stat-detail">{detail}</div>
    </div>
  );
}

function SectionHeading({ eyebrow, title, description }) {
  return (
    <div className="dt-section-heading">
      <div>
        {eyebrow && <div className="dt-eyebrow">{eyebrow}</div>}

        <h2>{title}</h2>

        {description && <p>{description}</p>}
      </div>
    </div>
  );
}

// ==========================================
// FLEET DISTRIBUTION
// ==========================================

function FleetDistribution() {
  const maxTracks = Math.max(...fleetTests.map((fleet) => fleet.tracks));

  return (
    <div className="dt-panel">
      <div className="dt-panel-heading">
        <div>
          <h3>Fleet test distribution</h3>
          <p>Track distribution across the six fleet test groups</p>
        </div>

        <span className="dt-panel-tag">6 TESTS</span>
      </div>

      <div className="dt-fleet-list">
        {fleetTests.map((fleet) => (
          <div className="dt-fleet-row" key={fleet.id}>
            <div className="dt-fleet-label">
              <span>Test {fleet.id}</span>
              <strong>{formatNumber(fleet.tracks)}</strong>
            </div>

            <div className="dt-progress-track">
              <div
                className="dt-progress-fill"
                style={{
                  width: `${(fleet.tracks / maxTracks) * 100}%`,
                }}
              />
            </div>

            <div className="dt-fleet-meta">
              <span>{fleet.vehicles} vehicles</span>
              <span>{formatNumber(fleet.tours)} tours</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==========================================
// DATASET COVERAGE
// ==========================================

function DatasetCoverage() {
  return (
    <div className="dt-panel">
      <div className="dt-panel-heading">
        <div>
          <h3>Dataset coverage</h3>
          <p>Telemetry collection periods</p>
        </div>

        <span className="dt-panel-tag">2021–2024</span>
      </div>

      <div className="dt-coverage-list">
        <div className="dt-coverage-item">
          <div className="dt-coverage-info">
            <strong>August 2021 – October 2022</strong>
            <span>126,950 tracks · 83.7%</span>
          </div>

          <div className="dt-progress-track">
            <div className="dt-progress-fill" style={{ width: "83.7%" }} />
          </div>
        </div>

        <div className="dt-coverage-item">
          <div className="dt-coverage-info">
            <strong>September 2023 – February 2024</strong>
            <span>24,648 tracks · 16.3%</span>
          </div>

          <div className="dt-progress-track">
            <div
              className="dt-progress-fill dt-progress-secondary"
              style={{ width: "16.3%" }}
            />
          </div>
        </div>
      </div>

      <div className="dt-insight-note">
        <span className="dt-note-icon">i</span>

        <p>
          The dataset has episodic collection periods. Gaps between periods
          should not automatically be interpreted as missing telemetry.
        </p>
      </div>
    </div>
  );
}

// ==========================================
// ANALYTICS PIPELINE
// ==========================================

function PipelineStep({ number, title, description, type }) {
  return (
    <div className={`dt-pipeline-step ${type || ""}`}>
      <span className="dt-step-number">{number}</span>

      <div>
        <h4>{title}</h4>
        <p>{description}</p>
      </div>
    </div>
  );
}

function AnalyticsPipeline() {
  return (
    <div className="dt-panel">
      <div className="dt-panel-heading">
        <div>
          <h3>Analytics pipeline</h3>
          <p>How raw telemetry becomes operational intelligence</p>
        </div>

        <span className="dt-panel-tag">METHODOLOGY</span>
      </div>

      <div className="dt-pipeline">
        <PipelineStep
          number="01"
          title="Raw telemetry"
          description="Track records, vehicle metadata and speed observations."
        />

        <PipelineStep
          number="02"
          title="Preprocessing & quality assessment"
          description="Validate telemetry, extract features and assess track quality."
        />

        <div className="dt-pipeline-branches">
          <div className="dt-pipeline-branch dt-track-branch">
            <div className="dt-branch-label">TRACK-LEVEL ANALYSIS</div>

            <PipelineStep
              number="03A"
              title="Movement clustering"
              description="K-Means groups tracks by movement characteristics."
            />

            <PipelineStep
              number="04A"
              title="Anomaly detection"
              description="Cluster-specific Isolation Forest identifies unusual tracks."
            />

            <div className="dt-branch-output">
              <strong>Track anomaly scores</strong>
              <span>Unusual movement patterns for investigation</span>
            </div>
          </div>

          <div className="dt-pipeline-branch dt-tour-branch">
            <div className="dt-branch-label">TOUR-LEVEL ANALYSIS</div>

            <PipelineStep
              number="03B"
              title="Tour aggregation & clustering"
              description="Aggregate tracks into tours and group tour behaviour."
            />

            <PipelineStep
              number="04B"
              title="Duration regression"
              description="Decision Tree regression estimates elapsed tour span."
            />

            <div className="dt-branch-output">
              <strong>Tour duration estimates</strong>
              <span>Expected elapsed tour span for analysis</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// OVERVIEW PAGE
// ==========================================

function OverviewPage() {
  return (
    <div className="dt-overview">
      <section className="dt-welcome">
        <div className="dt-eyebrow">FLEET INTELLIGENCE PLATFORM</div>

        <div className="dt-welcome-title-row">
          <div>
            <h1>Understand your fleet. Improve your operations.</h1>

            <p>
              Explore vehicle telemetry, identify unusual movement patterns and
              analyse tour behaviour through data-driven intelligence.
            </p>
          </div>

          <div className="dt-version-card">
            <span>PLATFORM VERSION</span>
            <strong>DT-CARGO v2.0</strong>
            <small>Vehicle telemetry intelligence</small>
          </div>
        </div>
      </section>

      <section className="dt-stats-grid">
        <StatCard
          label="Total tracks"
          value="151,598"
          detail="Telemetry track records"
          icon="↗"
        />

        <StatCard
          label="Vehicles"
          value="163"
          detail="Unique tracked vehicles"
          icon="▣"
        />

        <StatCard
          label="Tours"
          value="13,444"
          detail="Unique tour identifiers"
          icon="⇄"
        />

        <StatCard
          label="Fleet tests"
          value="6"
          detail="Distinct fleet_test_id groups"
          icon="▤"
        />
      </section>

      <section className="dt-dashboard-grid">
        <FleetDistribution />
        <DatasetCoverage />
      </section>

      <section className="dt-pipeline-section">
        <SectionHeading
          eyebrow="FROM DATA TO DECISIONS"
          title="How DT-CARGO works"
          description="Two analytical paths built on a shared telemetry preprocessing foundation."
        />

        <AnalyticsPipeline />
      </section>

      <section className="dt-bottom-grid">
        <div className="dt-panel">
          <div className="dt-panel-heading">
            <div>
              <h3>Dataset observations</h3>
              <p>Important characteristics identified during EDA</p>
            </div>
          </div>

          <div className="dt-observation-list">
            <div className="dt-observation">
              <span className="dt-observation-icon">↗</span>

              <div>
                <strong>88 multi-vehicle tours</strong>
                <p>Some tours contain tracks from multiple vehicles.</p>
              </div>
            </div>

            <div className="dt-observation">
              <span className="dt-observation-icon">◷</span>

              <div>
                <strong>9 negative-duration records</strong>
                <p>Flagged for duration-dependent calculations.</p>
              </div>
            </div>

            <div className="dt-observation">
              <span className="dt-observation-icon">⌁</span>

              <div>
                <strong>Variable track coverage</strong>
                <p>
                  Vehicles have uneven numbers of tracks and observation
                  periods.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="dt-panel dt-platform-panel">
          <div className="dt-platform-logo">DT</div>

          <div className="dt-eyebrow">PROJECT WORKSPACE</div>

          <h3>DT-CARGO v2.0</h3>

          <p>
            A vehicle telemetry analysis platform designed to support
            fleet-operation understanding through machine learning.
          </p>

          <div className="dt-platform-footer">
            <span className="dt-status-dot" />
            Local development environment
          </div>
        </div>
      </section>

      <footer className="dt-footer">
        <span>DT-CARGO · Vehicle Telemetry Intelligence</span>
        <span>Version 2.0</span>
      </footer>
    </div>
  );
}

// ==========================================
// APPLICATION ROUTING
// ==========================================

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          {/* Default route */}
          <Route path="/" element={<Navigate to="/overview" replace />} />

          {/* Operational Intelligence */}
          <Route path="/overview" element={<OverviewPage />} />

          <Route path="/anomalies" element={<AnomalyPage />} />
          <Route
            path="/regression"
            element={<Navigate to="/regression/validation" replace />}
          />
          <Route path="/regression/validation" element={<ValidationPage />} />

          <Route path="/vehicles" element={<VehicleIntelligencePage />} />

          <Route path="/tracks" element={<TrackAnalyticsPage />} />

          <Route
            path="/data-quality"
            element={<MethodologyPage module="quality" />}
          />

          {/* Project Methodology */}
          <Route
            path="/methodology/eda"
            element={<MethodologyPage module="eda" />}
          />

          <Route
            path="/methodology/preprocessing"
            element={<MethodologyPage module="preprocessing" />}
          />

          <Route
            path="/methodology/clustering"
            element={<MethodologyPage module="clustering" />}
          />

          <Route
            path="/methodology/models"
            element={<MethodologyPage module="models" />}
          />

          <Route
            path="/methodology/evaluation"
            element={<MethodologyPage module="evaluation" />}
          />
          {/* Unknown routes */}
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Route>
        <Route path="/insights" element={<OperationalInsightsPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
