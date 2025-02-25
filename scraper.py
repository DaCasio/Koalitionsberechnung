#!/usr/bin/env python3
# scraper.py
# Dieses Skript lädt Wahlumfragedaten von wahlrecht.de, berechnet die Sitzverteilung
# (basierend auf den Zweitstimmen) und ermittelt alle Koalitionen, die bei 630 Sitzen
# eine Mehrheit (≥316 Sitze) erzielen. Anschließend werden die Koalitionsdaten im LaMetric-
# kompatiblen JSON-Format ausgegeben, wobei jede Partei separat in einem 7‑Zeichen‑Frame dargestellt wird.

import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd
from itertools import combinations
import json

# Konfigurationen
PARTIES_CONFIG = [
    ("CDU/CSU", "cdu"),
    ("SPD", "spd"),
    ("GRÜNE", "gru"),
    ("FDP", "fdp"),
    ("DIE LINKE", "lin"),
    ("AfD", "afd"),
    ("FREIE WÄHLER", "frw"),
    ("Sonstige", "son")
]

# ICON_IDS – Nummer-Icon-IDs (bitte passe diese ggf. an)
ICON_IDS = [
    16880, 16881, 16882, 16883, 16884, 16885, 16886, 16887,
    16888, 16889, 16879, 16890, 16891, 16892, 16893, 16894,
    16895, 16896, 16898, 16899, 16900, 16901, 16905, 16906,
    16907, 16908, 16909, 16910, 16911, 16912, 16913
]

TOTAL_SEATS = 630
MAJORITY_SEATS = TOTAL_SEATS // 2 + 1  # ca. 316 Sitze

# ---------------------------------------------------------------------
def fetch_poll_data():
    """
    Lädt die HTML-Tabelle von wahlrecht.de, parst sie und berechnet den Durchschnittswert
    für jede Partei. Rückgabe: Dictionary, z.B. {'CDU/CSU': 35.0, 'SPD': 18.0, ...}.
    """
    url = "https://www.wahlrecht.de/umfragen/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "wilko"})
    if not table:
        raise ValueError("Umfragetabelle nicht gefunden - HTML-Struktur möglicherweise geändert")
    header_row = table.find("tr", {"id": "datum"})
    institutes = [span.text.strip() for span in header_row.find_all("span", class_="li")][1:]
    poll_data = {}
    for party_name, party_id in PARTIES_CONFIG:
        row = table.find("tr", {"id": party_id})
        if not row:
            continue
        cells = row.find_all("td")[1:len(institutes)+1]
        values = []
        for cell in cells:
            text = cell.text.strip().replace('%','').replace(',', '.').replace('–', '0')
            try:
                values.append(float(text))
            except ValueError:
                values.append(0.0)
        if len(values) == len(institutes):
            poll_data[party_name] = values
    df = pd.DataFrame(poll_data)
    avg = df.mean().round(1).to_dict()
    logging.debug("Durchschnittliche Wahlergebnisse: %s", avg)
    return avg

# ---------------------------------------------------------------------
def filter_parties_by_threshold(poll_data):
    """
    Filtert Parteien, die weniger als 5 % der Gesamtstimmen erhalten, und entfernt 'Sonstige'.
    """
    total_votes = sum(poll_data.values())
    filtered = {party: votes for party, votes in poll_data.items() 
                if (votes / total_votes)*100 >= 5 and party != "Sonstige"}
    logging.debug("Gefilterte Parteien (>=5%% und ohne 'Sonstige'): %s", filtered)
    return filtered

# ---------------------------------------------------------------------
def calculate_seat_distribution(filtered_data):
    """
    Berechnet die Sitzverteilung der gefilterten Zweitstimmenergebnisse.
    """
    total_votes = sum(filtered_data.values())
    distribution = {party: round((votes / total_votes) * TOTAL_SEATS) 
                    for party, votes in filtered_data.items()}
    logging.debug("Berechnete Sitzverteilung: %s", distribution)
    return distribution

# ---------------------------------------------------------------------
def calculate_majority_coalitions(seat_distribution):
    """
    Prüft alle Kombinationen von mindestens zwei Parteien (aus der Sitzverteilung)
    und gibt Liste aller Koalitionen zurück, deren Gesamt-Sitze ≥ MAJORITY_SEATS betragen.
    """
    coalitions = []
    parties = list(seat_distribution.keys())
    for r in range(2, len(parties) + 1):
        for combo in combinations(parties, r):
            seats = sum(seat_distribution[p] for p in combo)
            if seats >= MAJORITY_SEATS:
                coalitions.append({"parties": list(combo), "seats": seats})
                logging.debug("Koalition gefunden: %s, Sitze: %s", combo, seats)
    if not coalitions:
        logging.warning("Keine Koalitionen mit Mehrheit gefunden.")
    else:
        logging.info("Anzahl der gefundenen Koalitionen: %s", len(coalitions))
    return coalitions

# ---------------------------------------------------------------------
def split_text(text):
    """
    Formatiert einen Text so, dass er in einem Frame von 7 Zeichen angezeigt wird.
    Kürzt 'GRÜNE' zu 'GRÜN', 'DIE LINKE' zu 'LINKE' und 'Sonstige' zu 'Sonst'.
    Liefert als Ergebnis den Text, rechts aufgefüllt auf 7 Zeichen.
    """
    text = text.replace("GRÜNE", "GRÜN").replace("DIE LINKE", "LINKE").replace("Sonstige", "Sonst")
    # Erstelle einen String von genau 7 Zeichen (padding rechts)
    return text.ljust(7)[:7]

# ---------------------------------------------------------------------
def format_for_lametric(coalitions):
    """
    Transformiert die Koalitionsdaten in das von der LaMetric Indicator App benötigte JSON-Format.
    Für jede Koalition:
      - Es wird für jede beteiligte Partei ein eigener Frame erzeugt, wobei der Name auf 7 Zeichen formatiert wird.
      - Anschließend folgen ein Frame mit "Gesamt:" und ein Frame mit den Sitzen (z.B. "403 Sitze").
    Es werden maximal 10 Koalitionen ausgegeben.
    """
    if not coalitions:
        return {"frames": [{"text": "Keine Mehrh.", "icon": str(ICON_IDS[0])}]}
    
    frames = []
    # Wir begrenzen auf 10 Koalitionen
    for idx, coalition in enumerate(coalitions[:10]):
        if idx >= len(ICON_IDS):
            logging.warning("Nicht genügend Icon-IDs verfügbar.")
            break
        # Für jede Partei in der Koalition: Formatierung (7 Zeichen, rechts aufgefüllt)
        for party in coalition["parties"]:
            # Ersetze eventuelle lange Bezeichnungen
            formatted_party = split_text(party)
            frames.append({"text": formatted_party, "icon": str(ICON_IDS[idx])})
        frames.append({"text": "Gesamt:", "icon": str(ICON_IDS[idx])})
        frames.append({"text": f"{coalition['seats']} Sitze", "icon": str(ICON_IDS[idx])})
    logging.debug("Formatiertes LaMetric JSON: %s", frames)
    return {"frames": frames}

# ---------------------------------------------------------------------
def save_to_json(data):
    """
    Speichert das Ergebnis im JSON-Format in der Datei data.json.
    """
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info("Daten in data.json gespeichert.")

# ---------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    try:
        # Schritt 1: Umfragedaten abrufen
        poll_data = fetch_poll_data()
        logging.info("Umfragedaten: %s", poll_data)
        
        # Schritt 2: Parteien filtern (>=5% + ohne 'Sonstige')
        filtered_data = filter_parties_by_threshold(poll_data)
        logging.info("Gefilterte Daten: %s", filtered_data)
        
        # Schritt 3: Sitzverteilung berechnen
        seat_distribution = calculate_seat_distribution(filtered_data)
        logging.info("Sitzverteilung: %s", seat_distribution)
        
        # Schritt 4: Koalitionen mit Mehrheit berechnen
        coalitions = calculate_majority_coalitions(seat_distribution)
        logging.info("Berechnete Koalitionen: %s", coalitions)
        
        # Schritt 5: Formatieren für LaMetric
        lametric_json = format_for_lametric(coalitions)
        logging.info("LaMetric JSON: %s", lametric_json)
        
        # Schritt 6: JSON speichern
        save_to_json(lametric_json)
        logging.info("Prozess erfolgreich abgeschlossen!")
    except Exception as e:
        logging.error("Ein Fehler ist aufgetreten: %s", e, exc_info=True)
