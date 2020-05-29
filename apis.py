from typing import Generator, Optional, Dict, Union, Iterable
from flask import current_app as app
import requests as req
from abc import ABCMeta, abstractmethod
import fhir
import jmespath as path
import json

class Api():
    
    url_config: str

    def __init__(self, id: str, token: str):
        self.id: str = id
        self.token: str = token
        self.base_url: str = app.config[self.url_config]

    def get(self, url, params=None) -> dict:
        headers = {"Authorization": f"Bearer {self.token}"}
        res = req.get(url, headers=headers, params=params)
        return res.json()

class FhirApi(Api):

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
    
    def get_explanations_of_benefits(self) -> Iterable[fhir.ExplanationOfBenefits]:
        for resource in self.get_fhir_bundle('ExplanationOfBenefit', count=50):
            yield fhir.ExplanationOfBenefits(resource)




