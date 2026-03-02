from pathlib import Path
from hw2_grader_core import grade_folder

DATASET_NUM = 2
ROOT = Path(".").resolve()

grade_folder(
    dataset_num=DATASET_NUM,
    submissions_dir=ROOT / "ds2",
    dataset_file=ROOT / "aa_coffee_exam_2.json",
    out_csv=ROOT / "hw2_ds2_grades.csv",
)