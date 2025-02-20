# scraper.py
import logging
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

    logging.info(f"Institute gefunden: {institutes}")

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
                
        # Überprüfe, ob die Anzahl der Werte mit der Anzahl der Institute übereinstimmt
        if len(values) != len(institutes):
            logging.warning(f"Anzahl der Werte für {party_name} stimmt nicht überein: {len(values)} Werte, {len(institutes)} Institute")
            continue
        
        poll_data[party_name] = values

    logging.info(f"Rohdaten für Parteien: {poll_data}")

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

    logging.info(f"Gefilterte Daten (letzte 14 Tage):\n{df_filtered}")

    # Behandlung fehlender Werte
    df_filtered = df_filtered.replace(0.0, pd.NA).dropna(how="all")
    
    # Durchschnittsberechnung mit Rundung
    avg_values = df_filtered.mean().round(1).to_dict()
    
    logging.info(f"Durchschnittswerte:\n{avg_values}")
    
    return avg_values

def calculate_coalitions(poll_data, threshold=5.0, majority=50.0):
    eligible_parties = {k: v for k, v in poll_data.items() if v >= threshold}
    
    if not eligible_parties:
        logging.warning("Keine Parteien über der 5%-Hürde gefunden!")
    
    logging.info(f"Berücksichtigte Parteien: {eligible_parties}")

    coalitions = {"with_afd": [], "without_afd": []}
    
    for r in range(2, len(eligible_parties)+1):  # Mindestens zwei Parteien erforderlich
        for combo in combinations(eligible_parties.keys(), r):
            if "CDU/CSU" not in combo:
                continue
                
            total = sum(eligible_parties[p] for p in combo)
            afd_included = "AfD" in combo
            
            coalition = {
                "parties": list(combo),
                "total": round(total, 1),
                "possible": total >= majority,
            }
            
            key = "with_afd" if afd_included else "without_afd"
            coalitions[key].append(coalition)
    
    logging.info(f"Koalitionen mit AfD:\n{coalitions['with_afd']}")
    logging.info(f"Koalitionen ohne AfD:\n{coalitions['without_afd']}")

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
        
        if not poll_data:
            logging.error("Keine Umfragedaten verfügbar!")
        
        logging.info("Berechne mögliche Koalitionen...")
        
        coalitions = calculate_coalitions(poll_data)
        
        if not coalitions["with_afd"] and not coalitions["without_afd"]:
            logging.warning("Keine möglichen Koalitionen gefunden!")
        
        logging.info("Speichere Ergebnisse...")
        
        save_to_json(coalitions)
        
        logging.info("Prozess erfolgreich abgeschlossen!")
        
    except Exception as e:
        logging.error(f"Kritischer Fehler: {str(e)}", exc_info=True)
