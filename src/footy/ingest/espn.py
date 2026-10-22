"""ESPN 공개 사이트 API — 5대 리그 + 챔스 일정·결과 (키 불필요).

공식 문서가 없는 내부 API라 응답 구조가 바뀔 수 있다. 필드는 모두 방어적으로 읽고,
파싱에 실패하면 수집 보고서에 오류로 남는다.
출력 스키마는 football-data.org 수집기와 같다 (ext_id, utc_kickoff, status, …).
"""
from __future__ import annotations

import pandas as pd
import requests

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard"

# ESPN은 User-Agent에 봇 표식이 있으면 403을 준다 (Actions 진단으로 확인) — 일반 브라우저 헤더 사용
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

COLUMNS = [
    "ext_id", "utc_kickoff", "status", "stage", "group", "matchday",
    "home_id", "home", "home_short", "away_id", "away", "away_short",
    "hg", "ag", "duration",
]


def _months(season: int):
    """시즌(7월~이듬해 6월)의 월 목록 → 'YYYYMM'.

    ESPN scoreboard는 날짜 구간(YYYYMMDD-YYYYMMDD)을 400으로 거부하고
    월 단위(YYYYMM)는 받는다 (Actions 진단으로 확인).
    """
    for i in range(12):
        y, m = season + (6 + i) // 12, (6 + i) % 12 + 1
        yield f"{y}{m:02d}"


def _status(st: dict) -> str:
    t = (st or {}).get("type") or {}
    name = str(t.get("name", ""))
    if t.get("completed"):
        return "FINISHED"
    if "POSTPONED" in name:
        return "POSTPONED"
    if "CANCEL" in name or "ABANDON" in name:
        return "CANCELLED"
    if t.get("state") == "in":
        return "IN_PLAY"
    return "SCHEDULED"


def _duration(st: dict) -> str:
    name = str(((st or {}).get("type") or {}).get("name", ""))
    if "PEN" in name:
        return "PENALTY_SHOOTOUT"
    if "AET" in name or "EXTRA" in name:
        return "EXTRA_TIME"
    return "REGULAR"


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def fetch(slug: str, season: int, session: requests.Session) -> pd.DataFrame:
    events: dict[str, dict] = {}
    for month in _months(season):
        res = session.get(
            BASE.format(slug=slug),
            params={"dates": month, "limit": 500},
            headers=HEADERS,
            timeout=60,
        )
        res.raise_for_status()
        for ev in res.json().get("events", []) or []:
            events[str(ev.get("id"))] = ev

    rows = []
    for ev in events.values():
        comp = (ev.get("competitions") or [{}])[0]
        st = comp.get("status") or ev.get("status") or {}
        teams = {c.get("homeAway"): c for c in comp.get("competitors", []) or []}
        h, w = teams.get("home") or {}, teams.get("away") or {}
        status = _status(st)
        done = status == "FINISHED"
        rows.append(
            {
                "ext_id": _int(ev.get("id")),
                "utc_kickoff": ev.get("date") or comp.get("date"),
                "status": status,
                "stage": (ev.get("season") or {}).get("slug"),
                "group": None,
                "matchday": (ev.get("week") or {}).get("number"),
                "home_id": _int((h.get("team") or {}).get("id")),
                "home": (h.get("team") or {}).get("displayName"),
                "home_short": (h.get("team") or {}).get("shortDisplayName"),
                "away_id": _int((w.get("team") or {}).get("id")),
                "away": (w.get("team") or {}).get("displayName"),
                "away_short": (w.get("team") or {}).get("shortDisplayName"),
                "hg": _int(h.get("score")) if done else None,
                "ag": _int(w.get("score")) if done else None,
                "duration": _duration(st) if done else None,
            }
        )
    df = pd.DataFrame(rows, columns=COLUMNS)
    if df.empty:
        raise RuntimeError(f"ESPN {slug} {season}: 경기 0건 (응답 구조 변경 의심)")
    for c in ("ext_id", "home_id", "away_id", "hg", "ag"):
        df[c] = df[c].astype("Int64")
    return df.sort_values("utc_kickoff").reset_index(drop=True)
