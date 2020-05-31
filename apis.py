from typing import Generator, Optional, Dict, Union, Iterable, Tuple, List, cast, Any
from flask import current_app as app, g
import requests as req
from abc import ABCMeta, abstractmethod
import fhir
import jmespath as path
import json
import umls
from gevent import spawn, iwait, Greenlet
import logging

class Api():
    
    url_config: str

    def __init__(self):
        self.base_url: str = app.config[self.url_config]

    def _get_response(self, url: str, headers: Optional[Dict[str,str]] = None, params: Optional[Dict[str, str]] = None) -> req.Response:
        return req.get(url, headers=headers, params=params)

    def _get(self, url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, str]] = None) -> dict:
        return self._get_response(url, headers=headers, params=params).json()

class UmlsApi(Api):

    url_config = 'UMLS_BASE_URL'

    extraction_functions = {
        'crosswalk': path.compile("result[?ui != 'TCGA' && ui != 'OMFAQ' && ui != 'MPN-SAF'].{code: ui, description:name} | [0]")
    }

    def __init__(self):
        self.auth = umls.Authentication(app.config['UMLS_API_KEY'])
        self.tgt = g.setdefault('tgt', self.auth.gettgt())
        super().__init__()

    def get_crosswalk(self, orig_code: str, codeset: str) -> Tuple[Optional[str], Optional[str]]:
        tik = self.auth.getst(self.tgt)
        params = {"targetSource": "NCI", "ticket": tik}
        url = f"{self.base_url}{codeset}/{orig_code}"
        response = self._get_response(url, params=params)
        if response.status_code != 200:
            return None, None
        result = response.json()
        crosswalk = self.extraction_functions['crosswalk'].search(result)
        return (crosswalk['code'], crosswalk['description'])

    def get_matches(self, conditions_by_code: Dict[str, Dict[str, str]]) -> Iterable[Tuple[str, Optional[Dict[str, str]]]]:
        matches: Dict[Greenlet, str] = {}
        for orig_code, condition in conditions_by_code.items():
            logging.info(f"Getting match for {condition['codeset']} code {orig_code} [{condition['description']}] ")
            matches[spawn(self.get_crosswalk, orig_code, condition['codeset'])] = orig_code
        for match in iwait(matches):
            orig_code = matches[match]
            ncit_code, ncit_desc = cast(Tuple[Optional[str], Optional[str]], match.value)
            if ncit_code and ncit_desc:
                logging.info(f"Match for {orig_code} is {ncit_code}")
                yield orig_code, {'match': ncit_code, 'description': ncit_desc}
            else:
                logging.info(f"No match for {orig_code}")
                yield orig_code, None

class NciApi(Api):
    
    url_config = 'TRIALS_URL'

    def __init__(self):
        self.age: int
        self.gender: str

    def get_trials(self, age: int, gender: str, ncit_codes: List[str]) -> Iterable[Dict[str,Any]]:
        pass


class PatientApi(Api):

    def __init__(self, id: str, token: str):
        self.id: str = id
        self.token: str = token
        super().__init__()

    def get(self, url: str, params: Optional[Dict[str,str]] = None) -> dict:
        headers = {"Authorization": f"Bearer {self.token}"}
        return self._get(url, headers, params)

class FhirApi(PatientApi):

    extraction_functions: Dict[str, path.parser.ParsedResult] = {
        'resources': path.compile('entry[*].resource'),
        'next': path.compile("link[?relation=='next'].url | [0]")
    }

    def get_fhir_bundle(self, endpoint: str, params=None, count=100) -> Iterable[Dict[str, Union[str, list, dict]]]:
        url: Optional[str] = f"{self.base_url}{endpoint}?patient={self.id}&_count={count}"
        while url is not None:
            bundle = self.get(url, params)
            for resource in self.extraction_functions['resources'].search(bundle):
                yield resource
            url = self.extraction_functions['next'].search(bundle)

    def get_demographics(self) -> fhir.Demographics:
        url = f"{self.base_url}Patient/{self.id}"
        return fhir.Demographics(self.get(url))

class VaApi(FhirApi):

    url_config = "VA_API_HEALTH_BASE_URL"

    def get_observations(self) -> Iterable[fhir.Observation]:
        for resource in self.get_fhir_bundle("Observation"):
            yield fhir.Observation(resource)

    def get_conditions(self) -> Iterable[fhir.Condition]:
        for resource in self.get_fhir_bundle("Condition"):
            yield fhir.Condition(resource)

class CmsApi(FhirApi):

    url_config = "CMS_API_BASE_URL"
    
    def get_explanations_of_benefit(self) -> Iterable[fhir.ExplanationOfBenefit]:
        for resource in self.get_fhir_bundle('ExplanationOfBenefit', count=50):
            yield fhir.ExplanationOfBenefit(resource)




