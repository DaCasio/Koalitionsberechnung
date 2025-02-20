#!/usr/bin/env python3
"""
Dieses Skript ruft Umfragedaten von wahlrecht.de ab, berechnet den Durchschnittswert pro Partei
und ermittelt mögliche Regierungskoalitionen basierend auf den aktuellen Umfragewerten.
Die Ergebnisse werden in data.json gespeichert.
"""

import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import json
from itertools import combinations

def fetch_poll_data():
    """
    Ruft die Umfragedaten von wahlrecht.de ab, parst die Tabelle und berechnet den Durchschnitt
    aller verfügbaren Daten. Dabei werden alle Datensätze berücksichtigt.
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
        ("FREIE WÄHLER", "frw"),
        ("BSW", "bsw"),
        ("Sonstige", "son")
    ]
    
    poll_data = {}
    # Gehe durch die Konfiguration und extrahiere die Umfragewerte
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
    
    # Konvertiere den Index in Datumsobjekte – passe das Format bei Bedarf an
    df.index = pd.to_datetime(df.index, format="%d.%m.%Y", errors="coerce")
    logging.info("DataFrame nach Konvertierung des Datumsindex:")
    logging.info(df.head())

    # Bereinige den DataFrame: Ersetze 0.0 durch NA und entferne komplett leere Zeilen
    df_cleaned = df.replace(0.0, pd.NA).dropna(how="all")
    
    # Berechne den Durchschnittswert je Partei und runde auf eine Nachkommastelle
    avg_values = df_cleaned.mean().round(1).to_dict()
    logging.info("Durchschnittswerte:")
    logging.info(avg_values)
    
    return avg_values

def calculate_coalitions(poll_data, threshold=5.0, majority=50.0):
    """
    Berechnet mögliche Koalitionen, die mindestens 50% erreichen, basierend auf Parteien,
    die über der 5%-Hürde liegen. Die CDU/CSU muss in jeder Koalition enthalten sein.
    
    Spezielle Regeln:
    - Koalitionen mit AfD: Es wird nur die minimale Kombination (CDU/CSU + AfD) berücksichtigt.
    - Koalitionen ohne AfD: Es muss immer auch die SPD enthalten sein.
    """
    # Filtere Parteien, die über der Hürde liegen
    eligible_parties = {k: v for k, v in poll_data.items() if v >= threshold}
    logging.info(f"Berücksichtigte Parteien: {eligible_parties}")

    coalitions = {"with_afd": [], "without_afd": []}

    # Koalition mit AfD: Nur die Kombination CDU/CSU + AfD, wenn beide vorhanden sind
    if "CDU/CSU" in eligible_parties and "AfD" in eligible_parties:
        total = eligible_parties["CDU/CSU"] + eligible_parties["AfD"]
        coalition = {
            "parties": ["CDU/CSU", "AfD"],
            "total": round(total, 1),
            "possible": total >= majority,
        }
        coalitions["with_afd"].append(coalition)

    # Koalitionen ohne AfD: Nur Kombinationen aus Parteien (ohne AfD), die mindestens 2 Parteien enthalten
    # und zwingend CDU/CSU sowie SPD beinhalten.
    non_afd_parties = {k: v for k, v in eligible_parties.items() if k != "AfD"}
    for r in range(2, len(non_afd_parties) + 1):
        for combo in combinations(non_afd_parties.keys(), r):
            if "CDU/CSU" not in combo or "SPD" not in combo:
                continue
            total = sum(non_afd_parties[p] for p in combo)
            if total < majority:
                continue
            coalition = {
                "parties": list(combo),
                "total": round(total, 1),
                "possible": True,
            }
            coalitions["without_afd"].append(coalition)

    return coalitions

def save_to_json(data):
    """
    Speichert das Ergebnis (Koalitionen) in der data.json.
    """
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
