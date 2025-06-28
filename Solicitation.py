import inspect

from dataclasses import dataclass
from typing import Dict, Optional, List, Any, cast


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
    
    def __str__(self):
        return f"Solicitation(Id={self.Id}, EntityName={self.EntityName}, " \
               f"statecode={self.statecode}, evp_opendate={self.evp_opendate}, " \
               f"owningbusinessunit={self.owningbusinessunit}, evp_posteddate={self.evp_posteddate}, " \
               f"evp_solicitationid={self.evp_solicitationid}, evp_name={self.evp_name}, " \
               f"statuscode={self.statuscode}, evp_solicitationnbr={self.evp_solicitationnbr}, " \
               f"evp_description={self.evp_description})"
