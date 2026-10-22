"""data/raw → data/processed 통합 테이블 생성.

산출물 (모두 CSV, 팀 이름은 canonical = Understat 이름):
- team_aliases.csv     소스별 팀 이름 → canonical
- matches.csv          5대 리그 전 경기 (결과 + 예정), xG + 기본 통계 + 정확한 킥오프(가능할 때)
- ucl_matches.csv      챔스 현재 시즌 (football-data.org 키가 있을 때)
- fixtures.csv         앞으로 열릴 경기 (리그 + 챔스), KST 킥오프 포함
- team_match_stats.csv Understat 팀 경기별 지표 (xG, npxG, PPDA, deep 등)
- players.csv          Understat 선수 시즌 지표
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from .align import build_aliases, understat_matches
from .config import KST, LEAGUES, PROCESSED, RAW

STAT_COLS = [
    "time_uk", "ht_hg", "ht_ag", "referee", "h_shots", "a_shots", "h_sot", "a_sot",
    "h_fouls", "a_fouls", "h_corners", "a_corners", "h_yellow", "a_yellow", "h_red", "a_red",
]
FINISHED = {"FINISHED", "AWARDED"}


def _concat(pattern: str, source: str) -> pd.DataFrame:
    frames = []
    for p in sorted((RAW / source).glob(pattern)):
        df = pd.read_csv(p)
        if df.empty:
            continue
        stem = p.stem
        parts = stem.split("_")
        df["league"] = parts[-2]
        df["season"] = int(parts[-1])
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _map(df: pd.DataFrame, aliases: pd.DataFrame, source: str, by: str = "name") -> pd.DataFrame:
    a = aliases[aliases["source"] == source]
    key = "source_id" if by == "id" else "name"
    keys = pd.to_numeric(a[key], errors="coerce").astype("Int64").astype(str) if by == "id" else a[key].astype(str)
    lut = dict(zip(keys, a["canonical"]))
    out = df.copy()
    for side in ("home", "away"):
        col = f"{side}_id" if by == "id" else side
        vals = out[col].astype("Int64").astype(str) if by == "id" else out[col].astype(str)
        out[f"{side}_canon"] = vals.map(lut)
    return out


def _kst(utc_series: pd.Series) -> pd.Series:
    return pd.to_datetime(utc_series, utc=True).dt.tz_convert(KST).dt.strftime("%Y-%m-%d %H:%M")


def build() -> dict[str, int]:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    aliases = build_aliases()
    aliases["source_id"] = pd.to_numeric(aliases["source_id"], errors="coerce").astype("Int64")
    aliases.to_csv(PROCESSED / "team_aliases.csv", index=False)

    us = understat_matches()
    out: dict[str, int] = {"team_aliases": len(aliases)}
    if us.empty:
        return out

    m = us.rename(columns={"datetime": "understat_datetime"})[
        ["league", "season", "understat_id", "understat_datetime", "date", "home", "away",
         "is_result", "hg", "ag", "hxg", "axg"]
    ]

    # football-data.co.uk 통계 붙이기 — 한 시즌 한 리그에서 (홈, 원정) 조합은 유일
    fd = _concat("*_*.csv", "fdcouk")
    if not fd.empty:
        fd = fd.reindex(columns=list(dict.fromkeys([*fd.columns, *STAT_COLS])))
        fd = _map(fd, aliases, "fdcouk")
        fd = fd.dropna(subset=["home_canon", "away_canon"])
        fd = fd.drop_duplicates(["league", "season", "home_canon", "away_canon"], keep="last")
        m = m.merge(
            fd[["league", "season", "home_canon", "away_canon", *STAT_COLS]].rename(
                columns={"home_canon": "home", "away_canon": "away"}
            ),
            on=["league", "season", "home", "away"],
            how="left",
        )

    # football-data.org 정확한 킥오프(UTC)·상태 붙이기
    org = _concat("*_*.csv", "fdorg")
    org_league = org[org["league"].isin(LEAGUES)] if not org.empty else org
    if not org_league.empty:
        o = _map(org_league, aliases, "fdorg", by="id")
        o = o.dropna(subset=["home_canon", "away_canon"])
        o = o.drop_duplicates(["league", "season", "home_canon", "away_canon"], keep="last")
        m = m.merge(
            o[["league", "season", "home_canon", "away_canon", "fdorg_id", "utc_kickoff", "status"]].rename(
                columns={"home_canon": "home", "away_canon": "away", "status": "fdorg_status"}
            ),
            on=["league", "season", "home", "away"],
            how="left",
        )
    else:
        m["fdorg_id"] = pd.NA
        m["utc_kickoff"] = pd.NA
        m["fdorg_status"] = pd.NA

    m["fdorg_id"] = pd.to_numeric(m["fdorg_id"], errors="coerce").astype("Int64")
    m["status"] = m["is_result"].map({True: "FT", False: "SCHEDULED"})
    m = m.drop(columns=["is_result"]).sort_values(["league", "season", "date", "home"])
    m.to_csv(PROCESSED / "matches.csv", index=False)
    out["matches"] = len(m)

    # 챔스
    ucl = org[org["league"] == "UCL"] if not org.empty else pd.DataFrame()
    if not ucl.empty:
        u = _map(ucl, aliases, "fdorg", by="id")
        u["home"] = u["home_canon"].fillna(u["home_short"])
        u["away"] = u["away_canon"].fillna(u["away_short"])
        u = u[["season", "fdorg_id", "utc_kickoff", "status", "stage", "group", "matchday",
               "home", "away", "hg", "ag", "duration"]].sort_values("utc_kickoff")
        u.to_csv(PROCESSED / "ucl_matches.csv", index=False)
        out["ucl_matches"] = len(u)

    # 앞으로 열릴 경기
    now = datetime.now(timezone.utc)
    fx = []
    lg = m[m["status"] == "SCHEDULED"].copy()
    lg["competition"] = lg["league"]
    lg["kickoff_source"] = lg["utc_kickoff"].notna().map({True: "fdorg", False: "understat"})
    # Understat datetime은 시간대가 확실치 않아 fdorg가 없을 때만 보조로 쓴다
    lg["utc_kickoff"] = lg["utc_kickoff"].fillna(lg["understat_datetime"])
    fx.append(lg[["competition", "season", "utc_kickoff", "kickoff_source", "home", "away", "fdorg_id", "understat_id"]])
    if not ucl.empty:
        uu = u[~u["status"].isin(FINISHED)].copy()
        uu["competition"] = "UCL"
        uu["kickoff_source"] = "fdorg"
        uu["understat_id"] = pd.NA
        fx.append(uu[["competition", "season", "utc_kickoff", "kickoff_source", "home", "away", "fdorg_id", "understat_id"]])
    fixtures = pd.concat(fx, ignore_index=True)
    ts = pd.to_datetime(fixtures["utc_kickoff"], utc=True, errors="coerce")
    fixtures = fixtures[ts >= pd.Timestamp(now) - pd.Timedelta(hours=3)]
    fixtures["kst_kickoff"] = _kst(fixtures["utc_kickoff"])
    for c in ("fdorg_id", "understat_id"):
        fixtures[c] = pd.to_numeric(fixtures[c], errors="coerce").astype("Int64")
    fixtures = fixtures.sort_values("utc_kickoff")
    fixtures.to_csv(PROCESSED / "fixtures.csv", index=False)
    out["fixtures"] = len(fixtures)

    th = _concat("team_history_*_*.csv", "understat")
    if not th.empty:
        th.sort_values(["league", "season", "team", "datetime"]).to_csv(PROCESSED / "team_match_stats.csv", index=False)
        out["team_match_stats"] = len(th)
    pl = _concat("players_*_*.csv", "understat")
    if not pl.empty:
        pl.sort_values(["league", "season", "team", "player"]).to_csv(PROCESSED / "players.csv", index=False)
        out["players"] = len(pl)
    return out
