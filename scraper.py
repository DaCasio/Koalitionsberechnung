import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from datetime import datetime, timedelta


def fetch_poll_data():
    """
    Extrahiert die Umfragedaten aus der Tabelle auf wahlrecht.de.
    """
    # Die URL der Seite
    url = "https://www.wahlrecht.de/umfragen/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Tabelle mit Umfragedaten finden
    table = soup.find("table", {"class": "wilko"})
    rows = table.find_all("tr")
    
    # Spaltennamen aus der Tabelle extrahieren
    headers = [th.text.strip() for th in rows[0].find_all("th")]
    
    # Datenzeilen extrahieren
    data = []
    for row in rows[1:]:
        cells = [cell.text.strip() for cell in row.find_all(["td", "th"])]
        data.append(cells)
    
    # DataFrame erstellen
    df = pd.DataFrame(data, columns=headers)
    
    # Veröffentlichungsdatum extrahieren
    release_dates = table.find("tr", id="datum").find_all("span", class_="li")
    release_dates = [date.text.strip() for date in release_dates if date.text.strip()]
    
    # Datum als neue Spalte hinzufügen
    df["Veröffentl."] = release_dates
    
    # Konvertiere Datum in datetime-Format
    df["Zeitraum"] = pd.to_datetime(df["Veröffentl."], format="%d.%m.%Y", errors="coerce")
    
    # Nur Umfragen der letzten 14 Tage
    two_weeks_ago = datetime.now() - timedelta(days=14)
    df = df[df["Zeitraum"] >= two_weeks_ago]
    
    # Relevante Spalten für Parteien extrahieren
    parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD", "BSW"]
    df = df[["Zeitraum"] + parties]

    # Prozente in numerische Werte umwandeln
    for party in parties:
        df[party] = df[party].str.replace("%", "").astype(float)

    return df


def calculate_weekly_average(df):
    """
    Berechnet den Durchschnitt der Umfragewerte pro Partei.
    """
    parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD", "BSW"]
    averages = df[parties].mean().round(1)
    return averages.to_dict()


def calculate_coalitions(averages, include_afd=True):
    """
    Berechnet mögliche Koalitionen basierend auf den Durchschnittswerten.
    """
    parties = list(averages.keys())
    if not include_afd:
        parties.remove("AfD")
    
    coalitions = []

    # Zweier-Koalitionen
    for i, p1 in enumerate(parties):
        for p2 in parties[i + 1:]:
            total = averages[p1] + averages[p2]
            coalitions.append({
                "parties": [p1, p2],
                "total": total,
                "majority": total >= 50.0
            })

    # Dreier-Koalitionen
    for i, p1 in enumerate(parties):
        for j, p2 in enumerate(parties[i + 1:]):
            for p3 in parties[i + j + 2:]:
                total = averages[p1] + averages[p2] + averages[p3]
                coalitions.append({
                    "parties": [p1, p2, p3],
                    "total": total,
                    "majority": total >= 50.0
                })

    return coalitions


def save_to_json(filename, with_afd, without_afd):
    """
    Speichert die Ergebnisse in einer JSON-Datei.
    """
    output = {
        "with_afd": with_afd,
        "without_afd": without_afd
    }
    with open(filename, "w") as f:
        json.dump(output, f, indent=4)
    print(f"Ergebnisse in {filename} gespeichert.")


if __name__ == "__main__":
    try:
        print("Daten von Wahlrecht.de abrufen...")
        df = fetch_poll_data()
        print("Daten erfolgreich abgerufen:")
        print(df.head())

        print("Berechnungen starten...")
        averages = calculate_weekly_average(df)

        with_afd = calculate_coalitions(averages, include_afd=True)
        without_afd = calculate_coalitions(averages, include_afd=False)

        print("Speichere Ergebnisse...")
        save_to_json("data.json", with_afd, without_afd)

    except Exception as e:
        print(f"Fehler: {e}")
