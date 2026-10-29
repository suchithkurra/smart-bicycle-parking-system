import io
import os
import sqlite3
import secrets
from datetime import datetime

import qrcode
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, abort, send_file
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "bicycle parking.db")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the tables if they do not already exist. Existing data is preserved."""
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            accessibility_need INTEGER NOT NULL DEFAULT 0
                CHECK (accessibility_need IN (0, 1)),
            qr_token TEXT UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS parking_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spot_name TEXT NOT NULL UNIQUE,
            is_accessible INTEGER NOT NULL DEFAULT 0
                CHECK (is_accessible IN (0, 1)),
            status TEXT NOT NULL DEFAULT 'FREE'
                CHECK (status IN ('FREE', 'OCCUPIED')),
            last_used_at TEXT
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            spot_id INTEGER NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT,
            status TEXT NOT NULL DEFAULT 'ACTIVE'
                CHECK (status IN ('ACTIVE', 'COMPLETED')),
            FOREIGN KEY (user_id) REFERENCES Users(user_id),
            FOREIGN KEY (spot_id) REFERENCES parking_spots(id)
        );

        CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);
        CREATE INDEX IF NOT EXISTS idx_bookings_spot_status
            ON bookings(spot_id, status);
        """)

        # Add qr_token for older versions of Users, without deleting existing data.
        cols = {row["name"] for row in db.execute("PRAGMA table_info(Users)")}
        if "qr_token" not in cols:
            db.execute("ALTER TABLE Users ADD COLUMN qr_token TEXT")
        if "created_at" not in cols:
            db.execute("ALTER TABLE Users ADD COLUMN created_at TEXT")

        # Seed a small set of spaces only if there are no spaces yet.
        count = db.execute("SELECT COUNT(*) FROM parking_spots").fetchone()[0]
        if count == 0:
            for i in range(1, 13):
                accessible = 1 if i <= 2 else 0
                db.execute(
                    "INSERT INTO parking_spots (spot_name, is_accessible, status) "
                    "VALUES (?, ?, 'FREE')",
                    (f"A{i:02d}", accessible)
                )


def new_qr_token():
    return secrets.token_urlsafe(24)


def qr_png_bytes(payload):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def ensure_qr_token(db, user):
    token = user["qr_token"]
    if token:
        return token
    token = new_qr_token()
    db.execute(
        "UPDATE Users SET qr_token=? WHERE user_id=?",
        (token, user["user_id"]),
    )
    return token


def priority_allocate(db, user):
    """
    Allocate a free spot. Accessibility-required users are assigned an accessible
    spot first. Otherwise, prefer the least recently used spot, then the spot
    used least often, to encourage fair rotation.
    """
    free_spots = db.execute("""
        SELECT p.*,
            (SELECT COUNT(*) FROM bookings b WHERE b.spot_id = p.id) AS use_count,
            (SELECT MAX(b.check_in) FROM bookings b WHERE b.spot_id = p.id) AS last_check_in
        FROM parking_spots p
        WHERE p.status = 'FREE'
        ORDER BY
            CASE
                WHEN ? = 1 AND p.is_accessible = 1 THEN 0
                WHEN ? = 1 AND p.is_accessible = 0 THEN 1
                WHEN ? = 0 AND p.is_accessible = 0 THEN 0
                ELSE 1
            END,
            CASE WHEN last_check_in IS NULL THEN 0 ELSE 1 END,
            last_check_in ASC,
            use_count ASC,
            p.spot_name ASC
    """, (
        int(user["accessibility_need"]),
        int(user["accessibility_need"]),
        int(user["accessibility_need"])
    )).fetchall()

    if not free_spots:
        return None
    return free_spots[0]


@app.route("/")
def dashboard():
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM parking_spots").fetchone()[0]
        free = db.execute(
            "SELECT COUNT(*) FROM parking_spots WHERE status='FREE'"
        ).fetchone()[0]
        occupied = db.execute(
            "SELECT COUNT(*) FROM parking_spots WHERE status='OCCUPIED'"
        ).fetchone()[0]
        users = db.execute("SELECT COUNT(*) FROM Users").fetchone()[0]

        spots = db.execute("""
            SELECT p.*,
                   u.name AS current_user_name,
                   b.check_in AS current_check_in
            FROM parking_spots p
            LEFT JOIN bookings b
              ON b.spot_id = p.id AND b.status = 'ACTIVE'
            LEFT JOIN Users u ON u.user_id = b.user_id
            ORDER BY p.spot_name
        """).fetchall()

        recent = db.execute("""
            SELECT b.id, u.name, u.user_id, p.spot_name,
                   b.check_in, b.check_out, b.status
            FROM bookings b
            JOIN Users u ON u.user_id = b.user_id
            JOIN parking_spots p ON p.id = b.spot_id
            ORDER BY b.id DESC LIMIT 8
        """).fetchall()

    return render_template(
        "dashboard.html", total=total, free=free, occupied=occupied,
        users=users, spots=spots, recent=recent
    )



@app.route("/users")
def user_list():
    # Allow only the specified page sizes.
    allowed_sizes = [10, 25, 50, 100]

    try:
        per_page = int(request.args.get("per_page", 10))
    except (ValueError, TypeError):
        per_page = 10

    if per_page not in allowed_sizes:
        per_page = 10

    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    with get_db() as db:
        # Count all registered users.
        total_users = db.execute(
            "SELECT COUNT(*) FROM Users"
        ).fetchone()[0]

        # Calculate the number of pages.
        total_pages = max(
            1, (total_users + per_page - 1) // per_page
        )

        # Keep the requested page within the valid range.
        page = min(page, total_pages)

        # Calculate where this page starts.
        offset = (page - 1) * per_page

        # Retrieve only the users needed for this page.
        users = db.execute("""
            SELECT u.*,
                (
                    SELECT COUNT(*)
                    FROM bookings b
                    WHERE b.user_id = u.user_id
                ) AS booking_count
            FROM Users u
            ORDER BY u.name
            LIMIT ? OFFSET ?
        """, (per_page, offset)).fetchall()

    return render_template(
        "users.html",
        users=users,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_users=total_users,
        allowed_sizes=allowed_sizes
    )


@app.route("/users/<user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id):
    with get_db() as db:
        user = db.execute(
            "SELECT * FROM Users WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if user is None:
            flash("User not found.", "error")
            return redirect(url_for("user_list"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            accessibility_need = int(
                "accessibility_need" in request.form
            )

            if not name or not email:
                flash("Name and email are required.", "error")
                return render_template("edit_user.html", user=user)

            duplicate = db.execute(
                """
                SELECT 1 FROM Users
                WHERE email = ? COLLATE NOCASE
                  AND user_id != ?
                """,
                (email, user_id)
            ).fetchone()

            if duplicate:
                flash("This email is already registered.", "error")
                return render_template("edit_user.html", user=user)

            db.execute(
                """
                UPDATE Users
                SET name = ?, email = ?, accessibility_need = ?
                WHERE user_id = ?
                """,
                (name, email, accessibility_need, user_id)
            )

            flash("User updated successfully.", "success")
            return redirect(url_for("user_list"))

    return render_template("edit_user.html", user=user)


@app.route("/users/<user_id>/delete", methods=["POST"])
def delete_user(user_id):
    with get_db() as db:
        user = db.execute(
            "SELECT user_id FROM Users WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if user is None:
            flash("User not found.", "error")
            return redirect(url_for("user_list"))

        booking = db.execute(
            "SELECT 1 FROM bookings WHERE user_id = ? LIMIT 1",
            (user_id,)
        ).fetchone()

        if booking:
            flash(
                "This user has booking history and cannot be deleted.",
                "error"
            )
            return redirect(url_for("user_list"))

        db.execute(
            "DELETE FROM Users WHERE user_id = ?",
            (user_id,)
        )

        flash("User deleted successfully.", "success")

    return redirect(url_for("user_list"))




@app.route("/users/add", methods=["GET", "POST"])
def add_user():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        accessibility = 1 if request.form.get("accessibility_need") == "on" else 0

        if not first_name or not last_name or not email:
            flash("Please fill in all required fields.", "error")
            return render_template("add_user.html")

        name = f"{first_name} {last_name}"
        qr_token = secrets.token_urlsafe(24)

        try:
            with get_db() as db:
                # Check for an existing email, ignoring letter case.
                existing_email = db.execute(
                    "SELECT 1 FROM Users WHERE email = ? COLLATE NOCASE",
                    (email,)
                ).fetchone()

                if existing_email:
                    flash("This email address is already registered.", "error")
                    return render_template("add_user.html")

                # Generate a unique User ID.
                while True:
                    user_id = "USR-" + secrets.token_hex(4).upper()
                    existing_id = db.execute(
                        "SELECT 1 FROM Users WHERE user_id = ?",
                        (user_id,)
                    ).fetchone()
                    if not existing_id:
                        break

                db.execute("""
                    INSERT INTO Users
                        (user_id, name, email, accessibility_need, qr_token)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, name, email, accessibility, qr_token))

            flash("User registered successfully.", "success")
            return render_template(
                "add_user.html",
                created_user_id=user_id,
                created_token=qr_token
            )

        except sqlite3.IntegrityError:
            flash("This email or user ID is already registered.", "error")

    return render_template("add_user.html")


@app.route("/users/<user_id>/qr")
def user_qr(user_id):
    with get_db() as db:
        user = db.execute(
            "SELECT user_id, name, qr_token FROM Users WHERE user_id=?",
            (user_id,)
        ).fetchone()
        if user is None:
            abort(404)
        token = ensure_qr_token(db, user)
        user = dict(user)
        user["qr_token"] = token
    return render_template("qr.html", user=user)


@app.route("/users/<user_id>/qr.png")
def user_qr_image(user_id):
    download = request.args.get("download") == "1"
    with get_db() as db:
        user = db.execute(
            "SELECT user_id, qr_token FROM Users WHERE user_id=?",
            (user_id,)
        ).fetchone()
        if user is None:
            abort(404)
        token = ensure_qr_token(db, user)
    filename = f"{user['user_id']}-bicycle-parking-qr.png"
    return send_file(
        qr_png_bytes(token),
        mimetype="image/png",
        as_attachment=download,
        download_name=filename,
    )


@app.route("/scan", methods=["GET", "POST"])
def scan():
    if request.method == "POST":
        token = request.form.get("qr_token", "").strip()
        if not token:
            flash("Scan the user QR code, or paste the token if the camera is unavailable.", "error")
            return redirect(url_for("scan"))

        with get_db() as db:
            user = db.execute(
                "SELECT * FROM Users WHERE qr_token=?", (token,)
            ).fetchone()
            if user is None:
                # Allows an existing QR code containing the user_id during migration.
                user = db.execute(
                    "SELECT * FROM Users WHERE user_id=?", (token,)
                ).fetchone()

            if user is None:
                flash("QR code not recognized. Check that the user is registered.", "error")
                return redirect(url_for("scan"))

            active = db.execute("""
                SELECT b.id, b.spot_id, p.spot_name
                FROM bookings b
                JOIN parking_spots p ON p.id=b.spot_id
                WHERE b.user_id=? AND b.status='ACTIVE'
                ORDER BY b.id DESC LIMIT 1
            """, (user["user_id"],)).fetchone()

            now = datetime.now().astimezone().isoformat(timespec="seconds")

            if active:
                db.execute(
                    "UPDATE bookings SET check_out=?, status='COMPLETED' WHERE id=?",
                    (now, active["id"])
                )
                db.execute(
                    "UPDATE parking_spots SET status='FREE' WHERE id=?",
                    (active["spot_id"],)
                )
                flash(
                    f"Check-out recorded for {user['name']} from space "
                    f"{active['spot_name']}.", "success"
                )
            else:
                spot = priority_allocate(db, user)
                if spot is None:
                    flash("No free parking spaces are currently available.", "error")
                    return redirect(url_for("scan"))

                db.execute("""
                    INSERT INTO bookings (user_id, spot_id, check_in, status)
                    VALUES (?, ?, ?, 'ACTIVE')
                """, (user["user_id"], spot["id"], now))
                db.execute("""
                    UPDATE parking_spots
                    SET status='OCCUPIED', last_used_at=?
                    WHERE id=?
                """, (now, spot["id"]))
                flash(
                    f"Check-in recorded for {user['name']}. Assigned space "
                    f"{spot['spot_name']}.", "success"
                )

        return render_template("parking_result.html")

    return render_template("scan.html")



@app.route("/history")
def history():
    # Get the search text from the URL.
    search = request.args.get("q", "").strip()

    # Allowed number of records per page.
    allowed_sizes = [10, 25, 50, 100]

    try:
        per_page = int(request.args.get("per_page", 10))
    except (ValueError, TypeError):
        per_page = 10

    if per_page not in allowed_sizes:
        per_page = 10

    # Get the requested page number.
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    # Build the search condition once, for both counting and retrieving.
    where_sql = ""
    params = []

    if search:
        pattern = f"%{search}%"
        where_sql = """
            WHERE u.name LIKE ?
               OR u.user_id LIKE ?
               OR p.spot_name LIKE ?
        """
        params = [pattern, pattern, pattern]

    with get_db() as db:
        # Count all records that match the search.
        total_records = db.execute(f"""
            SELECT COUNT(*)
            FROM bookings b
            JOIN Users u ON u.user_id = b.user_id
            JOIN parking_spots p ON p.id = b.spot_id
            {where_sql}
        """, params).fetchone()[0]

        # Calculate the number of pages.
        total_pages = max(
            1, (total_records + per_page - 1) // per_page
        )

        # Make sure the requested page is valid.
        page = min(page, total_pages)

        # Calculate where this page starts.
        offset = (page - 1) * per_page

        # Retrieve only the records needed for this page.
        rows = db.execute(f"""
            SELECT b.id, u.name, u.user_id, p.spot_name,
                   b.check_in, b.check_out, b.status
            FROM bookings b
            JOIN Users u ON u.user_id = b.user_id
            JOIN parking_spots p ON p.id = b.spot_id
            {where_sql}
            ORDER BY b.id DESC
            LIMIT ? OFFSET ?
        """, params + [per_page, offset]).fetchall()

    return render_template(
        "history.html",
        rows=rows,
        search=search,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_records=total_records,
        allowed_sizes=allowed_sizes
    )


@app.route("/spaces", methods=["GET", "POST"])
def spaces():
    if request.method == "POST":
        spot_id = request.form.get("spot_id", type=int)
        status = request.form.get("status", "")

        if status not in ("FREE", "OCCUPIED") or not spot_id:
            flash("Invalid parking-space update.", "error")
            return redirect(url_for("spaces"))

        # Check whether this space has an active booking.
        with get_db() as db:
            active = db.execute(
                "SELECT id FROM bookings WHERE spot_id=? AND status='ACTIVE'",
                (spot_id,)
            ).fetchone()

            if status == "FREE" and active:
                flash(
                    "This space has an active booking. Check the user out first.",
                    "error"
                )
            elif status == "OCCUPIED" and not active:
                flash(
                    "Use the QR check-in page to occupy a space so a booking is recorded.",
                    "error"
                )
            else:
                db.execute(
                    "UPDATE parking_spots SET status=? WHERE id=?",
                    (status, spot_id)
                )
                flash("Parking-space status updated.", "success")

        return redirect(url_for("spaces"))

    # Allowed number of spaces per page.
    allowed_sizes = [10, 25, 50, 100]

    try:
        per_page = int(request.args.get("per_page", 10))
    except (ValueError, TypeError):
        per_page = 10

    if per_page not in allowed_sizes:
        per_page = 10

    # Get the requested page.
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    with get_db() as db:
        # Count all parking spaces.
        total_spots = db.execute(
            "SELECT COUNT(*) FROM parking_spots"
        ).fetchone()[0]

        # Calculate total pages.
        total_pages = max(
            1, (total_spots + per_page - 1) // per_page
        )

        page = min(page, total_pages)
        offset = (page - 1) * per_page

        # Retrieve only the spaces for this page.
        rows = db.execute("""
            SELECT p.*,
                   u.name AS current_user_name,
                   b.check_in AS current_check_in
            FROM parking_spots p
            LEFT JOIN bookings b
                ON b.spot_id = p.id AND b.status = 'ACTIVE'
            LEFT JOIN Users u
                ON u.user_id = b.user_id
            ORDER BY p.spot_name
            LIMIT ? OFFSET ?
        """, (per_page, offset)).fetchall()

    return render_template(
        "spaces.html",
        spots=rows,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_spots=total_spots,
        allowed_sizes=allowed_sizes
    )

@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    # For local testing only. For a trusted LAN, set host='0.0.0.0'.
    app.run(host="127.0.0.1", port=5000, debug=True)
