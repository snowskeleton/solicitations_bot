from flask import Flask, request, redirect, render_template, session

from emailer import send_email
from env import ADMIN_EMAIL, COOKIE_SECRET, URI
import storage


app = Flask(__name__)
app.secret_key = COOKIE_SECRET

@app.route("/", methods=["GET"])
def default():
    email = session.get("email")
    if not email:
        return redirect("/login")
    return render_template("main.html", email=email, is_admin=email == ADMIN_EMAIL)

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("email", None)
    return redirect("/")

@app.route("/admin", methods=["GET"])
def admin_console():
    email = session.get("email")
    if not email or email != ADMIN_EMAIL:
        return redirect("/login")

    return render_template("admin.html", users=storage.list_users())


@app.route("/admin/add-user", methods=["POST"])
def add_user():
    email = session.get("email")
    if not email or email != ADMIN_EMAIL:
        return "Unauthorized", 403

    new_email = request.form.get("email")
    if new_email:
        storage.add_user(new_email, is_admin=False)
    return redirect("/admin")


@app.route("/login", methods=["GET"])
def login_form():
    return render_template("login.html")


@app.route("/send-link", methods=["POST"])
def send_magic_link():
    email = request.form.get("email")
    if not email:
        return "Email required", 400
    if not storage.get_user(email) and not email == ADMIN_EMAIL:
        return "User not found. Please check your spelling or contact your admin.", 404

    token = storage.generate_magic_token(email)
    link = f"{URI}/magic-login?token={token}"
    send_email(email, "Solicitations Login Link", f"Click here to log in: {link}")
    return f"Login link sent to {email}"


@app.route("/magic-login")
def magic_login():
    token = request.args.get("token")
    if not token:
        return "No token provided", 400

    email = storage.get_email_for_token(token)
    storage.invalidate_token(token)
    if not email:
        return "Invalid or expired token", 400

    session["email"] = email
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
