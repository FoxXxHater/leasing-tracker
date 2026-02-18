# 🚗 Leasing Tracker for Home Assistant

<p align="center">
  <img src="banner.svg" alt="Leasing Tracker Banner" width="100%">
</p>

<p align="center">
  <a href="https://github.com/foxxxhater/leasing-tracker/releases">
    <img src="https://img.shields.io/github/release/foxxxhater/leasing-tracker.svg?style=flat-square" alt="GitHub Release">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/foxxxhater/leasing-tracker.svg?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/hacs/integration">
    <img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square" alt="HACS">
  </a>
</p>

<p align="center">
  A custom integration for Home Assistant to monitor leased vehicles and calculate remaining kilometers.
</p>

## 📸 Screenshot

<p align="center">
  <img src="SCREENSHOT.png" alt="Dashboard Screenshot" high="15%">
</p>

- made with the <a href="https://github.com/WJDDesigns/Ultra-Vehicle-Card" alt="Link to Ultra Vehicle Card">Ultra Vehicle Card</a>, <a href="https://github.com/th3jesta/ha-lcars" alt="Link to HA-LCARS">HA-LCARS</a> (YES i am a Star Trek Fan...), <a href="https://github.com/skodaconnect/homeassistant-myskoda">MySkoda</a> Integration and of course <a href="https://github.com/foxxxhater/leasing-tracker-card/" alt="Link to Leasing Tracker Card">My Leasing Tracker Card</a>


A huge Thanks to all great Dev out there!

---

## ✨ Features

- ✅ **22 automatic sensors** - Comprehensive monitoring of all leasing data
- ✅ **Actual + estimated values**
- ✅ **UI configuration** - No YAML configuration needed
- ✅ **Multiple vehicles** - Any number of leasing contracts in parallel
- ✅ **HACS compatible** - Easy installation and updates
- ✅ **German + English** - Full translations

## 📦 Companion project

<a href="https://github.com/FoxXxHater/leasing-tracker-card" alt="Link to my Card Project">**My Leasing Tracker Card**</a>

## 📊 Sensors

### Remaining Kilometers
- Remaining KM Total
- Remaining KM this year (actual)
- Remaining KM this month (actual)
- Estimated remaining KM this year
- Estimated remaining KM this month

### Driven Kilometers
- Driven KM (total)
- Driven KM this month
- Driven KM this year
- Average KM per day
- Average KM per month

### Status & Progress
- Status (On Track / Over Plan / Under Plan)
- KM difference to plan
- Progress (%)
- Remaining days/months

### Contract Data
- Allowed KM total
- Allowed KM this year
- Allowed KM this month
- Allowed KM per month (average)

## 🚀 Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant
2. "Integrations" → ⋮ → "Custom Repositories"
3. Add repository:
   - URL: `https://github.com/foxxxhater/leasing-tracker`
   - Category: "Integration"
4. Search for "Leasing Tracker" and install
5. Restart Home Assistant
6. Add integration via UI

### Manual

1. Download the latest version: [Releases](https://github.com/foxxxhater/leasing-tracker/releases)
2. Extract the archive
3. Copy the `leasing_tracker` folder to `custom_components/`
4. Restart Home Assistant
5. Add integration via UI

## ⚙️ Configuration

### Step 1: Create mileage sensor (Optional)
(If no entity from your car is available)

Add to `configuration.yaml`:

```yaml
input_number:
  car_mileage:
    name: "Car Mileage"
    min: 0
    max: 500000
    step: 1
    unit_of_measurement: "km"
    icon: mdi:counter
```

### Step 2: Add integration

1. **Settings** → **Devices & Services**
2. **+ Add Integration**
3. Search: **"Leasing Tracker"**
4. Fill out the form:
   - Name (e.g. "BMW 3 Series Leasing")
   - Mileage sensor
   - Start/end date
   - Starting KM
   - Allowed KM/year

### Step 3: Done! 🎉

All sensors are created automatically and update whenever the mileage changes.

## 📱 Dashboard Examples

### Compact Overview
```yaml
type: entities
title: 🚗 My Leasing
entities:
  - sensor.bmw_3er_status
  - sensor.bmw_3er_verbleibende_km_monat
  - sensor.bmw_3er_verbleibende_km_jahr
  - sensor.bmw_3er_km_differenz_zum_plan
  - sensor.bmw_3er_gefahrene_km
```

## 🔔 Example Automation

Notification when mileage is too high:

```yaml
automation:
  - alias: "Leasing Warning"
    trigger:
      platform: numeric_state
      entity_id: sensor.bmw_3er_km_differenz_zum_plan
      above: 500
    action:
      service: notify.mobile_app
      data:
        title: "⚠️ Leasing Warning"
        message: "You are {{ states('sensor.bmw_3er_km_differenz_zum_plan') }} km over the plan!"
```

## 📚 Documentation

- [📝 Changelog](CHANGELOG.md)

## 🐛 Bugs & Issues
→ [Create an issue](https://github.com/foxxxhater/leasing-tracker/issues)

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## 💬 Support

- 🐛 [Issues](https://github.com/foxxxhater/leasing-tracker/issues)
- 💡 [Discussions](https://github.com/foxxxhater/leasing-tracker/discussions)
- 🏠 [Home Assistant Community Forum](https://community.home-assistant.io/)

## ⭐ Thanks!

If this integration helps you, feel free to give the project a star! ⭐

---

Developed with ❤️ for the Home Assistant Community

P.S. with kind support from Claude
