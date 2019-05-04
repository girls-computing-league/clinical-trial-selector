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
#        logging.getLogger().setLevel(logging.DEBUG)
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
        self.trials = []
#        trials_json = pt.find_trials(self.codes)
        trials_json = pt.find_trials(self.codes_ncit)
        for trialset in trials_json:
            for trial_json in trialset["trials"]:
                trial = Trial(trial_json)
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

    def snomed2ncit(self,code_snomed):
        condition = self.conditions[self.codes_snomed.index(code_snomed)]
        tik = self.auth.getst(self.tgt)
        params = {"targetSource":"NCI","ticket":tik}
        res = req.get("https://uts-ws.nlm.nih.gov/rest/crosswalk/current/source/SNOMEDCT_US/"+code_snomed,params = params)
        if (res.status_code != 200):
            logging.info("SNOMED CODE {} ({}) --> NO MATCH".format(code_snomed, condition))
            return "no code match"
        for result in res.json()["result"]:
            if not (result["ui"] in ["TCGA", "OMFAQ"]): 
                name_ncit = result["name"]
                code_ncit = result["ui"]
                logging.info("SNOMED CODE {} ({})---> NCIT CODE {} ({})".format(code_snomed, condition, code_ncit, name_ncit))
                logging.debug("SNOMED CODE {} JSON: {}".format(code_snomed, res.json()))
                return code_ncit
        return "no code match"

class PatientLoader:
    def __init__(self):
        self.patients = []
        self.pat_tokens = pt.load_patients()
        for pat_token in self.pat_tokens:
            self.patients.append(Patient(pat_token, self.pat_tokens[pat_token]))

    def load_all_patients(self):
        for patient in self.patients:
            patient.load_all()
        return

class Trial:
    def __init__(self, trial_json):
        self.trial_json = trial_json
        self.id = trial_json['nci_id']
        self.title = trial_json['brief_title']
        self.summary = trial_json['brief_summary']
        return