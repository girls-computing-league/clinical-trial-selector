import patient as pt
import importlib
importlib.reload(pt)
import logging
import sys
import umls
import requests as req
from datetime import date

import json

class Patient:
    def __init__(self, sub, pat_token):
        #logging.getLogger().setLevel(logging.DEBUG)
        self.sub = sub
        self.mrn = pat_token["mrn"]
        self.token = pat_token["token"]
        self.auth = umls.Authentication("***REMOVED***")
        self.tgt = self.auth.gettgt()

    def load_demographics(self):
        self.gender, self.birthdate, self.name, self.PatientJSON = pt.load_demographics(self.mrn, self.token)
        logging.info("Patient gender: {}, birthdate: {}".format(self.gender, self.birthdate))

    def calculate_age(self):
        today = date.today()
        born = date.fromisoformat(self.birthdate)
        self.age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def load_conditions(self):
        self.conditions,self.codes_snomed = pt.load_conditions(self.mrn, self.token)

    def load_codes(self):
        # self.codes, self.names = pt.find_all_codes(self.conditions)
        self.codes_ncit = []
        self.matches = []
        self.codes_without_matches = []
        for code_snomed in self.codes_snomed:
            code_ncit = self.snomed2ncit(code_snomed)
            orig_desc = self.conditions[self.codes_snomed.index(code_snomed)]
            if (code_ncit["ncit"] != "999999"):
                self.codes_ncit.append(code_ncit)
                self.matches.append({"orig_desc":orig_desc, "orig_code":code_snomed, "codeset":"SNOMED", "new_code":code_ncit["ncit"], "new_desc":code_ncit["ncit_desc"]})
            else:
                self.codes_without_matches.append({"orig_desc":orig_desc, "orig_code":code_snomed, "codeset":"SNOMED"})

    def find_trials(self):
        logging.info("Searching for trials...")
        self.trials = []
        #trials_json = pt.find_trials(self.codes)
        trials_json = pt.find_trials(self.codes_ncit, gender=self.gender, age=self.age)
        for trialset in trials_json:
            code_ncit = trialset["code_ncit"]
            logging.info("Trials for NCIT code {}:".format(code_ncit))
            for trial_json in trialset["trialset"]["trials"]:
                trial = Trial(trial_json, code_ncit)
                logging.info("{} - {}".format(trial.id, trial.title))
                self.trials.append(trial)
        return

    def load_all(self):
        self.load_demographics()
        self.calculate_age()
        self.load_conditions()
        self.load_codes()
        self.find_trials()
        return

    def print_trials(self):
        space = "      "
        for trial in self.trials: 
            print(trial.id)
            print(space + trial.title)
            print(space + trial.summary)
            print()
        return

    def code2ncit(self, code_orig, code_list, codeset):
        no_match = {"ncit": "999999", "ncit_desc": "No code match"}
        condition = self.conditions[code_list.index(code_orig)]
        tik = self.auth.getst(self.tgt)
        params = {"targetSource":"NCI","ticket":tik}
        res = req.get("https://uts-ws.nlm.nih.gov/rest/crosswalk/current/source/{}/".format(codeset)+code_orig,params = params)
        if (res.status_code != 200):
            logging.info("{} CODE {} ({}) --> NO MATCH ({})".format(codeset, code_orig, condition, res.status_code))
            return no_match
        for result in res.json()["result"]:
            if not (result["ui"] in ["TCGA", "OMFAQ", "MPN-SAF"]): 
                name_ncit = result["name"]
                code_ncit = result["ui"]
                logging.info("{} CODE {} ({})---> NCIT CODE {} ({})".format(codeset, code_orig, condition, code_ncit, name_ncit))
                logging.debug("{} CODE {} JSON: {}".format(codeset, code_orig, res.json()))
                return {"ncit": code_ncit, "ncit_desc": name_ncit}
        return no_match
    
    def snomed2ncit(self, code_snomed):
        return self.code2ncit(code_snomed, self.codes_snomed, "SNOMEDCT_US")
    
class CMSPatient(Patient):

    def load_conditions(self):
        self.codes_icd9 = []
        url = "https://sandbox.bluebutton.cms.gov/v1/fhir/ExplanationOfBenefit"
        params = {"patient": self.mrn, "_count":"50"}
        headers = {"Authorization": "Bearer {}".format(self.token)}
        res = req.get(url, params=params, headers=headers)
        fhir = res.json()
        logging.debug("CONDITIONS JSON: {}".format(json.dumps(fhir)))
        codes = []
        names = []
        for entry in fhir["entry"]:
            diags = entry["resource"]["diagnosis"]
            for diag in diags:
                coding = diag["diagnosisCodeableConcept"]["coding"][0]
                code = coding["code"]
                if len(code) > 3:
                    code = code[0:3] + "." + code[3:]
                if code != "999.9999" and not (code in codes):
                    codes.append(code)
                    names.append(coding["display"])
        self.codes_icd9 = codes
        self.conditions = names
    
    def load_demographics(self):
        url = "https://sandbox.bluebutton.cms.gov/v1/fhir/Patient/" + self.mrn
        headers = {"Authorization": "Bearer {}".format(self.token)}
        res = req.get(url, headers=headers)
        fhir = res.json()
        self.gender = fhir["gender"]
        self.birthdate = fhir["birthDate"]
        name = fhir["name"][0]
        self.name = "{} {}".format(name["given"][0], name["family"])
        self.PatientJSON = res.text
        logging.info("FHIR: {}".format(self.PatientJSON))
        logging.info("Patient gender: {}, birthdate: {}".format(self.gender, self.birthdate))

    def load_codes(self):
        self.codes_ncit = []
        self.matches = []
        self.codes_without_matches = []
        for code_icd9 in self.codes_icd9:
            code_ncit = self.icd2ncit(code_icd9)
            orig_desc = self.conditions[self.codes_icd9.index(code_icd9)]
            if (code_ncit["ncit"] != "999999"):
                self.codes_ncit.append(code_ncit)
                self.matches.append({"orig_desc":orig_desc, "orig_code":code_icd9, "codeset":"ICD-9", "new_code":code_ncit["ncit"], "new_desc":code_ncit["ncit_desc"]})
            else:
                self.codes_without_matches.append({"orig_desc":orig_desc, "orig_code":code_icd9, "codeset":"ICD-9"})

    def icd2ncit(self, code_icd9):
        return self.code2ncit(code_icd9, self.codes_icd9, "ICD9CM")


class PatientLoader:
    def __init__(self):
        self.patients = []

        # Load VA Patients
        va_tokens = pt.load_patients("va")
        for pat_token in va_tokens:
            self.patients.append(Patient(pat_token, va_tokens[pat_token]))

        # Load CMS Patients
        cms_tokens = pt.load_patients("cms")
        for pat_token in cms_tokens:
            self.patients.append(CMSPatient(pat_token, cms_tokens[pat_token]))

        self.pat_tokens = {va_tokens, cms_tokens}

    def load_all_patients(self):
        for patient in self.patients:
            patient.load_all()

class Trial:
    def __init__(self, trial_json, code_ncit):
        self.trial_json = trial_json
        self.code_ncit = code_ncit
        self.id = trial_json['nci_id']
        self.title = trial_json['brief_title']
        self.official = trial_json['official_title']
        self.summary = trial_json['brief_summary']
        self.description = trial_json['detail_description']
        self.measures = trial_json['outcome_measures']
        self.pi = trial_json['principal_investigator']
        self.sites = trial_json['sites']
        self.population = trial_json['study_population_description']
        self.diseases = trial_json['diseases']

class CombinedPatient:
    def __init__(self):
        self.VAPatient = None
        self.CMSPatient = None
        self.loaded = False
        self.clear_collections()
        self.numTrials = 0
        self.num_conditions_with_trials = 0
    
    def clear_collections(self):
        self.trials = []
        self.ncit_codes = []
        self.trials_by_ncit = []
        self.ncit_without_trials = []
        self.matches = []
        self.codes_without_matches = []

    def load_data(self):
        self.clear_collections() 
        if self.VAPatient is not None:
            self.append_patient_data(self.VAPatient)
        if self.CMSPatient is not None:
            self.append_patient_data(self.CMSPatient)
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

    def append_patient_data(self,patient):
        patient.load_all()
        for trial in patient.trials:
            if not (trial in self.trials):
                self.trials.append(trial)
        for code in patient.codes_ncit:
            if not (code in self.ncit_codes):
                self.ncit_codes.append(code)
        self.matches += patient.matches
        self.codes_without_matches += patient.codes_without_matches