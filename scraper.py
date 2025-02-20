#!/usr/bin/env python3
# scraper.py
# Dieses Skript ruft Umfragedaten von wahlrecht.de ab, berechnet Koalitionen und erstellt ein LaMetric-kompatibles JSON-Format.

import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd
from itertools import combinations
import json

def fetch_poll_data():
    """
    Ruft die Umfragedaten von wahlrecht.de ab und berechnet den Durchschnitt aller verfügbaren Daten.
    """
    url = "https://www.wahlrecht.de/umfragen/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "wilko"})

    if not table:
        logging.error("Umfragetabelle nicht gefunden - HTML-Struktur möglicherweise geändert")
        raise ValueError("Umfragetabelle nicht gefunden")

    # Extrahiere Institute/Datumsangaben aus der Kopfzeile
    header_row = table.find("tr", {"id": "datum"})
    institutes = [span.text.strip() for span in header_row.find_all("span", class_="li")][1:]
    logging.info(f"Gefundene Institute: {institutes}")

    # Konfiguration der Parteien: (Anzeigename, HTML-Zeilen-ID)
    parties_config = [
        ("CDU/CSU", "cdu"),
        ("SPD", "spd"),
        ("GRÜNE", "gru"),
        ("FDP", "fdp"),
        ("DIE LINKE", "lin"),
        ("AfD", "afd"),
        ("FREIE WÄHLER", "frw"),
        ("Sonstige", "son")
    ]

    poll_data = {}
    for party_name, party_id in parties_config:
        row = table.find("tr", {"id": party_id})
        if not row:
            logging.warning(f"Zeile für {party_name} nicht gefunden")
            continue

        cells = row.find_all("td")[1:len(institutes)+1]
        values = []
        for cell in cells:
            text = cell.text.strip().replace('%', '').replace(',', '.').replace('–', '0')
            try:
                values.append(float(text))
            except ValueError:
                logging.warning(f"Ungültiger Wert für {party_name}: '{text}'")
                values.append(0.0)

        if len(values) != len(institutes):
            logging.warning(f"Anzahl Werte für {party_name} stimmt nicht überein: {len(values)} vs. {len(institutes)} Institute")
            continue

        poll_data[party_name] = values

    logging.info(f"Rohdaten für Parteien: {poll_data}")

    # Erstelle ein DataFrame mit den Umfragedaten
    df = pd.DataFrame(poll_data, index=institutes)
    df.index.name = "Datum"

    # Berechne den Durchschnittswert je Partei
    avg_values = df.mean().round(1).to_dict()
    logging.info(f"Durchschnittswerte: {avg_values}")
    
    return avg_values

def calculate_coalitions(poll_data, threshold=5.0, majority=50.0):
    """
    Berechnet mögliche Koalitionen basierend auf Parteien mit mindestens 5% Stimmenanteil.
    Berücksichtigt:
      - Nur Koalitionen mit mindestens 50 % (true).
      - SPD, Grüne und Linke koalieren nicht mit der AfD.
      - Begrenzung auf maximal 3 Partner.
    """
    eligible_parties = {k: v for k, v in poll_data.items() if v >= threshold}
    
    if not eligible_parties:
        logging.warning("Keine Parteien über der 5%-Hürde gefunden!")
    
    coalitions = {"with_afd": [], "without_afd": []}
    
    for r in range(2, 4):  # Nur Kombinationen mit 2 oder 3 Parteien
        for combo in combinations(eligible_parties.keys(), r):
            if "CDU/CSU" not in combo:
                continue
            
            total = sum(eligible_parties[p] for p in combo)
            afd_included = "AfD" in combo
            
            # Filtere Koalitionen mit AfD und SPD/Grüne/Linke aus
            if afd_included and any(party in combo for party in ["SPD", "GRÜNE", "DIE LINKE"]):
                continue
            
            coalition = {
                "parties": list(combo),
                "total": round(total, 1),
                "possible": total >= majority,
            }
            
            key = "with_afd" if afd_included else "without_afd"
            coalitions[key].append(coalition)

    logging.info(f"Koalitionen mit AfD: {coalitions['with_afd']}")
    logging.info(f"Koalitionen ohne AfD: {coalitions['without_afd']}")
    
    return coalitions

def format_for_lametric(coalitions):
    """
    Formatiert die Koalitionsdaten im LaMetric-kompatiblen JSON-Format.
    """
    frames = []
    
    # Waage-Icon-ID (Beispiel)
    icon_id = "661"  # Beispiel-ID für eine Waage
    
    for key, coalition_list in coalitions.items():
        for coalition in coalition_list:
            if coalition["possible"]:  # Nur Koalitionen mit mindestens 50%
                frames.append({
                    "text": f"{', '.join(coalition['parties'])}: {coalition['total']}%",
                    "icon": icon_id
                })
    
    return {"frames": frames}

def save_to_json(data, filename="data.json"):
    """
    Speichert das Ergebnis (Koalitionen) oder LaMetric-Daten in einer JSON-Datei.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    try:
        # Logging-Konfiguration
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
            raise ValueError("Keine Daten zum Berechnen gefunden.")
        
        logging.info("Berechne mögliche Koalitionen...")
        
        coalitions = calculate_coalitions(poll_data)
        
        if not coalitions["with_afd"] and not coalitions["without_afd"]:
            logging.warning("Keine möglichen Koalitionen gefunden!")
        
        logging.info("Formatiere Daten für LaMetric...")
        
        lametric_data = format_for_lametric(coalitions)
        
        save_to_json(lametric_data, filename="lametric.json")
        
        logging.info("Prozess erfolgreich abgeschlossen!")
    
    except Exception as e:
        logging.error(f"Kritischer Fehler: {str(e)}", exc_info=True)
