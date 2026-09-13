# FloodGuard BD — All-in-one upgrade

Features:
- 19 monitored representative zones
- Stable zone selection (selection survives refresh/background sync)
- Working 24h and 15-day experimental projection for every zone
- English / Bangla UI toggle
- Simple public-facing flood summary before technical charts
- Bangladesh interactive risk map with filters
- Compare zones
- Risk analytics
- Login / profile preferences
- WhatsApp-alert preference storage; actual sending requires an approved WhatsApp provider and environment credentials
- Background FFWC sync with cache; requests never block the homepage

## Data integrity
The app labels data states. Official FFWC observations are only marked LIVE when matched from the public feed. If the public feed cannot be read, the app uses clearly labelled FFWC snapshot or simulation/reference data. Do not present simulation data as official live measurements.

## Local
Double-click `run.bat`, then open http://127.0.0.1:5081

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn app:app`
Set `SECRET_KEY` in the Render environment for production.

### WhatsApp provider
To enable real delivery, configure an approved provider separately (for example WhatsApp Business Cloud API or Twilio) and add provider credentials as environment variables. The repo intentionally does not include secrets.
