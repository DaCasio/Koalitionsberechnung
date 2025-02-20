import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import json


def fetch_poll_data():
    """
    Ruft die Tabelle von Wahlrecht.de ab und extrahiert relevante Daten.
    """
    # URL der Seite mit Umfragedaten
    url = "https://www.wahlrecht.de/umfragen/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Tabelle finden
    table = soup.find("table", {"class": "wilko"})
    raw_data = pd.read_html(str(table))[0]
    
    # Debug: Aktuelle Spaltennamen ausgeben
    print("Aktuelle Spaltennamen:", raw_data.columns.tolist())
    
    # Erste Zeile als Header setzen
    raw_data.columns = raw_data.iloc[0]
    df = raw_data[1:].reset_index(drop=True)
    
    # Veröffentlichtes Datum verwenden
    if "Veröffentl." not in df.columns:
        raise KeyError(f"Spalte 'Veröffentl.' nicht vorhanden. Vorhandene Spalten: {df.columns.tolist()}")
    
    # Extrahiere Veröffentlichungsdatum
    df["Zeitraum"] = df["Veröffentl."].str.extract(r'(\d{2}\.\d{2}\.\d{4})')
    df["Zeitraum"] = pd.to_datetime(df["Zeitraum"], format='%d.%m.%Y', errors='coerce')
    
    # Filter auf letzte 14 Tage
    two_weeks_ago = datetime.now() - timedelta(days=14)
    df_filtered = df[df["Zeitraum"] >= two_weeks_ago]
    
    # Parteidaten filtern
    parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD", "BSW"]
    institutes = ['Allensbach', 'Verian (Emnid)', 'Forsa', 'Forsch\'gr. Wahlen', 'GMS', 
                  'Infratest dimap', 'INSA', 'YouGov']
    
    # Nur relevante Spalten
    df_filtered = df_filtered[["Institut", *parties, "Zeitraum"]]
    df_filtered = df_filtered[df_filtered["Institut"].isin(institutes)]
    
    # Konvertierung der Parteienwerte
    for party in parties:
        df_filtered[party] = pd.to_numeric(df_filtered[party], errors='coerce')
    
    return df_filtered


def calculate_weekly_average(data):
    """
    Berechnet den Durchschnitt der Parteienwerte der letzten 14 Tage.
    """
    parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD", "BSW"]
    averages = data[parties].mean().round(1)  # Durchschnitt berechnen und auf eine Dezimalstelle runden
    return averages.to_dict()


def calculate_coalitions(party_data, include_afd=True):
    """
    Berechnet alle möglichen Zwei- und Dreier-Koalitionen.
    """
    parties = list(party_data.keys())
    if not include_afd:
        parties.remove("AfD")  # AfD ausschließen, falls erforderlich
    
    coalitions = []
    
    # Zwei-Parteien-Koalitionen
    for i, p1 in enumerate(parties):
        for p2 in parties[i+1:]:
            total = party_data[p1] + party_data[p2]
            coalitions.append({
                "parties": [p1, p2],
                "total": round(total, 1),
                "majority": total >= 50.0
            })
    
    # Drei-Parteien-Koalitionen
    for i, p1 in enumerate(parties):
        for j, p2 in enumerate(parties[i+1:]):
            for p3 in parties[i+j+2:]:
                total = party_data[p1] + party_data[p2] + party_data[p3]
                coalitions.append({
                    "parties": [p1, p2, p3],
                    "total": round(total, 1),
                    "majority": total >= 50.0
                })
    
    return sorted(coalitions, key=lambda x: x['total'], reverse=True)


def save_to_json(filename, coalitions_with_afd, coalitions_without_afd):
    """
    Speichert die Ergebnisse in einer JSON-Datei.
    """
    output = {
        "with_afd": coalitions_with_afd,
        "without_afd": coalitions_without_afd
    }
    
    with open(filename, "w") as f:
        json.dump(output, f, indent=4)
    
    print(f"Datei {filename} erfolgreich erstellt!")


if __name__ == "__main__":
    try:
        data = fetch_poll_data()
        print("Erfolgreich Daten von Wahlrecht.de geladen. Übersicht der Daten:")
        print(data.head())  # Erste 5 Zeilen zeigen
        
        if data.empty:
            print("Warnung: Keine Daten in den letzten 14 Tagen gefunden!")
            save_to_json("data.json", [], [])
        else:
            print("Berechne Koalitionen...")
            averages = calculate_weekly_average(data)
            
            coalitions_with_afd = calculate_coalitions(averages, include_afd=True)
            coalitions_without_afd = calculate_coalitions(averages, include_afd=False)
            
            print("Speichere Ergebnisse...")
            save_to_json("data.json", coalitions_with_afd, coalitions_without_afd)
            print("Daten erfolgreich gespeichert.")
            
    except Exception as e:
        print(f"Kritischer Fehler: {str(e)}")
        save_to_json("data.json", [], [])
