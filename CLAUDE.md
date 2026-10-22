# footy — Claude 작업 규칙

5대 리그(EPL·라리가·분데스리가·세리에A·리그1) + 챔피언스리그 승부 예측 파이프라인.
사용자는 오우영과 Claude 둘뿐이다. 코드가 기준(source of truth)이고 docs/는 규칙집이다.

## 먼저 읽을 것

| 작업 | 문서 |
|---|---|
| 전체 구조·실행 흐름 | `docs/architecture.md` |
| 데이터 소스·컬럼·제약 | `docs/data-sources.md` |
| "오늘 경기 분석해줘" / 라인업 재분석 / 경기 후 기록 | `docs/match-analysis.md` |

## 핵심 규칙

1. **역할 분담** — 외부 데이터 수집·학습·예측 계산은 GitHub Actions가 한다. Claude 작업 공간은
   GitHub 외 사이트에 셸로 접속하지 못하므로, Claude는 저장소에 커밋된 데이터를 읽고
   웹 검색(WebSearch/WebFetch)으로 뉴스·부상·라인업을 보강한다.
2. **배당률 미사용** — 어떤 단계에서도 배당 데이터를 피처·보정 근거로 쓰지 않는다.
3. **팀 이름** — 내부 기준 이름은 Understat 이름. 새 소스를 붙이면 `align.py` 방식(날짜+스코어 짝짓기)으로 매핑한다. 이름 하드코딩 금지.
4. **시간** — 저장은 UTC, 사람에게 보여줄 때는 KST. "오늘 경기" = KST 정오 ~ 다음날 정오.
5. **시즌 표기** — 시작 연도 정수 (2026 = 2026/27).
6. **데이터 파일** — `data/`는 Actions가 쓴다. Claude가 손으로 고치지 않는다. 문제가 있으면 코드를 고친다.
7. **검증** — 수집 상태는 `data/ingest_report.md`가 진실. 코드를 바꾸면 Actions를 수동 실행해 보고서로 확인한다.
8. **범위** — 요청받은 것만 고친다. 큰 변경은 계획을 먼저 공유한다.

## 명령

```bash
pip install -e .
python -m footy ingest [--full]   # 수집 → data/processed 통합 → data/ingest_report.md
python -m footy build             # data/raw → data/processed 재생성
python -m footy check [--strict]  # 검증 보고서
```
