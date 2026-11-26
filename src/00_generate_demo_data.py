import argparse
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.generate_demo_data import generate_demo_dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic demo PMS dataset.")
    parser.add_argument(
        "--output-dir",
        default="data/demo_sample",
        type=pathlib.Path,
        help="Target directory for synthetic Excel reports",
    )
    args = parser.parse_args()
    generate_demo_dataset(args.output_dir)
