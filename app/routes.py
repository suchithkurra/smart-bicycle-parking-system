from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash

bp = Blueprint("main", __name__)

# Placeholder data so the pages have something to show.
# Replace with real database queries later.
SPACES = [
    {"label": "A1", "zone": "front", "status": "FREE"},
    {"label": "A2", "zone": "front", "status": "OCCUPIED"},
    {"label": "A3", "zone": "front", "status": "FREE"},
    {"label": "B1", "zone": "standard", "status": "FREE"},
    {"label": "B2", "zone": "standard", "status": "OCCUPIED"},
    {"label": "B3", "zone": "standard", "status": "FREE"},
]


@bp.route("/")
def dashboard():
    free = sum(1 for s in SPACES if s["status"] == "FREE")
    return render_template("dashboard.html", spaces=SPACES, free=free, total=len(SPACES))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        # TODO: save user, generate unique ID and QR code
        flash(f"Registration received for {name} (not saved yet).")
        return redirect(url_for("main.register"))
    return render_template("register.html")


@bp.route("/history")
def history():
    # TODO: load parking history
    return render_template("history.html", sessions=[])


# ---------- API (used later by the camera/QR scanner) ----------

@bp.route("/api/spaces")
def api_spaces():
    return jsonify(SPACES)


@bp.route("/api/scan", methods=["POST"])
def api_scan():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    # TODO: check user, then check in (assign space) or check out
    return jsonify({"user_id": user_id, "message": "Scan received (logic not implemented yet)"}), 501
