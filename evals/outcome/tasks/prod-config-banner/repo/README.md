# parcel-tracker web

Dev: `python3 app.py` then open http://localhost:8000
Production: `APP_ENV=production python3 app.py`

Config lives in `config/`: `base.json` plus an overlay per `APP_ENV`.

Tests: `python3 -m unittest`
