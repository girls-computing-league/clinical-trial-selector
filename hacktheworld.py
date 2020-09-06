import patient as pt
import logging
import sys
import umls
import requests as req
from typing import Dict, List, Optional, Union, Iterable, Match, Set, Callable, Type, cast, Tuple, Any
from abc import ABCMeta, abstractmethod
from mypy_extensions import TypedDict
from datetime import date
from distances import distance
from zipcode import Zipcode
from flask import current_app as app
from apis import VaApi, CmsApi, FhirApi, UmlsApi, NciApi, FbApi
from filter import FacebookFilter
from fhir import Observation
from labtests import labs, LabTest
from datetime import datetime
from gevent import spawn, iwait, pool
import os
import subprocess
import json

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
        self.added_codes: List[Tuple[str, str]] = []
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
        logging.info(f"Patient JSON: {self.PatientJSON}")
        logging.info("Patient gender: {}, birthdate: {}".format(self.gender, self.birthdate))
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
        for code in self.added_codes:
            found = False
            for r_code in self.codes_ncit:
                if code[0] == r_code['ncit']:
                    found = True
                    break
            if not found:
                self.codes_ncit.append({'ncit': code[0], 'ncit_desc': code[1]})
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
        ncit_codes = {match['match'] for match in self.code_matches.values()}
        for code in self.added_codes:
            ncit_codes.add(code)
        logging.info(self.added_codes)
        logging.info(ncit_codes)
        if len(ncit_codes) == 0:
            logging.info('No ncit conditions to search for')
            return
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

        code_results = {}
        gpool = pool.Pool(10)
        for ncit_code in self.codes_ncit:
            gpool.wait_available()
            code_results[gpool.spawn(pt.find_new_trails, ncit_code, app.config['ADDITIONAL_TRIALS_URL'])] = ncit_code

        for code_result in iwait(code_results):
            ncit_code = code_results[code_result]
            logging.info(f"Received trials for code {code_results[code_result]}")
            logging.debug(ncit_code)
            new_trails_json = code_result.value
            nt_max_age=self.age+1
            nt_min_age=self.age-1
            nt_gender="Unknown"
            for trial_set in new_trails_json.get('FullStudiesResponse', {}).get('FullStudies', []):
                # Modify this
                if 'Completed' not in trial_set['Study']['ProtocolSection']['StatusModule']['OverallStatus']:
                    if 'Gender' in trial_set['Study']['ProtocolSection']['EligibilityModule'].keys():
                        nt_gender = trial_set['Study']['ProtocolSection']['EligibilityModule']['Gender']
                    if 'MinimumAge' in str(trial_set['Study']['ProtocolSection']['EligibilityModule'].keys()):
                        nt_min_age = trial_set['Study']['ProtocolSection']['EligibilityModule']['MinimumAge']
                        if 'Years' in nt_min_age.split(' ')[1]:
                            nt_min_age = int(nt_min_age.split(' ')[0])
                        elif 'Month' in nt_min_age.split(' ')[1]:
                            nt_min_age = (int(nt_min_age.split(' ')[0]))/12
                        elif 'Week' in nt_min_age.split(' ')[1]:
                            nt_min_age = (int(nt_min_age.split(' ')[0]))/52.143
                        else:
                            nt_min_age = self.age - 1
                    if 'MaximumAge' in str(trial_set['Study']['ProtocolSection']['EligibilityModule'].keys()):
                        nt_max_age = trial_set['Study']['ProtocolSection']['EligibilityModule']['MaximumAge']
                        if 'Years' in nt_max_age.split(' ')[1]:
                            nt_max_age = int(nt_max_age.split(' ')[0])
                        else:
                            nt_max_age = self.age + 1
                    if ((nt_gender in ['All', self.gender]) and (nt_min_age<=self.age and nt_max_age>=self.age)):
                        trial = TrialV2(trial_set['Study']['ProtocolSection'], ncit_code['ncit'])
                        self.trials.append(trial)
        logging.debug(self.conditions)
        logging.debug(self.matches)
        logging.debug(self.codes_ncit)

        return

    def add_code(self, code: str) -> bool:
        translated_code, description = self.umls.get_crosswalk(code, "NCI")
        logging.info("TRANSLATED CODE")
        logging.info(translated_code)
        if translated_code is None:
            return False
        self.added_codes.append((code, description))
        return True

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

class FBPatient(Patient):
    def after_init(self):
        pass

    def load_conditions(self):
        pass

    api_factory = FbApi

    def load_demographics(self):
        dem = self.api.get_demographics()
        self.name = dem.fullname
        self.gender = dem.gender
        self.birthdate = dem.birth_date
        self.zipcode = dem.zipcode
        self.mrn = dem.id
        # self.PatientJSON = dem.JSON
        # logging.debug(f"Patient JSON: {self.PatientJSON}")
        # logging.debug("Patient gender: {}, birthdate: {}".format(self.gender, self.birthdate))
        today = date.today()
        born = date.fromisoformat(self.birthdate)
        self.age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

class Criterion(TypedDict):
    inclusion_indicator: bool
    description: str

class Trial:
    def __init__(self, trial_json, code_ncit):
        # self.trial_json = trial_json
        self.code_ncit = code_ncit
        self.id = trial_json['nci_id']
        self.title = trial_json['brief_title']
        self.official = trial_json['official_title']
        self.summary = trial_json['brief_summary']
        self.description = trial_json['detail_description']
        self.eligibility: List[Criterion] = trial_json['eligibility']['unstructured']
        self.inclusions: Union[List[str], None] = [criterion['description'] for criterion in self.eligibility if criterion['inclusion_indicator']]
        self.exclusions: Union[List[str], None] = [criterion['description'] for criterion in self.eligibility if not criterion['inclusion_indicator']]
        self.eligibility_combined = '"\n\t\tInclusion Criteria:\n\n\t\t - ' + "\n\n\t\t - ".join(
            self.inclusions).replace('"', "'") \
                                    + '\n\n\t\tExclusion Criteria:\n\n\t\t - ' + "\n\n\t\t - ".join(
            self.exclusions).replace('"', "'") + '"'
        self.measures = trial_json['outcome_measures']
        self.pi = trial_json['principal_investigator']
        self.sites = trial_json['sites']
        self.locations: list = []
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


class TrialV2(Trial):

    def __init__(self, trial_json, code_ncit): #write the code based on the condition it will attatch to that dropdown
        self.trial_json = trial_json
        self.code_ncit = code_ncit
        self.id = trial_json['IdentificationModule']['NCTId']
        self.title = trial_json['IdentificationModule']['BriefTitle']
        self.official = trial_json['IdentificationModule'].get('OfficialTitle')
        self.summary = trial_json['DescriptionModule'].get('BriefSummary')
        self.description = trial_json['DescriptionModule'].get('DetailedDescription')
        self.eligibility: List[Dict] = [{'description': trial_json['EligibilityModule'].get('EligibilityCriteria'), 'inclusion_indicator': True}]
        self.inclusions: Union[List[str], None] = None
        self.exclusions: Union[List[str], None] = None
        self.eligibility_combined = '"' + self.trial_json['EligibilityModule'].get('EligibilityCriteria').replace('"',"") + '"' \
            if self.trial_json['EligibilityModule'].get('EligibilityCriteria') is not None else ""
        self.measures = [measure for types in ['Primary', 'Secondary', 'Other'] for measure in self.get_measures(types)]
        self.pi = trial_json.get('SponsorCollaboratorsModule', {}).get('ResponsibleParty', {}).get('ResponsiblePartyInvestigatorFullName', 'N/A')
        self.sites: list = []
        self.locations = trial_json.get('ContactsLocationsModule', {}).get('LocationList',{}).get('Location', [])
        self.population = trial_json['EligibilityModule'].get('StudyPopulation')
        self.diseases = []
        self.filter_condition = []

    def get_measures(self, key):
        return [
            {
                'name': measure.get(f'{key}OutcomeMeasure'),
                'description': measure.get(f'{key}OutcomeDescription'),
                'timeframe': measure.get(f'{key}OutcomeTimeFrame')
            }
                for measure in self.trial_json
                    .get('OutcomesModule', {})
                    .get(f'{key}OutcomeList', {})
                    .get(f'{key}Outcome', [])
            ]

class CombinedPatient:

    patient_type: Dict[str, Type[Patient]] = {'va': VAPatient, 'cms': CMSPatient, 'fb': FBPatient}

    def __init__(self):
        self.loaded = False
        self.clear_collections()
        self.numTrials = 0
        self.num_conditions_with_trials = 0
        self.filtered = False
        self.from_source: Dict[str, Patient] = {}

    def add_extra_code(self, code: str) -> bool:
        for source, patient in self.from_source.items():
            if not patient.add_code(code):
                return False
        return True

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
        if self.from_source.get('va'):
            patzip = self.from_source['va'].zipcode[:5]
        elif self.from_source.get('cms'):
            patzip = self.from_source['cms'].zipcode[:5]
        else:
            return
        pat_latlong = db.zip2geo(patzip)
        logging.debug(f"Zipcode {patzip}, pat_latlong: {pat_latlong}")

        logging.debug(f"Checking distances for {len(self.trials)} trials")
        for trial in self.trials:
            if trial.sites is None:
                logging.debug(f"Site list empty for trial {trial.id}")
            else:
                logging.debug(f"Trial {trial.id} has {len(trial.sites)} sites")
                for site in trial.sites:
                    coordinates = site.get("org_coordinates", 0)
                    logging.debug(f"Coordinates: {coordinates}")
                    if coordinates == 0:
                        site_latlong = db.zip2geo(site["org_postal_code"][:5])
                        logging.debug(f"site lat-long (from zip): {site_latlong}")
                    else:
                        site_latlong = (coordinates["lat"], coordinates["lon"])
                        logging.debug(f"site lat-long (from coords): {site_latlong}")
                    if (site_latlong is None) or (pat_latlong is None):
                        logging.warn(f"no distance for site {site['org_name']} at trial={trial.id}")
                    else:
                        site["distance"] = distance(pat_latlong, site_latlong)
                        logging.debug(f"Distance={site['distance']} for Trial={trial.id}")

            if trial.locations is None:
                logging.debug(f"Location list empty for trial {trial.id}")
            else:
                logging.debug(f"Trial {trial.id} has {len(trial.locations)} locations")
                for site in trial.locations:
                    site_latlong = db.zip2geo(site.get("LocationZip", "00000")[:5])
                    logging.debug(f"site lat-long (from zip): {site_latlong}")
                    if (site_latlong is None) or (pat_latlong is None):
                        logging.debug(f"no distance for site {site.get('LocationFacility', 'unknown')} at trial={trial.id}")
                    else:
                        site["distance"] = distance(pat_latlong, site_latlong)
                        logging.debug(f"Distance={site['distance']} for Trial={trial.id}")

    def load_data(self):
        self.clear_collections()
        for source, patient in self.from_source.items():
            self.append_patient_data(patient)
            if source=='va':
                self.results = patient.results
        self.calculate_distances()
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

    def filter_by_criteria(self, form) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        trials_by_ncit = self.trials_by_ncit
        if form.validate_on_submit():
            lab_results = {key: value for (key, value) in form.data.items() if key != 'csrf_token'}
            for lab in self.latest_results:
                if lab not in lab_results:
                    lab_results[lab] = self.latest_results[lab]
        else:
            lab_results = self.latest_results

        filtered_trials_by_ncit = []
        excluded_trials_by_ncit = []
        cfg = FacebookFilter('cfg')

        for condition in trials_by_ncit:
            ncit = condition['ncit']
            trials = condition['trials']
            inc = []
            exc = []
            for trial in trials:
                if cfg.filter_trial(trial, lab_results):
                    inc.append(trial)
                else:
                    exc.append(trial)
            if len(inc) != 0:
                filtered_trials_by_ncit.append({"ncit": ncit, "trials": inc})
            if len(exc) != 0:
                excluded_trials_by_ncit.append({"ncit": ncit, "trials": exc})

        return filtered_trials_by_ncit, excluded_trials_by_ncit


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
