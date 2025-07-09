import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from data_sources.Solicitation import Solicitation, Solicitations
from storage.db import save_solicitations, clear_solicitations_by_source

ESBD_URL = "https://www.txsmartbuy.gov/app/extensions/CPA/CPAMain/1.0.0/services/ESBD.Service.ss"


def esbd_from_dict(record: Dict[str, Any]) -> Solicitation:
    """
    Create a Solicitation from a Texas SmartBuy ESBD record.
    """
    return Solicitation(
        Id=str(record.get("internalid", "")),
        EntityName="TXSMARTBUY_ESBD",
        solicitation_id=str(record.get("internalid", "")),
        solicitation_number=record.get("solicitationId", ""),
        title=record.get("title", ""),
        description="",  # Not present in ESBD sample
        department=record.get("agencyName", ""),
        status=record.get("statusName", ""),
        open_date=record.get("postingDate", ""),
        posted_date=record.get("postingDate", ""),
        url=f"https://www.txsmartbuy.gov/esbd/{record.get('solicitationId', '')}"
    )


def fetch_txsmartbuy_esbd_data(params: Dict[str, Any] = {}) -> Any:
    """
    Fetch data from the Texas SmartBuy ESBD endpoint.
    If no specific page is provided, fetches all pages and combines the data.
    :param params: Optional query parameters for the request.
    :return: Parsed JSON response from the ESBD endpoint.
    """
    # If no page is specified, fetch all pages
    if "page" not in params:
        print("Fetching all Texas SmartBuy ESBD data with pagination...")

        # Fetch first page to get total records info
        first_page = fetch_txsmartbuy_esbd_data({"page": 1})

        # Extract pagination info
        total_records = first_page.get("totalRecordsFound", 0)
        records_per_page = first_page.get(
            "recordsPerPage", 24)  # Default fallback
        total_pages = (total_records + records_per_page -
                       1) // records_per_page

        print(
            f"Total records: {total_records}, Records per page: {records_per_page}, Total pages: {total_pages}")

        # Start with first page data
        all_lines = first_page.get("lines", [])

        # Fetch remaining pages using threading (3 concurrent requests)
        print(
            f"Fetching remaining {total_pages - 1} pages with 3 concurrent threads...")

        def fetch_page(page_num: int) -> List[Dict[str, Any]]:
            """Helper function to fetch a single page"""
            try:
                page_data = fetch_txsmartbuy_esbd_data({"page": page_num})
                page_lines = page_data.get("lines", [])
                print(f"Page {page_num}: {len(page_lines)} records")
                return page_lines
            except Exception as e:
                print(f"Error fetching page {page_num}: {e}")
                return []

        # Use ThreadPoolExecutor to run 3 concurrent requests
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all page requests
            future_to_page = {
                executor.submit(fetch_page, page): page
                for page in range(2, total_pages + 1)
            }

            # Collect results as they complete
            for future in as_completed(future_to_page):
                page_lines = future.result()
                all_lines.extend(page_lines)

        # Return combined data in same format as single page
        return {
            "lines": all_lines,
            "totalRecordsFound": total_records,
            "recordsPerPage": records_per_page,
            "page": 1  # Indicate this is now all data
        }

        # Set default parameters with date filtering for last month
    from datetime import datetime, timedelta

    # Calculate last 30 days date range
    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)

    start_date = thirty_days_ago.strftime("%m/%d/%Y")
    end_date = today.strftime("%m/%d/%Y")

    default_params = {
        "page": 1,
        "dateRange": "thisMonth",
        "startDate": start_date,
        "endDate": end_date,
        "urlRoot": "esbd"
    }
    # Merge with any provided params, with provided params taking precedence
    request_params = {**default_params, **params}

    response = requests.post(ESBD_URL, json=request_params)
    response.raise_for_status()
    return response.json()


def fetch_txsmartbuy_solicitations() -> Solicitations:
    """
    Fetch solicitations from Texas SmartBuy ESBD and return as Solicitations object.
    """
    print("Starting Texas SmartBuy ESBD data fetch...")

    try:
        # Fetch all data with pagination
        data = fetch_txsmartbuy_esbd_data()

        # Convert to Solicitations
        lines = data.get("lines", [])
        solicitations = Solicitations(
            esbd_from_dict(record)
            for record in lines
        )

        print(
            f"Fetched {len(solicitations)} solicitations from Texas SmartBuy")
        return solicitations

    except Exception as e:
        print(f"Error fetching Texas SmartBuy data: {e}")
        return Solicitations()


def save_txsmartbuy_solicitations_to_db() -> None:
    """
    Fetch Texas SmartBuy solicitations and save them to the database.
    """
    print("Fetching and saving Texas SmartBuy solicitations...")

    # Clear old Texas SmartBuy solicitations
    clear_solicitations_by_source("TXSMARTBUY_ESBD")

    # Fetch new solicitations
    solicitations = fetch_txsmartbuy_solicitations()

    # Save to database
    if solicitations:
        save_solicitations(solicitations)
        print(
            f"Saved {len(solicitations)} Texas SmartBuy solicitations to database")
    else:
        print("No Texas SmartBuy solicitations to save")
