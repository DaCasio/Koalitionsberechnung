# scraper.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from itertools import combinations

def fetch_poll_data():
    url = "https://www.wahlrecht.de/umfragen/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "wilko"})

    # Extrahiere Veröffentlichungsdaten
    release_dates = [
        span.text.strip() 
        for span in table.find("tr", id="datum").find_all("span", class_="li")
    ][1:]

    # Parteien und ihre Zeilen-IDs
    parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD", "BSW"]
    party_ids = ["cdu", "spd", "gru", "fdp", "lin", "afd", "bsw"]

    # Extrahiere Umfragewerte
    data = []
    for party_id in party_ids:
        row = table.find("tr", id=party_id)
        cells = row.find_all("td")[1:]
        values = [cell.text.strip().replace("%", "").replace(",", ".") for cell in cells]
        data.append(values)

    # Erstelle DataFrame
    df = pd.DataFrame(data, index=parties, columns=release_dates).T
    
    # Konvertiere Datum und filtere die letzten 14 Tage
    df["Datum"] = pd.to_datetime(df.index, format="%d.%m.%Y", errors="coerce")
    two_weeks_ago = datetime.now() - timedelta(days=14)
    df_filtered = df[df["Datum"] >= two_weeks_ago]

    # Konvertiere Prozentwerte
    for party in parties:
        df_filtered[party] = pd.to_numeric(df_filtered[party], errors="coerce")

    return df_filtered[parties].mean().to_dict()

def calculate_coalitions(poll_data):
    threshold = 5.0
    majority = 50.0
    parties = [p for p, v in poll_data.items() if v >= threshold]
    
    coalitions = {"with_afd": [], "without_afd": []}
    
    # Generiere alle möglichen Kombinationen
    for r in range(2, len(parties)+1):
        for combo in combinations(parties, r):
            if "CDU/CSU" not in combo:
                continue
                
            total = sum(poll_data[p] for p in combo)
            afd_included = "AfD" in combo
            bsw_included = "BSW" in combo
            
            entry = {
                "parties": list(combo),
                "total": round(total, 1),
                "possible": total >= majority,
                "bsw": bsw_included
            }
            
            key = "with_afd" if afd_included else "without_afd"
            coalitions[key].append(entry)
    
    # Sortiere die Ergebnisse
    for key in coalitions:
        coalitions[key] = sorted(
            coalitions[key],
            key=lambda x: (-x["total"], len(x["parties"]))
        )
    
    return coalitions

def save_to_json(data):
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    try:
        print("Starte Datenerfassung...")
        poll_data = fetch_poll_data()
        print("Umfragedaten:", poll_data)
        
        print("Berechne Koalitionen...")
        coalitions = calculate_coalitions(poll_data)
        
        print("Speichere Daten...")
        save_to_json(coalitions)
        
        print("Erfolgreich abgeschlossen!")
    except Exception as e:
        print(f"Fehler aufgetreten: {str(e)}")
        raise
