"""수집 결과 검증 → data/ingest_report.md

Claude와 사람이 한눈에 데이터 상태를 확인하는 용도.
--strict 이면 치명적 문제(소스 오류, 과거 시즌 경기 수 부족, 팀 매칭 실패)가 있을 때 종료 코드 1.
"""
from __future__ import annotations

import json

import pandas as pd

from .config import DATA, EXPECTED_MATCHES, LEAGUES, PROCESSED, current_season


def report() -> tuple[str, list[str]]:
    problems: list[str] = []
    lines = ["# 수집 보고서", ""]

    last = PROCESSED / "last_ingest.json"
    if last.exists():
        log = json.loads(last.read_text(encoding="utf-8"))
        lines += [
            f"- 실행: {log.get('started_utc')} → {log.get('finished_utc')} (UTC)",
            f"- 현재 시즌: {log.get('current_season')}",
            f"- 수집 {len(log['fetched'])}건 / 건너뜀 {len(log['skipped'])}건 / 오류 {len(log['errors'])}건",
        ]
        for e in log["errors"]:
            lines.append(f"  - ❌ {e}")
            problems.append(f"수집 오류: {e}")
        for s in log["skipped"]:
            if "fdorg" in s:
                lines.append(f"  - ⚠️ {s}")
        lines.append("")

    mp = PROCESSED / "matches.csv"
    if not mp.exists():
        problems.append("matches.csv 없음")
        lines.append("matches.csv 없음")
        return "\n".join(lines), problems

    m = pd.read_csv(mp)
    cur = current_season()
    lines += ["## 리그·시즌별 경기", "",
              "| 리그 | 시즌 | 전체 | 종료 | 예상 | xG 결측 | 기본통계 연결 | 정확한 킥오프 |",
              "|---|---|---|---|---|---|---|---|"]
    for (lg, s), g in m.groupby(["league", "season"]):
        ft = g[g["status"] == "FT"]
        exp = EXPECTED_MATCHES.get(lg, 0)
        xg_missing = int(ft["hxg"].isna().sum())
        stats = ft["h_shots"].notna().mean() if "h_shots" in ft and len(ft) else 0
        ko = g["utc_kickoff"].notna().mean() if "utc_kickoff" in g and len(g) else 0
        lines.append(
            f"| {lg} | {s} | {len(g)} | {len(ft)} | {exp} | {xg_missing} | {stats:.0%} | {ko:.0%} |"
        )
        if s < cur and len(ft) < exp:
            problems.append(f"{lg} {s}: 종료 경기 {len(ft)} < {exp}")
        if len(g) != exp:
            problems.append(f"{lg} {s}: 전체 경기 {len(g)} ≠ {exp}")
        if len(ft) and stats < 0.95:
            problems.append(f"{lg} {s}: 기본통계 연결률 {stats:.0%}")
    lines.append("")

    ap = PROCESSED / "team_aliases.csv"
    if ap.exists():
        a = pd.read_csv(ap)
        lines += ["## 팀 이름 매칭", ""]
        for (src, method), g in a.groupby(["source", "method"]):
            lines.append(f"- {src} / {method}: {len(g)}개")
        bad = a[a["method"].isin(["fuzzy", "unmatched"])]
        if len(bad):
            lines += ["", "확인 필요 (경기 짝짓기로 증명되지 않은 매칭):", ""]
            for _, r in bad.iterrows():
                lines.append(f"- [{r['source']} {r['league']}] {r['name']} → {r['canonical']} ({r['method']})")
            if (bad["method"] == "unmatched").any():
                problems.append("팀 이름 매칭 실패 있음")
        # 한 canonical에 같은 소스·리그에서 이름 둘 이상 → 오매칭 의심
        dup = a[a["source"] != "fdorg"].groupby(["source", "league", "canonical"]).filter(lambda g: len(g) > 1)
        if len(dup):
            lines += ["", "⚠️ 한 팀에 이름이 둘 이상 매핑됨:", ""]
            for _, r in dup.iterrows():
                lines.append(f"- [{r['source']} {r['league']}] {r['name']} → {r['canonical']}")
            problems.append("중복 매핑 의심")
        lines.append("")

    fx = PROCESSED / "fixtures.csv"
    if fx.exists():
        f = pd.read_csv(fx)
        lines += ["## 다가오는 경기", "", f"- 총 {len(f)}경기 (리그별: " +
                  ", ".join(f"{k} {v}" for k, v in f["competition"].value_counts().sort_index().items()) + ")"]
        nxt = f.head(10)
        if len(nxt):
            lines += ["", "| KST | 대회 | 홈 | 원정 | 킥오프 출처 |", "|---|---|---|---|---|"]
            for _, r in nxt.iterrows():
                lines.append(f"| {r['kst_kickoff']} | {r['competition']} | {r['home']} | {r['away']} | {r['kickoff_source']} |")
        lines.append("")

    # Understat datetime 시간대 추정 (fdorg UTC와 비교)
    both = m.dropna(subset=["utc_kickoff", "understat_datetime"])
    if len(both):
        diff = (pd.to_datetime(both["understat_datetime"]) -
                pd.to_datetime(both["utc_kickoff"], utc=True).dt.tz_localize(None)).dt.total_seconds() / 3600
        lines += ["## Understat 시각 오프셋 (Understat − UTC, 시간)", "",
                  f"- 중앙값 {diff.median():+.1f}h, 분포: " +
                  ", ".join(f"{k:+.0f}h×{v}" for k, v in diff.round().value_counts().sort_index().items()), ""]

    lines += ["## 판정", ""]
    lines += [f"- ❌ {p}" for p in problems] or ["- ✅ 문제 없음"]
    return "\n".join(lines) + "\n", problems


def run(strict: bool = False) -> int:
    text, problems = report()
    (DATA / "ingest_report.md").write_text(text, encoding="utf-8")
    print(text)
    return 1 if (strict and problems) else 0
