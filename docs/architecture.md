# 아키텍처

## 하루 흐름 (KST)

| 시각 | 주체 | 하는 일 | 산출물 |
|---|---|---|---|
| 08:15 | Actions `ingest` | 결과·xG·일정 수집, 팀 이름 정렬, 통합 | `data/processed/*`, `data/ingest_report.md` |
| 08:30 | Actions `predict` *(2단계)* | 피처 생성, 통계 모델 + ML 예측, 어제 경기 적중 기록 | `predictions/YYYY-MM-DD.json`, `eval/ledger.csv` |
| 11:40 | Claude 예약 작업 *(3단계)* | 예측 + 웹 정보 보정, 신뢰도, 해설 | `reports/YYYY-MM-DD.md`, 폰 알림 |
| 킥오프 −1h | 채팅 | 확정 라인업 반영해 해당 경기 재분석 | 리포트 갱신 |
| 월요일 | Actions `train` + Claude *(4단계)* | 재학습, 주간 회고 (모델 비교·보정 효과) | `eval/weekly/YYYY-Www.md` |

## 단계별 구축 계획

1. **수집** — `ingest` 워크플로, 원본 → 통합 테이블, 검증 보고서 ← *현재*
2. **예측** — 피처(폼·xG·피로도·상대전적·중요도·전술 지표), Dixon-Coles + ML, 챔스는 국내 리그 전력 이관
3. **분석 자동화** — Claude 예약 작업, 리포트 포맷, 적중 기록
4. **회고·대시보드** — 주간 재학습·회고, 적중률 대시보드

## 디렉터리

```
src/footy/
  config.py          리그 코드, 시즌, KST 창
  ingest/            소스별 수집기 (fdcouk, understat, espn, fdorg) + run.py
  align.py           소스 간 팀 이름 정렬
  build.py           data/raw → data/processed
  check.py           검증 보고서
data/
  raw/<source>/      소스별 정규화 CSV (지난 시즌은 한 번만 수집)
  processed/         통합 테이블 (아래)
  ingest_report.md   최신 수집 상태
predictions/         날짜별 모델 예측 (2단계)
reports/             날짜별 분석 리포트 (3단계)
eval/                적중 기록·회고 (2~4단계)
```

## data/processed

| 파일 | 내용 |
|---|---|
| `matches.csv` | 5대 리그 전 경기 (최근 3시즌 + 현재). 결과·xG·슈팅 등 기본 통계·정확한 킥오프(가능 시) |
| `fixtures.csv` | 앞으로 열릴 경기 (리그 + 챔스), `kst_kickoff` 포함 |
| `ucl_matches.csv` | 챔스 현재 시즌 (ESPN) |
| `team_match_stats.csv` | 팀 경기별 xG·npxG·PPDA·deep·xPts |
| `players.csv` | 선수 시즌 지표 (분, 골, xG, xA, xGChain…) — 라인업 영향 추정용 |
| `team_aliases.csv` | 소스별 팀 이름 → 기준 이름, 매칭 방법(fixture/fuzzy/external) |

## 설계 결정

- **키 없는 소스만 기본** — football-data.co.uk, Understat, ESPN. football-data.org는 예비.
- **GitHub Actions가 계산** — Claude 작업 공간 셸은 GitHub 외 사이트 접속 불가. 공개 저장소라 Actions 시간 무료.
- **CSV 커밋** — 사람·Claude 모두 바로 읽을 수 있고 diff가 남는다. 지난 시즌 파일은 고정.
- **팀 이름은 경기로 증명** — 같은 날 같은 스코어 경기를 소스 간에 짝지어 매핑. 증명 안 된 매칭은 보고서에 표시.
