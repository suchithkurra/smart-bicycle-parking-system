# Smart Bicycle Parking System — base Flask app

Starting skeleton. No database yet; the dashboard uses placeholder data in `app/routes.py`.

## Run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open http://localhost:5000 (or `http://<pi-ip>:5000` from another device).

## Structure

```
run.py                 # starts the app
app/__init__.py        # create_app() factory
app/routes.py          # pages + API endpoints (TODOs mark where logic goes)
app/templates/         # base, dashboard, register, history
app/static/style.css
```

## Pages / endpoints

| Route | Purpose |
|---|---|
| `/` | Dashboard – FREE/OCCUPIED spaces |
| `/register` | Registration form (not saved yet) |
| `/history` | Parking history (empty for now) |
| `GET /api/spaces` | Spaces as JSON |
| `POST /api/scan` | `{"user_id": "..."}` – for the QR scanner later |

## Next steps
1. Add the database (users, spaces, parking sessions)
2. Generate QR codes on registration
3. Camera scanner script that POSTs to `/api/scan`
4. Check-in/check-out + priority allocation
