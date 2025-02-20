#!/usr/bin/env python3
# scraper.py

import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import json
from itertools import combinations

def fetch_poll_data():
    """
    Diese Funktion ruft die Umfragedaten von wahlrecht.de ab,
    parst die Tabelle und berechnet den Durchschnitt aller verfügbaren Daten.
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
    logging.info(f"Institute gefunden: {institutes}")

    # Konfiguration der Parteien: (Anzeigename, HTML-Zeilen-ID)
    parties_config = [
        ("CDU/CSU", "cdu"),
        ("SPD", "spd"),
        ("GRÜNE", "gru"),
        ("FDP", "fdp"),
        ("DIE LINKE", "lin"),
        ("AfD", "afd"),
        ("FREIE WÄHLER", "frw"),  # Hinzugefügt
        ("BSW", "bsw"),
        ("Sonstige", "son")       # Hinzugefügt
    ]

    poll_data = {}
    # Gehe durch die Konfiguration und extrahiere die Werte
    for party_name, party_id in parties_config:
        row = table.find("tr", {"id": party_id})
        if not row:
            logging.warning(f"Zeile für {party_name} nicht gefunden")
            continue

        cells = row.find_all("td")[1:]
        values = []
        for cell in cells:
            text = cell.text.strip()
            # Bereinige den Wert: Entferne '%' und ersetze ',' durch '.'
            text = text.replace('%', '').replace(',', '.').replace('–', '0')
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

    # Konvertiere den Index in Datum(e) – passe das Format bei Bedarf an
    df.index = pd.to_datetime(df.index, format="%d.%m.%Y", errors="coerce")
    logging.info("DataFrame nach Konvertierung des Datumsindex:")
    logging.info(df.head())

    # Ersetze 0.0 durch NA und entferne Zeilen, die komplett leer sind
    df_cleaned = df.replace(0.0, pd.NA).dropna(how="all")

    # Berechne den Durchschnittswert je Partei
    avg_values = df_cleaned.mean().round(1).to_dict()
    logging.info("Durchschnittswerte:")
    logging.info(avg_values)
    
    return avg_values

def calculate_coalitions(poll_data, threshold=5.0, majority=50.0):
    """
    Berechnet mögliche Koalitionen, die mindestens 50% erreichen,
    basierend auf den über der 5%-Hürde liegenden Parteien. Die CDU/CSU 
    muss stets Teil der Koalition sein.
    """
    # Wähle alle Parteien, die über der Hürde liegen
    eligible_parties = {k: v for k, v in poll_data.items() if v >= threshold}
    if not eligible_parties:
        logging.warning("Keine Parteien über der 5%-Hürde gefunden!")
    logging.info(f"Berücksichtigte Parteien: {eligible_parties}")

    # Initialisiere das Ergebnis-Dictionary
    coalitions = {"with_afd": [], "without_afd": []}
    
    # Erzeuge Kombinationen (mind. 2 Parteien) und prüfe, ob CDU/CSU enthalten ist
    for r in range(2, len(eligible_parties) + 1):
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
    
    logging.info("Ermittelte Koalitionen mit AfD:")
    logging.info(coalitions['with_afd'])
    logging.info("Ermittelte Koalitionen ohne AfD:")
    logging.info(coalitions['without_afd'])
    
    return coalitions

def save_to_json(data):
    """
    Speichert das Ergebnis (Koalitionen) in der data.json.
    """
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    try:
        # Konfiguration des Loggings (Ausgabe in Konsole und logfile)
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
            raise ValueError("Keine Daten zum Berechnen gefunden.")
        
        logging.info("Berechne mögliche Koalitionen...")
        coalitions = calculate_coalitions(poll_data)
        if not coalitions["with_afd"] and not coalitions["without_afd"]:
            logging.warning("Keine möglichen Koalitionen gefunden!")
        
        logging.info("Speichere Ergebnisse...")
        save_to_json(coalitions)
        logging.info("Prozess erfolgreich abgeschlossen!")
        
    except Exception as e:
        logging.error(f"Kritischer Fehler: {str(e)}", exc_info=True)
