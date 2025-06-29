import gzip
import requests

from io import BytesIO

import json

from seleniumbase import Driver

from Solicitation import Solicitation
from storage import User
from emailer import send_summary_email


def run_scraper_job(user: User):
    # Optional: Run headless
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--headless=new")

    driver = Driver(
        headless=True,
        agent="user",
        browser="chrome",
        use_wire=True
    )

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
                send_summary_email(user.email, records)

                break

    driver.quit()
