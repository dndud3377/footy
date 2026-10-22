# 데이터 소스

| 소스 | 범위 | 제공 | 키 | 비고 |
|---|---|---|---|---|
| football-data.co.uk | 5대 리그, 과거 전 시즌 | 결과, 전반 스코어, 슈팅·유효슈팅·코너·파울·카드, 심판 | 불필요 | 배당 컬럼은 수집 단계에서 버림. 갱신 주기가 며칠 늦을 수 있음 |
| Understat | 5대 리그, 2014/15~ | 경기별 xG, 팀 경기별 npxG·PPDA·deep·xPts, 선수 시즌 xG·xA | 불필요 | `getLeagueData/<league>/<season>` 한 번에 경기·팀·선수 |
| football-data.org v4 | 5대 리그 + 챔스, **현재 시즌만** | 일정(UTC 킥오프), 결과, 스테이지 | `FOOTBALL_DATA_TOKEN` | 무료 분당 10회. 라인업·경기 통계 미제공 |

## 없는 것과 대안

- **확정 라인업** — 무료 API에 없음. 킥오프 약 1시간 전 Claude가 웹(구단 공식 발표 우선)에서 찾아 반영.
- **부상·징계** — Claude가 분석 시점에 웹에서 확인.
- **챔스 과거 시즌** — football-data.org 무료는 현재 시즌만. 챔스는 국내 리그 전력 이관 방식이라 과거 데이터 없이도 예측 가능. 리그 간 전력 보정이 필요해지면 별도 소스 추가.
- **FBref** — 2026년 Opta 데이터 제공 중단으로 xG 등 고급 지표가 사라져 쓰지 않음.

## football-data.org 키 설정

1. https://www.football-data.org/client/register 에서 무료 가입 → 메일로 토큰 수신
2. GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret
3. 이름 `FOOTBALL_DATA_TOKEN`, 값에 토큰

키가 없으면 수집은 계속되고, 챔스 일정과 정확한 킥오프 시각만 빠진다 (보고서에 ⚠️ 표시).
