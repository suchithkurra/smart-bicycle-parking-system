# Smart Bicycle Parking System — Flask Dashboard

## Features
- Dashboard overview and free/occupied space cards
- User registration with random QR token
- QR-token check-in and check-out
- Priority allocation with accessible-space preference and fair rotation
- Parking history and search
- SQLite database creation and starter parking spaces
- Responsive HTML/CSS dashboard

## Run locally
1. Install Python 3.9+.
2. Create and activate a virtual environment (recommended).
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the app:
   ```bash
   python app.py
   ```
5. Open http://127.0.0.1:5000

The database file `bicycle parking.db` is created next to `app.py` on first run.

## Important integration notes
- This is a standalone starter schema. If you already have a database, back it up and adapt the SQL queries to your existing table/column names before replacing your current app.
- The QR page displays a random token as text. Generate an actual QR image from that token with your QR-code library, or connect your existing QR-generation route.
- The scan form accepts a token pasted from a QR scanner. It does not access the camera by itself.
- Camera/OpenCV occupancy detection is not included yet. The current space status changes through check-in/check-out.
- The app has no administrator login. Do not expose it to the public internet without adding authentication, CSRF protection, HTTPS, and appropriate access controls.
- The development server uses `debug=True`; turn debug off for deployment.
- For Raspberry Pi LAN testing, change `host="127.0.0.1"` to `host="0.0.0.0"` and ensure the network is trusted.
