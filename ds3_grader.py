from pathlib import Path
from hw2_grader_core import grade_folder

DATASET_NUM = 3
ROOT = Path(".").resolve()

grade_folder(
    dataset_num=DATASET_NUM,
    submissions_dir=ROOT / "ds3",
    dataset_file=ROOT / "aa_coffee_exam_3.json",
    out_csv=ROOT / "ds3_grades.csv",
)
