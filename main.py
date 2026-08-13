import html
import re, logging, json
import requests

with open("config.json", "r") as file:
    config = json.load(file)

DOMAIN = config["Domain"]
LOGIN = DOMAIN + "Identity/Account/Login/"
PREDICTION = DOMAIN + "Predictions/"
GW = PREDICTION + "GameWeek/"

USERNAME = config["Email"]
PASSWORD = config["Password"]

TABLE = [
    "Arsenal",
    "Manchester City",
    "Manchester United",
    "Aston Villa",
    "Liverpool",
    "Bournemouth",
    "Sunderland",
    "Brighton and Hove Albion",
    "Brentford",
    "Chelsea",
    "Fulham",
    "Newcastle United",
    "Everton",
    "Leeds",
    "Crystal Palace",
    "Nottingham Forest",
    "Tottenham Hotspur",
    "Coventry City",
    "Ipswich Town",
    "Hull City"
]

logging.captureWarnings(True)

def get_csrf_token(session, url):
    response = session.get(url, verify=False)
    csrf_token = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', response.text).group(1)
    return csrf_token

def login(session, username, password):
    csrf_token = get_csrf_token(session, LOGIN)
    payload = {
        "Input.Email": username,
        "Input.Password": password,
        "Input.RememberMe": "false",
        "__RequestVerificationToken": csrf_token
    }
    response = session.post(LOGIN, data=payload, verify=False)
    return response

def get_teams(session, gw_id):
    predictions_url = f"{GW}?id={gw_id}"
    html = session.get(predictions_url, verify=False).text
    teams = re.findall(r'<td>([A-Za-z\s]*)</td>', html)

    # if len(teams) != 20:
    #     raise Exception(f"Unexpected number of teams found in the HTML. Expected 20, found {len(teams)}.")

    return teams

def make_predictions(teams, table):
    predictions = {}
    fixtures = [(teams[i], teams[i + 1]) for i in range(0, len(teams), 2)]

    for home, away in fixtures:
        if table.index(home) < table.index(away):
            predictions[home] = 2
            predictions[away] = 1
        else:
            predictions[home] = 1
            predictions[away] = 2

    return predictions

def post_predictions(session, predictions, gw_id):
    predictions_url = f"{GW}?id={gw_id}"

    csrf_token = get_csrf_token(session, predictions_url)
    
    html = session.get(predictions_url, verify=False).text
    fixture_id_start = int(re.search(r'name="Predictions\[0\]\.FixtureId"\s+value="([^"]+)"', html).group(1))
    teams = get_teams(session, gw_id)
    teams = [predictions[team] for team in teams]

    fixtures = [(fixture_id_start + i, home, away) for i, (home, away) in enumerate(zip(teams[::2], teams[1::2]))]
    print(fixtures)

    # build payload
    payload = {
        "__RequestVerificationToken": csrf_token,
        "Id": gw_id,
    }

    for i in range(len(fixtures)):
        fixture_id, home_score, away_score = fixtures[i]
        payload[f"Predictions[{i}].FixtureId"] = fixture_id
        payload[f"Predictions[{i}].HomeScore"] = home_score
        payload[f"Predictions[{i}].AwayScore"] = away_score

    response = session.post(predictions_url, data=payload, verify=False)
    return response

def do_predictions(session, gw_id):
    predictions = make_predictions(get_teams(session, gw_id=gw_id), TABLE)
    r = post_predictions(session, predictions=predictions, gw_id=gw_id)
    if r.status_code != 200:
        raise Exception(f"Posting predictions failed with status code {r.status_code}")

def get_avaliable_gws(session):
    html = session.get(PREDICTION, verify=False).text
    gw_ids = [int(x) for x in re.findall(r'<a[^>]*href="/Predictions/GameWeek\?id=(\d+)"[^>]*>\s*Edit\s*</a>', html)]
    return gw_ids

s = requests.Session()
response = login(s, USERNAME, PASSWORD)

if response.status_code != 200:
    raise Exception(f"Login failed with status code {response.status_code}")

print("Login successful!")

for gw_id in get_avaliable_gws(s):
    print(f"Making predictions for Game Week {gw_id}...")
    do_predictions(s, gw_id)
    print(f"Predictions for Game Week {gw_id} submitted successfully!")