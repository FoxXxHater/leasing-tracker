# Changelog

## [1.2.2] - 31-03-2026

### Fixed
- 🐛 **Average sensor units now respect unit system**
  - Fixed: "Average Distance per Day" showing "km/day" even when Imperial selected
  - Fixed: "Average Distance per Month" showing "km/month" even when Imperial selected
  - Now correctly shows "mi/day" and "mi/month" for Imperial units

## [1.2.1] - 31-03-2026

### Changed
- 🔄 **Unit-neutral labels in setup dialog**
  - Changed "Allowed Kilometers per Year" → "Allowed Distance per Year"
  - Labels now work for both km and miles


## [1.2.0] - 30-03-2026

### Added
- 🇺🇸 **Imperial Units Support (Miles)**
  - New option in setup: Choose between Metric (km) or Imperial (miles)
  - All distance sensors automatically convert to miles when imperial is selected
  - Available in both initial setup and options dialog
  
### Fixed
- ✅ **Status translations now working!**
  - Status values ("Im Plan", "Over Plan", etc.) now properly translate
  - Changed status to ENUM sensor with translated states
  - Fixed: "Deutlich über Plan" showing in English HA

### Technical Changes
- Status sensor now uses `device_class: ENUM` with state translations
- Added conversion factors: KM_TO_MILES (0.621371) and MILES_TO_KM (1.609344)
- Automatic unit conversion based on `unit_system` config
- All distance sensors respect the chosen unit system

## [1.1.6] - 30-03-2026

### Fixed
- ✅ **Multi-language support now working!**
  - Entity names now respect Home Assistant language settings
  - English users see English names
  - German users see German names  
  - Dutch users see Dutch names
- 🔧 Changed from hardcoded German names to translation_key system
- 🌍 Sensors properly translate based on user's HA language

### Added
- 🇳🇱 **Dutch translation** (nl.json)
- 📖 Complete English translations for all entities

### Changed
- Refactored sensor.py to use `_attr_translation_key` instead of `_attr_name`
- All sensor names now come from translation files
- Cangelog now will be written on englisch - delete the german


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
