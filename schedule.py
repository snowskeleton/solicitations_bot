import threading
import time
from datetime import datetime, time as dt_time
from typing import Any
from storage.db import has_run_today, mark_as_run, get_all_schedules, get_user_by_id
# Import the centralized job function
from routes import fetch_and_save_all_solicitations, process_user_solicitations
from emailer import send_summary_email, send_email
from env import ADMIN_EMAIL

def should_run(schedule_time_str: str) -> bool:
    now = datetime.now()
    try:
        target_time = dt_time.fromisoformat(schedule_time_str)
        scheduled_datetime = datetime.combine(now.date(), target_time)
        print(f"Checking if should run {now} at {scheduled_datetime} for schedule time {schedule_time_str} from {target_time}")
        return now >= scheduled_datetime
    except ValueError:
        print("Exception parsing time:", schedule_time_str)
        return False

def scheduler_loop():
    # print("Scheduler loop started")
    weekday_fields = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    while True:
        now = datetime.now()
        today_index = now.weekday()  # 0 = Monday, ..., 6 = Sunday
        today_field = weekday_fields[today_index]
        date_str = now.strftime("%Y-%m-%d")

        schedules: list[Any] = get_all_schedules()
        # Find all schedules that are due to run
        due_schedules: list[Any] = []
        for schedule in schedules:
            schedule_time = getattr(schedule, today_field)
            if not schedule_time:
                continue
            if has_run_today(schedule.id, date_str):
                continue
            if should_run(schedule_time):
                due_schedules.append(schedule)

        if due_schedules:
            fetch_and_save_all_solicitations()
            for schedule in due_schedules:
                user = get_user_by_id(schedule.user_id)
                if user is None:
                    continue
                print(
                    f"Running scheduled job for user {user.email} on {today_field} at {getattr(schedule, today_field)}")
                try:
                    filtered_solicitations = process_user_solicitations(user)
                    send_summary_email(user.email, filtered_solicitations)
                    mark_as_run(schedule.id, date_str)
                except Exception as e:
                    print(
                        f"Error running scheduled job for user {user.email}: {e}")
                    send_email(ADMIN_EMAIL, "Error running scheduled job",
                               f"Error running scheduled job for user {user.email} with {schedule.id}: {e}")
        else:
            print("No schedules due to run at this time.")

        time.sleep(60)

def start_scheduler():
    print("Starting scheduler...")
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
