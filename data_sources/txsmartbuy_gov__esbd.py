import requests
from typing import Any, Dict

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
    :param params: Optional query parameters for the request.
    :return: Parsed JSON response from the ESBD endpoint.
    """
    response = requests.post(ESBD_URL, params=params or {})
    response.raise_for_status()
    return response.json()


def fetch_txsmartbuy_solicitations() -> Solicitations:
    """
    Fetch solicitations from Texas SmartBuy ESBD and return as Solicitations object.
    """
    print("Starting Texas SmartBuy ESBD data fetch...")

    try:
        # Fetch raw data
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
