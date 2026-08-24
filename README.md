# pandas-to-polars-performance

Objective: The goal is to create an example "legacy" Pandas pipeline and migrate it to Polars to improve execution time and memory efficiency. I have noticed increasing slowness in our pipelines at work that creates one new csv every day and then performs analytic functions across the entire set of files. Since they have been running for years they now consist of ~1k individual csv files. In order to determine the best solution(s) to remedy the slowness, I would like to see the duration (hh:mm:ss) run time for each permutation of the following: pandas vs polars, many files vs few files,  CSVs vs parquets.

The results of this comparative analysis should include the following (A-H):
A Time Duration (hh:mm:ss) - Pandas analysis of dataset as 1000 CSVs
B Time Duration (hh:mm:ss) - Polars analysis of dataset as 1000 CSVs
C Time Duration (hh:mm:ss) - Pandas analysis of dataset as a few CSVs
D Time Duration (hh:mm:ss) - Polars analysis of dataset as a few CSVs
E Time Duration (hh:mm:ss) - Pandas analysis of dataset as 1000 parquets
F Time Duration (hh:mm:ss) - Polars analysis of dataset as 1000 parquets
G Time Duration (hh:mm:ss) - Pandas analysis of dataset as a few parquets
H Time Duration (hh:mm:ss) - Polars analysis of dataset as a few parquets

Dataset: The project uses Mimesis to synthesize a fake clinical dataset of large size (e.g., 1M rows) and then chunks it out into **X** number of smaller files having filetype **Y** (e.g., csv, parquet) and then performs an analysis of type **Z** in pandas and polars. The analysis should require moderate computational time (e.g., up to 20 minutes; using tqdm if possible to show completion percentage as it runs) and perform some type of function that acts in aggregate across all the files (e.g., GROUP BY "FirstName, ' ', LastName, ' ', DOB(yyyymmdd)" AS PatientUIDtext ORDER BY rowct desc.)

Key Optimizations: I aim to explicitly highlight the use of Polars' lazy evaluation engine and the transition from CSV to Parquet file formats for I/O speed.

Results: A small markdown table that compares the final execution times of Tests A-H.

Future Improvements: Include Memory Usage as a result (in addition to time duration)
