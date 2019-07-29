from pathlib import Path
import json
import requests as req
import logging
import pyodbc
import re
import boto3
from jsonpath_rw_ext import parse
from typing import Dict, List, Any, Tuple, Union

#BASE_URL = "https://dev-api.vets.gov/services/argonaut/v0/"
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
    'hemoglobin': '718-7',
    'leukocytes': '6690-2',
    'platelets': '32623-1'
}

TABLE_NAME_BY_CELL_TYPE = {
    'hemoglobin': 'Dataset1_Hemoglobin_Trials_First',
    'wbc' : 'Dataset1_WBC_Trials_First',
    'Platelets': 'Dataset1_Platelets_Trials_First',
}


def execute_sql(sql):
    with pyodbc.connect(connection_details) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()


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
    return api_res["gender"], api_res["birthDate"], api_res["name"][0]["text"], json.dumps(api_res)

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
        params = {}
        #params = {"diseases.nci_thesaurus_concept_id": ncit}
        #if (gender != "unknown"):
        #    params["eligibility.structured.gender"] = gender
        #if (age != 0):
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
    values_by_cell_type = {}

    for cell_type in LOINC_CODES:
        params = {'patient': patient_id, 'code': LOINC_CODES[cell_type]}
        observations = get_api(token, url=OBSERVATION_URL, params=params)

        # extract values from observations.
        # getting only one value for now.
        entries = observations.get('entry')
        if entries:
            value = str(entries[0]['resource']['valueQuantity']['value'])
            values_by_cell_type[cell_type] = value
        else:
            values_by_cell_type[cell_type] = 'Not Found'
        # for entry in observations.get('entry')[0]:
        #     try:
        #         values_by_cell_type[cell_type].append(entry['resource']['valueQuantity']['value'])
        #     except KeyError:
        #         pass
    print("VALUES:", values_by_cell_type)
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
    # for lab_result in lab_results:
    for trial in trials_by_ncit:
        filtered_trials, excluded_trails = filter_trials_from_description(trial['trials'],lab_results)
        filtered_trials_by_ncit.append({"ncit": trial['ncit'], "trials": filtered_trials})
        excluded_trials_by_ncit.append({"ncit": trial['ncit'], "trials": excluded_trails})

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
        if conditions:
            trial.filter_condition = ',\t'.join(value for key, value in conditions.items())
            trial.lab_result = ', '.join([key + '=' + value for key, value in lab_results.items()])
            for cell_type, condition in conditions.items():
                lab_value = lab_results.get(cell_type)
                lab_value, condition = convert_expressions(lab_value, condition)
                if eval(lab_value + condition):
                    flag = True
                else:
                    flag = False
                    break
            if flag:
                filtered_trials.append(trial)
            else:
                excluded_trials.append(trial)
        else:
            trial.filter_condition = 'No Inclusion Criteria Found'
            trial.lab_result = 'N/A'
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
            return {match[1]: str(match[0]) for match in matches}
        else:
            entity_mapping = get_mapping_with_aws_comprehend(unstructured_descriptions)
            return entity_mapping
    else:
        return {}


def get_mapping_with_aws_comprehend(descriptions: List) -> Dict:
    client = boto3.client(service_name="comprehendmedical")
    description = ' '.join([match.value.replace('\r\n', ' ').lower() for match in descriptions]).replace(',', '')
    entities = []
    limit = 19999
    if len(description) < limit:
        entities.extend(client.detect_entities(Text=description)['Entities'])
    else:
        splits = ['']
        count = 0
        for desc in descriptions:
            if len(desc.value) >= limit:
                splits[count] = desc.value[:limit]
                splits[count] = desc.value[limit:]
                count += 2
                continue
            if len(desc.value)+len(splits[count]) >= limit:
                count += 1
            else:
                splits[count] += desc.value
        for split in splits:
            try:
                entities.extend(client.detect_entities(Text=split)['Entities'])
            except Exception as exc:
                print(exc)
                continue
    cell_types = ['hemoglobin', 'platelets', 'leukocytes']
    conditions = {}
    for entity in entities:
        entity_type = entity['Text']
        if any(cell_type in entity_type for cell_type in cell_types) and entity.get('Attributes'):
            conditions[entity_type] = entity_type + entity['Attributes'][0]['Text']
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
    lab_value = lab_value.split(' ')[0]
    return lab_value, condition


# def filter_trials_from_db(trials: List['Trial'], comparision_val: str,
#                           cell_type: str) -> Tuple[List['Trial'], List['Trial']]:
#     """
#     :param trials: List[obj(Trail)]
#     :param comparision_val: str
#     :param cell_type: str
#     :return: (List[obj(Trial], List[obj(Trial)])
#     """
#     trials_dict = {trial.id: trial for trial in trials}
#     nci_ids_str = '(' + ', '.join(["'" + nci_trial.id + "'" for nci_trial in trials]) + ')'
#
#     filtered_trials = []
#     excluded_trials = []
#     if trials:
#         condition_by_trails = filtered_trails_from_db(nci_ids_str=nci_ids_str,
#                                                       table_name=TABLE_NAME_BY_CELL_TYPE[cell_type])
#
#         for condition_by_trail, condition in condition_by_trails.items():
#             if eval(comparision_val+condition):
#                 filtered_trials.append(trials_dict[condition_by_trail])
#             else:
#                 excluded_trials.append(trials_dict[condition_by_trail])
#     return filtered_trials, excluded_trials
#
#
# def filtered_trails_from_db(nci_ids_str, table_name):
#     """
#     Returns results matched from DB based on nci_id
#     :param nci_ids_str: A formatted string with a list of nci_id's used in the where clause of SQL
#     :param table_name: Table that the filter
#     :return: dict: { 'nci_id1': 'condition1', 'nci_id2': 'condition2' }
#     """
#     filter_trails_sql = f"""SELECT * FROM dbo.{table_name} WHERE nci_id in {nci_ids_str};"""
#     rows = execute_sql(filter_trails_sql)
#     inclusion_condition_by_nci_id = {row.nci_id: row.Condition+row.Platelets.replace(',', '').replace('/', '')
#                                      for row in rows}
#     return inclusion_condition_by_nci_id