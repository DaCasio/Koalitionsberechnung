#!/usr/bin/env python3
# scraper.py
# Dieses Skript ruft Umfragedaten von wahlrecht.de ab, berechnet Koalitionen und erstellt ein LaMetric-kompatibles JSON-Format.

import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd
from itertools import combinations
import json

# Konfiguration: Parteien und Nummer-Icon-IDs
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
    
    poll_data = {}
    for party_name, party_id in PARTIES_CONFIG:
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
                values.append(0.0)

        if len(values) == len(institutes):
            poll_data[party_name] = values

    # Berechne den Durchschnittswert je Partei
    df = pd.DataFrame(poll_data)
    return df.mean().round(1).to_dict()

def calculate_coalitions(poll_data):
    """
    Berechnet mögliche Koalitionen basierend auf Parteien mit mindestens 5% Stimmenanteil.
    """
    threshold = 5.0
    majority = 50.0

    eligible_parties = {k: v for k, v in poll_data.items() if v >= threshold}
    
    coalitions = {"with_afd": [], "without_afd": []}
    
    for r in range(2, 4): 
        for combo in combinations(eligible_parties.keys(), r):
            if "CDU/CSU" not in combo:
                continue
            
            total = sum(eligible_parties[p] for p in combo)
            afd_included = "AfD" in combo
            
            if afd_included and any(party in combo for party in ["SPD", "GRÜNE", "DIE LINKE"]):
                continue
            
            coalition = {
                "parties": list(combo),
                "total": round(total, 1),
                "possible": total >= majority,
            }
            
            key = "with_afd" if afd_included else "without_afd"
            coalitions[key].append(coalition)

    return coalitions

def split_text(text):
    """
    Teilt einen Text in mehrere Teile auf (maximal 7 Zeichen pro Teil).
    """
    text = text.replace("Sonstige", "Sonst")
    return [text[i:i + 7] for i in range(0, len(text), 7)]

def format_for_lametric(coalitions):
    """
    Formatiert die Koalitionsdaten im LaMetric-kompatiblen JSON-Format.
    """
    frames = []
    
    icon_index = -1
    
    # Koalitionen mit AfD
    frames.append({"text": split_text("Koalit.AfD")[0], "icon": str(ICON_IDS[0])})
    
    for coalition in coalitions["with_afd"]:
        if coalition["possible"]:
            icon_index += 1
            for part in split_text(f"{' + '.join(coalition['parties'])}"):
                frames.append({"text": part, "icon": str(ICON_IDS[icon_index])})
            frames.append({"text": f"Gesamt:", "icon": str(ICON_IDS[icon_index])})
            frames.append({"text": f"{coalition['total']}%", "icon": str(ICON_IDS[icon_index])})
    
    # Koalitionen ohne AfD
    frames.append({"text": split_text("Koalit.oAf")[0], "icon": str(ICON_IDS[icon_index + 1])})
    
    for coalition in coalitions["without_afd"]:
        if coalition["possible"]:
            icon_index += 1
            for part in split_text(f"{' + '.join(coalition['parties'])}"):
                frames.append({"text": part, "icon": str(ICON_IDS[icon_index])})
            frames.append({"text": f"Gesamt:", "icon": str(ICON_IDS[icon_index])})
            frames.append({"text": f"{coalition['total']}%", "icon": str(ICON_IDS[icon_index])})
    
    return {"frames": frames}

def save_to_json(data):
    """
    Speichert das Ergebnis (Koalitionen) oder LaMetric-Daten in einer JSON-Datei.
    """
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    poll_data = fetch_poll_data()
    
    coalitions = calculate_coalitions(poll_data)
    
    lametric_data = format_for_lametric(coalitions)
    
    save_to_json(lametric_data)
