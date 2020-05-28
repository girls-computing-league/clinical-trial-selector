from typing import Tuple, Optional, Dict, Any, Union
from dateutil.parser import parse
from datetime import datetime
import json

class Observation:
    
    def __init__(self, resource : Dict[str, Any]):
        self._resource = resource
        self.loinc = self._extract_loinc()
        value, unit = self._extract_value()
        self.value = value
        self.unit = unit
        self.datetime = self._extract_datetime()

    def _extract_loinc(self) -> str:
        coding_list = self._resource.get('code',{}).get('coding',[])
        coding_system = 'http://loinc.org'
        return next((coding.get('code') for coding in coding_list \
                if coding.get('system') == coding_system) ,'')

    def _extract_value(self) -> Tuple[Optional[float], Optional[str]]:
        value_quantity: Dict[str, Any] = self._resource.get('valueQuantity', {})
        return value_quantity.get('value'), value_quantity.get('code')

    def _extract_datetime(self) -> Optional[datetime]:
        iso = self._resource.get('effectiveDateTime')
        if not iso:
            return None
        return parse(iso)

class Demographics:

    def __init__(self, resource: Dict[str, Any]):
        self._resource = resource
        self.fullname = self._extract_fullname()
        self.gender = self._extract_gender()
        self.birth_date = self._extract_birth_date()
        self.zipcode = self._extract_zipcode()
        self.JSON = json.dumps(self._resource, indent=2)

    def _extract_fullname(self) -> str:
        name = self._resource.get('name', [{'text': ''}])[0]
        fullname = name.get('text', '')
        if fullname == "":
            given = name.get('given', [''])[0]
            family = name.get('family', '')
            fullname = f"{given} {family}"
        return fullname

    def _extract_gender(self) -> str:
        return self._resource.get('gender', '')

    def _extract_birth_date(self) -> str:
        return self._resource.get('birthDate', '')

    def _extract_zipcode(self) -> str:
        return self._resource.get('address', [{'postalCode': ''}])[0].get('postalCode', '')

