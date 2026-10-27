"""Analysis helpers with explicit age support and common age-bin standardization."""
import numpy as np
import pandas as pd
from analysis import METRICS

MEASURES = {**METRICS, "hip": "엉덩이둘레 (cm)", "chest": "가슴둘레 (cm)", "leg": "샅높이 (cm)", "sitting": "앉은키 (cm)", "arm": "팔길이 (cm)", "whr": "허리/엉덩이 비율", "leg_ratio": "샅높이/신장 비율", "sitting_ratio": "앉은키/신장 비율"}


def group_stats(frame, metric, groups):
    result = frame.groupby(groups, observed=True, dropna=True)[metric].agg(n="count", mean="mean", sd="std", median="median", p5=lambda a: a.quantile(.05), p95=lambda a: a.quantile(.95)).reset_index()
    result["ci95"] = (1.96 * result.sd / np.sqrt(result.n)).where(result.n >= 30)
    return result


def common_age_standardization(frame, metric, surveys, min_n):
    """Equal weight per common five-year cell, separately by sex.

    No extrapolation into missing age cells, no population weighting.
    """
    rows, supports = [], []
    valid = frame.dropna(subset=["age", metric]).copy()
    valid["age_group"] = (valid.age // 5 * 5).astype(int)
    table = group_stats(valid, metric, ["survey", "sex", "age_group"])
    for sex, part in table.groupby("sex"):
        supported = part[part.n >= min_n]
        counts = supported.groupby("age_group").survey.nunique()
        common = counts[counts == len(surveys)].index.tolist()
        if not common:
            continue
        selected = supported[supported.age_group.isin(common)]
        for survey, cells in selected.groupby("survey"):
            if set(cells.age_group) != set(common):
                continue
            rows.append({"survey": survey, "sex": sex, "mean": cells["mean"].mean(), "age_bins": len(common), "n": int(cells.n.sum())})
        supports.append({"sex": sex, "common_age_bins": ", ".join(f"{int(a)}–{int(a)+4}" for a in common), "weight_per_bin": 1 / len(common)})
    return pd.DataFrame(rows), pd.DataFrame(supports)


def stable_cohorts(frame):
    """Only assign a decade if the entire possible birth-year range fits it."""
    out = frame.dropna(subset=["age"]).copy()
    low = out.year_start - out.age - 1
    high = out.year_end - out.age
    out["birth_min"], out["birth_max"] = low, high
    out["cohort"] = (low // 10 * 10).where(low // 10 == high // 10)
    return out
