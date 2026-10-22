"""football-data.co.uk — 5대 리그 결과 + 기본 경기 통계 (키 불필요).

배당률 컬럼은 사용하지 않기로 했으므로 수집 단계에서 버린다.
"""
from __future__ import annotations

import io

import pandas as pd
import requests

from ..config import fdcouk_season_code

BASE = "https://www.football-data.co.uk/mmz4281/{code}/{div}.csv"

# 원본 컬럼 → 내부 컬럼
KEEP = {
    "Date": "date",
    "Time": "time_uk",
    "HomeTeam": "home",
    "AwayTeam": "away",
    "FTHG": "hg",
    "FTAG": "ag",
    "HTHG": "ht_hg",
    "HTAG": "ht_ag",
    "Referee": "referee",
    "HS": "h_shots",
    "AS": "a_shots",
    "HST": "h_sot",
    "AST": "a_sot",
    "HF": "h_fouls",
    "AF": "a_fouls",
    "HC": "h_corners",
    "AC": "a_corners",
    "HY": "h_yellow",
    "AY": "a_yellow",
    "HR": "h_red",
    "AR": "a_red",
}


def fetch(div: str, season: int, session: requests.Session) -> pd.DataFrame:
    url = BASE.format(code=fdcouk_season_code(season), div=div)
    res = session.get(url, timeout=60)
    if res.status_code == 404:
        return pd.DataFrame(columns=list(KEEP.values()))
    res.raise_for_status()

    raw = res.content
    for enc in ("utf-8-sig", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    df = pd.read_csv(io.StringIO(text), on_bad_lines="skip")
    df = df.dropna(subset=["HomeTeam", "AwayTeam"])

    cols = [c for c in KEEP if c in df.columns]
    df = df[cols].rename(columns=KEEP)
    for c in KEEP.values():
        if c not in df.columns:
            df[c] = pd.NA

    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce").dt.date
    for c in [v for v in KEEP.values() if v not in ("date", "time_uk", "home", "away", "referee")]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    df["home"] = df["home"].str.strip()
    df["away"] = df["away"].str.strip()
    return df[list(KEEP.values())].reset_index(drop=True)
