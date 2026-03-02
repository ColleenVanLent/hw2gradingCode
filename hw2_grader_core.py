# hw2_grader_core.py
#
# Latest changes implemented:
# - Do NOT grade (or otherwise “sort”) any .py files whose names start with "hw2_"
# - CSV does NOT include a dataset column
# - Filename column shows ONLY the portion before the first "_" (e.g., "pawarsaeesagar_9028..." -> "pawarsaeesagar")
# - Per-task columns contain the POINT VALUE (0 / 4 / 7 / 8), not PASS/PARTIAL/FAIL
# - Lowest rated: if they return ("Rubric Roastery and Canvas Crash Cafe", year) instead of just Canvas Crash Cafe,
#   award HALF CREDIT (4 points) IF the year is correct.
# - Highest rated & lowest rated: accept year as a string or a number (e.g., "2026" or 2026)
# - Expected values are shown once on Row 2 ("EXPECTED_VALUES") in the *_got columns.
# - Student *_got values are only shown when the task score is not a full 8.

import csv
import importlib.util
import re
from pathlib import Path


# ----------------------------
# Generic helpers (schema-robust)
# ----------------------------

def _extract_shop_list(payload: dict):
    for k, v in payload.items():
        if k in ("id", "last_updated"):
            continue
        if isinstance(v, list) and (len(v) == 0 or isinstance(v[0], dict)):
            return v
    raise KeyError(f"Could not find shop list in keys={sorted(payload.keys())}")


def _get_in(d, path):
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _first_found(d, paths):
    for p in paths:
        v = _get_in(d, p)
        if v is not None:
            return v
    return None


def _shop_name(shoprec):
    return _first_found(shoprec, [
        ("shop", "name"),
        ("shop", "meta", "display_name"),
        ("info", "name"),
        ("name",),
    ]) or "Unknown"


def _shop_location(shoprec):
    return _first_found(shoprec, [
        ("shop", "neighborhood"),
        ("shop", "place", "neighborhood"),
        ("place", "neighborhood"),
        ("info", "location", "area"),
        ("location", "area"),
        ("area",),
        ("neighborhood",),
    ]) or "Unknown"


def _menu_list(shoprec):
    v = _first_found(shoprec, [("menu",), ("items",)])
    return v if isinstance(v, list) else []


def _drink_name(item):
    return _first_found(item, [
        ("drink", "name"),
        ("drink", "title"),
        ("beverage", "name"),
        ("drink_name",),
        ("title",),
        ("name",),
    ])


def _drink_price(item):
    return _first_found(item, [
        ("drink", "price"),
        ("beverage", "price"),
        ("price",),
        ("drink", "cost"),
        ("beverage", "cost"),
        ("cost",),
    ])


def _reviews_list(shoprec):
    v = _first_found(shoprec, [("reviews",), ("feedback", "reviews")])
    return v if isinstance(v, list) else []


def _rating(review):
    return _first_found(review, [("rating",)])


def _to_float(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip())
        except Exception:
            return None
    return None


def _year_from_last_updated(payload):
    s = payload.get("last_updated")
    if not isinstance(s, str):
        return None
    m = re.search(r"\b(\d{4})\b", s)
    return m.group(1) if m else None


def _parse_time_to_minutes(t):
    if not isinstance(t, str):
        return None
    s = t.strip().upper()

    ampm = None
    if s.endswith("AM"):
        ampm = "AM"
        s = s[:-2].strip()
    elif s.endswith("PM"):
        ampm = "PM"
        s = s[:-2].strip()

    m = re.match(r"^(\d{1,2})\s*:\s*(\d{1,2})$", s)
    if not m:
        return None

    hh = int(m.group(1))
    mm = int(m.group(2))
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return None

    if ampm == "AM":
        if hh == 12:
            hh = 0
    elif ampm == "PM":
        if hh != 12:
            hh += 12

    return hh * 60 + mm


def _open_time_str(shoprec):
    return _first_found(shoprec, [
        ("operations", "hours", "open"),
        ("operations", "open"),
        ("schedule", "open_time"),
        ("hours_open",),
    ])


def _score_names_year_penalty(got, expected):
    """
    Start at 8, subtract penalties:

      - If NONE of the names match → return 0 immediately
      - Subtract 4 if too many or too few names
      - Subtract 3.5 if year incorrect

    Final score never below 0.
    Accept year as string or number.
    """

    if not (isinstance(expected, tuple) and len(expected) == 2):
        return 0.0

    exp_names, exp_year = expected
    eset = _split_and_names(exp_names)
    ey = _coerce_year(exp_year)

    if eset is None or ey is None:
        return 0.0

    if not (isinstance(got, tuple) and len(got) == 2):
        return 0.0

    got_names, got_year = got
    gset = _split_and_names(got_names)
    gy = _coerce_year(got_year)

    if gset is None or gy is None:
        return 0.0

    # 🚨 If none of the names match → 0 immediately
    if len(gset.intersection(eset)) == 0:
        return 0.0

    score = 8.0

    # Too many or too few names
    if len(gset) != len(eset):
        score -= 4.0

    # Year incorrect
    if gy != ey:
        score -= 3.5

    return max(0.0, score)

# ----------------------------
# Reference solutions
# ----------------------------

def ref_list_top_level_keys(payload):
    shops = _extract_shop_list(payload)
    if not shops:
        return []
    return list(shops[0].keys())


def ref_count_coffee_shops(payload):
    return len(_extract_shop_list(payload))


def ref_shop_names_and_locations(payload):
    shops = _extract_shop_list(payload)
    return [(_shop_name(s), _shop_location(s)) for s in shops]


def ref_most_expensive_drink(payload):
    shops = _extract_shop_list(payload)
    best = None  # (drink, price_float, shopname)
    for s in shops:
        shopname = _shop_name(s)
        for item in _menu_list(s):
            dn = _drink_name(item)
            price = _to_float(_drink_price(item))
            if dn is None or price is None:
                continue
            if (best is None) or (price > best[1]):
                best = (dn, float(price), shopname)
    return best


def ref_average_price_of_drink(payload, drink_name):
    shops = _extract_shop_list(payload)
    total = 0.0
    count = 0
    for s in shops:
        for item in _menu_list(s):
            dn = _drink_name(item)
            if dn != drink_name:
                continue
            price = _to_float(_drink_price(item))
            if price is None:
                continue
            total += float(price)
            count += 1
    return None if count == 0 else total / count


def ref_highest_rated_shop(payload):
    shops = _extract_shop_list(payload)
    year = _year_from_last_updated(payload)  # <- THIS LINE

    best_avg = None
    best_names = []
    for s in shops:
        ratings = []
        for r in _reviews_list(s):
            val = _to_float(_rating(r))
            if val is not None:
                ratings.append(val)
        if not ratings:
            continue
        avg = sum(ratings) / len(ratings)
        nm = _shop_name(s)
        if (best_avg is None) or (avg > best_avg + 1e-12):
            best_avg = avg
            best_names = [nm]
        elif abs(avg - best_avg) <= 1e-12:
            best_names.append(nm)

    return ((None if best_avg is None else " and ".join(best_names)), year)


def ref_lowest_rated_shop(payload):
    shops = _extract_shop_list(payload)
    year = _year_from_last_updated(payload)  # <- THIS LINE

    worst_avg = None
    worst_names = []
    for s in shops:
        ratings = []
        for r in _reviews_list(s):
            val = _to_float(_rating(r))
            if val is not None:
                ratings.append(val)
        if not ratings:
            continue
        avg = sum(ratings) / len(ratings)
        nm = _shop_name(s)
        if (worst_avg is None) or (avg < worst_avg - 1e-12):
            worst_avg = avg
            worst_names = [nm]
        elif abs(avg - worst_avg) <= 1e-12:
            worst_names.append(nm)

    return ((None if worst_avg is None else " and ".join(worst_names)), year)


def ref_earliest_opening_shop(payload):
    shops = _extract_shop_list(payload)
    best = None  # (minutes, shopname)
    for s in shops:
        t = _open_time_str(s)
        mins = _parse_time_to_minutes(t)
        if mins is None:
            continue
        nm = _shop_name(s)
        if best is None or mins < best[0]:
            best = (mins, nm)
    return None if best is None else best[1]


# ----------------------------
# Comparison helpers
# ----------------------------

def _same_unordered_list(a, b):
    try:
        return set(a) == set(b)
    except Exception:
        return False


def _float_close(a, b, tol=1e-6):
    if a is None or b is None:
        return a is b
    return abs(float(a) - float(b)) <= tol


def _norm_expensive_tuple(t):
    if not isinstance(t, tuple) or len(t) != 3:
        return None
    dn, price, sn = t
    pf = _to_float(price)
    if dn is None or pf is None or sn is None:
        return None
    return (dn, float(pf), sn)


def _split_and_names(s):
    if not isinstance(s, str):
        return None
    parts = [p.strip() for p in s.split(" and ") if p.strip()]
    return set(parts)


def _coerce_year(y):
    """Accept year as '2026' or 2026 (or 2026.0). Return int or None."""
    if y is None:
        return None
    if isinstance(y, (int, float)):
        return int(y)
    if isinstance(y, str):
        s = y.strip()
        if s.isdigit():
            return int(s)
    return None


def _compare_shop_tuple_order_insensitive(got, expected):
    """Compare (shop_string, year) where shop_string is 'A and B and C' in any order; year accepts str or int."""
    if not (isinstance(got, tuple) and len(got) == 2):
        return False
    if not (isinstance(expected, tuple) and len(expected) == 2):
        return False

    got_names, got_year = got
    exp_names, exp_year = expected

    gy = _coerce_year(got_year)
    ey = _coerce_year(exp_year)
    if gy is None or ey is None or gy != ey:
        return False

    gset = _split_and_names(got_names)
    eset = _split_and_names(exp_names)
    if gset is None or eset is None:
        return False
    return gset == eset


# ----------------------------
# Student loading + safe repr
# ----------------------------

def load_student_module(py_path: Path):
    spec = importlib.util.spec_from_file_location(py_path.stem, py_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _safe_repr(x, maxlen=600):
    s = repr(x)
    return s if len(s) <= maxlen else (s[:maxlen] + "...[truncated]")


# ----------------------------
# Public grading API
# ----------------------------

FUNCTION_COLUMNS = [
    "list_top_level_keys",
    "count_coffee_shops",
    "shop_names_and_locations",
    "most_expensive_drink",
    "average_price_of_drink",
    "highest_rated_shop",
    "lowest_rated_shop",
    "earliest_opening_shop",
]


def compute_expected_map(payload, dataset_num: int):
    expected = {
        "list_top_level_keys": ref_list_top_level_keys(payload),
        "count_coffee_shops": ref_count_coffee_shops(payload),
        "shop_names_and_locations": ref_shop_names_and_locations(payload),
        "most_expensive_drink": ref_most_expensive_drink(payload),
        "average_price_of_drink": ref_average_price_of_drink(payload, "NFT Nitro"),
        "highest_rated_shop": ref_highest_rated_shop(payload),
        "lowest_rated_shop": ref_lowest_rated_shop(payload),
        "earliest_opening_shop": ref_earliest_opening_shop(payload),
    }

    # DS1 override for highest rated (order-insensitive) and year 2026
    if dataset_num == 1:
        expected["highest_rated_shop"] = (
            "Panic at the Espresso and Canvas Crash Cafe and Thesis & Beans",
            "2026",
        )

    return expected


def grade_one(student_mod, payload, dataset_num: int, expected_map: dict):
    """
    Returns:
      total_score (float),
      per_fn dict: {fn: {"points": float, "got": any}}
    """
    per_fn = {fn: {"points": 0.0, "got": None} for fn in FUNCTION_COLUMNS}
    total = 0.0

    # -------- Task 1 --------
    # 8 if already a list and matches; 7 if only matches after casting to list.
    exp = expected_map["list_top_level_keys"]
    try:
        got_raw = student_mod.list_top_level_keys(payload)

        if isinstance(got_raw, list):
            ok = _same_unordered_list(got_raw, exp)
            per_fn["list_top_level_keys"]["points"] = 8.0 if ok else 0.0
            per_fn["list_top_level_keys"]["got"] = got_raw
        else:
            try:
                got_cast = list(got_raw)
            except Exception:
                got_cast = got_raw
            ok_cast = _same_unordered_list(got_cast, exp)
            per_fn["list_top_level_keys"]["points"] = 7.0 if ok_cast else 0.0
            per_fn["list_top_level_keys"]["got"] = got_cast

    except Exception as e:
        per_fn["list_top_level_keys"]["points"] = 0.0
        per_fn["list_top_level_keys"]["got"] = f"ERROR: {e}"

    total += per_fn["list_top_level_keys"]["points"]

    # -------- Task 2 --------
    try:
        got = student_mod.count_coffee_shops(payload)
        exp = expected_map["count_coffee_shops"]
        per_fn["count_coffee_shops"]["points"] = 8.0 if got == exp else 0.0
        per_fn["count_coffee_shops"]["got"] = got
    except Exception as e:
        per_fn["count_coffee_shops"]["points"] = 0.0
        per_fn["count_coffee_shops"]["got"] = f"ERROR: {e}"
    total += per_fn["count_coffee_shops"]["points"]

    # -------- Task 3 --------
    try:
        got = student_mod.shop_names_and_locations(payload)
        exp = expected_map["shop_names_and_locations"]
        per_fn["shop_names_and_locations"]["points"] = 8.0 if _same_unordered_list(got, exp) else 0.0
        per_fn["shop_names_and_locations"]["got"] = got
    except Exception as e:
        per_fn["shop_names_and_locations"]["points"] = 0.0
        per_fn["shop_names_and_locations"]["got"] = f"ERROR: {e}"
    total += per_fn["shop_names_and_locations"]["points"]

    # -------- Task 4 --------
    try:
        got_raw = student_mod.most_expensive_drink(payload)
        exp_raw = expected_map["most_expensive_drink"]
        got = _norm_expensive_tuple(got_raw)
        exp = _norm_expensive_tuple(exp_raw)

        ok = (
            got is not None and exp is not None and
            got[0] == exp[0] and got[2] == exp[2] and _float_close(got[1], exp[1])
        )
        if not ok and got is not None and exp is not None and _float_close(got[1], exp[1]):
            ok = True  # allow ties by price

        per_fn["most_expensive_drink"]["points"] = 8.0 if ok else 0.0
        per_fn["most_expensive_drink"]["got"] = got_raw

    except Exception as e:
        per_fn["most_expensive_drink"]["points"] = 0.0
        per_fn["most_expensive_drink"]["got"] = f"ERROR: {e}"
    total += per_fn["most_expensive_drink"]["points"]

    # -------- Task 5 --------
    # 8 if correct (skips missing prices)
    # 7 if missing prices treated as 0
    # 0 otherwise
    partial_credit = False
    all_correct = True
    got_detail = {}

    for dn in ["NFT Nitro", "Quantum Cortado"]:
        try:
            g = student_mod.average_price_of_drink(payload, dn)
            e = ref_average_price_of_drink(payload, dn)

            if e is None:
                ok_dn = (g is None)
            else:
                ok_dn = (g is not None and _float_close(g, e, tol=1e-4))

            if not ok_dn and e is not None and g is not None:
                shops = _extract_shop_list(payload)
                total0 = 0.0
                count0 = 0
                for s in shops:
                    for item in _menu_list(s):
                        dn2 = _drink_name(item)
                        if dn2 == dn:
                            price_raw = _drink_price(item)
                            price = _to_float(price_raw)
                            if price is None:
                                price = 0.0
                            total0 += float(price)
                            count0 += 1
                wrong_avg = None if count0 == 0 else total0 / count0

                if wrong_avg is not None and _float_close(g, wrong_avg, tol=1e-4):
                    partial_credit = True
                else:
                    all_correct = False
            else:
                if not ok_dn:
                    all_correct = False

        except Exception as ex:
            g = f"ERROR: {ex}"
            e = ref_average_price_of_drink(payload, dn)
            all_correct = False

        got_detail[dn] = {"got": g, "expected": e}

    if all_correct:
        per_fn["average_price_of_drink"]["points"] = 8.0
        per_fn["average_price_of_drink"]["got"] = ""
    elif partial_credit:
        per_fn["average_price_of_drink"]["points"] = 7.0
        per_fn["average_price_of_drink"]["got"] = got_detail
    else:
        per_fn["average_price_of_drink"]["points"] = 0.0
        per_fn["average_price_of_drink"]["got"] = got_detail

    total += per_fn["average_price_of_drink"]["points"]

    # -------- Task 6 (highest rated) --------
    # -------- Task 6 (highest rated) --------
    try:
        got = student_mod.highest_rated_shop(payload)
        exp = expected_map["highest_rated_shop"]

        pts = _score_names_year_penalty(got, exp)

        per_fn["highest_rated_shop"]["points"] = pts
        per_fn["highest_rated_shop"]["got"] = got
    except Exception as e:
        per_fn["highest_rated_shop"]["points"] = 0.0
        per_fn["highest_rated_shop"]["got"] = f"ERROR: {e}"
    total += per_fn["highest_rated_shop"]["points"]

    # -------- Task 7 (lowest rated) --------
    # Half credit (4) if they return "Rubric Roastery and Canvas Crash Cafe" instead of just "Canvas Crash Cafe"
# -------- Task 7 (lowest rated) --------
    try:
        got = student_mod.lowest_rated_shop(payload)
        exp = expected_map["lowest_rated_shop"]

        pts = _score_names_year_penalty(got, exp)

        per_fn["lowest_rated_shop"]["points"] = pts
        per_fn["lowest_rated_shop"]["got"] = got
    except Exception as e:
        per_fn["lowest_rated_shop"]["points"] = 0.0
        per_fn["lowest_rated_shop"]["got"] = f"ERROR: {e}"
    total += per_fn["lowest_rated_shop"]["points"]

    # -------- Task 8 --------
    try:
        got = student_mod.earliest_opening_shop(payload)
        exp = expected_map["earliest_opening_shop"]
        per_fn["earliest_opening_shop"]["points"] = 8.0 if got == exp else 0.0
        per_fn["earliest_opening_shop"]["got"] = got
    except Exception as e:
        per_fn["earliest_opening_shop"]["points"] = 0.0
        per_fn["earliest_opening_shop"]["got"] = f"ERROR: {e}"
    total += per_fn["earliest_opening_shop"]["points"]

    return total, per_fn


def grade_folder(dataset_num: int, submissions_dir: Path, dataset_file: Path, out_csv: Path):
    import json

    payload = json.loads(dataset_file.read_text())
    expected_map = compute_expected_map(payload, dataset_num)

    # Columns: file, score_out_of_64, status, then each fn_points and fn_got
    fieldnames = ["file", "score_out_of_64", "status"]
    for fn in FUNCTION_COLUMNS:
        fieldnames.append(fn)               # points
        fieldnames.append(f"{fn}_got")      # got/expected values in row 2

    rows = []

    # ---- Row 2: expected values (in *_got columns) ----
    expected_row = {
        "file": "EXPECTED_VALUES",
        "score_out_of_64": "",
        "status": "",
    }
    for fn in FUNCTION_COLUMNS:
        expected_row[fn] = ""
        expected_row[f"{fn}_got"] = _safe_repr(expected_map[fn])
    rows.append(expected_row)

    # ---- Student rows ----
    for py in sorted(submissions_dir.glob("*.py")):
        # Do not grade any file starting with hw2_
        if py.name.startswith("hw2_"):
            continue

        status = "OK"
        try:
            student_mod = load_student_module(py)
            total_score, per_fn = grade_one(student_mod, payload, dataset_num, expected_map)
        except Exception as e:
            total_score = 0.0
            status = f"IMPORT_ERROR: {e}"
            per_fn = {fn: {"points": 0.0, "got": ""} for fn in FUNCTION_COLUMNS}

        display_name = py.name.split("_", 1)[0]

        row = {
            "file": display_name,
            "score_out_of_64": "",  # will be replaced with formula
            "status": status,
}

        for fn in FUNCTION_COLUMNS:
            pts = float(per_fn.get(fn, {}).get("points", 0.0))
            got = per_fn.get(fn, {}).get("got", "")

            # Put the point value directly
            row[fn] = pts

            # Only show got values if NOT a full 8
            row[f"{fn}_got"] = "" if pts >= 7.9999 else _safe_repr(got)

            # Excel formula for column B (score_out_of_64)
            excel_row = len(rows) + 2  # header = row 1, expected row = row 2
            row["score_out_of_64"] = (f"=SUM(D{excel_row},F{excel_row},H{excel_row},J{excel_row},"
                                      f"L{excel_row},N{excel_row},P{excel_row},R{excel_row})")

        rows.append(row)

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {out_csv} ({len(rows)-1} student rows + 1 expected row)")