from flask import current_app as app
import requests as req
from abc import ABC, abstractmethod

class Api(ABC):

    def __init__(self, id, token):
        self.id = id
        self.token = token

    def get(self, url, params=None) -> dict:
        headers = {"Authorization": f"Bearer {self.token}"}
        res = req.get(url, headers=headers, params=params)
        return res.json()

class VaApi(Api):

    def __init__(self, id, token):
        
        base_url = app.config["VA_API_HEALTH_BASE_URL"]
        pass

    def get_lab_results(self) -> Iterable[dict]:
        for resource in self._get_fhir_bundle("Observation"):
            yield resource

class CmsApi(Api):

    pass



