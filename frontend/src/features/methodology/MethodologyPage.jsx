
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

import "./methodology.css";

const modules = {
  eda: {
    eyebrow: "DATA UNDERSTANDING",
    title: "Exploratory Data Analysis",
    description:
      "Understand the structure, coverage, characteristics and limitations of the vehicle telemetry dataset before modelling.",
    stats: [
      ["151,598", "Track records"],
      ["163", "Vehicles"],
      ["13,444", "Tour identifiers"],
      ["6", "Fleet test groups"],
    ],
    sections: [
      {
        title: "Dataset structure",
        description:
          "The project combines track metadata, vehicle specifications and timestamped speed telemetry.",
        items: [
          ["tracks.csv", "151,598 records containing track, vehicle, tour, time, distance and speed information."],
          ["fleet.csv", "163 vehicles with fleet test and vehicle configuration information."],
          ["Speed telemetry", "Individual vehicle-track files containing epoch, speed and HDOP observations."],
        ],
      },
      {
        title: "Temporal coverage",
        description:
          "The dataset contains two distinct collection periods rather than continuous coverage.",
        items: [
          ["August 2021 – October 2022", "126,950 tracks · 83.7%"],
          ["September 2023 – February 2024", "24,648 tracks · 16.3%"],
        ],
      },
      {
        title: "Important observations",
        description: "Findings that influence downstream analysis.",
        items: [
          ["Multi-vehicle tours", "88 tours contain tracks from multiple vehicles. A tour is not necessarily a single-vehicle journey."],
          ["Duration anomalies", "Nine records have negative durations and require special handling."],
          ["Uneven coverage", "Track counts and observation periods differ across vehicles."],
          ["Telemetry consistency", "Track-level summary speeds may disagree with raw telemetry, so detailed investigation should use raw speed observations where available."],
        ],
      },
    ],
  },

  preprocessing: {
    eyebrow: "DATA PREPARATION",
    title: "Data Preprocessing",
    description:
      "Transform raw vehicle telemetry into quality-assessed track and tour datasets suitable for machine learning.",
    stats: [
      ["151,598", "Original tracks"],
      ["148,359", "Scored tracks"],
      ["3,239", "Unscored / unassigned"],
      ["163", "Vehicles"],
    ],
    sections: [
      {
        title: "Preprocessing workflow",
        items: [
          ["Data ingestion", "Load track metadata, fleet specifications and individual speed telemetry files."],
          ["Timestamp handling", "Parse timestamps consistently using UTC. Preserve invalid duration records for investigation rather than swapping timestamps."],
          ["Telemetry assessment", "Evaluate observation count, telemetry coverage, interval validity and metadata consistency."],
          ["Feature extraction", "Calculate raw speed statistics, low-speed time and stop episode counts."],
          ["Track preparation", "Retain eligible and eligible-with-warnings tracks for the applicable modelling workflow; exclude ineligible tracks."],
          ["Tour aggregation", "Aggregate track records by tour_id for separate tour-level analysis."],
        ],
      },
      {
        title: "Stop detection",
        items: [
          ["Low-speed threshold", "Speed at or below 0.3 m/s."],
          ["Interval continuity", "Consecutive low-speed observations must have a gap of at most 2 seconds."],
          ["Minimum duration", "A continuous low-speed period must last at least 30 seconds to count as a stop episode."],
        ],
      },
      {
        title: "Track movement features",
        items: [
          ["raw_speed_mean_kmh", "Mean speed derived from raw speed telemetry."],
          ["raw_speed_std", "Standard deviation of raw speed observations."],
          ["low_speed_time_pct_03", "Percentage of telemetry time at or below 0.3 m/s."],
          ["stop_episode_count_03", "Number of qualifying stop episodes."],
        ],
      },
    ],
  },

  clustering: {
    eyebrow: "UNSUPERVISED LEARNING",
    title: "Movement & Tour Clustering",
    description:
      "Separate track-level movement patterns from tour-level behavioural segmentation.",
    stats: [
      ["3", "Track movement clusters"],
      ["2", "Tour clusters"],
      ["4", "Track model features"],
      ["K-Means", "Clustering algorithm"],
    ],
    sections: [
      {
        title: "Track-level movement clustering",
        description:
          "K-Means groups tracks using raw telemetry-derived movement characteristics.",
        items: [
          ["Cluster 0 · Active Transit", "Higher-speed movement with comparatively lower low-speed time."],
          ["Cluster 1 · Stop-Dominant Movement", "Movement records with very high low-speed time."],
          ["Cluster 2 · Brief Near-Stationary Tracks", "Very short tracks with near-stationary movement characteristics."],
        ],
      },
      {
        title: "Track clustering features",
        items: [
          ["Mean raw speed", "raw_speed_mean_kmh"],
          ["Speed variability", "raw_speed_std"],
          ["Low-speed time", "low_speed_time_pct_03"],
          ["Stop episodes", "stop_episode_count_03"],
        ],
      },
      {
        title: "Tour-level clustering",
        description:
          "A separate K-Means workflow operates on aggregated tour-level information.",
        items: [
          ["Total distance", "total_distance_km"],
          ["Mean track speed", "mean_track_speed_kmh"],
          ["Maximum track speed", "max_track_speed_kmh"],
          ["Track count", "Optional clustering feature."],
        ],
      },
      {
        title: "Interpretation",
        items: [
          ["Separate analytical units", "Track clusters describe individual track movement; tour clusters describe aggregated tour behaviour."],
          ["Descriptive labels", "Cluster names summarise observed feature patterns. They are not independently verified operational states."],
        ],
      },
    ],
  },

  models: {
    eyebrow: "MACHINE LEARNING",
    title: "Model Development",
    description:
      "Two distinct modelling branches: track-level anomaly detection and tour-level elapsed-duration regression.",
    stats: [
      ["3", "Isolation Forest models"],
      ["300", "Trees per anomaly model"],
      ["1", "Tour regression model"],
      ["4", "Anomaly input features"],
    ],
    sections: [
      {
        title: "Track-level anomaly detection",
        description:
          "A separate Isolation Forest model is trained for each movement cluster.",
        items: [
          ["Algorithm", "Isolation Forest."],
          ["Model count", "Three cluster-specific models."],
          ["Estimators", "300 trees per model."],
          ["Model inputs", "Four raw telemetry-derived movement features."],
          ["Anomaly score", "Negative Isolation Forest decision_function. Higher scores indicate more unusual observations."],
          ["Thresholds", "Each movement cluster has its own threshold."],
        ],
      },
      {
        title: "Cluster-specific thresholds",
        items: [
          ["Cluster 0", "0.106925"],
          ["Cluster 1", "0.165261"],
          ["Cluster 2", "0.190944"],
        ],
      },
      {
        title: "Tour elapsed-span regression",
        description:
          "A separate Decision Tree regression workflow estimates elapsed tour span.",
        items: [
          ["Algorithm", "DecisionTreeRegressor."],
          ["Maximum depth", "10."],
          ["Minimum split samples", "10."],
          ["Minimum leaf samples", "5."],
          ["Random state", "42."],
          ["Target", "elapsed_span_hours, transformed using log1p for modelling and expm1 for prediction."],
        ],
      },
    ],
  },

  evaluation: {
    eyebrow: "MODEL VALIDATION",
    title: "Model Evaluation",
    description:
      "Assess inference coverage, anomaly flagging behaviour, prediction consistency and tour regression performance.",
    stats: [
      ["148,359", "Scored tracks"],
      ["4,185", "Flagged tracks"],
      ["2.82%", "Flag rate"],
      ["0", "Inference errors"],
    ],
    sections: [
      {
        title: "Anomaly inference results",
        items: [
          ["Scored population", "148,359 tracks."],
          ["Flagged population", "4,185 tracks."],
          ["Flag rate", "2.82% of scored tracks."],
          ["Unscored population", "3,239 tracks."],
          ["Processing errors", "Zero errors reported in the full inference output."],
        ],
      },
      {
        title: "Inference parity",
        items: [
          ["Validation sample", "29,673 tracks."],
          ["Flag agreement", "Exact agreement between tested inference outputs."],
          ["Score difference", "Effectively zero score difference."],
          ["Interpretation", "This verifies inference consistency, not anomaly detection accuracy against ground-truth labels."],
        ],
      },
      {
        title: "Tour regression validation",
        items: [
          ["Training / test split", "80:20 random split, random_state=42."],
          ["Training tours", "6,050."],
          ["Test tours", "1,513."],
          ["MAE", "1.816 hours."],
          ["RMSE", "6.455 hours."],
          ["Median absolute error", "0.542 hours."],
          ["R²", "0.868."],
          ["MAPE", "22.38%."],
        ],
      },
      {
        title: "Evaluation limitations",
        items: [
          ["No verified anomaly labels", "Flagged tracks are statistical outliers, not confirmed faults."],
          ["Random split", "Vehicles may occur in both training and test data; this is held-out-tour validation, not unseen-vehicle validation."],
          ["Operational validation", "Real-world incidents and analyst adjudications are needed to establish operational usefulness."],
        ],
      },
    ],
  },

  quality: {
    eyebrow: "DATA RELIABILITY",
    title: "Data Quality Assessment",
    description:
      "Inspect telemetry sufficiency, metadata consistency, missing values and fleet specification coverage.",
    stats: [
      ["151,598", "Original tracks"],
      ["148,359", "Scored tracks"],
      ["3,239", "Unscored / unassigned"],
      ["14", "Vehicles missing specifications"],
    ],
    sections: [
      {
        title: "Track-level quality findings",
        items: [
          ["Negative durations", "9 records."],
          ["Insufficient telemetry", "49 tracks with extremely limited raw speed observations."],
          ["Missing r_signal_loss", "1,714 tracks."],
          ["Negative n_signal_loss", "1,927 tracks."],
          ["Negative avg_speed", "6 tracks."],
        ],
      },
      {
        title: "Telemetry quality assessment",
        items: [
          ["Coverage", "Assess the proportion of the expected track duration supported by valid telemetry intervals."],
          ["Observation sufficiency", "Identify records with too few observations to support reliable movement statistics."],
          ["Metadata consistency", "Check missing, negative and inconsistent track-level fields."],
          ["Quality flags", "Preserve individual diagnostic flags rather than collapsing every issue into one generic invalid label."],
        ],
      },
      {
        title: "Fleet specification coverage",
        items: [
          ["Vehicles with specifications", "149."],
          ["Vehicles missing all three specification fields", "14."],
          ["Fields", "gross_vehicle_weight, total_mass_with_trailer and axle_class."],
          ["Missingness pattern", "13 vehicles in fleet test 5 and one vehicle in fleet test 6."],
          ["Handling", "Do not blindly impute structurally missing vehicle specifications."],
        ],
      },
      {
        title: "Important distinction",
        items: [
          ["Unscored does not mean normal", "Tracks without model predictions must remain distinguishable from tracks that were scored and not flagged."],
          ["Quality does not establish fault", "A quality flag identifies a data concern, not necessarily a mechanical or operational fault."],
        ],
      },
    ],
  },
};

function StatCard({ value, label }) {
  return (
    <div className="method-stat">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function Section({ section }) {
  return (
    <section className="method-section">
      <div className="method-section-heading">
        <h2>{section.title}</h2>
        {section.description && <p>{section.description}</p>}
      </div>

      <div className="method-item-list">
        {section.items.map(([label, description]) => (
          <article className="method-item" key={label}>
            <strong>{label}</strong>
            <p>{description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function MethodologyPage({ module }) {
  const page = modules[module];

  if (!page) {
    return <main className="method-page">Module not found.</main>;
  }

  return (
    <main className="method-page">
      <header className="method-header">
        <span className="method-eyebrow">{page.eyebrow}</span>
        <h1>{page.title}</h1>
        <p>{page.description}</p>
      </header>

      <section className="method-stats">
        {page.stats.map(([value, label]) => (
          <StatCard key={label} value={value} label={label} />
        ))}
      </section>

      {module === "eda" && (
        <section className="method-section">
          <div className="method-section-heading">
            <h2>Fleet test distribution</h2>
            <p>Track counts across the six fleet test groups.</p>
          </div>
          <div className="method-chart">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={[
                  { test: "Test 1", tracks: 40048 },
                  { test: "Test 2", tracks: 12089 },
                  { test: "Test 3", tracks: 22933 },
                  { test: "Test 4", tracks: 26860 },
                  { test: "Test 5", tracks: 25020 },
                  { test: "Test 6", tracks: 24648 },
                ]}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#29394c" />
                <XAxis dataKey="test" stroke="#8494a9" />
                <YAxis stroke="#8494a9" />
                <Tooltip />
                <Bar dataKey="tracks" fill="#55b5a5" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {page.sections.map((section) => (
        <Section key={section.title} section={section} />
      ))}

      <footer className="method-footer">
        DT-CARGO · Vehicle Telemetry Intelligence
      </footer>
    </main>
  );
}
