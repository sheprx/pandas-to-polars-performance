"""Generate data and compare pandas and Polars across file layouts."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import platform
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Callable


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MANY_FILES = 1000
FEW_FILES = 10


def format_duration(seconds: float) -> str:
    """Return elapsed seconds as hh:mm:ss.milliseconds."""
    total_milliseconds = round(seconds * 1000)
    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"


def _clinical_rows(row_count: int, seed: int = 42):
    from mimesis import Person

    randomizer = random.Random(seed)
    person = Person("en")
    departments = ("Cardiology", "Oncology", "Neurology", "Pediatrics", "Radiology")
    start = dt.date(1940, 1, 1)
    date_span = (dt.date(2005, 1, 1) - start).days
    for row_id in range(row_count):
        first_name = person.first_name()
        last_name = person.last_name()
        birth_date = start + dt.timedelta(days=randomizer.randrange(date_span))
        yield {
            "PatientID": row_id + 1,
            "FirstName": first_name,
            "LastName": last_name,
            "DOB": birth_date.isoformat(),
            "Department": randomizer.choice(departments),
            "VisitDate": (dt.date(2020, 1, 1) + dt.timedelta(days=randomizer.randrange(1461))).isoformat(),
            "LengthOfStay": randomizer.randint(1, 14),
            "Charge": round(randomizer.uniform(100.0, 25000.0), 2),
        }


def generate_dataset(output_dir: Path, row_count: int, file_count: int, file_type: str) -> Path:
    """Generate one dataset, split evenly over CSV or Parquet files."""
    if file_type not in {"csv", "parquet"}:
        raise ValueError("file_type must be csv or parquet")
    dataset_dir = output_dir / f"{file_type}_{file_count}"
    if dataset_dir.exists():
        shutil.rmtree(dataset_dir)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    rows_per_file, remainder = divmod(row_count, file_count)
    rows = iter(_clinical_rows(row_count))
    columns = ["PatientID", "FirstName", "LastName", "DOB", "Department", "VisitDate", "LengthOfStay", "Charge"]

    if file_type == "parquet":
        import polars as pl
    from tqdm import tqdm

    for file_number in tqdm(range(file_count), desc=f"Generating {file_type} data", unit="file"):
        current_count = rows_per_file + (1 if file_number < remainder else 0)
        batch = [next(rows) for _ in range(current_count)]
        destination = dataset_dir / f"part-{file_number:04d}.{file_type}"
        if file_type == "csv":
            with destination.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns)
                writer.writeheader()
                writer.writerows(batch)
        else:
            pl.DataFrame(batch).write_parquet(destination)
    return dataset_dir


def process_pandas(dataset_dir: Path, file_type: str):
    """Read every file with pandas and aggregate patient visits."""
    import pandas as pd

    reader: Callable = pd.read_csv if file_type == "csv" else pd.read_parquet
    frames = [reader(path) for path in sorted(dataset_dir.glob(f"*.{file_type}"))]
    if not frames:
        raise FileNotFoundError(f"No {file_type} files found in {dataset_dir}")
    data = pd.concat(frames, ignore_index=True)
    data["PatientUID"] = data["FirstName"] + " " + data["LastName"] + " " + data["DOB"].str.replace("-", "", regex=False)
    result = (
        data.groupby("PatientUID", as_index=False)
        .agg(VisitCount=("PatientID", "size"), TotalCharge=("Charge", "sum"), AverageStay=("LengthOfStay", "mean"))
        .sort_values("VisitCount", ascending=False)
    )
    return result


def process_polars(dataset_dir: Path, file_type: str):
    """Aggregate files through Polars' lazy scan and collect once."""
    import polars as pl

    pattern = str(dataset_dir / f"*.{file_type}")
    scan = (
        pl.scan_csv(pattern, schema_overrides={"PatientID": pl.Int64, "LengthOfStay": pl.Int64, "Charge": pl.Float64})
        if file_type == "csv"
        else pl.scan_parquet(pattern)
    )
    return (
        scan.with_columns(
            (pl.col("FirstName") + " " + pl.col("LastName") + " " + pl.col("DOB").str.replace_all("-", "")).alias("PatientUID")
        )
        .group_by("PatientUID")
        .agg(
            pl.len().alias("VisitCount"),
            pl.col("Charge").sum().alias("TotalCharge"),
            pl.col("LengthOfStay").mean().alias("AverageStay"),
        )
        .sort("VisitCount", descending=True)
        .collect()
    )


def _run_processor(processor, dataset_dir: Path, file_type: str) -> dict:
    started = time.perf_counter()
    result = processor(dataset_dir, file_type)
    elapsed = time.perf_counter() - started
    return {"rows": result.shape[0], "seconds": elapsed, "duration": format_duration(elapsed)}


def run_benchmarks(data_dir: Path, row_count: int) -> list[dict]:
    results = []
    for file_type in ("csv", "parquet"):
        for file_label, file_count in (("many", MANY_FILES), ("few", FEW_FILES)):
            dataset_dir = generate_dataset(data_dir, row_count, file_count, file_type)
            for engine, processor in (("pandas", process_pandas), ("polars", process_polars)):
                measurement = _run_processor(processor, dataset_dir, file_type)
                results.append({"test": chr(65 + len(results)), "engine": engine, "files": file_label, "file_type": file_type, **measurement})
    return results


def _print_report(results: list[dict]) -> None:
    print("| Test | Engine | Files | Format | Duration | Groups |")
    print("| --- | --- | --- | --- | ---: | ---: |")
    for result in results:
        print(f"| {result['test']} | {result['engine']} | {result['files']} | {result['file_type']} | {result['duration']} | {result['rows']} |")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="generate one dataset")
    generate.add_argument("--rows", type=int, default=1_000_000)
    generate.add_argument("--files", type=int, default=MANY_FILES)
    generate.add_argument("--format", choices=("csv", "parquet"), default="csv", dest="file_type")
    generate.add_argument("--output", type=Path, default=DEFAULT_DATA_DIR)

    benchmark = subparsers.add_parser("benchmark", help="generate and run tests A-H")
    benchmark.add_argument("--rows", type=int, default=1_000_000)
    benchmark.add_argument("--output", type=Path, default=DEFAULT_DATA_DIR)
    benchmark.add_argument("--json", type=Path, help="also write raw results as JSON")

    args = parser.parse_args()
    if args.command == "generate":
        print(generate_dataset(args.output, args.rows, args.files, args.file_type))
        return
    results = run_benchmarks(args.output, args.rows)
    _print_report(results)
    if args.json:
        args.json.write_text(json.dumps({"environment": {"python": sys.version, "platform": platform.platform()}, "results": results}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()