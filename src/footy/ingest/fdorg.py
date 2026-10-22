"""football-data.org v4 — 챔피언스리그 포함 일정·결과 (무료 키 필요, 선택 사항).

ESPN 수집기가 기본이고, 키가 있으면 보조로 함께 받는다.

무료 플랜: 분당 10회, 현재 시즌만, 라인업 미제공.
환경변수 FOOTBALL_DATA_TOKEN 이 없으면 수집을 건너뛴다.
"""
from __future__ import annotations

import os
import time

import pandas as pd
import requests

BASE = "https://api.football-data.org/v4"
MIN_INTERVAL = 6.5  # 초 — 분당 10회 제한 준수

_last_call = 0.0


def token() -> str | None:
    return os.environ.get("FOOTBALL_DATA_TOKEN") or None


def fetch(code: str, season: int, session: requests.Session) -> pd.DataFrame:
    global _last_call
    tok = token()
    if not tok:
        raise RuntimeError("FOOTBALL_DATA_TOKEN not set")

    wait = MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    res = session.get(
        f"{BASE}/competitions/{code}/matches",
        params={"season": season},
        headers={"X-Auth-Token": tok},
        timeout=60,
    )
    _last_call = time.monotonic()
    res.raise_for_status()

    rows = []
    for m in res.json().get("matches", []):
        ft = (m.get("score") or {}).get("fullTime") or {}
        rows.append(
            {
                "ext_id": m["id"],
                "utc_kickoff": m["utcDate"],
                "status": m["status"],
                "stage": m.get("stage"),
                "group": m.get("group"),
                "matchday": m.get("matchday"),
                "home_id": (m.get("homeTeam") or {}).get("id"),
                "home": (m.get("homeTeam") or {}).get("name"),
                "home_short": (m.get("homeTeam") or {}).get("shortName"),
                "away_id": (m.get("awayTeam") or {}).get("id"),
                "away": (m.get("awayTeam") or {}).get("name"),
                "away_short": (m.get("awayTeam") or {}).get("shortName"),
                "hg": ft.get("home"),
                "ag": ft.get("away"),
                "duration": (m.get("score") or {}).get("duration"),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["hg"] = df["hg"].astype("Int64")
        df["ag"] = df["ag"].astype("Int64")
    return df
