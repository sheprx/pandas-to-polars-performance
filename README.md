# pandas-to-polars-performance

Objective: The goal is to create an example "legacy" Pandas pipeline and migrate it to Polars to improve execution time and memory efficiency. I have noticed increasing slowness in our pipelines at work that creates one new csv every day and then performs analytic functions across the entire set of files. Since they have been running for years they now consist of ~1k individual csv files. In order to determine the best solution(s) to remedy the slowness, I would like to see the duration (hh:mm:ss) run time for each permutation of the following: pandas vs polars, many files vs few files,  CSVs vs parquets.

The results of this comparative analysis should include the following (A-H):
* A Time Duration (hh:mm:ss) - Pandas analysis of dataset as 1000 CSVs
* B Time Duration (hh:mm:ss) - Polars analysis of dataset as 1000 CSVs
* C Time Duration (hh:mm:ss) - Pandas analysis of dataset as a few CSVs
* D Time Duration (hh:mm:ss) - Polars analysis of dataset as a few CSVs
* E Time Duration (hh:mm:ss) - Pandas analysis of dataset as 1000 parquets
* F Time Duration (hh:mm:ss) - Polars analysis of dataset as 1000 parquets
* G Time Duration (hh:mm:ss) - Pandas analysis of dataset as a few parquets
* H Time Duration (hh:mm:ss) - Polars analysis of dataset as a few parquets

Dataset: The project uses Mimesis to synthesize a fake clinical dataset of large size (e.g., 1M rows) and then chunks it out into **X** number of smaller files having filetype **Y** (e.g., csv, parquet) and then performs an analysis of type **Z** in pandas and polars. The analysis should require moderate computational time (e.g., up to 20 minutes; using tqdm if possible to show completion percentage as it runs) and perform some type of function that acts in aggregate across all the files (e.g., GROUP BY "FirstName, ' ', LastName, ' ', DOB(yyyymmdd)" AS PatientUIDtext ORDER BY rowct desc.)

Key Optimizations: I aim to explicitly highlight the use of Polars' lazy evaluation engine and the transition from CSV to Parquet file formats for I/O speed.

## Results

The following results were measured on Windows 11 with Python 3.13.15 using a
one-million-row synthetic dataset. The `many` configuration uses 1,000 files;
the `few` configuration uses 10 files. Durations measure processing only and do
not include dataset generation.

| Test | Engine | Files | Format | Duration | Groups |
| --- | --- | --- | --- | ---: | ---: |
| A | pandas | many | CSV | 00:00:11.832 | 999,991 |
| B | Polars | many | CSV | 00:00:00.520 | 999,991 |
| C | pandas | few | CSV | 00:00:03.294 | 999,989 |
| D | Polars | few | CSV | 00:00:00.265 | 999,989 |
| E | pandas | many | Parquet | 00:00:09.483 | 999,992 |
| F | Polars | many | Parquet | 00:00:00.270 | 999,992 |
| G | pandas | few | Parquet | 00:00:01.713 | 999,990 |
| H | Polars | few | Parquet | 00:00:00.186 | 999,990 |

Polars was faster in every measured configuration, completing the 1,000-file
CSV case in 0.520 seconds versus pandas at 11.832 seconds, and the 1,000-file
Parquet case in 0.270 seconds versus 9.483 seconds. Parquet also reduced pandas
processing time compared with CSV, while Polars combined lazy file scanning with
efficient columnar reads for the shortest times in this run. The results suggest
that both the engine and file format matter for this workload, but they are
single-run measurements on synthetic data; repeated runs, memory measurements,
and production-shaped data are needed before treating the speedups as universal.

Future Improvements: Include Memory Usage as a result (in addition to time duration)

## Running the benchmark

Install the dependencies, then run the complete comparison. The default creates
one million rows and regenerates the four datasets needed for tests A-H:

```powershell
uv sync
uv run python -m src.benchmark benchmark --json data/results.json
```

The command prints a Markdown table with tests A-H. Use a smaller row count for
a quick smoke test:

```powershell
uv run python -m src.benchmark benchmark --rows 10000 --output data/benchmark-small
```

To generate a single dataset for inspection, choose its format and partition
count explicitly:

```powershell
uv run python -m src.benchmark generate --rows 1000000 --files 1000 --format parquet
```

The pandas and Polars processors can also be run directly against a generated
dataset:

```powershell
uv run python src/process_pandas.py data/csv_1000 --format csv
uv run python src/process_polars data/parquet_1000 --format parquet
```

The Polars path uses lazy file scans and collects only after constructing the
patient grouping query. Generation progress is shown with `tqdm`. The benchmark
measures processing time separately from data generation time and reports
durations as `hh:mm:ss.sss`, while retaining raw seconds in the
optional JSON output.
