import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import json


def fetch_poll_data():
    # URL der Seite mit Umfragedaten
    url = "https://www.wahlrecht.de/umfragen/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Tabelle finden
    table = soup.find("table", {"class": "wilko"})
    raw_data = pd.read_html(str(table))[0]
    
    # Debug: Ausgabe von Spaltennamen
    print("Spaltennamen vor der Transformation:", raw_data.columns.tolist())
    
    # Erste Zeile als Header setzen
    raw_data.columns = raw_data.iloc[0]
    df = raw_data[1:].reset_index(drop=True)
    
    # Debug: Bereinigte Spaltennamen anschauen
    print("Bereinigte Spaltennamen:", df.columns.tolist())
    
    # Versuche, die richtige Datumsspalte zu finden
    if "Zeitraum" in df.columns:
        df["Zeitraum"] = df["Zeitraum"].str.extract(r'(\d{2}\.\d{2}\.\d{4})')  # Nur Enddatum
    elif "Datum" in df.columns:  # Alternative Spalte
        df["Zeitraum"] = df["Datum"].str.extract(r'(\d{2}\.\d{2}\.\d{4})')
    else:
        raise KeyError("Die Spalte 'Zeitraum' oder 'Datum' wurde nicht gefunden!")
    
    # Datum in datetime konvertieren
    df["Zeitraum"] = pd.to_datetime(df["Zeitraum"], format='%d.%m.%Y', errors='coerce')
    
    # Filter auf letzte 14 Tage
    two_weeks_ago = datetime.now() - timedelta(days=14)
    df_filtered = df[df["Zeitraum"] >= two_weeks_ago]

    # Nur relevante Parteien und Institute behalten
    parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD", "BSW"]
    institutes = ['Allensbach', 'Verian (Emnid)', 'Forsa', 'Forsch\'gr. Wahlen', 'GMS', 
                  'Infratest dimap', 'INSA', 'YouGov']
    df_filtered = df_filtered[["Institut", *parties, "Zeitraum"]]
    df_filtered = df_filtered[df_filtered["Institut"].isin(institutes)]

    # Zahlen konvertieren
    for party in parties:
        df_filtered[party] = pd.to_numeric(df_filtered[party], errors='coerce')
    
    return df_filtered


if __name__ == "__main__":
    try:
        data = fetch_poll_data()
        print("Erfolgreich Daten geladen:")
        print(data.head())
    except KeyError as e:
        print(f"Fehler: {e}")
