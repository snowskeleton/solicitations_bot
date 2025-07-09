from typing import Dict

from flask import Flask, request, redirect, render_template, session

from storage import db
from storage.db import get_all_solicitations

from emailer import send_email
from env import ADMIN_EMAIL, COOKIE_SECRET, URI
from data_sources.Solicitation import Solicitation
from data_sources.evp_nc_gov import save_evp_solicitations_to_db
from data_sources.txsmartbuy_gov__esbd import save_txsmartbuy_solicitations_to_db


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

    return render_template("admin.html", users=db.list_users(), email=email)


@app.route("/admin/add-user", methods=["POST"])
def add_user():
    email = session.get("email")
    if not email or email != ADMIN_EMAIL:
        return "Unauthorized", 403

    new_email = request.form.get("email")
    if new_email:
        db.add_user(new_email, is_admin=False)
    return redirect("/admin")

@app.route("/admin/impersonate", methods=["POST"])
def impersonate_user():
    email = session.get("email")
    if not email or email != ADMIN_EMAIL:
        return "Unauthorized", 403

    impersonate_email = request.form.get("impersonate_email")
    if impersonate_email and db.get_user(impersonate_email):
        session["email"] = impersonate_email
    return redirect("/")


@app.route("/login", methods=["GET"])
def login_form():
    return render_template("base.html")


@app.route("/send-link", methods=["POST"])
def send_magic_link():
    email = request.form.get("email")
    if not email:
        return render_template("base.html", error="Email required")
    if not db.get_user(email) and not email == ADMIN_EMAIL:
        return render_template("base.html", error="User not found. Please check your spelling or contact your admin.")

    token = db.generate_magic_token(email)
    link = f"{URI}/magic-login?token={token}"
    send_email(email, "Solicitations Login Link", f"Click here to log in: {link}")
    return render_template("base.html", error=f"Login link sent to {email}")


@app.route("/magic-login")
def magic_login():
    token = request.args.get("token")
    if not token:
        return "No token provided", 400

    email = db.get_email_for_token(token)
    db.invalidate_token(token)
    if not email:
        return "Invalid or expired token", 400

    session["email"] = email
    return redirect("/")


@app.route("/schedules", methods=["GET"])
def schedule():
    email = session.get("email")
    if not email:
        return redirect("/login")
    user = db.get_user(email)
    if not user:
        return redirect("/login")
    schedules = db.get_schedules_for_user(user.id)
    return render_template("schedules.html", schedules=schedules, email=email)


@app.route("/schedules/<int:schedule_id>/edit", methods=["GET"])
def schedule_edit(schedule_id: int):
    email = session.get("email")
    if not email:
        return redirect("/login")
    user = db.get_user(email)
    if not user:
        return "User not found", 404

    if schedule_id == 0:
        # schedule starts index from 1, so this is safe
        schedule = None
    else:
        schedule = db.get_schedule_by_id(schedule_id)
        if not schedule or schedule.user_id != user.id:
            return "Schedule not found or access denied", 404

    if schedule:
        form_action = f"/schedules/{schedule_id}/save"
        name = schedule.name
        day_fields = ["Monday", "Tuesday", "Wednesday",
                      "Thursday", "Friday", "Saturday", "Sunday"]
        selected_days = [
            day for day in day_fields if getattr(schedule, day.lower())]
        times = {day: getattr(schedule, day.lower()) for day in selected_days}
    else:
        form_action = f"/schedules/create"
        name = ""
        selected_days = []
        times = {}

    return render_template("schedule_edit.html", schedule=schedule, email=email,
                           form_action=form_action, name=name,
                           selected_days=selected_days, times=times)


@app.route("/schedules/create", methods=["POST"])
def schedule_create():
    email = session.get("email")
    if not email:
        return redirect("/login")
    user = db.get_user(email)
    if not user:
        return "User not found", 404

    schedule_data: Dict[str, str] = {
        "name": request.form.get("name", "").strip() or "Default",
        "Monday": request.form.get("time_Monday", "") or "",
        "Tuesday": request.form.get("time_Tuesday", "") or "",
        "Wednesday": request.form.get("time_Wednesday", "") or "",
        "Thursday": request.form.get("time_Thursday", "") or "",
        "Friday": request.form.get("time_Friday", "") or "",
        "Saturday": request.form.get("time_Saturday", "") or "",
        "Sunday": request.form.get("time_Sunday", "") or "",
    }

    db.add_schedule(user.id, schedule_data)
    return redirect("/schedules")


@app.route("/schedules/<int:schedule_id>/save", methods=["POST"])
def schedule_save(schedule_id: int):
    email = session.get("email")
    if not email:
        return redirect("/login")
    user = db.get_user(email)
    if not user:
        return "User not found", 404

    schedule = db.get_schedule_by_id(schedule_id)
    if not schedule or schedule.user_id != user.id:
        return "Schedule not found or access denied", 404

    updated_data: Dict[str, str] = {
        "name": request.form.get("name", "").strip() or "Default",
        "Monday": request.form.get("time_Monday", "") or "",
        "Tuesday": request.form.get("time_Tuesday", "") or "",
        "Wednesday": request.form.get("time_Wednesday", "") or "",
        "Thursday": request.form.get("time_Thursday", "") or "",
        "Friday": request.form.get("time_Friday", "") or "",
        "Saturday": request.form.get("time_Saturday", "") or "",
        "Sunday": request.form.get("time_Sunday", "") or "",
    }

    db.update_schedule(schedule_id, updated_data)
    return redirect("/schedules")


# Route to trigger the "run now" functionality for the logged-in user
@app.route("/run", methods=["POST"])
def run_scraper():
    email = session.get("email")
    if not email:
        return redirect("/login")

    user = db.get_user(email)
    if not user:
        return redirect("/login")

    print(f"Starting scraper job for user {user.email}")

    # Fetch and save solicitations from all sources
    print("Fetching EVP solicitations...")
    save_evp_solicitations_to_db()

    print("Fetching Texas SmartBuy solicitations...")
    save_txsmartbuy_solicitations_to_db()

    all_solicitations = get_all_solicitations()
    print(f"Total solicitations in database: {len(all_solicitations)}")

    user_filters = db.get_filters_for_user(user.id)
    print(f"User has {len(user_filters)} filters")

    if user_filters:
        filtered_solicitations = all_solicitations.filter(user_filters)
        print(
            f"After filtering: {len(filtered_solicitations)} solicitations match")
    else:
        filtered_solicitations = all_solicitations
        print(
            f"No filters applied, sending all {len(filtered_solicitations)} solicitations")

    # Send email with filtered results
    from emailer import send_summary_email
    send_summary_email(user.email, filtered_solicitations)

    return redirect("/")

# Filter management routes


@app.route("/filters", methods=["GET"])
def filters():
    email = session.get("email")
    if not email:
        return redirect("/login")

    user = db.get_user(email)
    if not user:
        return redirect("/login")

    user_filters = db.get_filters_for_user(user.id)
    return render_template("filters.html", filters=user_filters, email=email, fields=Solicitation.get_filterable_fields())


@app.route("/filters/create", methods=["POST"])
def create_filter():
    email = session.get("email")
    if not email:
        return redirect("/login")

    user = db.get_user(email)
    if not user:
        return redirect("/login")

    filter_id = request.form.get("filter_id")
    name = request.form.get("name")
    criteria = request.form.get("criteria")

    if not name or not criteria:
        return "Missing name or criteria", 400

    if filter_id:
        db.update_filter(int(filter_id), name, criteria)
    else:
        db.add_filter(user.id, name, criteria)
    return redirect("/filters")


@app.route("/filters/<int:filter_id>/delete", methods=["POST"])
def delete_filter(filter_id: int):
    email = session.get("email")
    if not email:
        return redirect("/login")

    user = db.get_user(email)
    if not user:
        return redirect("/login")

    filter = db.get_filter_by_id(filter_id)
    if not filter or filter.user_id != user.id:
        return "Filter not found or access denied", 404

    db.delete_filter(filter_id)
    return redirect("/filters")


@app.route("/filters/fetch", methods=["POST"])
def fetch_data_for_filters():
    email = session.get("email")
    if not email:
        return redirect("/login")

    user = db.get_user(email)
    if not user:
        return redirect("/login")

    print(f"Fetching data for user {user.email}")

    # Fetch and save solicitations from all sources
    print("Fetching EVP solicitations...")
    save_evp_solicitations_to_db()

    print("Fetching Texas SmartBuy solicitations...")
    save_txsmartbuy_solicitations_to_db()

    return redirect("/filters")


@app.route("/filters/test", methods=["POST"])
def test_filters():
    email = session.get("email")
    if not email:
        return redirect("/login")

    user = db.get_user(email)
    if not user:
        return redirect("/login")

    filters = db.get_filters_for_user(user.id)
    print(f"User {user.email} has {len(filters)} filters")

    all_solicitations = get_all_solicitations()
    print(
        f"Retrieved {len(all_solicitations)} total solicitations from database")

    if filters:
        matched = all_solicitations.filter(filters)
        print(f"After filtering: {len(matched)} solicitations match")
    else:
        matched = all_solicitations
        print(f"No filters applied, showing all {len(matched)} solicitations")

    return render_template("filters.html", filters=filters, email=email, fields=Solicitation.get_filterable_fields(), matches=matched)
