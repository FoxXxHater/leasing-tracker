# Changelog

## [1.1.3] - 04-02-2026

- "OptionsFlow" Fehler behoben
- Fehler beim Laden gespeicherter Daten behoben
- Webserver stürzt nicht mehr ab bei änderungen

## [1.1.2] - 04-02-2026

- Weitere Änderungen an der Grafiken in HA

## [1.1.1] - 04-02-2026

### Hinzugefügt
- **Bilder und Logos für das Repo und HACS**

## [1.1.0] - 04-02-2026

### Hinzugefügt
- **Neue Sensoren für tatsächliche Werte (ohne Schätzung):**
  - `Verbleibende KM diesen Monat` - Monatslimit minus bereits gefahrene KM im Monat
  - `Verbleibende KM dieses Jahr` - Jahreslimit minus bereits gefahrene KM im Jahr
  - `Gefahrene KM diesen Monat` - Tatsächlich im aktuellen Monat gefahrene KM
  - `Gefahrene KM dieses Jahr` - Tatsächlich im aktuellen Jahr gefahrene KM
  - `Erlaubte KM dieses Jahr` - Für das aktuelle Kalenderjahr erlaubte KM
  - `Erlaubte KM diesen Monat` - Für den aktuellen Monat erlaubte KM

- **Neue Schätzungs-Sensoren:**
  - `Schätzung Verbleibende KM diesen Monat` - Basierend auf Durchschnittsverbrauch
  - `Schätzung Verbleibende KM dieses Jahr` - Basierend auf Durchschnittsverbrauch
  - `Schätzung KM am Monatsende` - Voraussichtlicher Stand am Monatsende
  - `Schätzung KM am Jahresende` - Voraussichtlicher Stand am Jahresende

### Geändert
- **Umbenennungen zur besseren Klarheit:**
  - Alte "Verbleibende KM diesen Monat" → "Schätzung Verbleibende KM diesen Monat"
  - Alte "Verbleibende KM dieses Jahr" → "Schätzung Verbleibende KM dieses Jahr"
  - Alle Schätzungen sind jetzt klar als "Schätzung" gekennzeichnet

- **Verbesserte Berechnungen:**
  - Monatliche Werte basieren nun auf tatsächlich gefahrenen KM im Monat
  - Jährliche Werte basieren nun auf tatsächlich gefahrenen KM im Jahr
  - Genauere Berechnung der erlaubten KM pro Monat/Jahr
  - Berücksichtigung von anteiligen Monaten/Jahren bei Leasingbeginn

## [1.0.0] - 04-02-2026

### Initial Release
- Erste Version des Leasing Trackers
- 14 Basis-Sensoren
- UI-Konfiguration
- HACS-Kompatibilität
- Deutsche und englische Übersetzungen
