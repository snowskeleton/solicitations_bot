from typing import Dict

from flask import Flask, request, redirect, render_template, session

import storage

from emailer import send_email
from env import ADMIN_EMAIL, COOKIE_SECRET, URI
from Solicitation import Solicitation
from evp_nc_gov import filter_cached_solicitations
# from evp_nc_gov import download_cached_records, filter_solicitations


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

    return render_template("admin.html", users=storage.list_users(), email=email)


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
    return render_template("base.html")


@app.route("/send-link", methods=["POST"])
def send_magic_link():
    email = request.form.get("email")
    if not email:
        return render_template("base.html", error="Email required")
    if not storage.get_user(email) and not email == ADMIN_EMAIL:
        return render_template("base.html", error="User not found. Please check your spelling or contact your admin.")

    token = storage.generate_magic_token(email)
    link = f"{URI}/magic-login?token={token}"
    send_email(email, "Solicitations Login Link", f"Click here to log in: {link}")
    return render_template("base.html", error=f"Login link sent to {email}")


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


@app.route("/schedules", methods=["GET"])
def schedule():
    email = session.get("email")
    if not email:
        return redirect("/login")
    user = storage.get_user(email)
    if not user:
        return redirect("/login")
    schedules = storage.get_schedules_for_user(user.id)
    return render_template("schedules.html", schedules=schedules, email=email)


@app.route("/schedules/<int:schedule_id>/edit", methods=["GET"])
def schedule_edit(schedule_id: int):
    email = session.get("email")
    if not email:
        return redirect("/login")
    user = storage.get_user(email)
    if not user:
        return "User not found", 404

    if schedule_id == 0:
        # schedule starts index from 1, so this is safe
        schedule = None
    else:
        schedule = storage.get_schedule_by_id(schedule_id)
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
    user = storage.get_user(email)
    if not user:
        return "User not found", 404

    schedule_data: Dict[str, str | None] = {
        "name": request.form.get("name", "").strip() or "Default",
        "Monday": request.form.get("time_Monday", "") or None,
        "Tuesday": request.form.get("time_Tuesday", "") or None,
        "Wednesday": request.form.get("time_Wednesday", "") or None,
        "Thursday": request.form.get("time_Thursday", "") or None,
        "Friday": request.form.get("time_Friday", "") or None,
        "Saturday": request.form.get("time_Saturday", "") or None,
        "Sunday": request.form.get("time_Sunday", "") or None,
    }

    storage.add_schedule(user.id, schedule_data)
    return redirect("/schedules")


@app.route("/schedules/<int:schedule_id>/save", methods=["POST"])
def schedule_save(schedule_id: int):
    email = session.get("email")
    if not email:
        return redirect("/login")
    user = storage.get_user(email)
    if not user:
        return "User not found", 404

    schedule = storage.get_schedule_by_id(schedule_id)
    if not schedule or schedule.user_id != user.id:
        return "Schedule not found or access denied", 404

    updated_data: Dict[str, str | None] = {
        "name": request.form.get("name", "").strip() or "Default",
        "Monday": request.form.get("time_Monday", "") or None,
        "Tuesday": request.form.get("time_Tuesday", "") or None,
        "Wednesday": request.form.get("time_Wednesday", "") or None,
        "Thursday": request.form.get("time_Thursday", "") or None,
        "Friday": request.form.get("time_Friday", "") or None,
        "Saturday": request.form.get("time_Saturday", "") or None,
        "Sunday": request.form.get("time_Sunday", "") or None,
    }

    storage.update_schedule(schedule_id, updated_data)
    return redirect("/schedules")


# Route to trigger the "run now" functionality for the logged-in user
@app.route("/run", methods=["POST"])
def run_scraper():
    email = session.get("email")
    if not email:
        return redirect("/login")

    user = storage.get_user(email)
    if not user:
        return redirect("/login")

    from evp_nc_gov import run_scraper_job
    run_scraper_job(user)

    return redirect("/")

# Filter management routes


@app.route("/filters", methods=["GET"])
def filters():
    email = session.get("email")
    if not email:
        return redirect("/login")

    user = storage.get_user(email)
    if not user:
        return redirect("/login")

    user_filters = storage.get_filters_for_user(user.id)
    return render_template("filters.html", filters=user_filters, email=email, fields=Solicitation.get_filterable_fields())


@app.route("/filters/create", methods=["POST"])
def create_filter():
    email = session.get("email")
    if not email:
        return redirect("/login")

    user = storage.get_user(email)
    if not user:
        return redirect("/login")

    filter_id = request.form.get("filter_id")
    name = request.form.get("name")
    criteria = request.form.get("criteria")

    if not name or not criteria:
        return "Missing name or criteria", 400

    if filter_id:
        storage.update_filter(int(filter_id), name, criteria)
    else:
        storage.add_filter(user.id, name, criteria)
    return redirect("/filters")


@app.route("/filters/<int:filter_id>/delete", methods=["POST"])
def delete_filter(filter_id: int):
    email = session.get("email")
    if not email:
        return redirect("/login")

    user = storage.get_user(email)
    if not user:
        return redirect("/login")

    filter = storage.get_filter_by_id(filter_id)
    if not filter or filter.user_id != user.id:
        return "Filter not found or access denied", 404

    storage.delete_filter(filter_id)
    return redirect("/filters")


@app.route("/filters/fetch", methods=["POST"])
def fetch_data_for_filters():
    email = session.get("email")
    if not email:
        return redirect("/login")

    user = storage.get_user(email)
    if not user:
        return redirect("/login")

    # download_cached_records()
    return redirect("/filters")


@app.route("/filters/test", methods=["POST"])
def test_filters():
    email = session.get("email")
    if not email:
        return redirect("/login")

    user = storage.get_user(email)
    if not user:
        return redirect("/login")

    filters = storage.get_filters_for_user(user.id)
    # records = download_cached_records()
    matched = filter_cached_solicitations(user)
    # matched = [
    #     record for record in records
    #     if any(filter_solicitations([record], user, [f])[0] for f in filters)
    # ]
    return render_template("filters.html", filters=filters, email=email, fields=Solicitation.get_filterable_fields(), matches=matched)
