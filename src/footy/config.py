"""경로, 리그 코드, 시즌 계산 등 전역 설정.

시즌은 시작 연도로 표기한다 (2026 = 2026/27 시즌).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"

KST = timezone(timedelta(hours=9))

# 내부 리그 코드 → 소스별 코드
LEAGUES: dict[str, dict[str, str]] = {
    "EPL": {"name": "Premier League", "fdcouk": "E0", "understat": "EPL", "fdorg": "PL"},
    "LALIGA": {"name": "La Liga", "fdcouk": "SP1", "understat": "La_Liga", "fdorg": "PD"},
    "BUNDESLIGA": {"name": "Bundesliga", "fdcouk": "D1", "understat": "Bundesliga", "fdorg": "BL1"},
    "SERIEA": {"name": "Serie A", "fdcouk": "I1", "understat": "Serie_A", "fdorg": "SA"},
    "LIGUE1": {"name": "Ligue 1", "fdcouk": "F1", "understat": "Ligue_1", "fdorg": "FL1"},
}

CUPS: dict[str, dict[str, str]] = {
    "UCL": {"name": "UEFA Champions League", "fdorg": "CL"},
}

# 학습에 쓰는 과거 시즌 수 (현재 시즌 별도)
N_PAST_SEASONS = 3

# 시즌당 정상 경기 수 (검증용)
EXPECTED_MATCHES = {"EPL": 380, "LALIGA": 380, "SERIEA": 380, "BUNDESLIGA": 306, "LIGUE1": 306}


def current_season(today: date | None = None) -> int:
    """7월 이후면 그 해, 아니면 전년도를 현재 시즌 시작 연도로 본다."""
    today = today or datetime.now(KST).date()
    return today.year if today.month >= 7 else today.year - 1


def seasons(today: date | None = None) -> list[int]:
    cur = current_season(today)
    return list(range(cur - N_PAST_SEASONS, cur + 1))


def fdcouk_season_code(season: int) -> str:
    """2026 → '2627'"""
    return f"{season % 100:02d}{(season + 1) % 100:02d}"


def match_day_window(day: date) -> tuple[datetime, datetime]:
    """'오늘 경기' = KST 정오 ~ 다음날 정오."""
    start = datetime(day.year, day.month, day.day, 12, 0, tzinfo=KST)
    return start, start + timedelta(days=1)
