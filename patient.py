from pathlib import Path
import json
import requests as req

BASE_URL = "https://dev-api.vets.gov/services/argonaut/v0/"
DEMOGRAPHICS_URL = BASE_URL + "Patient/"
CONDITIONS_URL = BASE_URL + "Condition?patient="


def filepaths_gen():
    acc_dir = Path("./accesscodes")
    return(acc_dir.glob("*.json"))

def load_patients():
    patients = {}
    for file in filepaths_gen():
        patient = load_patient(file)
        patients[file.stem] = patient
    return(patients)

def get_api(code, url):
    token = code["access_token"]
    mrn = code["patient"]
    headers = {"Authorization": "Bearer {}".format(token)}
    res = req.get(url+mrn, headers=headers)
    return res.json()

def load_patient(file):
    f = file.open()
    code = json.load(f)
    f.close()
    patient = get_api(code, DEMOGRAPHICS_URL)
    conditions = get_api(code, CONDITIONS_URL)
    return({"Patient": patient, "Conditions": conditions})

