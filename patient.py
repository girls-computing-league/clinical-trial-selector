from pathlib import Path
import json
import requests as req
import logging
import re
import boto3
from jsonpath_rw_ext import parse
from typing import Dict, List, Any, Tuple, Union
import concurrent.futures as futures

client = boto3.client(service_name="comprehendmedical")

# BASE_URL = "https://dev-api.vets.gov/services/argonaut/v0/"
BASE_URL = "https://dev-api.va.gov/services/fhir/v0/argonaut/data-query/"
DEMOGRAPHICS_URL = BASE_URL + "Patient/"
CONDITIONS_URL = BASE_URL + "Condition?_count=50&patient="
DISEASES_URL = "https://clinicaltrialsapi.cancer.gov/v1/diseases"
TRIALS_URL = "https://clinicaltrialsapi.cancer.gov/v1/clinical-trials"
OBSERVATION_URL = BASE_URL + 'Observation'


server = '108.31.54.198'
database = 'CTA'
username = 'ctauser'
password = 'sql'
connection_details = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + \
                     username + ';PWD=' + password

LOINC_CODES = {
    '718-7': 'hemoglobin',
    '6690-2': 'leukocytes',
    '32623-1': 'platelets'
}

TABLE_NAME_BY_CELL_TYPE = {
    'hemoglobin': 'Dataset1_Hemoglobin_Trials_First',
    'wbc': 'Dataset1_WBC_Trials_First',
    'platelets': 'Dataset1_Platelets_Trials_First',
}


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
    return api_res["gender"], api_res["birthDate"], api_res["name"][0]["text"], api_res["address"][0]["postalCode"], json.dumps(api_res)

def load_patients(direct="va"):
    patients = {}
    for file in filepaths_gen(direct):
        patient = load_patient(file)
        patients[file.stem] = patient
    return(patients)

def get_patient():
    return

def get_api(token, url, params=None):
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
        logging.debug("Conditions JSON: {}".format(json.dumps(api_res)))
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
        # if (gender != "unknown"):
        #    params["eligibility.structured.gender"] = gender
        # if (age != 0):
        #    params["eligibility.structured.max_age_in_years_gte"] = age
        #    params["eligibility.structured.min_age_in_years_lte"] = age
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


def get_lab_observations_by_patient(patient_id, token):
    # loinc_codes = ','.join(list(LOINC_CODES.keys()))
    current_url = OBSERVATION_URL + f'?patient={patient_id}&_count=40'

    lab_results = {}
    while len(lab_results) != 3 and current_url is not None:
        observations = get_api(token, url=current_url)

        # extract values from observations.
        for entry in observations.get('entry'):
            resource = entry['resource']

            try:
                code = resource['code']['coding'][0]['code']
                value_quantity = resource['valueQuantity']
                value = (str(value_quantity['value']), value_quantity['unit'])
                effective_date_time = resource['effectiveDateTime']
            except KeyError:
                continue

            # Store the latest observation result
            if code in LOINC_CODES and (code not in lab_results or effective_date_time > lab_results[code]['effectiveDateTime']):
                lab_results[code] = {'effectiveDateTime': effective_date_time, 'value': value}

        current_url = None
        for link in observations['link']:
            if link['relation'] == 'next':
                current_url = link['url']

    values_by_cell_type = {LOINC_CODES[key]: val['value'] for key, val in lab_results.items()}
    return values_by_cell_type


def filter_by_inclusion_criteria(trials_by_ncit: List[Dict[str, Any]],
                                 lab_results: Dict[str, Union[str, 'Trial']])\
        -> Tuple[List[Dict[str, Union[str, 'Trial']]], List[Dict[str, Union[str, 'Trial']]]]:
    """
    :param trials_by_ncit: List[dict]
    :param lab_results: dict
    :return: (List[dict], List[dict])
    """
    filtered_trials_by_ncit = []
    excluded_trials_by_ncit = []
    with futures.ThreadPoolExecutor(max_workers=8) as executor:
        tasks = {
            executor.submit(filter_trials_from_description, trial['trials'], lab_results): trial['ncit']
            for trial in trials_by_ncit
        }
        for future in futures.as_completed(tasks):
            ncit_code = tasks[future]
            try:
                filtered_trials, excluded_trails = future.result()
                filtered_trials_by_ncit.append({"ncit": ncit_code, "trials": filtered_trials})
                excluded_trials_by_ncit.append({"ncit": ncit_code, "trials": excluded_trails})
            except Exception as exc:
                print('Failed task: ', exc)
                continue

    return filtered_trials_by_ncit, excluded_trials_by_ncit


def filter_trials_from_description(trials: List['Trial'], lab_results: Dict) -> Tuple[List['Trial'], List['Trial']]:
    """
    :param trials: List[obj(Trail)]
    :param comparision_val: str
    :param cell_type: str
    :return: (List[obj(Trial], List[obj(Trial)])
    """
    filtered_trials = []
    excluded_trials = []
    for trial in trials:
        conditions = find_conditions(trial.trial_json)
        trial.filter_condition = []
        if conditions:
            include_trail = True
            for cell_type, condition in conditions.items():
                lab_value = lab_results.get(cell_type)
                if not lab_value:
                    trial.filter_condition.append((condition, True))
                    continue
                lab_value, converted_condition = convert_expressions(lab_value, condition)
                if eval(lab_value + converted_condition):
                    trial.filter_condition.append((condition, True))
                else:
                    include_trail = False
                    trial.filter_condition.append((condition, False))
            if include_trail:
                filtered_trials.append(trial)
            else:
                excluded_trials.append(trial)
        else:
            trial.filter_condition.append(('No Inclusion Criteria Found', True))
            filtered_trials.append(trial)
    return filtered_trials, excluded_trials


def find_conditions(trial: Dict) -> Dict:
    match_type = 'hemoglobin|platelets|leukocytes'
    cell_types = ['hemoglobin', 'platelets', 'leukocytes']
    parser = parse(f'$.eligibility.unstructured[?inclusion_indicator=true].description')
    unstructured_descriptions = parser.find(trial)
    description = ' '.join([match.value.replace('\r\n', ' ').lower() for match in unstructured_descriptions
                            if any(cell_type in match.value.lower() for cell_type in cell_types)])
    if description:
        pattern = re.compile(f'(\[?({match_type})\]?\s?[\>\=\<]+\s?\d+[\.\,]?\d*\s?\w+\/?\s?\w+(\^\d*)?)')
        matches = pattern.findall(description)
        if matches:
            conditions = {match[1]: str(match[0]) for match in matches}
            return conditions if len(conditions) == 3 else get_mapping_with_aws_comprehend(unstructured_descriptions)
        else:
            entity_mapping = get_mapping_with_aws_comprehend(unstructured_descriptions)
            return entity_mapping
    else:
        return {}


def split_description(description, limit):
    data = []
    while len(description) > limit:
        data.append(description[:limit])
        description = description[limit:]
    data.append(description)
    return data


def get_mapping_with_aws_comprehend(descriptions: List) -> Dict:
    def get_description():
        data = ''
        limit = 19999
        for match in descriptions:
            description = match.value.replace('\r\n', ' ').lower().replace(',', '')
            if len(description) > limit:
                for split in split_description(description, limit):
                    yield split
            elif len(data) + len(description) > limit:
                yield data
                data = description
            else:
                data += description
        yield data

    conditions = {}
    cell_types = ['hemoglobin', 'platelets', 'leukocytes']
    for description in get_description():
        try:
            entities = client.detect_entities(Text=description)['Entities']
            for entity in entities:
                entity_type = entity['Text']
                if any(cell_type == entity_type.lower() for cell_type in cell_types) and entity.get('Attributes'):
                    conditions[entity_type] = entity_type + entity['Attributes'][0]['Text']
        except Exception as exc:
            print(f'Failed to retrieve aws comprehend entities: {str(exc)}')
    return conditions


# TODO conversion
def convert_expressions(lab_value: str, condition: str):
    """

    :param lab_value: 4000 ul
    :param condition:
    :return: value: 4000, condition >= 3000
    """
    # platelets< 100 x 10^9/l, >= 100000/ul
    # leukocytes: 3000/ mm^3, >= 3000/mcl

    pattern = re.compile('(\s?[\>\=\<]+\s?\d+[\,\.]?\d*)')
    condition = pattern.findall(condition)[0].replace(',', '')
    lab_value = lab_value[0]
    return lab_value, condition
