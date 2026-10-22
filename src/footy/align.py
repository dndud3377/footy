"""소스 간 팀 이름 정렬.

기준(canonical) 이름은 Understat 팀 이름이다 (5대 리그).
이름을 퍼지 매칭하는 대신, 같은 날짜·같은 스코어로 끝난 경기를 소스 간에
짝지어 "이 소스의 X = Understat의 Y"를 경기 데이터로 증명한다.
날짜+스코어 조합이 양쪽에서 유일한 경기만 사용해 오매칭을 막는다.
짝이 안 생긴 이름(시즌 초 승격팀 등)만 문자열 유사도로 보완하고 method로 표시한다.

챔스에만 나오는 5대 리그 밖 팀은 일정 소스(ESPN 등)의 짧은 이름을 그대로 쓴다.
"""
from __future__ import annotations

import difflib
from collections import Counter, defaultdict

import pandas as pd

from .config import EXT_SOURCES, LEAGUES, RAW


def _read(path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def understat_matches() -> pd.DataFrame:
    frames = []
    for code in LEAGUES:
        for p in sorted((RAW / "understat").glob(f"matches_{code}_*.csv")):
            df = pd.read_csv(p)
            df["league"] = code
            df["season"] = int(p.stem.rsplit("_", 1)[1])
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["datetime"]).dt.date
    return df


def _unique_key_rows(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    counts = df.groupby(keys)[keys[0]].transform("size")
    return df[counts == 1]


def _pair_counts(src: pd.DataFrame, ref: pd.DataFrame, src_home: str, src_away: str) -> Counter:
    """src(date,hg,ag,home,away) ↔ ref(date,hg,ag,home,away) 짝짓기 → (src이름, ref이름) 빈도."""
    keys = ["date", "hg", "ag"]
    a = _unique_key_rows(src.dropna(subset=["hg", "ag"]), keys)
    b = _unique_key_rows(ref.dropna(subset=["hg", "ag"]), keys)
    a = a[keys + [src_home, src_away]].astype({"hg": int, "ag": int}).rename(
        columns={src_home: "s_home", src_away: "s_away"}
    )
    b = b[keys + ["home", "away"]].astype({"hg": int, "ag": int}).rename(
        columns={"home": "r_home", "away": "r_away"}
    )
    m = a.merge(b, on=keys)
    c: Counter = Counter()
    for sh, sa, rh, ra in zip(m["s_home"], m["s_away"], m["r_home"], m["r_away"]):
        c[(sh, rh)] += 1
        c[(sa, ra)] += 1
    return c


def _resolve(counts: Counter, names: set, ref_names: set) -> dict[str, tuple[str, str, int]]:
    """빈도가 가장 높은 짝을 채택. 짝이 없으면 문자열 유사도로 보완."""
    best: dict[str, tuple[str, int]] = {}
    by_src: dict[str, Counter] = defaultdict(Counter)
    for (s, r), n in counts.items():
        by_src[s][r] += n
    out: dict[str, tuple[str, str, int]] = {}
    for s, c in by_src.items():
        r, n = c.most_common(1)[0]
        best[s] = (r, n)
        out[s] = (r, "fixture", n)
    used = {v[0] for v in out.values()}
    for s in sorted(names - set(out)):
        pool = sorted(ref_names - used) or sorted(ref_names)
        guess = difflib.get_close_matches(s, pool, n=1, cutoff=0.0)
        if guess:
            out[s] = (guess[0], "fuzzy", 0)
            used.add(guess[0])
        else:
            out[s] = (s, "unmatched", 0)
    return out


def build_aliases() -> pd.DataFrame:
    us = understat_matches()
    rows = []
    if us.empty:
        return pd.DataFrame(columns=["source", "league", "name", "source_id", "canonical", "method", "support"])

    for code in LEAGUES:
        ref = us[us["league"] == code]
        ref_names = set(ref["home"]) | set(ref["away"])

        # football-data.co.uk
        frames = []
        for p in sorted((RAW / "fdcouk").glob(f"{code}_*.csv")):
            df = pd.read_csv(p)
            df["date"] = pd.to_datetime(df["date"]).dt.date
            frames.append(df)
        if frames:
            fd = pd.concat(frames, ignore_index=True)
            counts = _pair_counts(fd, ref, "home", "away")
            names = set(fd["home"].dropna()) | set(fd["away"].dropna())
            for name, (canon, method, n) in _resolve(counts, names, ref_names).items():
                rows.append(("fdcouk", code, name, None, canon, method, n))

        # 일정·결과 외부 소스 (ESPN, football-data.org) — 팀 id 기준
        for src in EXT_SOURCES:
            frames_ext = [pd.read_csv(p) for p in sorted((RAW / src).glob(f"{code}_*.csv"))]
            frames_ext = [f for f in frames_ext if not f.empty]
            if not frames_ext:
                continue
            org = pd.concat(frames_ext, ignore_index=True)
            org["date"] = pd.to_datetime(org["utc_kickoff"], utc=True).dt.date
            org["home_key"] = org["home_id"].astype("Int64").astype(str)
            org["away_key"] = org["away_id"].astype("Int64").astype(str)
            counts = _pair_counts(org, ref, "home_key", "away_key")
            ids = set(org["home_key"]) | set(org["away_key"])
            id_name = dict(zip(org["home_key"], org["home_short"])) | dict(zip(org["away_key"], org["away_short"]))
            for tid, (canon, method, n) in _resolve(counts, ids, ref_names).items():
                if method == "fuzzy":
                    # id가 아니라 이름으로 다시 유사도 매칭
                    g = difflib.get_close_matches(str(id_name.get(tid)), sorted(ref_names), n=1, cutoff=0.0)
                    canon = g[0] if g else str(id_name.get(tid))
                rows.append((src, code, id_name.get(tid), tid, canon, method, n))

    aliases = pd.DataFrame(rows, columns=["source", "league", "name", "source_id", "canonical", "method", "support"])

    # 챔스 팀: 같은 소스의 리그 매핑에 있는 id는 그 이름, 없으면(5대 리그 밖 팀) 소스의 짧은 이름
    for src in EXT_SOURCES:
        ucl = sorted((RAW / src).glob("UCL_*.csv"))
        if not ucl:
            continue
        df = pd.concat([pd.read_csv(p) for p in ucl], ignore_index=True)
        known = {str(k) for k in aliases.loc[aliases["source"] == src, "source_id"]}
        seen = set()
        for side in ("home", "away"):
            for tid, short in zip(df[f"{side}_id"], df[f"{side}_short"]):
                if pd.isna(tid):
                    continue
                key = str(int(tid))
                if key in seen or key in known:
                    continue
                seen.add(key)
                aliases.loc[len(aliases)] = (src, "UCL", short, key, short, "external", 0)
    return aliases.sort_values(["source", "league", "name"]).reset_index(drop=True)
