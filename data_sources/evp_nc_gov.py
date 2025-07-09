import gzip
import requests

from io import BytesIO

import json
import os

from seleniumbase import Driver

from data_sources.Solicitation import Solicitation, Solicitations
# from filters import evaluate_filter
from storage.db import User, get_filters_for_user
from emailer import send_summary_email


def fetch_solicitation_data() -> str:
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--headless=new")

    print("Starting Selenium driver...")
    driver = Driver(
        headless=True,
        agent="user",
        browser="chrome",
        use_wire=True,
        # no_sandbox=False,
        remote_debug=True
    )

    print("Navigating to the solicitations page...")
    driver.get("https://evp.nc.gov/solicitations/")
    driver.implicitly_wait(10)

    data = None
    print("Processing requests...")
    for request in driver.requests:
        if not request.response:
            print("Invalid response")
            continue
        if request.response.status_code != 200:
            print("Bad status code")
            continue
        if "/_services/entity-grid-data.json/" not in request.url:
            print("Skipping request:", request.url)
            continue

        print("Processing request:", request.url)
        updated_payload = json.loads(request.body.decode('utf-8'))
        updated_payload['pageSize'] = 1000

        headers = dict(request.headers)
        headers.pop('Content-Length', None)
        headers['Referer'] = "https://evp.nc.gov/solicitations/"
        headers['Origin'] = "https://evp.nc.gov"
        headers['Accept-Encoding'] = "gzip"

        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])

        resp = session.post(
            request.url,
            headers=headers,
            json=updated_payload,
            verify=False
        )

        encoding = resp.headers.get('Content-Encoding', '').lower()
        if 'gzip' in encoding:
            try:
                with gzip.GzipFile(fileobj=BytesIO(resp.content)) as f:
                    data = json.loads(f.read().decode('utf-8'))
            except gzip.BadGzipFile:
                data = resp.json()
        else:
            data = resp.json()

        # Cache to disk
        with open("solicitations_cache.json", "w") as f:
            json.dump(data, f, indent=2)

        break

    driver.quit()

    return "solicitations_cache.json"


def load_cached_solicitations() -> Solicitations:
    if not os.path.exists("solicitations_cache.json"):
        return Solicitations()

    with open("solicitations_cache.json", "r") as f:
        data = json.load(f)

    return Solicitations(Solicitation.evp_from_dict(record) for record in data.get("Records", []))


def filter_cached_solicitations(user: User) -> Solicitations:
    cached_records = load_cached_solicitations()
    filters = get_filters_for_user(user.id)
    filtered_records = cached_records.filter(filters)
    return filtered_records


def run_scraper_job(user: User):
    fetch_solicitation_data()
    filtered_records = filter_cached_solicitations(user)
    send_summary_email(user.email, filtered_records)
