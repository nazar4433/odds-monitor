import requests
import csv
import time
from datetime import datetime

API_KEY = 'a61931e1b164f8bb7886e2098adb5f72'
TELEGRAM_TOKEN = '8966581535:AAHdUqun4y_2SKVSPnxJXJy2hrhbmie87ow'
TELEGRAM_CHAT_ID = '384201189'

def send_telegram(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message})

def check_odds():
    url = 'https://api.the-odds-api.com/v4/sports/soccer/odds/'
    params = {'apiKey': API_KEY, 'regions': 'eu', 'markets': 'h2h'}

    response = requests.get(url, params=params)
    games = response.json()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    current = {}
    for game in games:
        if game['bookmakers']:
            bookmaker = game['bookmakers'][0]
            outcomes = bookmaker['markets'][0]['outcomes']
            odds = {o['name']: o['price'] for o in outcomes}
            key = f"{game['home_team']} vs {game['away_team']}"
            current[key] = {
                'home': odds.get(game['home_team'], 0),
                'away': odds.get(game['away_team'], 0),
                'draw': odds.get('Draw', 0)
            }

    previous = {}
    try:
        with open('odds_history.csv', 'r') as file:
            rows = list(csv.reader(file))
            for row in rows[-50:]:
                if len(row) == 6:
                    key = f"{row[1]} vs {row[2]}"
                    previous[key] = {
                        'home': float(row[3]) if row[3] != '-' else 0,
                        'away': float(row[4]) if row[4] != '-' else 0,
                        'draw': float(row[5]) if row[5] != '-' else 0
                    }
    except FileNotFoundError:
        pass

    THRESHOLD = 0.05
    print(f"\n🔍 Аналіз о {timestamp}")

    for key, curr in current.items():
        if key in previous:
            prev = previous[key]
            for side, label in [('home', 'Хазяї'), ('away', 'Гості'), ('draw', 'Нічия')]:
                if prev[side] > 0:
                    change = abs(curr[side] - prev[side]) / prev[side]
                    if change >= THRESHOLD:
                        direction = "⬆️" if curr[side] > prev[side] else "⬇️"
                        msg = (f"🚨 АНОМАЛІЯ: {key}\n"
                               f"{label}: {prev[side]} → {curr[side]} {direction} ({change*100:.1f}%)")
                        print(msg)
                        send_telegram(msg)

    with open('odds_history.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        for game in games:
            if game['bookmakers']:
                bookmaker = game['bookmakers'][0]
                outcomes = bookmaker['markets'][0]['outcomes']
                odds = {o['name']: o['price'] for o in outcomes}
                writer.writerow([
                    timestamp,
                    game['home_team'],
                    game['away_team'],
                    odds.get(game['home_team'], '-'),
                    odds.get(game['away_team'], '-'),
                    odds.get('Draw', '-')
                ])

    print(f"✅ Збережено {len(games)} матчів")

# Головний цикл — працює безперервно
print("🚀 Бот запущено!")
send_telegram("🚀 OddsMonitor запущено і працює!")

while True:
    check_odds()
    print("⏳ Наступна перевірка через 10 хвилин...")
    time.sleep(600)