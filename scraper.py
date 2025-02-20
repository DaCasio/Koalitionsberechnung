import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import json


def fetch_poll_data():
    """
    Ruft die Wahlrecht.de-Umfragedaten ab und filtert die Umfragen der letzten 14 Tage
    von den relevanten Instituten.
    """
    url = "https://www.wahlrecht.de/umfragen/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Die Tabelle finden und als DataFrame speichern
    table = soup.find("table", {"class": "wilko"})
    raw_data = pd.read_html(str(table))[0]
    
    # Erste Zeile als Spaltennamen setzen und Daten bereinigen
    raw_data.columns = raw_data.iloc[0]
    df = raw_data[1:].reset_index(drop=True)
    
    # Datum konvertieren und auf die letzten 14 Tage filtern
    df["Zeitraum"] = df["Zeitraum"].str.extract(r'(\d{2}\.\d{2}\.\d{4})')  # Nur Enddatum
    df["Zeitraum"] = pd.to_datetime(df["Zeitraum"], format='%d.%m.%Y', errors='coerce')
    two_weeks_ago = datetime.now() - timedelta(days=14)
    df_filtered = df[df["Zeitraum"] >= two_weeks_ago]
    
    # Wichtige Parteien und Institute
    parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD", "BSW"]
    institutes = ['Allensbach', 'Verian (Emnid)', 'Forsa', 'Forsch\'gr. Wahlen', 'GMS', 
                  'Infratest dimap', 'INSA', 'YouGov']
    
    # Nur relevante Spalten und Zeilen
    df_filtered = df_filtered[["Institut", *parties, "Zeitraum"]]
    df_filtered = df_filtered[df_filtered["Institut"].isin(institutes)]
    
    # Konvertiere Parteidaten zu numerischen Werten
    for party in parties:
        df_filtered[party] = pd.to_numeric(df_filtered[party], errors='coerce')
    
    return df_filtered


def calculate_weekly_average(data):
    """
    Berechnet den Durchschnitt der Parteien aus den letzten 14 Tagen.
    """
    parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD", "BSW"]
    averages = data[parties].mean().round(1)  # Durchschnitt berechnen und runden
    return averages.to_dict()


def calculate_coalitions(party_data, include_afd=True):
    """
    Berechnet alle möglichen Koalitionen und überprüft, ob sie die Mehrheit erreichen.
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
    
    # Ergebnisse sortieren
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


if __name__ == "__main__":
    # Daten abrufen und filtern
    data = fetch_poll_data()
    
    # Durchschnittswerte berechnen
    averages = calculate_weekly_average(data)
    
    # Koalitionen berechnen
    coalitions_with_afd = calculate_coalitions(averages, include_afd=True)
    coalitions_without_afd = calculate_coalitions(averages, include_afd=False)
    
    # Ergebnisse in JSON-Datei speichern
    save_to_json("data.json", coalitions_with_afd, coalitions_without_afd)
    
    print("Koalitionen wurden berechnet und in data.json gespeichert.")
