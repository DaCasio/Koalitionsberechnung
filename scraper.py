#!/usr/bin/env python3
# scraper.py
# Dieses Skript ruft Umfragedaten von wahlrecht.de ab, berechnet Koalitionen und Sitzverteilungen und erstellt ein LaMetric-kompatibles JSON-Format.

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

ICON_IDS = [
    16880, 16881, 16882, 16883, 16884, 16885, 16886, 16887,
    16888, 16889, 16879, 16890, 16891, 16892, 16893, 16894,
    16895, 16896, 16898, 16899, 16900, 16901, 16905, 16906,
    16907, 16908, 16909, 16910, 16911, 16912, 16913
]

TOTAL_SEATS = 630

def fetch_poll_data():
    """
    Ruft die Umfragedaten von wahlrecht.de ab und berechnet den Durchschnitt aller verfügbaren Daten.
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

    return pd.DataFrame(poll_data).mean().round(1).to_dict()

def filter_parties_by_threshold(zweitstimmen, threshold=5):
    """
    Filtert Parteien basierend auf der Fünf-Prozent-Hürde.
    """
    total_votes = sum(zweitstimmen.values())
    return {party: votes for party, votes in zweitstimmen.items() if (votes / total_votes) * 100 >= threshold}

def calculate_seat_distribution(zweitstimmen):
    """
    Berechnet die Sitzverteilung basierend auf dem Zweitstimmenergebnis.
    """
    total_votes = sum(zweitstimmen.values())
    return {party: round((votes / total_votes) * TOTAL_SEATS) for party, votes in zweitstimmen.items()}

def calculate_majority_coalitions(seat_distribution):
    """
    Berechnet alle möglichen Koalitionen basierend auf der Sitzverteilung.
    Zeigt nur Koalitionen mit einer Mehrheit (≥316 Sitze).
    """
    majority = TOTAL_SEATS // 2 + 1
    coalitions = []

    for r in range(2, len(seat_distribution) + 1):
        for combo in combinations(seat_distribution.keys(), r):
            seats = sum(seat_distribution[party] for party in combo)
            if seats >= majority:
                coalitions.append({"parties": list(combo), "seats": seats})

    return coalitions

def split_text(text):
    """
    Teilt einen Text in mehrere Teile auf (maximal 7 Zeichen pro Teil).
    Kürzt explizit 'GRÜNE' zu 'GRÜN' und 'DIE LINKE' zu 'LINKE'.
    """
    text = text.replace("GRÜNE", "GRÜN").replace("DIE LINKE", "LINKE").replace("Sonstige", "Sonst")
    
    return [text[i:i + 7] for i in range(0, len(text), 7)]

def format_for_lametric(coalitions):
    """
    Formatiert die Koalitionsdaten im LaMetric-kompatiblen JSON-Format.
    """
    frames = []
    
    icon_index = -1
    
    for coalition in coalitions:
        icon_index += 1
        frames.append({"text": split_text(f"{' + '.join(coalition['parties'])}")[0], "icon": str(ICON_IDS[icon_index])})
        frames.append({"text": f"Gesamt:", "icon": str(ICON_IDS[icon_index])})
        frames.append({"text": f"{coalition['seats']} Sitze", "icon": str(ICON_IDS[icon_index])})
    
    return {"frames": frames}

def save_to_json(data):
    """
    Speichert das Ergebnis (Koalitionen) oder LaMetric-Daten in einer JSON-Datei.
    """
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Daten abrufen und filtern
    poll_data = fetch_poll_data()
    
    filtered_data = filter_parties_by_threshold(poll_data)
    
    # Sitzverteilung berechnen
    seat_distribution = calculate_seat_distribution(filtered_data)
    
    # Koalitionen berechnen
    coalitions_with_majority = calculate_majority_coalitions(seat_distribution)
    
    # Daten für LaMetric formatieren und speichern
    lametric_data = format_for_lametric(coalitions_with_majority)
    
    save_to_json(lametric_data)
