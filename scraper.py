#!/usr/bin/env python3
# scraper.py
# Dieses Skript lädt Wahlumfragedaten von wahlrecht.de, berechnet die Sitzverteilung
# (basierend auf den Zweitstimmen) und ermittelt minimal gewinnende Koalitionen (d.h. nur so viele Koalitionspartner,
# wie nötig sind, um eine Mehrheit von mindestens 316 Sitzen bei 630 Sitzen zu erreichen).
# Anschließend werden die Ergebnisse im LaMetric-kompatiblen JSON-Format ausgegeben.

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
MAJORITY_SEATS = TOTAL_SEATS // 2 + 1

def fetch_poll_data():
    """
    Lädt die HTML-Tabelle von wahlrecht.de und berechnet den Durchschnittswert für jede Partei.
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
    return df.mean().round(1).to_dict()

def filter_parties_by_threshold(poll_data):
    """
    Filtert Parteien unterhalb der Fünf-Prozent-Hürde und entfernt 'Sonstige'.
    """
    total_votes = sum(poll_data.values())
    return {party: votes for party, votes in poll_data.items() 
            if (votes / total_votes) * 100 >= 5 and party != "Sonstige"}

def calculate_seat_distribution(filtered_data):
    """
    Berechnet die Sitzverteilung basierend auf den gefilterten Zweitstimmenergebnissen.
    """
    total_votes = sum(filtered_data.values())
    return {party: round((votes / total_votes) * TOTAL_SEATS) 
            for party, votes in filtered_data.items()}

def calculate_majority_coalitions(seat_distribution):
    """
    Berechnet minimal gewinnende Koalitionen basierend auf der Sitzverteilung.
    
    Es werden nur Koalitionen berücksichtigt:
      - Die eine Mehrheit (≥316 Sitze) erzielen.
      - Die minimal sind (d.h. keine Partei kann entfernt werden ohne die Mehrheit zu verlieren).
    """
    coalitions = []
    
    parties = list(seat_distribution.keys())
    
    # Prüfe einzelne Parteien (falls eine Partei allein die Mehrheit hat)
    for party in parties:
        if seat_distribution[party] >= MAJORITY_SEATS:
            coalitions.append({"parties": [party], "seats": seat_distribution[party]})
    
    # Prüfe Kombinationen von mindestens zwei Parteien
    for r in range(2, len(parties) + 1):
        for combo in combinations(parties, r):
            seats = sum(seat_distribution[p] for p in combo)
            if seats >= MAJORITY_SEATS:
                # Prüfe Minimalität: Entferne jede Partei einzeln. Wenn dabei die Mehrheit verloren geht -> minimal.
                minimal = True
                for party in combo:
                    if (seats - seat_distribution[party]) >= MAJORITY_SEATS:
                        minimal = False
                        break
                if minimal:
                    coalitions.append({"parties": list(combo), "seats": seats})
    
    # Sortiere nach Anzahl der Parteien (weniger ist besser) und dann nach Sitzen (absteigend)
    coalitions.sort(key=lambda x: (len(x["parties"]), -x["seats"]))
    
    return coalitions

def format_name(name):
    """
    Kürzt den Parteinamen auf exakt sieben Zeichen.
      - Kürzt bekannte Namen wie 'GRÜNE' zu 'GRÜN' oder 'DIE LINKE' zu 'LINKE'.
      - Füllt kürzere Namen rechts mit Leerzeichen auf.
      - Schneidet längere Namen ab.
    """
    name = name.replace("GRÜNE", "GRÜN").replace("DIE LINKE", "LINKE")
    return name.ljust(7)[:7]

def format_for_lametric(coalitions):
    """
    Formatiert die berechneten Koalitionen für LaMetric.
    
      - Jede Partei wird einzeln dargestellt (7 Zeichen pro Frame).
      - Es folgen ein Frame mit 'Gesamt:' und ein Frame mit der Sitzanzahl ('398 Sitz').
      - Maximal werden die ersten zehn Koalitionen angezeigt.
    
      Rückgabe: JSON-Format für LaMetric.
    """
    if not coalitions:
        return {"frames": [{"text": "Keine Mehrh.", "icon": str(ICON_IDS[0])}]}
    
    frames = []
    
    for idx, coalition in enumerate(coalitions[:10]): # Begrenze auf maximal zehn Koalitionen
        if idx >= len(ICON_IDS):
            break
        
        # Füge Frames für jede Partei hinzu
        for party in coalition["parties"]:
            frames.append({"text": format_name(party), "icon": str(ICON_IDS[idx])})
        
        # Füge Frames für Gesamt-Sitze hinzu
        frames.append({"text": "Gesamt:", "icon": str(ICON_IDS[idx])})
        frames.append({"text": f"{coalition['seats']} Sitz", "icon": str(ICON_IDS[idx])})
    
    return {"frames": frames}

def save_to_json(data):
    """
    Speichert das Ergebnis im JSON-Format in der Datei data.json.
    """
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    
    try:
        # Schritt: Umfragedaten abrufen
        poll_data = fetch_poll_data()
        
        # Schritt: Parteien filtern (>=5% und ohne 'Sonstige')
        filtered_data = filter_parties_by_threshold(poll_data)
        
        # Schritt: Sitzverteilung berechnen
        seat_distribution = calculate_seat_distribution(filtered_data)
        
        # Schritt: Minimal gewinnende Koalitionen berechnen
        coalitions = calculate_majority_coalitions(seat_distribution)
        
        # Schritt: Daten für LaMetric formatieren und speichern
        lametric_json = format_for_lametric(coalitions)
        
        save_to_json(lametric_json)
        
        print("Prozess erfolgreich abgeschlossen!")
    
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")
