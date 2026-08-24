"""Run the pandas analysis for a generated dataset."""

import argparse
from pathlib import Path

from benchmark import process_pandas


def main() -> None:
	parser = argparse.ArgumentParser()
	parser.add_argument("dataset", type=Path)
	parser.add_argument("--format", choices=("csv", "parquet"), required=True, dest="file_type")
	args = parser.parse_args()
	result = process_pandas(args.dataset, args.file_type)
	print(result.head(20).to_string(index=False))


if __name__ == "__main__":
	main()

