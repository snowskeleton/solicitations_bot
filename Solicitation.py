import inspect

from dataclasses import dataclass
from typing import Dict, Optional, List, Any, cast

from storage import Filter


FIELD_LABELS = {
    "evp_name": "Project Title",
    "evp_description": "Description",
    # "evp_solicitationnbr": "Solicitation Number",
    "evp_posteddate": "Posted Date",
    "evp_opendate": "Open Date",
    "owningbusinessunit": "Department",
    "statuscode": "Status",
    "statecode": "State",
    # ... add more as needed
}

@dataclass
class Solicitation:
    Id: str
    EntityName: str
    statecode: Optional[str] = None
    evp_opendate: Optional[str] = None
    owningbusinessunit: Optional[str] = None
    evp_posteddate: Optional[str] = None
    evp_solicitationid: Optional[str] = None
    evp_name: Optional[str] = None
    statuscode: Optional[str] = None
    evp_solicitationnbr: Optional[str] = None
    evp_description: Optional[str] = None

    @classmethod
    def from_dict(cls, record: Dict[str, Any]) -> 'Solicitation':
        attributes: List[Any] = record.get("Attributes", [])
        if not attributes:
            raise ValueError("No attributes found in the record")

        attribute_map = {}
        for raw_attr in attributes:
            if isinstance(raw_attr, dict):
                attr = cast(Dict[str, Any], raw_attr)
                attribute_map[attr.get("Name")] = attr.get("DisplayValue")

        return cls(
            Id=record.get("Id"),
            EntityName=record.get("EntityName"),
            **{
                k: v
                for k, v in attribute_map.items()
                if k in inspect.signature(cls).parameters and k not in ('Id', 'EntityName')
            }
        )
    
    @classmethod
    def get_filterable_fields(cls) -> List[Dict[str, str]]:
        return sorted(
            [
                {"field": field, "label": FIELD_LABELS[field]}
                for field in inspect.signature(cls).parameters
                if field in FIELD_LABELS
            ],
            key=lambda x: x["label"]
        )

    def __str__(self):
        return f"Solicitation(Id={self.Id}, EntityName={self.EntityName}, " \
               f"statecode={self.statecode}, evp_opendate={self.evp_opendate}, " \
               f"owningbusinessunit={self.owningbusinessunit}, evp_posteddate={self.evp_posteddate}, " \
               f"evp_solicitationid={self.evp_solicitationid}, evp_name={self.evp_name}, " \
               f"statuscode={self.statuscode}, evp_solicitationnbr={self.evp_solicitationnbr}, " \
               f"evp_description={self.evp_description})"

    def format_html(self) -> str:
        job_link = f"https://evp.nc.gov/solicitations/details/?id={self.Id}"
        lines = [
            f'<li><strong>{FIELD_LABELS.get("evp_name", "Name")}:</strong> <a href="{job_link}">{self.evp_name}</a><br>']
        for field, label in FIELD_LABELS.items():
            if field == "evp_name":
                continue
            value = getattr(self, field, "")
            if value:
                lines.append(f"<strong>{label}:</strong> {value}<br>")
        lines.append("</li>")
        return "\n".join(lines)


class Solicitations(List[Solicitation]):

    def to_html(self) -> str:
        if not self:
            return "No solicitations found."

        body_lines: List[str] = []
        body_lines.append("<h2>Solicitations Summary:</h2><ul>")
        for s in self:
            body_lines.append(s.format_html())
        body_lines.append("</ul>")
        return "\n".join(body_lines)

    def filter(self, filters: List[Filter]) -> "Solicitations":
        from filters import evaluate_filter
        if not filters:
            return self

        filtered_records = [
            record for record in self
            if any(evaluate_filter(f.criteria, record) for f in filters)
        ]
        return Solicitations(filtered_records)
