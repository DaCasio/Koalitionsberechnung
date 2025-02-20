# scraper.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import json
from itertools import combinations

def fetch_poll_data():
    url = "https://www.wahlrecht.de/umfragen/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "wilko"})

    # Extrahiere alle Überschriftenspalten
    header_row = table.find("tr", id="datum")
    release_dates = [
        span.text.strip() 
        for span in header_row.find_all("span", class_="li")
    ][1:]  # Erste Spalte überspringen
    
    print(f"Gefundene Umfragedaten für {len(release_dates)} Institute")

    # Definiere alle Parteien und ihre HTML-IDs
    parties_config = [
        ("CDU/CSU", "cdu"),
        ("SPD", "spd"),
        ("GRÜNE", "gru"),
        ("FDP", "fdp"),
        ("DIE LINKE", "lin"),
        ("AfD", "afd"),
        ("FREIE WÄHLER", "frw"),
        ("BSW", "bsw"),
        ("Sonstige", "son")
    ]

    # Extrahiere die Umfragewerte
    data = []
    party_names = []
    for party_name, party_id in parties_config:
        row = table.find("tr", id=party_id)
        if not row:
            print(f"Warnung: Zeile für {party_name} nicht gefunden")
            continue
            
        cells = row.find_all("td")[1:]  # Erste Zelle überspringen
        values = [cell.text.strip().replace("%", "").replace(",", ".") for cell in cells]
        
        # Auf Längengleichheit prüfen
        if len(values) != len(release_dates):
            print(f"Warnung: {party_name} hat {len(values)} Werte, erwartet {len(release_dates)}")
            continue
            
        data.append(values)
        party_names.append(party_name)

    print(f"Verarbeitete {len(party_names)} Parteien:")
    print(party_names)

    # Erstelle DataFrame
    df = pd.DataFrame(data, index=party_names, columns=release_dates).T
    
    # Datumskonvertierung und Filterung
    df["Datum"] = pd.to_datetime(df.index, format="%d.%m.%Y", errors="coerce")
    two_weeks_ago = datetime.now() - timedelta(days=14)
    df_filtered = df[df["Datum"] >= two_weeks_ago]

    # Wertekonvertierung
    for party in party_names:
        df_filtered[party] = pd.to_numeric(df_filtered[party], errors="coerce")

    # Durchschnitt berechnen
    avg_values = df_filtered[party_names].mean().to_dict()
    
    print("\nDurchschnittswerte der letzten 14 Tage:")
    for party, value in avg_values.items():
        print(f"{party}: {value:.1f}%")
    
    return avg_values

# Rest des Codes (calculate_coalitions, save_to_json) bleibt gleich
