"""Understat — 5대 리그 경기별 xG, 팀 경기 지표(PPDA 등), 선수 시즌 지표 (키 불필요).

Understat는 `getLeagueData/<league>/<season>` AJAX 엔드포인트 한 번으로
경기(dates)·팀(teams)·선수(players) 데이터를 모두 돌려준다.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import requests

BASE = "https://understat.com/"
AJAX_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


@dataclass
class UnderstatSeason:
    matches: pd.DataFrame
    team_history: pd.DataFrame
    players: pd.DataFrame


def _get(endpoint: str, session: requests.Session, referer: str) -> dict:
    res = session.get(
        BASE + endpoint,
        headers={**AJAX_HEADERS, "Referer": referer},
        timeout=60,
    )
    res.raise_for_status()
    return res.json()


def fetch(league: str, season: int, session: requests.Session) -> UnderstatSeason:
    referer = f"{BASE}league/{league}/{season}"
    # 세션 쿠키 확보용으로 리그 페이지를 먼저 연다 (실패해도 무시)
    try:
        session.get(referer, timeout=60)
    except requests.RequestException:
        pass
    data = _get(f"getLeagueData/{league}/{season}", session, referer)

    matches = pd.DataFrame(
        [
            {
                "understat_id": int(m["id"]),
                "is_result": bool(m["isResult"]),
                "datetime": m["datetime"],
                "home": m["h"]["title"],
                "away": m["a"]["title"],
                "hg": _int(m["goals"]["h"]),
                "ag": _int(m["goals"]["a"]),
                "hxg": _float(m["xG"]["h"]),
                "axg": _float(m["xG"]["a"]),
            }
            for m in data.get("dates", [])
        ]
    )

    rows = []
    for team in data.get("teams", {}).values():
        for h in team.get("history", []):
            ppda = h.get("ppda") or {}
            ppda_a = h.get("ppda_allowed") or {}
            rows.append(
                {
                    "team": team["title"],
                    "datetime": h.get("date"),
                    "h_a": h.get("h_a"),
                    "xg": _float(h.get("xG")),
                    "xga": _float(h.get("xGA")),
                    "npxg": _float(h.get("npxG")),
                    "npxga": _float(h.get("npxGA")),
                    "ppda_att": _float(ppda.get("att")),
                    "ppda_def": _float(ppda.get("def")),
                    "ppda_allowed_att": _float(ppda_a.get("att")),
                    "ppda_allowed_def": _float(ppda_a.get("def")),
                    "deep": _int(h.get("deep")),
                    "deep_allowed": _int(h.get("deep_allowed")),
                    "scored": _int(h.get("scored")),
                    "missed": _int(h.get("missed")),
                    "xpts": _float(h.get("xpts")),
                }
            )
    team_history = pd.DataFrame(rows)

    players = pd.DataFrame(
        [
            {
                "understat_player_id": int(p["id"]),
                "player": p["player_name"],
                "team": p["team_title"],
                "position": p.get("position"),
                "games": _int(p.get("games")),
                "minutes": _int(p.get("time")),
                "goals": _int(p.get("goals")),
                "assists": _int(p.get("assists")),
                "xg": _float(p.get("xG")),
                "xa": _float(p.get("xA")),
                "npg": _int(p.get("npg")),
                "npxg": _float(p.get("npxG")),
                "shots": _int(p.get("shots")),
                "key_passes": _int(p.get("key_passes")),
                "xg_chain": _float(p.get("xGChain")),
                "xg_buildup": _float(p.get("xGBuildup")),
                "yellow": _int(p.get("yellow_cards")),
                "red": _int(p.get("red_cards")),
            }
            for p in data.get("players", [])
        ]
    )
    return UnderstatSeason(matches, team_history, players)


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _float(v):
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None
