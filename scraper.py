import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import json

def fetch_poll_data():
    url = "https://www.wahlrecht.de/umfragen/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "wilko"})

    # Extrahiere Veröffentlichungsdaten (Header)
    release_dates = [
        span.text.strip()
        for span in table.find("tr", id="datum").find_all("span", class_="li")
    ][1:]  # Erste Zelle ist leer

    # Parteien und ihre Zeilen-IDs
    parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD", "BSW"]
    party_ids = ["cdu", "spd", "gru", "fdp", "lin", "afd", "bsw"]

    # Extrahiere Umfragewerte
    data = []
    for party_id in party_ids:
        row = table.find("tr", id=party_id)
        cells = row.find_all("td")[1:]  # Erste Zelle ist der Parteiname
        values = [cell.text.strip().replace("%", "") for cell in cells]
        data.append(values)

    # Erstelle DataFrame
    df = pd.DataFrame(data, index=parties, columns=release_dates).T

    # Konvertiere Datum und filtere die letzten 14 Tage
    df["Datum"] = pd.to_datetime(df.index, format="%d.%m.%Y", errors="coerce")
    two_weeks_ago = datetime.now() - timedelta(days=14)
    df_filtered = df[df["Datum"] >= two_weeks_ago]

    print("Gefilterte Daten:\n", df_filtered.head())  # Debugging

    # Konvertiere Prozentwerte
    for party in parties:
        df_filtered[party] = pd.to_numeric(df_filtered[party], errors="coerce")

    return df_filtered

# Rest des Codes (calculate_weekly_average, calculate_coalitions, save_to_json) bleibt unverändert
