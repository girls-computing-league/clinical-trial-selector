import patient as pt
import logging
import sys
import umls
import requests as req
from typing import Dict, List, Optional, Union, Iterable, Match, Set, Callable, Type, cast, Tuple
from abc import ABCMeta, abstractmethod
from mypy_extensions import TypedDict 
from datetime import date
from distances import distance
from zipcode import Zipcode
from flask import current_app as app
from apis import VaApi, CmsApi, FhirApi, UmlsApi, NciApi
from fhir import Observation
from labtests import labs, LabTest
from datetime import datetime
import json
import re
import time

class Patient(metaclass=ABCMeta):

    api_factory: Type[FhirApi]

    def __init__(self, mrn: str, token: str):
        #logging.geaLogger().setLevel(logging.DEBUG)
        self.mrn = mrn 
        self.token = token
        self.auth = umls.Authentication(app.config["UMLS_API_KEY"])
        self.tgt = self.auth.gettgt()
        self.results: List[TestResult] = []
        self.latest_results: Dict[str, TestResult] = {}
        self.api = self.api_factory(self.mrn, self.token)
        self.umls = UmlsApi()
        self.nci = NciApi()
        self.conditions_by_code: Dict[str, Dict[str, str]] = {}
        self.no_matches: set = set()
        self.code_matches: Dict[str, Dict[str, str]] = {}
        self.trials_by_id: Dict[str, Trial] = {}
        self.trial_ids_by_ncit: Dict[str, List[str]] = {}
        # The following collections are to be deprecated:
        self.conditions: List[str]
        self.codes_ncit: List[Dict[str,str]] = []
        self.matches: List[Dict[str,str]] = []
        self.codes_without_matches: List[Dict[str, str]] = []
        self.trials: List[Trial] = []

        self.after_init()

    @abstractmethod
    def after_init(self) -> None:
        pass

    def load_demographics(self):
        dem = self.api.get_demographics()
        self.name = dem.fullname
        self.gender = dem.gender
        self.birthdate = dem.birth_date
        self.zipcode = dem.zipcode
        self.PatientJSON = dem.JSON
        logging.debug(f"Patient JSON: {self.PatientJSON}")
        logging.debug("Patient gender: {}, birthdate: {}".format(self.gender, self.birthdate))
        today = date.today()
        born = date.fromisoformat(self.birthdate)
        self.age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    @abstractmethod
    def load_conditions(self) -> None:
        pass

    def load_codes(self):
        logging.info("loading Codes")

        for orig_code, match in self.umls.get_matches(self.conditions_by_code):
            if match:
                self.code_matches[orig_code] = match
            else:
                self.no_matches.add(orig_code)

        logging.info("Codes loaded - new approach")

        # Deprecate the following collections:
        self.codes_ncit = [{'ncit': match['match'], 'ncit_desc': match['description']} for match in self.code_matches.values()]
        self.matches = [{'orig_desc': self.conditions_by_code[orig_code]['description'], \
                        'orig_code': orig_code, \
                        'codeset': self.conditions_by_code[orig_code]['codeset'], \
                        'new_code': match['match'], \
                        'new_desc': match['description']} \
                            for orig_code, match in self.code_matches.items()]
        self.codes_without_matches = [{'orig_code': no_match, \
                                    'orig_desc': self.conditions_by_code[no_match]['description'], \
                                    'codeset': self.conditions_by_code[no_match]['codeset']} \
                                        for no_match in self.no_matches]

    def find_trials(self):
        logging.info("Searching for trials...")
        ncit_codes = {match['match'] for match in self.code_matches.values()}
        for ncit_code in ncit_codes:
            self.trial_ids_by_ncit[ncit_code] = []
        for trial_json in self.nci.get_trials(self.age, self.gender, ncit_codes):
            diseases = trial_json['ncit_codes']
            trial = Trial(trial_json, list(diseases)[0] if len(diseases) > 0 else '')
            self.trials_by_id[trial.id] = trial
            for ncit_code in trial_json['ncit_codes']:
                self.trial_ids_by_ncit[ncit_code].append(trial.id)
        logging.info("Completed trials (new method)")

        # Deprecate the following collections:
        self.trials = list(self.trials_by_id.values())

        # self.trials: list = []
        # trials_json = pt.find_trials(self.codes_ncit, gender=self.gender, age=self.age)
        # for trialset in trials_json:
        #     code_ncit = trialset["code_ncit"]
        #     logging.debug("Trials for NCIT code {}:".format(code_ncit))
        #     for trial_json in trialset["trialset"]["trials"]:
        #         trial = Trial(trial_json, code_ncit)
        #         logging.debug("{} - {}".format(trial.id, trial.title))
        #         self.trials.append(trial)
        # logging.info("Trials found")

        return

    def load_all(self):
        self.load_conditions()
        self.load_codes()
        self.find_trials()
        return

class VAPatient(Patient):

    api_factory = VaApi

    def after_init(self):
        self.va_api: VaApi = cast(VaApi, self.api)
        # Deprecate the following collections:
        self.codes_snomed: List[str]

    def load_conditions(self):
        logging.info("Loading conditions")
        self.conditions_by_code = {condition.code: 
                                    {'codeset': condition.codeset, 'description': condition.description} 
                                        for condition in self.va_api.get_conditions()}

        # Deprecate the following collections:
        self.conditions = [cond['description'] for cond in self.conditions_by_code.values()]
        self.codes_snomed = list(self.conditions_by_code.keys())
        logging.info("Conditions loaded")

    def load_test_results(self) -> None:
        self.results = []
        for obs in self.va_api.get_observations():
            app.logger.debug(f"LOINC CODE = {obs.loinc}")
            result = TestResult.from_observation(obs)
            if result is not None:
                app.logger.debug(f"Result added: {result.test_name} {result.value} {result.unit} on {result.datetime}")
                self.results.append(result)
                # Determine if result is the latest
                existing_result = self.latest_results.get(result.test_name)
                if existing_result is None or existing_result.datetime < result.datetime:
                    self.latest_results[result.test_name] = result

class CMSPatient(Patient):

    def after_init(self):
        self.cms_api: CmsApi = cast(CmsApi, self.api)

    api_factory = CmsApi

    def load_conditions(self):
        for eob in self.cms_api.get_explanations_of_benefit():
            if eob.diagnoses:
                for diagnosis in eob.diagnoses:
                    code = diagnosis['code']
                    self.conditions_by_code[code if len(code)<4 else f"{code[0:3]}.{code[3:]}"] = {'codeset': diagnosis['codeset'], 'description': diagnosis['description']}

        # Deprecate the following collections:
        logging.info("CMS Conditions loaded")
        self.codes_icd9 = list(self.conditions_by_code.keys())
        self.conditions = [condition['description'] for condition in self.conditions_by_code.values()]
        logging.info("CMS condition collections computed")

class Criterion(TypedDict): 
    inclusion_indicator: bool
    description: str

class Trial:
    def __init__(self, trial_json, code_ncit):
        self.trial_json = trial_json
        self.code_ncit = code_ncit
        self.id = trial_json['nci_id']
        self.title = trial_json['brief_title']
        self.official = trial_json['official_title']
        self.summary = trial_json['brief_summary']
        self.description = trial_json['detail_description']
        self.eligibility: List[Criterion] = trial_json['eligibility']['unstructured']
        self.inclusions: List[str] = [criterion['description'] for criterion in self.eligibility if criterion['inclusion_indicator']]
        self.exclusions: List[str] = [criterion['description'] for criterion in self.eligibility if not criterion['inclusion_indicator']]
        self.measures = trial_json['outcome_measures']
        self.pi = trial_json['principal_investigator']
        self.sites = trial_json['sites']
        self.population = trial_json['study_population_description']
        self.diseases = trial_json['diseases']
        self.filter_condition: list = []

    def determine_filters(self) -> None:
        s: Set[str] = set()
        for text in self.inclusions:
            alias_match = labs.alias_regex.findall(text)
            if alias_match:
                criteria_match = labs.criteria_regex.findall(text)
                if criteria_match:
                    for group in criteria_match:
                        if labs.by_alias[group[1].lower()].name == "platelets":
                            s.add(group[4])
        for unit in s:
            app.logger.debug(f"leukocytes unit: {unit}")
                    
class CombinedPatient:

    patient_type: Dict[str, Type[Patient]] = {'va': VAPatient, 'cms': CMSPatient}
    
    def __init__(self):
        self.loaded = False
        self.clear_collections()
        self.numTrials = 0
        self.num_conditions_with_trials = 0
        self.filtered = False
        self.from_source: Dict[str, Patient] = {}

    def has_patients(self) -> bool:
        return len(self.from_source) > 0

    def va_patient(self) -> Optional[VAPatient]:
        patient = self.from_source.get('va', None)
        return patient if isinstance(patient,VAPatient) else None

    def login_patient(self, source: str, mrn: str, token: str):
        patient = self.patient_type[source](mrn, token)
        patient.load_demographics()
        self.from_source[source] = patient
        self.loaded = False

    def clear_collections(self):
        self.trials: List[Trial] = []
        self.ncit_codes: list = []
        self.trials_by_ncit: list = []
        self.ncit_without_trials: list = []
        self.results: List[TestResult] = []
        self.latest_results: Dict[str, TestResult] = {}
        self.conditions_by_code: Dict[str, Dict[str, str]] = {}
        self.no_matches: set = set()
        self.code_matches: Dict[str, Dict[str, str]] = {}
        # Deprecate the following collections:
        self.matches: list = []
        self.codes_without_matches: list = []

    def calculate_distances(self):
        db = Zipcode()
        patzip = self.from_source['va'].zipcode
        pat_latlong = db.zip2geo(patzip)

        for trial in self.trials:
            for site in trial.sites:
                coordinates = site.get("org_coordinates", 0)
                if coordinates == 0:
                    site_latlong = db.zip2geo(site["org_postal_code"][:5])
                else:
                    site_latlong = (coordinates["lat"], coordinates["lon"])
                if (site_latlong is None) or (pat_latlong is None):
                    return
                site["distance"] = distance(pat_latlong, site_latlong)

    def load_data(self):
        self.clear_collections() 
        for source, patient in self.from_source.items():
            self.append_patient_data(patient)
            if source=='va':
                self.calculate_distances()
                self.results = patient.results
        for code in self.ncit_codes:
            trials = []
            for trial in self.trials:
                if trial.code_ncit == code["ncit"]:
                    trials.append(trial)
            if trials:
                self.trials_by_ncit.append({"ncit": code, "trials": trials})
            else:
                self.ncit_without_trials.append(code)
        self.loaded = True
        self.numTrials = len(self.trials)
        self.num_conditions_with_trials = len(self.trials_by_ncit)

    def load_test_results(self) -> None:
        va_patient = self.va_patient()
        if va_patient is None:
            return
        va_patient.load_test_results()
        self.results = va_patient.results
        self.latest_results = va_patient.latest_results

    def append_patient_data(self,patient):
        patient.load_all()
        for trial in patient.trials:
            if not (trial in self.trials):
                self.trials.append(trial)
        for code in patient.codes_ncit:
            if not (code in self.ncit_codes):
                self.ncit_codes.append(code)

        self.conditions_by_code.update(patient.conditions_by_code)
        self.code_matches.update(patient.code_matches)
        self.no_matches.update(patient.no_matches)

        # Deprecate the following collections
        self.matches += patient.matches
        self.codes_without_matches += patient.codes_without_matches

class TestResult:

    def __init__(self, test_name: str, datetime: datetime, value: float, unit: str):
        self.test_name = test_name
        self.datetime = datetime
        self.value = value
        self.unit = unit

    @classmethod
    def from_observation(cls, obs: Observation) -> Optional['TestResult']:
        # Returns None if observation is not the result of a test we are tracking
        test: Optional[LabTest] = labs.by_loinc.get(obs.loinc)
        if test is not None and obs.datetime is not None and obs.value is not None and obs.unit is not None:
            return cls(test.name, obs.datetime, obs.value, obs.unit)
        else:
            return None

