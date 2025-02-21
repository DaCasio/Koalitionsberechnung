# **Koalitionsanalyse für LaMetric**

Dieses Projekt analysiert aktuelle Wahlumfragedaten von [wahlrecht.de](https://www.wahlrecht.de/umfragen/) und berechnet mögliche Regierungskoalitionen. Die Ergebnisse werden im LaMetric-kompatiblen JSON-Format ausgegeben, sodass sie auf einem LaMetric-Gerät angezeigt werden können. Das Projekt berücksichtigt nur Koalitionen, die eine Mehrheit (mindestens 50 %) erreichen, und zeigt die erste relevante Konstellation an.

---

## **Funktionen**
- **Datenabfrage**: Ruft aktuelle Wahlumfragedaten von [wahlrecht.de](https://www.wahlrecht.de/umfragen/) ab.
- **Koalitionsberechnung**: Berechnet mögliche Koalitionen basierend auf den Umfragewerten.
- **Mehrheitsprüfung**: Zeigt nur Koalitionen an, die eine Mehrheit erreichen (mindestens 50 %).
- **LaMetric-kompatibles Format**: Die Ergebnisse werden im JSON-Format erstellt, das direkt auf einem LaMetric-Gerät angezeigt werden kann.
- **Kosmetische Optimierungen**:
  - Kürzt lange Bezeichnungen wie `"GRÜNE"` zu `"GRÜN"` und `"DIE LINKE"` zu `"LINKE"`.
  - Teilt lange Texte in Abschnitte mit maximal 7 Zeichen auf, um Scrollen auf LaMetric zu vermeiden.

---

## **Projektstruktur**
```plaintext
.
├── scraper.py         # Hauptskript für die Datenabfrage, Analyse und JSON-Erstellung
├── data.json          # Generierte JSON-Datei im LaMetric-kompatiblen Format
├── scraper.log        # Logdatei mit Debugging-Informationen
├── requirements.txt   # Liste der Python-Abhängigkeiten
└── README.md          # Dokumentation des Projekts
```

---

## **Voraussetzungen**
- Python 3.10 oder neuer
- Abhängigkeiten aus `requirements.txt`:
  - `pandas`
  - `requests`
  - `beautifulsoup4`
  - `lxml`

---

## **Installation**
1. **Repository klonen**:
   ```bash
   git clone https://github.com/dein-benutzername/koalitionsanalyse-lametric.git
   cd koalitionsanalyse-lametric
   ```

2. **Virtuelle Umgebung erstellen (optional)**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Für Linux/macOS
   venv\Scripts\activate     # Für Windows
   ```

3. **Abhängigkeiten installieren**:
   ```bash
   pip install -r requirements.txt
   ```

---

## **Verwendung**
1. **Skript ausführen**:
   ```bash
   python scraper.py
   ```

2. **Ergebnisse prüfen**:
   - Die berechneten Koalitionen werden in der Datei `data.json` gespeichert.
   - Beispielausgabe in `data.json`:
     ```json
     {
       "frames": [
         {
           "text": "Koalit.",
           "icon": "16880"
         },
         {
           "text": "CDU/CSU",
           "icon": "16880"
         },
         {
           "text": "+ AfD",
           "icon": "16880"
         },
         {
           "text": "Gesamt:",
           "icon": "16880"
         },
         {
           "text": "50.8%",
           "icon": "16880"
         }
       ]
     }
     ```

3. **LaMetric-Anzeige einrichten**:
   - Lade die generierte `data.json` auf dein LaMetric-Gerät hoch oder richte sie über eine kompatible App ein.

---

## **Funktionsweise**
### **1. Datenabfrage**
Das Skript ruft aktuelle Wahlumfragedaten von [wahlrecht.de](https://www.wahlrecht.de/umfragen/) ab und berechnet den Durchschnitt der letzten veröffentlichten Werte für jede Partei.

### **2. Koalitionsberechnung**
Basierend auf den Umfragewerten werden mögliche Koalitionen berechnet:
- Nur Parteien mit mindestens 5 % Stimmenanteil werden berücksichtigt.
- Es werden nur Koalitionen angezeigt, die eine Mehrheit (≥ 50 %) erreichen.
- Sobald eine Mehrheit gefunden wird, werden weitere Konstellationen ignoriert.

### **3. Ausgabe im LaMetric-Format**
Die berechneten Koalitionen werden in einem JSON-Format gespeichert, das mit der LaMetric Indicator App kompatibel ist. Lange Texte wie `"DIE LINKE"` oder `"Sonstige"` werden gekürzt, um Platz auf dem Display zu sparen.

---

## **Beispielausgabe**
### JSON-Ausgabe (`data.json`):
```json
{
  "frames": [
    {
      "text": "Koalit.",
      "icon": "16880"
    },
    {
      "text": "+ CDU",
      "icon": "16880"
    },
    {
      "text": "+ AfD",
      "icon": "16880"
    },
    {
      "text": "Gesamt:",
      "icon": "16880"
    },
    {
      "text": "50.8%",
      "icon": "16880"
    }
  ]
}
```

---

## **Besonderheiten**
1. **Kürzungen für bessere Lesbarkeit**:
   - `"GRÜNE"` wird zu `"GRÜN"`.
   - `"DIE LINKE"` wird zu `"LINKE"`.
   - `"Sonstige"` wird zu `"Sonst"`.

2. **Keine doppelten Mehrheiten**:
   - Sobald eine Koalition mit einer Mehrheit gefunden wird, werden alle weiteren Konstellationen ignoriert.

3. **Optimiert für LaMetric-Anzeige**:
   - Texte werden in Abschnitte mit maximal 7 Zeichen unterteilt, um Scrollen zu vermeiden.

---

## **Fehlerbehebung**
### Problem: Keine Daten in `data.json`
1. Prüfe das Logfile `scraper.log` auf Fehler.
2. Stelle sicher, dass die Struktur von [wahlrecht.de](https://www.wahlrecht.de/umfragen/) nicht geändert wurde.
3. Führe das Skript erneut aus:
   ```bash
   python scraper.py
   ```

### Problem: Abhängigkeiten fehlen
Installiere die Abhängigkeiten erneut:
```bash
pip install -r requirements.txt
```

---

## **Geplante Erweiterungen**
- Unterstützung für historische Datenanalysen.
- Dynamische Anpassung der Icon-Liste basierend auf den verfügbaren IDs.
- Integration in einen automatisierten Workflow mit GitHub Actions.

---

## **Lizenz**
Dieses Projekt steht unter der MIT-Lizenz – siehe [LICENSE](LICENSE) für weitere Details.
