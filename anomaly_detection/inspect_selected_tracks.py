import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def inspect_track(data_root, report_dir, model_table, vehicle_id, track_id):
    speed_path = (
        data_root / "raw" / "speed" / str(vehicle_id) / f"{track_id}.csv"
    )
    if not speed_path.exists():
        raise FileNotFoundError(f"Speed file not found: {speed_path}")

    raw = pd.read_csv(speed_path, low_memory=False)
    required = {"epoch", "speed", "hdop"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"{speed_path} is missing columns: {sorted(missing)}")

    epoch_all = pd.to_numeric(raw["epoch"], errors="coerce").to_numpy(float)
    speed_all = pd.to_numeric(raw["speed"], errors="coerce").to_numpy(float)
    hdop_all = pd.to_numeric(raw["hdop"], errors="coerce").to_numpy(float)

    valid_epoch = np.isfinite(epoch_all)
    epoch = epoch_all[valid_epoch]
    speed = speed_all[valid_epoch]
    hdop = hdop_all[valid_epoch]

    order = np.argsort(epoch, kind="stable")
    epoch, speed, hdop = epoch[order], speed[order], hdop[order]

    if len(epoch) == 0:
        raise ValueError(f"No valid timestamps in {speed_path}")

    dt = np.diff(epoch)
    valid_intervals = (dt > 0) & (dt <= 2)
    speed_for_plot = speed.copy()
    hdop_for_plot = hdop.copy()
    breaks = np.flatnonzero(~valid_intervals) + 1
    speed_for_plot[breaks] = np.nan
    hdop_for_plot[breaks] = np.nan

    finite_speed = speed[np.isfinite(speed)]
    finite_hdop = hdop[np.isfinite(hdop)]
    span_seconds = float(epoch[-1] - epoch[0])

    print(f"\nTrack {track_id} | vehicle {vehicle_id}")
    print(f"Speed file: {speed_path}")
    print(f"Raw rows: {len(raw):,}")
    print(f"Rows with valid epoch: {int(valid_epoch.sum()):,}")
    print(f"Rows with missing/invalid speed: {int((~np.isfinite(speed_all)).sum()):,}")
    print(f"Negative speed rows: {int((speed_all < 0).sum()):,}")
    print(f"Telemetry span: {span_seconds:.1f} seconds")
    print(f"Intervals with 0 < dt <= 2 seconds: {int(valid_intervals.sum()):,}")
    print(f"Intervals over 2 seconds: {int((dt > 2).sum()):,}")
    print(f"Nonpositive intervals: {int((dt <= 0).sum()):,}")
    print(f"Valid interval time: {float(dt[valid_intervals].sum()):.1f} seconds")

    if len(finite_speed):
        print(
            "Raw speed (m/s): "
            f"mean={np.mean(finite_speed):.3f}, "
            f"median={np.median(finite_speed):.3f}, "
            f"p95={np.percentile(finite_speed, 95):.3f}, "
            f"max={np.max(finite_speed):.3f}"
        )
    print(f"Rows with missing/invalid HDOP: {int((~np.isfinite(hdop_all)).sum()):,}")
    if len(finite_hdop):
        print(
            "HDOP (m): "
            f"median={np.median(finite_hdop):.3f}, "
            f"p95={np.percentile(finite_hdop, 95):.3f}"
        )

    track_numbers = pd.to_numeric(model_table["track_id"], errors="coerce")
    model_row = model_table.loc[track_numbers == int(track_id)]
    if not model_row.empty:
        columns = [
            "quality_status_core",
            "quality_status_extended",
            "raw_speed_mean_kmh",
            "raw_speed_std",
            "low_speed_time_pct_03",
            "stop_episode_count_03",
            "duration_minutes",
            "distance_km",
            "avg_speed",
            "max_speed",
            "avg_hdop",
            "n_signal_loss",
            "d_signal_loss",
            "r_signal_loss",
            "home_base",
            "long_haul",
            "rest_area",
            "service_area_fuel",
            "industrial_area",
            "reason_codes",
        ]
        columns += [c for c in model_table.columns if c.startswith("flag_")]
        columns = [c for c in columns if c in model_table.columns]
        print("Track metadata and model features:")
        print(model_row[columns].to_string(index=False))

    elapsed_minutes = (epoch - epoch[0]) / 60.0
    fig, (speed_ax, hdop_ax) = plt.subplots(
        2, 1, figsize=(13, 7), sharex=True, constrained_layout=True
    )
    speed_ax.plot(elapsed_minutes, speed_for_plot, linewidth=0.6)
    speed_ax.axhline(0.3, color="red", linestyle="--", linewidth=0.8)
    speed_ax.set_ylabel("Speed (m/s)")
    speed_ax.set_title(f"Track {track_id} — vehicle {vehicle_id}")
    speed_ax.grid(True, alpha=0.25)

    hdop_ax.plot(elapsed_minutes, hdop_for_plot, linewidth=0.6, color="darkorange")
    hdop_ax.set_xlabel("Elapsed time (minutes)")
    hdop_ax.set_ylabel("HDOP (m)")
    hdop_ax.grid(True, alpha=0.25)

    report_dir.mkdir(parents=True, exist_ok=True)
    plot_path = report_dir / f"track_review_{vehicle_id}_{track_id}.png"
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
    print(f"Plot saved: {plot_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument(
        "--modeling-csv",
        default="anomaly_detection/reports/full/modeling_dataset.csv",
    )
    parser.add_argument(
        "--track",
        action="append",
        required=True,
        help="Track in VEHICLE_ID:TRACK_ID form; repeat for multiple tracks.",
    )
    args = parser.parse_args()

    data_root = Path(args.data_root)
    model_table = pd.read_csv(args.modeling_csv, low_memory=False)
    report_dir = Path("anomaly_detection/reports/full")

    for item in args.track:
        vehicle_id, track_id = item.split(":", 1)
        inspect_track(
            data_root,
            report_dir,
            model_table,
            vehicle_id,
            track_id,
        )


if __name__ == "__main__":
    main()