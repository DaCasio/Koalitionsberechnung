#!/usr/bin/env python3
# scraper.py
# Dieses Skript ruft die Wahlumfragedaten von wahlrecht.de ab, berechnet anhand der Durchschnittswerte
# die Sitzverteilung (basierend auf den Zweitstimmen) und ermittelt alle Koalitionen, die mindestens
# eine Mehrheit (630/2+1 ≈ 316 Sitze) erzielen. Anschließend wird das Ergebnis in ein LaMetric-kompatibles
# JSON-Format überführt.

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

# Entferne "Sonstige" in der Filterung – niemand kann mit "Sonstige" koalieren.
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
    Lädt die Umfragedaten von wahlrecht.de, parst die HTML-Tabelle und 
    berechnet den Durchschnittswert für jede Partei. Rückgabe: Dictionary, z.B. {'CDU/CSU': 35.0, 'SPD': 18.0, ...}.
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
            text = cell.text.strip().replace('%', '').replace(',', '.').replace('–', '0')
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
    Filtert Parteien heraus, die weniger als 5 % der Zweitstimmen erhalten, 
    und entfernt 'Sonstige' komplett.
    """
    total_votes = sum(poll_data.values())
    filtered = {party: votes for party, votes in poll_data.items() 
                if (votes / total_votes) * 100 >= 5 and party != "Sonstige"}
    logging.debug("Gefilterte Parteien (>=5%% und ohne 'Sonstige'): %s", filtered)
    return filtered

# ---------------------------------------------------------------------
def calculate_seat_distribution(filtered_data):
    """
    Berechnet die Sitzverteilung basierend auf den gefilterten Zweitstimmenergebnissen.
    """
    total_votes = sum(filtered_data.values())
    distribution = {party: round((votes / total_votes) * TOTAL_SEATS) 
                    for party, votes in filtered_data.items()}
    logging.debug("Berechnete Sitzverteilung: %s", distribution)
    return distribution

# ---------------------------------------------------------------------
def calculate_majority_coalitions(seat_distribution):
    """
    Berechnet alle möglichen Koalitionen (Kombinationen ab 2 Parteien) 
    basierend auf der Sitzverteilung, deren Gesamtsitze ≥ MAJORITY_SEATS betragen.
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
        logging.info("Anzahl gefundener Koalitionen: %s", len(coalitions))
    return coalitions

# ---------------------------------------------------------------------
def split_text(text):
    """
    Teilt den Text in Segmente à maximal 7 Zeichen.
    Kürzt "GRÜNE" zu "GRÜN", "DIE LINKE" zu "LINKE". Vermeidet eine letzte Segmentierung, die nur aus einem einzelnen Buchstaben besteht.
    """
    text = text.replace("GRÜNE", "GRÜN").replace("DIE LINKE", "LINKE").replace("Sonstige", "Sonst")
    segments = [text[i:i+7] for i in range(0, len(text), 7)]
    if len(segments) > 1 and len(segments[-1]) == 1:
        segments[-2] += segments[-1]
        segments.pop(-1)
    return segments

# ---------------------------------------------------------------------
def format_for_lametric(coalitions):
    """
    Formatiert die berechneten Koalitionen in das JSON-Format der LaMetric Indicator App.
    Jede Koalition wird als Block ausgegeben:
      - Ein Frame mit den beteiligten Parteien (in 7-Zeichen-Segmenten).
      - Ein Frame mit "Gesamt:".
      - Ein Frame mit der Anzahl der Sitze (z.B. "403 Sitze").
    Es werden maximal 10 Koalitionen angezeigt.
    """
    if not coalitions:
        return {"frames": [{"text": "Keine Mehrh.", "icon": str(ICON_IDS[0])}]}
    frames = []
    for idx, coalition in enumerate(coalitions[:10]):
        if idx >= len(ICON_IDS):
            logging.warning("Nicht genügend Icon-IDs verfügbar.")
            break
        parties_str = " + ".join(coalition["parties"])
        segments = split_text(parties_str)
        for seg in segments:
            frames.append({"text": seg, "icon": str(ICON_IDS[idx])})
        frames.append({"text": "Gesamt:", "icon": str(ICON_IDS[idx])})
        frames.append({"text": f"{coalition['seats']} Sitze", "icon": str(ICON_IDS[idx])})
    logging.debug("Formatiertes LaMetric JSON: %s", frames)
    return {"frames": frames}

# ---------------------------------------------------------------------
def save_to_json(data):
    """
    Speichert die Daten im JSON-Format in der Datei data.json.
    """
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info("Daten in data.json gespeichert.")

# ---------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    try:
        # Schritt 1: Daten abrufen
        poll_data = fetch_poll_data()
        logging.info("Umfragedaten: %s", poll_data)
        
        # Schritt 2: Parteien filtern (>=5% und ohne 'Sonstige')
        filtered_data = filter_parties_by_threshold(poll_data)
        logging.info("Gefilterte Daten: %s", filtered_data)
        
        # Schritt 3: Sitzverteilung berechnen
        seat_distribution = calculate_seat_distribution(filtered_data)
        logging.info("Sitzverteilung: %s", seat_distribution)
        
        # Schritt 4: Koalitionen (≥ Mehrheitsgrenze) berechnen
        coalitions = calculate_majority_coalitions(seat_distribution)
        logging.info("Berechnete Koalitionen: %s", coalitions)
        
        # Schritt 5: Daten für LaMetric formatieren und speichern
        lametric_json = format_for_lametric(coalitions)
        logging.info("LaMetric JSON: %s", lametric_json)
        
        save_to_json(lametric_json)
        logging.info("Prozess erfolgreich abgeschlossen!")
        
    except Exception as e:
        logging.error("Ein Fehler ist aufgetreten: %s", e, exc_info=True)
