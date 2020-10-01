from typing import Tuple, Optional, Dict, Any, Union, List
from dateutil.parser import parse
from datetime import datetime
import json
import jmespath as path
from abc import ABCMeta, abstractmethod
import logging

class FHIRResource(metaclass=ABCMeta):

    expressions: Dict[str, str]

    compiled_expressions: Dict[str, path.parser.ParsedResult] 

    codeset_from_system: Dict[str, str] = {
        'http://snomed.info/sct': 'SNOMEDCT_US',
        'http://hl7.org/fhir/sid/icd-9-cm': 'ICD9CM',
        'http://hl7.org/fhir/sid/icd-10': 'ICD10CM'
    }
    
    @classmethod
    def compile_expressions(cls, expressions: Dict[str, str]) -> Dict[str, path.parser.ParsedResult]:
        return {key:path.compile(value) for key,value in expressions.items()}

    def __init__(self, resource: Dict[str, Any]):
        self._resource = resource
        self.JSON = json.dumps(self._resource, indent=2)
        self.after_init()

    @abstractmethod
    def after_init(self) -> None:
        pass

    def _extract(self, property: str):
        return self.compiled_expressions[property].search(self._resource)
        
class Observation(FHIRResource):

    expressions = {
        'loinc': "code.coding[?system=='http://loinc.org'].code | [0]",
        'value': 'valueQuantity.value',
        'unit': 'valueQuantity.code',
        'datetime': 'effectiveDateTime'
    }
 
    compiled_expressions = FHIRResource.compile_expressions(expressions)

    def after_init(self):
        self.loinc: str = self._extract('loinc')
        value = self._extract('value')
        self.value: float = float(value) if value else None
        self.unit: str = self._extract('unit')
        datetime: str = self._extract('datetime')
        self.datetime = parse(datetime) if datetime else None

class Demographics(FHIRResource):

    expressions  = {
        'fullname': 'name[0] | text || join(``, [given[0], `" "`, family])',
        'gender': 'gender',
        'birth_date': 'birthDate',
        'zipcode': 'address[0].postalCode'}
 
    compiled_expressions = FHIRResource.compile_expressions(expressions)

    def after_init(self):
        self.fullname: str = self._extract('fullname')
        self.gender: str = self._extract('gender')
        self.birth_date: str = self._extract('birth_date')
        self.zipcode: str = self._extract('zipcode')

class Condition(FHIRResource):

    expressions = {
        'description': 'code.text',
        'code': 'code.coding[0].code',
        'system': 'code.coding[0].system'
    }

    compiled_expressions = FHIRResource.compile_expressions(expressions)

    def after_init(self):
        self.description: str = self._extract('description')
        self.code: str = self._extract('code')
        self.system: str = self._extract('system')
        self.codeset: str = self.codeset_from_system[self.system]

class Procedure(FHIRResource):

    expressions = {
        'description': 'code.coding[0].display',
        'code': 'code.coding[0].code', 
        'system': 'code.coding[0].system', 
    }

    compiled_expressions = FHIRResource.compile_expressions(expressions)

    def after_init(self):
        self.description: str = self._extract('description')
        self.code: str = self._extract('code')
        self.system: str = self._extract('system')

class ExplanationOfBenefit(FHIRResource):

    expressions = {
        'diagnoses': "diagnosis[?diagnosisCodeableConcept.coding[0].code != '9999999'].diagnosisCodeableConcept.coding[0].{code:code, system: system, description:display}"
    }

    compiled_expressions = FHIRResource.compile_expressions(expressions)

    def after_init(self):
        self.diagnoses: List[Dict[str, str]] = self._extract('diagnoses')
        if self.diagnoses:
            logging.warn(f"Processing {len(self.diagnoses)} diagnoses")
            for diagnosis in self.diagnoses:
                diagnosis['codeset'] = self.codeset_from_system[diagnosis['system']] 