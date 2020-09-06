import json
import requests as req
import logging
import re
import boto3, botocore
import subprocess
from typing import Dict, List, Any, Tuple, Optional
from flask import current_app as app
import time

client = boto3.client(service_name="comprehendmedical", config=botocore.client.Config(max_pool_connections=40),region_name='us-east-2')

trial_filter_cnt = 0

LOINC_CODES = {
    '718-7': 'hemoglobin',
    '6690-2': 'leukocytes',
    '777-3': 'platelets'
}

match_type = 'hemoglobin|platelets|leukocytes'
lab_pattern = re.compile(f'(\[?({match_type})\]?\s?[\>\=\<]+\s?\d+[\.\,]?\d*\s?\w+\/?\s?\w+(\^\d*)?)')
lab_simple = re.compile(f'({match_type})')

def rchop(thestring, ending):
  if thestring.endswith(ending):
    return thestring[:-len(ending)]
  return thestring

def get_api(token, url, params=None):
    headers = {"Authorization": "Bearer {}".format(token)}
    res = req.get(url, headers=headers, params=params)
    return res.json()

def find_trials(ncit_codes, gender="unknown", age=0):
    logging.info("Searching for trials in patient.py...********************************************************************************************************************************************************************************************************************************************************************************************************************************************************")
    size = 50
    trials = []
    all_ncit = [ncit_dict['ncit'] for ncit_dict in ncit_codes]
    for ncit_dict in ncit_codes:
        total = 1
        next_trial = 1
        while next_trial<= total:
            ncit = ncit_dict["ncit"]
            params = {"size": f"{size}", "from": f"{next_trial}", "diseases.nci_thesaurus_concept_id": ncit}
            if (gender != "unknown"):
                params["eligibility.structured.gender"] = [gender, 'BOTH']
            if (age != 0):
                params["eligibility.structured.max_age_in_years_gte"] = age
                params["eligibility.structured.min_age_in_years_lte"] = age
            now = time.clock()
            res = req.get(app.config['TRIALS_URL'], params=params)
            logging.debug(f"Time elapsed: {time.clock()-now} seconds")
            res_dict = res.json()
            trialset = {"code_ncit": ncit, "trialset": res_dict}
            total = res_dict["total"]
            next_trial += size

            trials.append(trialset)
            if (gender != "unknown"):
                params["eligibility.structured.gender"] = gender
                res = req.get(app.config['TRIALS_URL'], params=params)
                res_dict = res.json()
                trialset = {"code_ncit": ncit, "trialset": res_dict}
                total = res_dict["total"]
                next_trial += size

                trials.append(trialset)
    return trials

def find_new_trails(ncit_code, url):
    tries_left = 5
    search_text = f"{ncit_code['ncit_desc']} AND SEARCH[Location](AREA[LocationCountry]United States AND AREA[LocationStatus]Recruiting)"
    while tries_left>0:
        logging.info('Calling clinicaltrials.gov api for ncit_code-' + ncit_code['ncit'] + ' and ncit desc -' + ncit_code['ncit_desc'] )
        params = {'expr': search_text, 'min_rnk': 1, 'max_rnk': 100, 'fmt': 'json'} #get trials based on condition
        response = req.get(url, params=params)
        filter: list = []
        #filter based on age/gender/demographic`s/make sure the trial is still valid
        if response.status_code == 200:
            return response.json()

        logging.warn(f"Response code = {response.status_code}")
        logging.warn(f"Response text = {response.text}")
        tries_left -= 1
        logging.warn(f"Tries left = {tries_left}")
        time.sleep(5)
    return {}

# def find_all_codes(disease_list):
#     codes: list = []
#     names: list = []
#     for disease in disease_list:
#         codelist, nameslist = find_codes(disease)
#         codes += codelist
#         names += nameslist
#     return codes, names

def get_lab_observations_by_patient(patient_id, token):
    # loinc_codes = ','.join(list(LOINC_CODES.keys()))
    current_url: Optional[str] = app.config['VA_OBSERVATION_URL'] + f'?patient={patient_id}&_count=100'

    lab_results: dict = {}
    while len(lab_results) != 3 and current_url is not None:
        observations = get_api(token, url=current_url)
        logging.debug(f"Total observations = {observations.get('total')}")

        # extract values from observations.
        for entry in observations.get('entry'):
            resource = entry['resource']
            logging.debug(f"Observation resource: {resource}")

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

def filter_trials_from_description(trials: List, lab_results: Dict) -> Tuple[list, list]:
    """
    :param trials: List[obj(Trail)]
    :param comparision_val: str
    :param cell_type: str
    :return: (List[obj(Trial], List[obj(Trial)])
    """
    filtered_trials = []
    excluded_trials = []
    for trial in trials:
        conditions = find_conditions(trial)
        trial.filter_condition = []
        if conditions:
            include_trail = True
            for cell_type, condition in conditions.items():
                lab_value = lab_results.get(cell_type)
                if not lab_value:
                    trial.filter_condition.append((condition, True))
                    continue
                lab_value, converted_condition = convert_expressions(lab_value, condition)
                if (lab_value != "0") and eval(lab_value + converted_condition):
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


def find_conditions(trial: Any) -> Dict:
    match_type = 'hemoglobin|platelets|leukocytes'
    cell_types = ['hemoglobin', 'platelets', 'leukocytes']
    # parser = parse(f'$.eligibility.unstructured[?inclusion_indicator=true].description')
    unstructured_inclusions = trial.inclusions
    filtered_inclusions = [inclusion.replace('\r\n', ' ').lower() for inclusion in trial.inclusions
                            if any(cell_type in inclusion.lower() for cell_type in cell_types)]
    joined_description = ' and '.join(filtered_inclusions)
    if joined_description:
        # lab_pattern = re.compile(f'(\[?({match_type})\]?\s?[\>\=\<]+\s?\d+[\.\,]?\d*\s?\w+\/?\s?\w+(\^\d*)?)')
        matches = lab_pattern.findall(joined_description)
        if matches:
            conditions = {match[1]: str(match[0]) for match in matches}
            simple_matches = len(lab_simple.findall(joined_description))
            if len(conditions) == simple_matches:
                return conditions
            else:
                mapping = get_mapping_with_aws_comprehend(filtered_inclusions)
                if len(mapping) > len(conditions):
                    return mapping
                else:
                    return conditions
        else:
            entity_mapping = get_mapping_with_aws_comprehend(filtered_inclusions)
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
    return {}
    # def get_description():
    #     data = ''
    #     limit = 19990
    #     for match in descriptions:
    #         description = match.replace('\r\n', ' ').lower().replace(',', '')
    #         if len(description) > limit:
    #             for split in split_description(description, limit):
    #                 yield split
    #         elif len(data) + len(description) > limit:
    #             yield data
    #             data = description
    #         else:
    #             data += description + " and "
    #     yield data

    # conditions = {}
    # cell_types = ['hemoglobin', 'platelets', 'leukocytes']
    # for description in get_description():
    #     try:
    #         entities = client.detect_entities_v2(Text=description)['Entities']
    #         logging.debug(f"Description text send to AWS: {description}")
    #         logging.debug("Entities returned:")
    #         for entity in entities:
    #             logging.debug(f"Entity text: {entity['Text']} ({entity['Category']}/{entity['Type']})")
    #             entity_type = entity['Text']
    #             if any(cell_type == entity_type.lower() for cell_type in cell_types) \
    #                 and entity.get('Attributes') \
    #                 and entity['Attributes'][0]['Type'] == "TEST_VALUE":
    #                 conditions[entity_type] = entity_type + entity['Attributes'][0]['Text']
    #                 logging.debug(f"Entity attribute text: {entity['Attributes'][0]['Text']}")
    #                 logging.debug(f"Entity attribute type: {entity['Attributes'][0]['Type']}")
    #     except Exception as exc:
    #         logging.warn(f'Failed to retrieve aws comprehend entities: {str(exc)}')
    # return conditions


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
    # if type(condition) is List:
    #     condition = condition[0]
    condition_reg = pattern.findall(condition)
    if len(condition_reg) == 0:
        return "0", ""
    condition = condition_reg[0].replace(',', '')
    condition = condition.replace('=<', '<=')
    condition = condition.replace('=>', '>=')
#    lab_value = lab_value[0]
    return lab_value, condition
