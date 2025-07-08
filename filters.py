import json
from typing import Dict, Any
from Solicitation import Solicitation


# def evaluate_filter(criteria: Dict[str, Any], solicitation) -> bool:
def evaluate_filter(criteria: Dict[str, Any] | str, solicitation: 'Solicitation') -> bool:
    if isinstance(criteria, str):
        criteria = json.loads(criteria)
    def evaluate(node: Dict[str, Any]) -> bool:
        if "conditions" in node:
            results = [evaluate(cond) for cond in node["conditions"]]
            return all(results) if node["op"].upper() == "AND" else any(results)
        else:
            field = node.get("field")
            op = node.get("operator")
            value = node.get("value", "").lower()
            invert = node.get("invert", False)

            # Default string logic
            if isinstance(field, str):
                field_value = str(getattr(solicitation, field, "")).lower()
            else:
                field_value = ""

            # Special handling for Open Date dynamic ranges
            if field == "evp_opendate" and op == "equals" and value in ["last_1_day", "last_3_days", "last_7_days"]:
                from datetime import datetime
                try:
                    open_date_str = solicitation.evp_opendate or ""
                    if not open_date_str:
                        return False
                    open_date = datetime.strptime(open_date_str, "%Y-%m-%d")
                except Exception:
                    return False
                today = datetime.today()
                if value == "last_1_day":
                    return (today - open_date).days < 1
                elif value == "last_3_days":
                    return (today - open_date).days < 3
                elif value == "last_7_days":
                    return (today - open_date).days < 7
            # Default string logic
            result = False
            if op == "contains":
                result = value in field_value
            elif op == "equals":
                result = value == field_value
            elif op == "startsWith":
                result = field_value.startswith(value)
            elif op == "endsWith":
                result = field_value.endswith(value)

            return not result if invert else result

    return evaluate(criteria)


def filter_solicitations(solicitations: Solicitations, filters: List[Dict[str, Any]]) -> Solicitations:
    return Solicitations([
        s for s in solicitations
        if any(evaluate_filter(f["criteria"], s) for f in filters)
    ])
