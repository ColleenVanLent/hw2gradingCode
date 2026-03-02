from pathlib import Path
from hw2_grader_core import grade_folder

DATASET_NUM = 7
ROOT = Path(".").resolve()

grade_folder(
    dataset_num=DATASET_NUM,
    submissions_dir=ROOT / "ds7",
    dataset_file=ROOT / "aa_coffee_exam_7.json",
    out_csv=ROOT / "ds7_grades.csv",
)
