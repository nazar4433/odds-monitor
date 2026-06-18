import requests
import csv
import time
from datetime import datetime, timezone

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

    # Тільки майбутні матчі
    now = datetime.now(timezone.utc)
    games = [g for g in games if datetime.fromisoformat(g['commence_time'].replace('Z', '+00:00')) > now]

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n🔍 Аналіз о {timestamp} — матчів: {len(games)}")

    # Поточні коефіцієнти
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

    # Читаємо ПЕРШИЙ знімок для кожного матчу (не попередній!)
    first_snapshot = {}
    try:
        with open('odds_history.csv', 'r') as file:
            rows = list(csv.reader(file))
            for row in rows:
                if len(row) == 6:
                    key = f"{row[1]} vs {row[2]}"
                    # Записуємо тільки якщо ще немає — тобто перший запис
                    if key not in first_snapshot:
                        try:
                            first_snapshot[key] = {
                                'home': float(row[3]) if row[3] != '-' else 0,
                                'away': float(row[4]) if row[4] != '-' else 0,
                                'draw': float(row[5]) if row[5] != '-' else 0
                            }
                        except ValueError:
                            pass
    except FileNotFoundError:
        pass

    # Алерти вже надіслані (щоб не спамити)
    alerted = set()
    try:
        with open('alerted.txt', 'r') as f:
            alerted = set(f.read().splitlines())
    except FileNotFoundError:
        pass

    THRESHOLD = 0.05  # 5%
    MAX_ODDS = 4.0    # Ігноруємо великі коефіцієнти аутсайдерів

    new_alerts = []

    for key, curr in current.items():
        if key not in first_snapshot:
            continue

        first = first_snapshot[key]

        for side, label in [('home', 'Хазяї'), ('away', 'Гості'), ('draw', 'Нічия')]:
            if first[side] <= 0 or curr[side] <= 0:
                continue

            # Ігноруємо великі коефіцієнти
            if first[side] > MAX_ODDS and curr[side] > MAX_ODDS:
                continue

            change = (curr[side] - first[side]) / first[side]
            abs_change = abs(change)

            if abs_change >= THRESHOLD:
                alert_key = f"{key}_{side}_{round(curr[side], 2)}"
                if alert_key in alerted:
                    continue

                direction = "⬆️" if change > 0 else "⬇️"

                # Визначаємо тип сигналу
                if change < 0 and curr[side] < 2.5:
                    signal = "💰 Гроші на фаворита"
                elif change < 0 and first[side] > 2.5:
                    signal = "⚠️ Аутсайдер стає фаворитом"
                elif abs_change > 0.15:
                    signal = "🔴 Різкий рух"
                else:
                    signal = "📊 Рух лінії"

                msg = (f"🚨 {signal}\n"
                       f"{key}\n"
                       f"{label}: {first[side]} → {curr[side]} {direction} ({abs_change*100:.1f}%)\n"
                       f"від початкової лінії")

                print(msg)
                send_telegram(msg)
                new_alerts.append(alert_key)

    # Зберігаємо надіслані алерти
    if new_alerts:
        with open('alerted.txt', 'a') as f:
            f.write('\n'.join(new_alerts) + '\n')

    # Зберігаємо знімок
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

print("🚀 Бот запущено!")
send_telegram("🚀 OddsMonitor оновлено — розумна фільтрація активна!")

while True:
    check_odds()
    print("⏳ Наступна перевірка через 10 хвилин...")
    time.sleep(600)