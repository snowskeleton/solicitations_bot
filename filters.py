import json
from datetime import datetime
from typing import Dict, Any, List

from Solicitation import Solicitation, Solicitations


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

            date_fields = ["evp_opendate", "evp_closedate", "evp_posteddate"]
            date_ranges = ["last_1_day", "last_3_days", "last_7_days"]
            if field in date_fields and value in date_ranges:
                date_str = getattr(solicitation, field, "") or ""
                if not date_str:
                    return False
                try:
                    try:
                        date_val = datetime.strptime(
                            date_str, "%m/%d/%Y %I:%M %p").date()
                    except ValueError:
                        date_val = datetime.strptime(
                            date_str, "%m/%d/%Y").date()
                except Exception:
                    print(f"Error parsing {field}: {date_str}")
                    return False
                today = datetime.today().date()
                if value == "last_1_day":
                    return (today - date_val).days < 1
                elif value == "last_3_days":
                    return (today - date_val).days < 3
                elif value == "last_7_days":
                    return (today - date_val).days < 7
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
