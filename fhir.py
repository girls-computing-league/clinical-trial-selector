from typing import Tuple, Optional, Dict, Any, Union
from dateutil.parser import parse
from datetime import datetime

class Observation:
    
    def __init__(self, resource : Dict[str, Any]):
        self._resource = resource
        self.loinc = self._extract_loinc()
        value, unit = self._extract_value()
        self.value = value
        self.unit = unit
        self.datetime = self._extract_datetime()

    def _extract_loinc(self) -> Optional[str]:
        for coding in self._resource.get('code',{}).get('coding',[]):
            if coding.get('system') == "http://loinc.org":
                return coding.get('code')
        return None

    def _extract_value(self) -> Tuple[Optional[float], Optional[str]]:
        value_quantity: Dict[str, Any] = self._resource.get('valueQuantity', {})
        return value_quantity.get('value'), value_quantity.get('code')

    def _extract_datetime(self) -> Optional[datetime]:
        iso = self._resource.get('effectiveDateTime')
        if not iso:
            return None
        return parse(iso)
