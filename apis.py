from typing import Generator, Optional, Dict, Union, Iterable
from flask import current_app as app
import requests as req
from abc import ABCMeta, abstractmethod
import fhir

class Api(metaclass = ABCMeta):
    
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

    def get_fhir_bundle(self, endpoint: str, params=None, count=100) -> Iterable[Dict[str, Union[str, list, dict]]]:
        url: Optional[str] = f"{self.base_url}{endpoint}?patient={self.id}&_count={count}"
        while url is not None:
            bundle = self.get(url, params)
            for entry in bundle.get('entry', []):
                resource = entry.get('resource')
                if resource is not None:
                    yield resource
            url = None
            for link in bundle.get('link', []):
                if link.get('relation') == 'next':
                    url = link.get('url')
                    break

class VaApi(FhirApi):

    url_config = "VA_API_HEALTH_BASE_URL"

    def get_lab_results(self) -> Iterable[fhir.Observation]:
        for resource in self.get_fhir_bundle("Observation"):
            yield fhir.Observation(resource)

class CmsApi(Api):

    pass



