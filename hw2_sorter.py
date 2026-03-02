from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

# ------------------------
# 1) What counts as "forced dataset1"
# ------------------------
FORCED_DS1 = re.compile(
    r"""
    \bsection8\b
    |dataset[_ -]?1
    |data[_ -]?set[_ -]?1
    |dataset1\.json
    |/1\.json\b
    |_1\.json\b
    |coffee.*1\.json
    |shops.*1\.json
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ------------------------
# 2) Find uniqname assignment
#    Matches:
#       uniqname = "abc"
#       uniqname='abc'
# ------------------------
UNIQ_RE = re.compile(
    r'^\s*uniqname\s*=\s*([\'"])(.*?)\1\s*$',
    re.MULTILINE
)

def dataset_number_from_uniqname(u: str) -> int:
    """sha256(lower(uniqname)) % 8 + 1  ->  1..8"""
    u = (u or "").strip().lower()
    if not u:
        raise ValueError("Missing uniqname")
    digest = hashlib.sha256(u.encode("utf-8")).hexdigest()
    return (int(digest, 16) % 8) + 1

def clean_filename(name: str) -> str:
    """Remove parentheses groups and spaces."""
    name = re.sub(r"\(.*?\)", "", name)  # remove "(1)" etc
    name = name.replace(" ", "")         # remove spaces
    return name

def unique_destination(dest: Path) -> Path:
    """Avoid overwriting existing files."""
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    i = 1
    while True:
        candidate = dest.with_name(f"{stem}_{i}{suffix}")
        if not candidate.exists():
            return candidate
        i += 1

def main() -> None:
    here = Path(".").resolve()

    # Create ds1–ds8 and unknown folders automatically
    ds_folders = {i: (here / f"ds{i}") for i in range(1, 9)}
    unknown_folder = here / "unknown"

    for folder in ds_folders.values():
        folder.mkdir(exist_ok=True)

    unknown_folder.mkdir(exist_ok=True)

    # ------------------------
    # OPTION 1: Skip hw2_sorter.py explicitly
    # ------------------------
    py_files = sorted([
        p for p in here.glob("*.py")
        if p.is_file() and p.name != "hw2_sorter.py"
    ])

    moved = 0

    for f in py_files:
        text = f.read_text(errors="ignore")

        # Determine destination folder
        if FORCED_DS1.search(text):
            target_folder = ds_folders[1]
            reason = "forced_ds1_pattern"
        else:
            m = UNIQ_RE.search(text)
            if m:
                uniq = (m.group(2) or "").strip()
                try:
                    ds = dataset_number_from_uniqname(uniq)
                    target_folder = ds_folders[ds]
                    reason = f"uniqname={uniq} -> ds{ds}"
                except Exception:
                    target_folder = unknown_folder
                    reason = "invalid_uniqname"
            else:
                target_folder = unknown_folder
                reason = "no_uniqname_found"

        # Clean filename and move
        new_name = clean_filename(f.name)
        dest = unique_destination(target_folder / new_name)

        shutil.move(str(f), str(dest))
        moved += 1

        print(f"Moved: {f.name} -> {dest.parent.name}/{dest.name}   [{reason}]")

    print(f"\nDone. Processed {moved} file(s).")
    print("Folders created/used: ds1..ds8, unknown")

if __name__ == "__main__":
    main()