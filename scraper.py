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
    Lädt die HTML-Tabelle von wahlrecht.de und berechnet den Durchschnittswert für jede Partei.
    Rückgabe: Dictionary mit Parteien und ihren Durchschnittswerten.
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
    Filtert Parteien unterhalb der Fünf-Prozent-Hürde und entfernt 'Sonstige'.
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
    Berechnet alle möglichen Koalitionen basierend auf der Sitzverteilung.
    
    Es werden nur Koalitionen mit der minimal erforderlichen Anzahl an Parteien berücksichtigt,
    die eine Mehrheit (≥316 Sitze) erzielen.
    
    Rückgabe: Liste von Dictionaries mit 'parties' (Liste der beteiligten Parteien)
              und 'seats' (Gesamtsitze).
    """
    coalitions = []
    
    # Sortiere die Parteien nach ihrer Sitzanzahl absteigend (effizientere Berechnung)
    sorted_parties = sorted(seat_distribution.items(), key=lambda x: x[1], reverse=True)
    
    for r in range(2, len(sorted_parties) + 1): # Mindestens zwei Parteien erforderlich
        for combo in combinations(sorted_parties, r):
            combo_parties = [party[0] for party in combo]
            seats = sum(party[1] for party in combo)
            
            if seats >= MAJORITY_SEATS:
                coalitions.append({"parties": combo_parties, "seats": seats})
                logging.debug("Koalition gefunden: %s mit %d Sitzen", combo_parties, seats)
                break # Sobald eine Mehrheit erreicht wurde -> keine weiteren Partner hinzufügen
    
        if coalitions: # Wenn bereits eine Mehrheit gefunden wurde -> keine weiteren Kombinationen prüfen
            break
    
    if not coalitions:
        logging.warning("Keine Koalitionen mit Mehrheit gefunden.")
    
    return coalitions

# ---------------------------------------------------------------------
def split_text(text):
    """
    Formatiert einen Text so, dass er genau auf einen Frame mit maximal 
     sieben Zeichen passt. Kürzt lange Namen wie 'GRÜNE' zu 'GRÜN'.
     """
     
text.replace("GRÜNE","GRÜN")
