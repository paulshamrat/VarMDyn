#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from statistics import mean, median

METRICS = {
    "rmsd.whole.dat": ("rmsd", "rmsd.whole.all.tsv", "whole_rmsd"),
    "rmsd.core.dat": ("rmsd", "rmsd.core.all.tsv", "core_rmsd"),
    "rg.dat": ("rg", "rg.all.tsv", "rg"),
}


def parse_args():
    p = argparse.ArgumentParser(description="Aggregate one state's QC-A outputs.")
    p.add_argument("--state", required=True, choices=["apo", "holo"])
    p.add_argument(
        "--root",
        required=True,
        type=Path,
        help="State QC-A root, e.g. qc/results/apo/qc-a",
    )
    return p.parse_args()


def read_meta(path):
    data = {}
    with path.open(newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader, None)
        if header != ["key", "value"]:
            raise ValueError(f"Unexpected metadata header in {path}: {header}")
        for row in reader:
            if len(row) >= 2:
                data[row[0]] = row[1]
    return data


def read_series(path):
    values = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) < 2:
                continue
            try:
                y = float(fields[1])
            except ValueError:
                continue
            if math.isfinite(y):
                values.append(y)
    return values


def stats(values):
    if not values:
        return dict(
            nframes=0,
            mean=math.nan,
            median=math.nan,
            sd=math.nan,
            min=math.nan,
            max=math.nan,
        )
    mu = mean(values)
    sd = (
        0.0
        if len(values) == 1
        else math.sqrt(sum((v - mu) ** 2 for v in values) / (len(values) - 1))
    )
    return dict(
        nframes=len(values),
        mean=mu,
        median=median(values),
        sd=sd,
        min=min(values),
        max=max(values),
    )


def fmt(v):
    if isinstance(v, float):
        return "NA" if math.isnan(v) else f"{v:.6f}"
    return str(v)


def column_id(meta):
    return f"{meta['state']}_{meta['system']}_{meta['replicate']}"


def collect(root, state):
    records = []
    for meta_file in sorted((root / "per-replica").glob("*/*/meta.tsv")):
        meta = read_meta(meta_file)
        if meta.get("state") != state:
            raise ValueError(f"Foreign-state metadata under {root}: {meta_file}")
        series = {}
        for filename in METRICS:
            path = meta_file.parent / filename
            if not path.is_file():
                raise FileNotFoundError(path)
            series[filename] = read_series(path)
        records.append((meta, series))
    return records


def write_wide_tables(root, records):
    records = sorted(records, key=lambda x: (x[0]["system"], x[0]["replicate"]))
    for filename, (subdir, outname, _) in METRICS.items():
        lengths = {len(series[filename]) for _, series in records}
        if len(lengths) != 1:
            raise ValueError(f"Frame-count mismatch for {filename}")
        nframes = next(iter(lengths))
        firsts = {int(m["first_frame"]) for m, _ in records}
        strides = {int(m["stride"]) for m, _ in records}
        dts = {float(m["frame_dt_ns"]) for m, _ in records}
        if len(firsts) != 1 or len(strides) != 1 or len(dts) != 1:
            raise ValueError(f"Sampling metadata mismatch for {filename}")
        first = next(iter(firsts))
        stride = next(iter(strides))
        dt = next(iter(dts))
        outdir = root / subdir
        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / outname
        with out.open("w", newline="") as h:
            w = csv.writer(h, delimiter="\t")
            w.writerow(["time_ns"] + [column_id(m) for m, _ in records])
            for i in range(nframes):
                time_ns = ((first - 1) + i * stride) * dt
                w.writerow(
                    [f"{time_ns:.6f}"]
                    + [f"{series[filename][i]:.6f}" for _, series in records]
                )
        print(f"Wrote {out}: {nframes} rows x {len(records)} trajectories")


def write_summary(root, records):
    rows = []
    for meta, series in records:
        sw = stats(series["rmsd.whole.dat"])
        sc = stats(series["rmsd.core.dat"])
        sr = stats(series["rg.dat"])
        counts = {sw["nframes"], sc["nframes"], sr["nframes"]}
        status = "PASS"
        notes = []
        if 0 in counts:
            status = "FAIL"
            notes.append("no_analyzed_frames")
        if len(counts) != 1:
            status = "FAIL"
            notes.append("inconsistent_metric_frame_counts")
        rows.append(
            {
                "state": meta["state"],
                "system": meta["system"],
                "label": meta["label"],
                "class": meta.get("class", "UNSET"),
                "replicate": meta["replicate"],
                "status": status,
                "notes": ";".join(notes) if notes else ".",
                "nframes": min(counts) if counts else 0,
                "first_frame": meta["first_frame"],
                "last_frame": meta["last_frame"],
                "stride": meta["stride"],
                "frame_dt_ns": meta["frame_dt_ns"],
                "whole_rmsd_mean_A": sw["mean"],
                "whole_rmsd_median_A": sw["median"],
                "whole_rmsd_sd_A": sw["sd"],
                "whole_rmsd_max_A": sw["max"],
                "core_rmsd_mean_A": sc["mean"],
                "core_rmsd_median_A": sc["median"],
                "core_rmsd_sd_A": sc["sd"],
                "core_rmsd_max_A": sc["max"],
                "rg_mean_A": sr["mean"],
                "rg_median_A": sr["median"],
                "rg_sd_A": sr["sd"],
                "rg_min_A": sr["min"],
                "rg_max_A": sr["max"],
                "trajectory": meta["trajectory"],
            }
        )
    out = root / "qc.summary.tsv"
    fields = list(rows[0])
    with out.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fields, delimiter="\t")
        w.writeheader()
        for row in rows:
            w.writerow({k: fmt(row[k]) for k in fields})
    print(f"Wrote {out}: {len(rows)} replica rows")


def main():
    a = parse_args()
    root = a.root.resolve()
    records = collect(root, a.state)
    if not records:
        raise SystemExit(f"No QC-A metadata below {root / 'per-replica'}")
    if len(records) != 48:
        raise ValueError(f"Expected 48 {a.state} QC-A replicas, found {len(records)}")
    write_wide_tables(root, records)
    write_summary(root, records)


if __name__ == "__main__":
    main()
