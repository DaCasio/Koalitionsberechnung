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

    # Extrahiere Institute und Datumsangaben
    header_row = table.find("tr", {"id": "datum"})
    institutes = [
        span.text.strip() 
        for span in header_row.find_all("span", class_="li")
    ][1:]  # Erste Spalte überspringen

    # Vollständige Parteienkonfiguration
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

    # Extrahiere Umfragewerte
    poll_data = {}
    for party_name, party_id in parties_config:
        row = table.find("tr", {"id": party_id})
        if not row:
            print(f"Warnung: Zeile für {party_name} nicht gefunden")
            continue
            
        cells = row.find_all("td")[1:]
        values = []
        for cell in cells:
            text = cell.text.strip()
            # Säubern der Daten
            text = text.replace('%', '').replace(',', '.').replace('–', '0')
            try:
                values.append(float(text))
            except ValueError:
                values.append(0.0)  # Setze 0 bei fehlenden Werten
                
        poll_data[party_name] = values

    # Erstelle DataFrame mit Validierung
    df = pd.DataFrame(poll_data, index=institutes)
    
    # Datumskonvertierung mit Fehlerbehandlung
    df.index = pd.to_datetime(
        df.index, 
        format="%d.%m.%Y", 
        errors="coerce"
    )
    
    # Filterung der letzten 14 Tage
    cutoff_date = datetime.now() - timedelta(days=14)
    df_filtered = df[df.index >= cutoff_date]

    # Behandlung fehlender Werte
    df_filtered = df_filtered.replace(0.0, pd.NA).dropna(how="all")
    
    # Durchschnittsberechnung mit Rundung
    avg_values = df_filtered.mean().round(1).to_dict()
    
    print("Aktuelle Durchschnittswerte:")
    for party, value in avg_values.items():
        print(f"{party}: {value}%")
    
    return avg_values

# Rest des Codes (calculate_coalitions, save_to_json) unverändert
