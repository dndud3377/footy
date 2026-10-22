"""Actions 환경에서 후보 데이터 소스 접근 가능 여부를 점검하는 진단 스크립트.

python scripts/probe.py → 각 URL의 상태 코드와 응답 앞부분 출력.
"""
import requests

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
H = {"User-Agent": BROWSER_UA, "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9"}

CANDIDATES = [
    ("range no limit", "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard?dates=20261001-20261031", H),
    ("range limit100", "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard?dates=20261001-20261031&limit=100", H),
    ("range limit1000", "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard?dates=20261001-20261031&limit=1000", H),
    ("month YYYYMM", "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard?dates=202610", H),
    ("year YYYY", "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard?dates=2026", H),
    ("season param", "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard?season=2026&limit=1000", H),
    ("week range EPL", "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard?dates=20261018-20261024", H),
    ("single day EPL", "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard?dates=20261019", H),
]

for name, url, headers in CANDIDATES:
    try:
        r = requests.get(url, headers=headers, timeout=30)
        try:
            j = r.json(); body = f"events={len(j.get('events', []))} " + (", ".join(e.get("date","") for e in j.get("events", [])[:3]) if isinstance(j, dict) else "")
        except Exception:
            body = r.text[:200].replace("\n", " ")
        print(f"[{r.status_code}] {name}\n    {url}\n    {body}\n")
    except Exception as e:  # noqa: BLE001
        print(f"[ERR] {name}\n    {url}\n    {e!r}\n")
