
from flask import Flask, render_template, request, send_file, abort
from database import register_user, find_user
from generate_qr import generate_qr
from uuid import uuid4


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        accessibility_need = (
            request.form.get("accessibility_need") == "on"
        )

        if not name or not email:
            return render_template(
                "register.html",
                error="Name and email are required."
            ), 400

        user_id = f"USER{uuid4().hex[:8].upper()}"

        success, message = register_user(
            user_id, name, email, accessibility_need
        )

        if not success:
            return render_template(
                "register.html",
                error=message
            ), 400

        user = find_user(user_id)

        return render_template(
            "qr.html",
            user={
                "user_id": user[1],
                "name": user[2],
                "email": user[3],
                "accessibility_need": bool(user[4])
            }
        )

    return render_template("register.html")


@app.route("/qr/<user_id>")
def show_qr(user_id):
    if not find_user(user_id):
        abort(404)

    return send_file(
        generate_qr(user_id),
        mimetype="image/png"
    )


@app.route("/qr/<user_id>/download")
def download_qr(user_id):
    if not find_user(user_id):
        abort(404)

    return send_file(
        generate_qr(user_id),
        mimetype="image/png",
        as_attachment=True,
        download_name=f"{user_id}.png"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)
