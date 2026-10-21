from dataclasses import dataclass, field
from typing import Any, Dict, List
import uuid

@dataclass
class HelperInstance:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    helper_type: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    items: List[Any] = field(default_factory=list)
    visible: bool = True