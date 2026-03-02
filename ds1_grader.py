from pathlib import Path
from hw2_grader_core import grade_folder

DATASET_NUM = 1
ROOT = Path(".").resolve()

grade_folder(
    dataset_num=DATASET_NUM,
    submissions_dir=ROOT / "ds1",
    dataset_file=ROOT / "aa_coffee_exam_1.json",
    out_csv=ROOT / "hw2_ds1_grades.csv",
)