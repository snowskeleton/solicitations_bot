import inspect

from dataclasses import dataclass
from typing import Dict, Optional, List

from storage.models import Filter


FIELD_LABELS = {
    "title": "Project Title",
    "description": "Description",
    # "solicitation_number": "Solicitation Number",
    "posted_date": "Posted Date",
    "open_date": "Open Date",
    "department": "Department",
    # "status": "Status",
    # "state": "State",
    # ... add more as needed
}

@dataclass
class Solicitation:
    Id: str
    EntityName: str
    state: Optional[str] = None
    open_date: Optional[str] = None
    department: Optional[str] = None
    posted_date: Optional[str] = None
    solicitation_id: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    solicitation_number: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None

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
            f"state={self.state}, open_date={self.open_date}, " \
            f"department={self.department}, posted_date={self.posted_date}, " \
            f"solicitation_id={self.solicitation_id}, title={self.title}, " \
            f"status={self.status}, solicitation_number={self.solicitation_number}, " \
            f"description={self.description})"

    def format_html(self) -> str:
        # Use the solicitation's URL if available, otherwise fall back to EVP format
        if self.url:
            job_link = self.url
        else:
            job_link = f"https://evp.nc.gov/solicitations/details/?id={self.Id}"

        lines = [
            f'<li><strong>{FIELD_LABELS.get("title", "Name")}:</strong> <a href="{job_link}">{self.title}</a><br>']
        for field, label in FIELD_LABELS.items():
            if field == "title":
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
