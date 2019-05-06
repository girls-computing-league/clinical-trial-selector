import patient as pt
import importlib
importlib.reload(pt)
import logging
import sys
import umls
import requests as req

import json

class Patient:
    def __init__(self, sub, pat_token):
        #logging.getLogger().setLevel(logging.DEBUG)
        self.sub = sub
        self.mrn = pat_token["mrn"]
        self.token = pat_token["token"]
        self.auth = umls.Authentication("***REMOVED***")
        self.tgt = self.auth.gettgt()
        return

    def load_conditions(self):
        self.conditions,self.codes_snomed = pt.load_conditions(self.mrn, self.token)
        return

    def load_codes(self):
        self.codes, self.names = pt.find_all_codes(self.conditions)
        self.codes_ncit = []
        for code_snomed in self.codes_snomed:
            code_ncit = self.snomed2ncit(code_snomed)
            if not (code_ncit == "no code match"):
                self.codes_ncit.append(code_ncit)
        return

    def find_trials(self):
        logging.info("Searching for trials...")
        self.trials = []
        #trials_json = pt.find_trials(self.codes)
        trials_json = pt.find_trials(self.codes_ncit)
        for trialset in trials_json:
            logging.info("Trials for NCIT code {}:".format(trialset["code_ncit"]))
            for trial_json in trialset["trialset"]["trials"]:
                trial = Trial(trial_json)
                logging.info("{} - {}".format(trial.id, trial.title))
                self.trials.append(trial)
        return

    def load_all(self):
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
        condition = self.conditions[code_list.index(code_orig)]
        tik = self.auth.getst(self.tgt)
        params = {"targetSource":"NCI","ticket":tik}
        res = req.get("https://uts-ws.nlm.nih.gov/rest/crosswalk/current/source/{}/".format(codeset)+code_orig,params = params)
        if (res.status_code != 200):
            logging.info("{} CODE {} ({}) --> NO MATCH ({})".format(codeset, code_orig, condition, res.status_code))
            return "no code match"
        for result in res.json()["result"]:
            if not (result["ui"] in ["TCGA", "OMFAQ", "MPN-SAF"]): 
                name_ncit = result["name"]
                code_ncit = result["ui"]
                logging.info("{} CODE {} ({})---> NCIT CODE {} ({})".format(codeset, code_orig, condition, code_ncit, name_ncit))
                logging.debug("{} CODE {} JSON: {}".format(codeset, code_orig, res.json()))
                return code_ncit
        return "no code match"
    
    def snomed2ncit(self, code_snomed):
        return self.code2ncit(code_snomed, self.codes_snomed, "SNOMEDCT_US")
    
    def snomed2ncit_old(self,code_snomed):
        condition = self.conditions[self.codes_snomed.index(code_snomed)]
        tik = self.auth.getst(self.tgt)
        params = {"targetSource":"NCI","ticket":tik}
        res = req.get("https://uts-ws.nlm.nih.gov/rest/crosswalk/current/source/SNOMEDCT_US/"+code_snomed,params = params)
        if (res.status_code != 200):
            logging.info("SNOMED CODE {} ({}) --> NO MATCH".format(code_snomed, condition))
            return "no code match"
        for result in res.json()["result"]:
            if not (result["ui"] in ["TCGA", "OMFAQ", "MPN-SAF"]): 
                name_ncit = result["name"]
                code_ncit = result["ui"]
                logging.info("SNOMED CODE {} ({})---> NCIT CODE {} ({})".format(code_snomed, condition, code_ncit, name_ncit))
                logging.debug("SNOMED CODE {} JSON: {}".format(code_snomed, res.json()))
                return code_ncit
        return "no code match"

class CMSPatient(Patient):

    def load_conditions(self):
        self.codes_icd9 = []
        url = "https://sandbox.bluebutton.cms.gov/v1/fhir/ExplanationOfBenefit"
        params = {"patient": self.mrn, "_count":"50"}
        headers = {"Authorization": "Bearer {}".format(self.token)}
        res = req.get(url, params=params, headers=headers)
        fhir = res.json()
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

    def load_codes(self):
        self.codes_ncit = []
        for code_icd9 in self.codes_icd9:
            code_ncit = self.icd2ncit(code_icd9)
            if not (code_ncit == "no code match"):
                self.codes_ncit.append(code_ncit)

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

        self.pat_tokens = {**va_tokens, **cms_tokens}

    def load_all_patients(self):
        for patient in self.patients:
            patient.load_all()

class Trial:
    def __init__(self, trial_json):
        self.trial_json = trial_json
        self.id = trial_json['nci_id']
        self.title = trial_json['brief_title']
        self.summary = trial_json['brief_summary']