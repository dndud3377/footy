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
    ("espn site api (browser UA)", "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard", H),
    ("espn site api dates", "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard?dates=20261021", H),
    ("espn site api (no UA)", "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard", {}),
    ("espn site.web.api", "https://site.web.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard", H),
    ("espn sports.core", "https://sports.core.api.espn.com/v2/sports/soccer/leagues/uefa.champions/events", H),
    ("uefa match api 2027", "https://match.uefa.com/v5/matches?competitionId=1&seasonYear=2027&limit=5&offset=0&order=ASC", H),
    ("uefa match api 2026", "https://match.uefa.com/v5/matches?competitionId=1&seasonYear=2026&limit=5&offset=0&order=ASC", H),
    ("fotmob league", "https://www.fotmob.com/api/leagues?id=42", H),
    ("sofascore", "https://api.sofascore.com/api/v1/unique-tournament/7/seasons", H),
    ("openfootball cl repo", "https://api.github.com/repos/openfootball/champions-league/contents", H),
    ("worldfootball", "https://www.worldfootball.net/all_matches/champions-league-2026-2027/", H),
    ("fbref ucl", "https://fbref.com/en/comps/8/schedule/Champions-League-Scores-and-Fixtures", H),
]

for name, url, headers in CANDIDATES:
    try:
        r = requests.get(url, headers=headers, timeout=30)
        body = r.text[:200].replace("\n", " ")
        print(f"[{r.status_code}] {name}\n    {url}\n    {body}\n")
    except Exception as e:  # noqa: BLE001
        print(f"[ERR] {name}\n    {url}\n    {e!r}\n")
