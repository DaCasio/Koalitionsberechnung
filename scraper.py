# scraper.py
import logging  # Import für Logging hinzugefügt
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

    if not table:
        logging.error("Umfragetabelle nicht gefunden - HTML-Struktur möglicherweise geändert")
        raise ValueError("Umfragetabelle nicht gefunden")

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
        ("FREIE WÄHLER", "frw"),  # Hinzugefügt
        ("BSW", "bsw"),
        ("Sonstige", "son")  # Hinzugefügt
    ]

    # Extrahiere Umfragewerte
    poll_data = {}
    for party_name, party_id in parties_config:
        row = table.find("tr", {"id": party_id})
        if not row:
            logging.warning(f"Zeile für {party_name} nicht gefunden")
            continue
            
        cells = row.find_all("td")[1:]
        values = []
        for cell in cells:
            text = cell.text.strip()
            text = text.replace('%', '').replace(',', '.').replace('–', '0')
            try:
                values.append(float(text))
            except ValueError:
                logging.warning(f"Ungültiger Wert für {party_name}: '{text}'")
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
    
    logging.info("Aktuelle Durchschnittswerte:")
    for party, value in avg_values.items():
        logging.info(f"{party}: {value}%")
    
    return avg_values

def calculate_coalitions(poll_data, threshold=5.0, majority=50.0):
    eligible_parties = {k: v for k, v in poll_data.items() if v >= threshold}
    logging.info(f"Berücksichtigte Parteien: {eligible_parties}")

    coalitions = {"with_afd": [], "without_afd": []}
    
    for r in range(1, len(eligible_parties)+1):
        for combo in combinations(eligible_parties.keys(), r):
            if "CDU/CSU" not in combo:
                continue
                
            total = sum(eligible_parties[p] for p in combo)
            afd_included = "AfD" in combo
            bsw_included = "BSW" in combo
            
            coalition = {
                "parties": list(combo),
                "total": round(total, 1),
                "possible": total >= majority,
                "bsw": bsw_included
            }
            
            key = "with_afd" if afd_included else "without_afd"
            coalitions[key].append(coalition)
    
    for key in coalitions:
        coalitions[key].sort(
            key=lambda x: (-x["total"], len(x["parties"])),
            reverse=False
        )
    
    return coalitions

def save_to_json(data):
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("scraper.log"),
                logging.StreamHandler()
            ]
        )
        
        logging.info("Starte Datenerfassung...")
        poll_data = fetch_poll_data()
        
        logging.info("Berechne mögliche Koalitionen...")
        coalitions = calculate_coalitions(poll_data)
        
        logging.info("Speichere Ergebnisse...")
        save_to_json(coalitions)
        
        logging.info("Prozess erfolgreich abgeschlossen!")
        
    except Exception as e:
        logging.error(f"Kritischer Fehler: {str(e)}", exc_info=True)
