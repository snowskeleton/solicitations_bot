import json
from typing import List, Dict, Any
from Solicitation import Solicitation  # Adjust import path as needed


def evaluate_filter(criteria: Dict[str, Any], solicitation: Solicitation) -> bool:
    def evaluate(node: Dict[str, Any]) -> bool:
        if "conditions" in node:
            results = [evaluate(cond) for cond in node["conditions"]]
            return all(results) if node["op"].upper() == "AND" else any(results)
        else:
            field = node.get("field")
            op = node.get("operator")
            value = node.get("value", "").lower()
            invert = node.get("invert", False)

            field_value = str(getattr(solicitation, field, "")).lower()

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


def filter_solicitations(solicitations: List[Solicitation], filters: List[Dict[str, Any]]) -> List[Solicitation]:
    return [
        s for s in solicitations
        if any(evaluate_filter(f["criteria"], s) for f in filters)
    ]
