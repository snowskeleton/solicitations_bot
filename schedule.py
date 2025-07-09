import threading
import time
from datetime import datetime, time as dt_time
from storage.db import has_run_today, mark_as_run, get_all_schedules, get_user_by_id
from data_sources.evp_nc_gov import run_scraper_job


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

        schedules = get_all_schedules()
        for schedule in schedules:
            schedule_time = getattr(schedule, today_field)
            if not schedule_time:
                # print(f"Didn't match {schedule_time} for {today_field} in schedule {schedule}")
                continue
            if has_run_today(schedule.id, date_str):
                # print(f"Already run today for schedule {schedule.id} on {today_field}")
                continue
            if should_run(schedule_time):
                user = get_user_by_id(schedule.user_id)
                if user is None:
                    # print(f"User with ID {schedule.user_id} not found for schedule {schedule.id}")
                    continue
                # print(f"Running scraper for user {user.email} on {today_field} at {schedule_time}")
                # run_scraper_job(user)
                mark_as_run(schedule.id, date_str)
            else:
                print(f"Skipping schedule {schedule.id} on {today_field} at {schedule_time}")    

        time.sleep(60)

def start_scheduler():
    print("Starting scheduler...")
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
