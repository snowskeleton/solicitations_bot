import gzip
import requests
from io import BytesIO
import json
from seleniumbase import Driver
# from selenium.webdriver.chrome.options import Options

from data_sources.Solicitation import Solicitation, Solicitations
from storage.db import save_solicitations, clear_solicitations_by_source


def evp_from_dict(record: dict) -> Solicitation:
    """
    Create a Solicitation from an EVP NC Gov record.
    """
    from typing import Dict, Any, List, cast

    attributes: List[Any] = record.get("Attributes", [])
    if not attributes:
        raise ValueError("No attributes found in the record")

    attribute_map: Dict[str, Any] = {}
    for raw_attr in attributes:
        if isinstance(raw_attr, dict):
            attr = cast(Dict[str, Any], raw_attr)
            name = attr.get("Name")
            if name is not None:
                attribute_map[str(name)] = attr.get("DisplayValue")

    # Map EVP keys to generic names
    mapping: Dict[str, str] = {
        "statecode": "state",
        "evp_opendate": "open_date",
        "owningbusinessunit": "department",
        "evp_posteddate": "posted_date",
        "evp_solicitationid": "solicitation_id",
        "evp_name": "title",
        "statuscode": "status",
        "evp_solicitationnbr": "solicitation_number",
        "evp_description": "description",
    }
    generic_kwargs: Dict[str, Any] = {
        mapping[k]: v for k, v in attribute_map.items() if k in mapping
    }
    return Solicitation(
        Id=record.get("Id", ""),
        EntityName=record.get("EntityName", ""),
        **generic_kwargs
    )


def save_evp_solicitations_to_db() -> None:
    """
    Fetch EVP solicitations and save them to the database.
    """
    print("Fetching and saving EVP solicitations...")

    # Clear old EVP solicitations
    clear_solicitations_by_source("EVP_NC_GOV")

    # Fetch new solicitations
    solicitations = fetch_solicitation_data()

    # Save to database
    if solicitations:
        save_solicitations(solicitations)
        print(f"Saved {len(solicitations)} EVP solicitations to database")
    else:
        print("No EVP solicitations to save")


def fetch_solicitation_data() -> Solicitations:
    """Fetch raw solicitation data from EVP NC Gov using Selenium and return as Solicitations."""
    # options = Options()
    # options.add_argument("--headless=new")

    print("Starting Selenium driver...")
    driver = Driver(
        headless=True,
        agent="user",
        browser="chrome",
        use_wire=True,
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
            # print("Skipping request:", request.url)
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

        break

    driver.quit()

    if not data:
        print("No data retrieved from EVP")
        return Solicitations()

    # Convert to Solicitations
    solicitations = Solicitations(
        evp_from_dict(record)
        for record in data.get("Records", [])
    )

    print(f"Fetched {len(solicitations)} solicitations from EVP")
    return solicitations
