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
