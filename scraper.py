import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import json


def fetch_poll_data():
    """
    Extrahiert die Partei- und Umfragedaten von wahlrecht.de.
    """
    # URL der Seite
    url = "https://www.wahlrecht.de/umfragen/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Tabelle mit Umfragedaten finden
    table = soup.find("table", {"class": "wilko"})

    # Zeile mit den Veröffentlichungsdaten (`id="datum"`)
    release_row = table.find("tr", {"id": "datum"})
    release_dates = [span.text.strip() for span in release_row.find_all("span", {"class": "li"}) if span.text.strip()]
    
    # Daten für jede Partei extrahieren
    parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD", "BSW"]
    data = []
    for party_id in ["cdu", "spd", "gru", "fdp", "lin", "afd", "bsw"]:
        row = table.find("tr", {"id": party_id})
        cells = row.find_all("td")
        # Parteiname (als erstes Element) ignorieren, sodass nur die Zahlen extrahiert werden
        values = [cell.text.strip().replace("%", "") for cell in cells[1:]]  # Skip the first column (party name)
        data.append(values)
    
    # DataFrame erstellen
    df = pd.DataFrame(data, index=parties, columns=release_dates).T  # Transponieren der Daten

    # Spalte mit Veröffentlichungsdatum hinzufügen
    df["Zeitraum"] = pd.to_datetime(df.index, format="%d.%m.%Y", errors="coerce")
    
    # Filter auf die letzten 14 Tage
    two_weeks_ago = datetime.now() - timedelta(days=14)
    df_filtered = df[df["Zeitraum"] >= two_weeks_ago]
    
    # Prozentwerte in numerische Werte konvertieren
    for party in parties:
        df_filtered[party] = pd.to_numeric(df_filtered[party], errors="coerce")
    
    return df_filtered


def calculate_weekly_average(df):
    """
    Berechnet den Durchschnitt der Parteienwerte der letzten 14 Tage.
    """
    parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD", "BSW"]
    averages = df[parties].mean().round(1)  # Durchschnitt berechnen und runden
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
        print("Daten von wahlrecht.de abrufen...")
        df = fetch_poll_data()
        print("Daten erfolgreich abgerufen:")
        print(df.head())

        print("Berechne Durchschnittswerte...")
        averages = calculate_weekly_average(df)

        print("Berechne Koalitionen...")
        with_afd = calculate_coalitions(averages, include_afd=True)
        without_afd = calculate_coalitions(averages, include_afd=False)

        print("Speichere Ergebnisse...")
        save_to_json("data.json", with_afd, without_afd)
        print("Alle Daten wurden erfolgreich verarbeitet.")
    except Exception as e:
        print(f"Fehler: {e}")
