
import { useState } from "react";
import { predictTourDuration } from "../../services/api/validationApi";
import "./liveTourPrediction.css";

export default function LiveTourPrediction() {
  const [distance, setDistance] = useState("");
  const [category, setCategory] = useState("0");

  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handlePredict(event) {
    event.preventDefault();

    setLoading(true);
    setError("");
    setPrediction(null);

    try {
      const result = await predictTourDuration({
        totalDistanceKm: distance,
        clusterId: category,
      });

      setPrediction(result);
    } catch (err) {
      setError(
        err.message || "Unable to generate prediction."
      );
    } finally {
      setLoading(false);
    }
  }

  const predictedHours =
    prediction?.predicted_elapsed_span_hours;

  const wholeHours =
    predictedHours == null
      ? 0
      : Math.floor(predictedHours);

  const minutes =
    predictedHours == null
      ? 0
      : Math.round(
          (predictedHours - wholeHours) * 60
        );

  return (
    <section className="live-prediction-section">
      <div className="live-prediction-heading">
        <div>
          <span className="live-prediction-eyebrow">
            PRE-TRIP ESTIMATION
          </span>

          <h2>Tour duration predictor</h2>

          <p>
            Estimate the elapsed tour span using planned
            distance and operational category.
          </p>
        </div>

        <span className="live-model-tag">
          Decision Tree
        </span>
      </div>

      <div className="live-prediction-layout">
        <form
          className="live-prediction-form"
          onSubmit={handlePredict}
        >
          <div className="live-field">
            <label htmlFor="tour-distance">
              Planned distance
            </label>

            <div className="live-distance-input">
              <input
                id="tour-distance"
                type="number"
                min="0.01"
                step="any"
                required
                value={distance}
                onChange={(event) => {
                  setDistance(event.target.value);
                  setPrediction(null);
                  setError("");
                }}
                placeholder="Enter distance"
              />

              <span>km</span>
            </div>
          </div>

          <div className="live-field">
            <label htmlFor="tour-category">
              Operational category
            </label>

            <select
              id="tour-category"
              value={category}
              onChange={(event) => {
                setCategory(event.target.value);
                setPrediction(null);
                setError("");
              }}
            >
              <option value="0">
                Category 0 — Longer-distance pattern
              </option>

              <option value="1">
                Category 1 — Shorter-distance pattern
              </option>
            </select>
          </div>

          <div className="live-input-note">
            Only distance and operational category are
            required. No telemetry or post-trip gap
            information is requested.
          </div>

          <button
            type="submit"
            disabled={loading || !distance}
          >
            {loading
              ? "Calculating..."
              : "Predict tour duration"}
          </button>

          {error && (
            <div className="live-prediction-error">
              {error}
            </div>
          )}
        </form>

        <div className="live-prediction-result">
          {!prediction && !loading && (
            <div className="live-empty-result">
              <span>ESTIMATED ELAPSED TOUR SPAN</span>
              <strong>—</strong>
              <p>
                Enter the tour details to generate a
                prediction.
              </p>
            </div>
          )}

          {loading && (
            <div className="live-empty-result">
              <span>MODEL INFERENCE</span>
              <strong>Calculating...</strong>
              <p>
                Running the saved regression model.
              </p>
            </div>
          )}

          {prediction && (
            <>
              <span>ESTIMATED ELAPSED TOUR SPAN</span>

              <div className="live-result-number">
                {wholeHours}
                <small>h</small>
                {" "}
                {minutes}
                <small>min</small>
              </div>

              <p className="live-result-category">
                {prediction.cluster_name}
              </p>

              <div className="live-result-details">
                <div>
                  <span>Planned distance</span>
                  <strong>
                    {Number(
                      prediction.distance_km
                    ).toFixed(1)} km
                  </strong>
                </div>

                <div>
                  <span>Model version</span>
                  <strong>
                    {prediction.model_version}
                  </strong>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="live-prediction-warning">
        <strong>Model assumption</strong>

        <p>
          This is a conditional regular-tour estimate.
          During historical training, Cluster 1 tours
          exceeding the selected unrecorded-gap threshold
          were excluded. That gap is not requested from
          the user and cannot be known before dispatch.
          Actual future tours may therefore have longer
          elapsed spans than predicted.
        </p>
      </div>
    </section>
  );
}
