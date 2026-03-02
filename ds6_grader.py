from pathlib import Path
from hw2_grader_core import grade_folder

DATASET_NUM = 6
ROOT = Path(".").resolve()

grade_folder(
    dataset_num=DATASET_NUM,
    submissions_dir=ROOT / "ds6",
    dataset_file=ROOT / "aa_coffee_exam_6.json",
    out_csv=ROOT / "ds6_grades.csv",
)
