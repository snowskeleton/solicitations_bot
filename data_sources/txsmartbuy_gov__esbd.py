import requests
from typing import Any, Dict

ESBD_URL = "https://www.txsmartbuy.gov/app/extensions/CPA/CPAMain/1.0.0/services/ESBD.Service.ss"

def fetch_txsmartbuy_esbd_data(params: Dict[str, Any] = {}) -> Any:
    """
    Fetch data from the Texas SmartBuy ESBD endpoint.
    :param params: Optional query parameters for the request.
    :return: Parsed JSON response from the ESBD endpoint.
    """
    response = requests.get(ESBD_URL, params=params or {})
    response.raise_for_status()
    return response.json()

# TODO: Add mapping logic to convert ESBD data to the generic Solicitation model 
