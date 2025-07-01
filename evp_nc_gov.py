import gzip
import requests

from io import BytesIO

import json
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from Solicitation import Solicitation, Solicitations
# from filters import evaluate_filter
from storage import User
from storage import get_filters_for_user
from emailer import send_summary_email


def fetch_solicitation_data() -> str:
    # from selenium.webdriver.chrome.options import Options

    # options = Options()
    # options.add_argument("--headless=new")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # caps = DesiredCapabilities.CHROME.copy()
    # caps["goog:loggingPrefs"] = {"performance": "ALL"}

    from selenium.webdriver.chrome.service import Service

    CHROMEDRIVER_PATH = "/usr/bin/chromedriver"  # Adjust if different in your Docker container

    service = Service(executable_path=CHROMEDRIVER_PATH)
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    driver = webdriver.Chrome(service=service, options=options)

    driver.get("https://evp.nc.gov/solicitations/")
    driver.implicitly_wait(5)

    # Note: This relies on the Chrome DevTools Protocol logs, not seleniumbase's `.requests`
    # The previous seleniumbase Driver supported `.requests`, which is not native to raw selenium
    # If you need detailed request access, consider using something like undetected-chromedriver or browsermob-proxy
    data = None
    # Collect network requests from Chrome DevTools logs
    logs = driver.get_log("performance")
    target_url = None
    target_request = None
    for entry in logs:
        log = json.loads(entry["message"])["message"]
        if (
            log.get("method") == "Network.requestWillBeSent"
            and "/_services/entity-grid-data.json/" in log.get("params", {}).get("request", {}).get("url", "")
        ):
            target_url = log["params"]["request"]["url"]
            target_request = log["params"]["request"]
            break

    if target_url and target_request:
        # There may be no body in GET requests, so adapt as needed
        body = target_request.get("postData")
        if body:
            updated_payload = json.loads(body)
            updated_payload['pageSize'] = 1000
        else:
            updated_payload = {"pageSize": 1000}
        headers = target_request.get("headers", {})
        headers.pop('Content-Length', None)
        headers['Referer'] = "https://evp.nc.gov/solicitations/"
        headers['Origin'] = "https://evp.nc.gov"
        headers['Accept-Encoding'] = "gzip"

        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])

        resp = session.post(
            target_url,
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

    driver.quit()

    return "solicitations_cache.json"


def load_cached_solicitations() -> Solicitations:
    if not os.path.exists("solicitations_cache.json"):
        return Solicitations()

    with open("solicitations_cache.json", "r") as f:
        data = json.load(f)

    return Solicitations(Solicitation.from_dict(record) for record in data.get("Records", []))


def filter_cached_solicitations(user: User) -> Solicitations:
    cached_records = load_cached_solicitations()
    filters = get_filters_for_user(user.id)
    filtered_records = cached_records.filter(filters)
    return filtered_records


def run_scraper_job(user: User):
    fetch_solicitation_data()
    filtered_records = filter_cached_solicitations(user)
    send_summary_email(user.email, filtered_records)
