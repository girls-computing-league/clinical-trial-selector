from pathlib import Path
import json
import requests as req
import logging

BASE_URL = "https://dev-api.vets.gov/services/argonaut/v0/"
DEMOGRAPHICS_URL = BASE_URL + "Patient/"
CONDITIONS_URL = BASE_URL + "Condition?_count=50&patient="
DISEASES_URL = "https://clinicaltrialsapi.cancer.gov/v1/diseases"
TRIALS_URL = "https://clinicaltrialsapi.cancer.gov/v1/clinical-trials"

def rchop(thestring, ending):
  if thestring.endswith(ending):
    return thestring[:-len(ending)]
  return thestring

def filepaths_gen(direct="va"):
    acc_dir = Path("./accesscodes/" + direct)
    return(acc_dir.glob("*.json"))

def load_demographics(mrn, token):
    url = DEMOGRAPHICS_URL + mrn
    api_res = get_api(token, url)
    logging.debug("Patient JSON: " + json.dumps(api_res))
    return api_res["gender"], api_res["birthDate"], api_res["name"][0]["text"]

def load_patients(direct="va"):
    patients = {}
    for file in filepaths_gen(direct):
        patient = load_patient(file)
        patients[file.stem] = patient
    return(patients)

def get_patient():
    return

def get_api(token, url, params={}):
    headers = {"Authorization": "Bearer {}".format(token)}
    res = req.get(url, headers=headers, params=params)
    return res.json()

def load_patient(file):
    f = file.open()
    code = json.load(f)
    f.close()
    mrn = code["patient"]
    token = code["access_code"]
    return({"mrn": mrn, "token": token})

def conditions_list(patients, index):
    pat = list(patients.values())[index]
    token = pat["token"]
    mrn = pat["mrn"]
    return load_conditions(mrn, token)

def load_conditions(mrn, token):
    more_pages = True
    url = CONDITIONS_URL+mrn
    conditions = []
    codes_snomed = []
    while more_pages:
        api_res = get_api(token, url)
        next_url = url
        for condition in api_res["entry"]:
            cond_str = rchop(condition["resource"]["code"]["text"], " (disorder)")
            if not (cond_str in conditions):
                conditions.append(cond_str)
            cond_snomed = condition["resource"]["code"]["coding"][0]["code"]
            if not (cond_snomed in codes_snomed):
                codes_snomed.append(cond_snomed)
        for link in api_res["link"]:
            if link["relation"] == "self":
                self_url = link["url"]
            if link["relation"] == "next":
                next_url = link["url"]
            if link["relation"] == "last":
                last_url = link["url"]
        url = next_url
        more_pages = not (self_url == last_url)
        return conditions, codes_snomed

def find_codes(disease):
    res = req.get(DISEASES_URL, params={"name": disease})
    codes_api = res.json()
    codes = []
    names = []
    for term in codes_api["terms"]:
        for code in term["codes"]:
            codes.append(code)
        names.append(term["name"])
    return codes, names

def find_trials(ncit_codes, gender="unknown", age=0):
    trials = []
    for ncit_dict in ncit_codes:
        ncit = ncit_dict["ncit"]
        params = {"diseases.nci_thesaurus_concept_id": ncit}
        if (gender != "unknown"):
            params["eligibility.structured.gender"] = gender
        if (age != 0):
            params["eligibility.structured.max_age_in_years_gte"] = age
            params["eligibility.structured.min_age_in_years_lte"] = age
        res = req.get(TRIALS_URL, params=params)
        trialset = {"code_ncit": ncit, "trialset": res.json()}

        trials.append(trialset)
    return trials

def find_all_codes(disease_list):
    codes = []
    names = []
    for disease in disease_list:
        codelist, nameslist = find_codes(disease)
        codes += codelist
        names += nameslist
    return codes, names
