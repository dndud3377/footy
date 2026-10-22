"""수집 실행: 소스별 원본을 정규화 CSV로 data/raw/ 아래 저장한다.

- 지난 시즌 파일은 이미 있으면 다시 받지 않는다 (--full 이면 전부 재수집).
- 현재 시즌은 매번 새로 받는다.
- 한 소스가 실패해도 나머지는 계속 진행하고, 오류는 run 결과에 담아 보고서에 남긴다.
"""
from __future__ import annotations

import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ..config import CUPS, LEAGUES, PROCESSED, RAW, current_season, seasons
from . import fdcouk, fdorg, make_session, understat


def _path(source: str, name: str) -> Path:
    p = RAW / source / f"{name}.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _save(df: pd.DataFrame, path: Path) -> int:
    df.to_csv(path, index=False)
    return len(df)


def run(full: bool = False) -> dict:
    session = make_session()
    cur = current_season()
    log: dict = {
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "current_season": cur,
        "fetched": [],
        "skipped": [],
        "errors": [],
    }

    def need(path: Path, season: int) -> bool:
        return full or season == cur or not path.exists()

    for code, ids in LEAGUES.items():
        for s in seasons():
            # football-data.co.uk
            p = _path("fdcouk", f"{code}_{s}")
            if need(p, s):
                try:
                    n = _save(fdcouk.fetch(ids["fdcouk"], s, session), p)
                    log["fetched"].append(f"fdcouk {code} {s}: {n}")
                except Exception as e:  # noqa: BLE001
                    log["errors"].append(f"fdcouk {code} {s}: {e!r}")
            else:
                log["skipped"].append(f"fdcouk {code} {s}")

            # Understat
            pm = _path("understat", f"matches_{code}_{s}")
            if need(pm, s):
                try:
                    us = understat.fetch(ids["understat"], s, session)
                    n = _save(us.matches, pm)
                    _save(us.team_history, _path("understat", f"team_history_{code}_{s}"))
                    _save(us.players, _path("understat", f"players_{code}_{s}"))
                    log["fetched"].append(f"understat {code} {s}: {n}")
                    time.sleep(1.0)
                except Exception as e:  # noqa: BLE001
                    log["errors"].append(f"understat {code} {s}: {e!r}")
            else:
                log["skipped"].append(f"understat {code} {s}")

    # football-data.org — 무료 플랜은 현재 시즌만
    if fdorg.token():
        comps = {c: ids["fdorg"] for c, ids in LEAGUES.items()} | {
            c: ids["fdorg"] for c, ids in CUPS.items()
        }
        for code, fd_code in comps.items():
            try:
                n = _save(fdorg.fetch(fd_code, cur, session), _path("fdorg", f"{code}_{cur}"))
                log["fetched"].append(f"fdorg {code} {cur}: {n}")
            except Exception as e:  # noqa: BLE001
                log["errors"].append(f"fdorg {code} {cur}: {e!r}")
    else:
        log["skipped"].append("fdorg (FOOTBALL_DATA_TOKEN 없음)")

    log["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    (PROCESSED / "last_ingest.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return log


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=False, indent=2))
    except Exception:
        traceback.print_exc()
        raise
