# Changelog

## [1.4.0] - 26-06-2026

### Added
- 🆕 **Four new sensors**
  - **Lease End Date** — a timestamp sensor showing your configured lease end date, so you can use it in dashboards and automations
  - **Estimated Odometer at Lease End** — projected total odometer reading at the end of the lease, based on your average distance driven so far
  - **Estimated Excess Distance** — projected distance over your total allowance at lease end (0 if you stay within the allowance)
  - **Estimated Excess Cost** — projected extra charges at lease end, calculated from the excess distance and your price per excess unit
- 💶 **Excess mileage pricing**
  - New optional field in setup and options: price per excess km/mile over the allowance
  - The price is interpreted in the same unit shown in the UI (km or miles)
- 💱 **Currency selection**
  - New field to choose the currency for the cost sensor: Euro (€), US Dollar ($), British Pound (£) or Swiss Franc (CHF)

### Changed
- 🌍 **Translations** updated for all new fields, the currency selector and the new sensors (English, German, Dutch)

### Technical
- New config keys: `excess_price`, `currency`
- The excess cost is projected to lease end (not the current overage); excess distance is clamped to 0 when within allowance
- Cost is computed in the display unit (price-per-mile × excess-in-miles for imperial), so it stays consistent with what the user entered
- `Estimated Excess Cost` uses `device_class: monetary` with the ISO currency code as unit (HA requires the ISO code, not the symbol) and no `state_class` (monetary does not allow `measurement`)
- `Lease End Date` uses `device_class: timestamp` with a timezone-aware datetime via `dt_util.start_of_local_day()`

## [1.3.0] - 26-06-2026 ⚠️ BREAKING CHANGES

**You have to delete the old entities and create it new!**

### Fixed
- 🐛 **Sensor display unit now actually matches the source entity's unit**
  - Distance sensors are now displayed in the unit of the source odometer entity (e.g. `mi` if the odometer reports in miles), regardless of Home Assistant's global metric/imperial setting
  - Fixes: Sensors being shown in `km` even when the source entity used `mi` and the user had selected Imperial in the Leasing Tracker setup
  - Root cause: Home Assistant auto-converts `device_class: distance` sensors to the user's HA-wide unit system. The integration now overrides this behaviour explicitly per sensor.
  - Works for both newly created and already-existing entities (the entity registry override is updated on startup if it doesn't match the detected source unit)

### Added
- 🔍 **Automatic unit detection from the source odometer entity**
  - The integration now reads the `unit_of_measurement` attribute from the configured odometer entity and uses that unit for all generated sensors
  - Recognised mile units: `mi`, `miles`, `mile` (case-insensitive, whitespace-tolerant)
  - Recognised kilometer units: `km`, `kilometer`, `kilometers`, `kilometre`, `kilometres` (case-insensitive, whitespace-tolerant)
  - Detection is re-checked on every update, so sensors react if the source entity's unit changes or is set after startup
  - The manual "Unit System" choice in the setup/options dialog now serves as a fallback for source entities that don't expose a `unit_of_measurement` (e.g. plain `input_number` helpers without a unit)

### Changed
- 📋 **Clearer debug logging for unit detection**
  - Debug log now states explicitly whether the unit came from the source entity or from the fallback, e.g. `is_metric=False via source unit 'mi' -> miles` or `is_metric=True via fallback (source has no unit_of_measurement)`
  - Makes it possible to diagnose unit-related issues without guessing

### Technical
- New helper `_detect_source_unit_is_metric()` returns both the detected unit system and a human-readable reason
- New method `_sync_registry_unit()` updates the entity registry's `unit_of_measurement` option for distance sensors when it doesn't match the detected unit; uses `entity_registry.async_update_entity_options()`
- Added `_attr_suggested_unit_of_measurement` for all `device_class: distance` sensors so newly registered entities pick up the right unit on first creation
- Unit detection now runs in `__init__`, in `async_added_to_hass()` (in case the source entity wasn't ready yet), and in every `update()` cycle
- Distance-to-miles conversion is now applied uniformly to all distance sensors at the end of `update()`, instead of only the sensor whose attribute happened to be set to `MILES`

## [1.2.4] - 31-03-2026

### Fixed
- 🐛 **CRITICAL: Sensor unit detection now works correctly**
  - Integration now reads `unit_of_measurement` from the odometer sensor
  - Automatically converts sensor values based on their unit:
    - If sensor is in `mi`/`miles` → converts to km for calculations
    - If sensor is in `km` → uses directly
    - If no unit specified → assumes km
  - Fixes: Wrong calculations when sensor unit differs from chosen unit system
  - Example: Sensor shows "2,294 mi" → correctly uses 2,294 miles (not treating as km)

### Technical
- Added sensor unit detection: `sensor_unit = current_km_state.attributes.get('unit_of_measurement', 'km')`
- Automatic conversion: sensor value → km (for internal calculations) → display unit
- All calculations now work correctly regardless of sensor's unit

## [1.2.3] - 31-03-2026

### Fixed
- 🐛 Imperial units config values now convert correctly

## [1.2.2] - 31-03-2026

### Fixed
- 🐛 Average sensor units (mi/day, mi/month)

## [1.2.1] - 31-03-2026

### Changed
- 🔄 Unit-neutral labels


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
