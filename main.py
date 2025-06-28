import routes  # Import admin console after app is created
import gzip
import requests

from io import BytesIO

import json

from flask import Flask
from seleniumbase import Driver

from Solicitation import Solicitation
from emailer import send_summary_email
from env import COOKIE_SECRET, ADMIN_EMAIL
from routes import app  # Import Flask app from routes
from storage import setup_db, add_user


# Suppress SSL warnings for self-signed certs
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def run_scraper_job():
    # Optional: Run headless
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--headless=new")

    import os
    prefs = {
        "download.default_directory": os.path.abspath("."),  # download to current project directory
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    driver = Driver(headless=True, options=options)

    # Step 1: Visit page, trigger JS-driven API call
    driver.get("https://evp.nc.gov/solicitations/")

    # Allow page to load and API calls to complete
    driver.implicitly_wait(5)  # Adjust as needed

    # Step 2: Loop through requests to find the JSON API response
    for request in driver.requests:
        if request.response:
            if "/_services/entity-grid-data.json/" in request.url and request.response.status_code == 200:
                updated_payload = json.loads(request.body.decode('utf-8'))
                updated_payload['pageSize'] = 100

                headers = dict(request.headers)
                headers.pop('Content-Length', None)  # Let requests calculate
                headers['Referer'] = "https://evp.nc.gov/solicitations/"
                headers['Origin'] = "https://evp.nc.gov"
                headers['Accept-Encoding'] = "gzip"

                # Make a new requests call with increased pageSize
                session = requests.Session()
                for cookie in driver.get_cookies():
                    session.cookies.set(cookie['name'], cookie['value'])

                resp = session.post(
                    request.url,
                    headers=headers,
                    json=updated_payload,
                    verify=False
                )

                # Decode gzip if necessary
                encoding = resp.headers.get('Content-Encoding', '').lower()
                if 'gzip' in encoding:
                    try:
                        with gzip.GzipFile(fileobj=BytesIO(resp.content)) as f:
                            data = json.loads(f.read().decode('utf-8'))
                    except gzip.BadGzipFile:
                        data = resp.json()
                else:
                    data = resp.json()

                records = [Solicitation.from_dict(record) for record in data.get("Records", [])]
                send_summary_email("isaac@snowskeleton.net", records)

                break

    driver.quit()


if __name__ == "__main__":
    setup_db()
    add_user(ADMIN_EMAIL, is_admin=True)
    app.run(host="0.0.0.0", port=5002, debug=True)
