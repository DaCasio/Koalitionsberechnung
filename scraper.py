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
    
    # Extrahiere die Veröffentlichungsdaten aus der 'datum'-Zeile
    release_dates = [
        span.text.strip() 
        for span in table.find("tr", id="datum").find_all("span", class_="li")
    ][1:]  # Skip empty first cell

    # Parteien und deren Zeilen-IDs
    parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD", "BSW"]
    party_ids = ["cdu", "spd", "gru", "fdp", "lin", "afd", "bsw"]
    
    # Extrahiere Umfragewerte für jede Partei (ignoriere erste Spalte)
    data = []
    for pid in party_ids:
        row = table.find("tr", id=pid)
        values = [cell.text.strip().replace("%", "") for cell in row.find_all("td")][1:]  # Erste Zelle (Parteiname) überspringen
        data.append(values)
    
    # DataFrame mit korrekten Spalten erstellen
    df = pd.DataFrame(data, index=parties, columns=release_dates).T
    
    # Datum konvertieren und filtern
    df["Datum"] = pd.to_datetime(df.index, format="%d.%m.%Y", errors="coerce")
    two_weeks_ago = datetime.now() - timedelta(days=14)
    df_filtered = df[df["Datum"] >= two_weeks_ago]
    
    # Konvertiere Prozentwerte
    for party in parties:
        df_filtered[party] = pd.to_numeric(df_filtered[party], errors="coerce")
    
    return df_filtered

# Rest des Codes (calculate_weekly_average, calculate_coalitions, etc.) bleibt unverändert
