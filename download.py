from requests import request
from jsonpath_rw_ext import parse
import csv
import re

MATCH_TYPE = 'hemoglobin|platelets|leukocytes'


def find_conditions(description):
    pattern = re.compile(f'(\[?({MATCH_TYPE})\]?\s?[\>\=\<]+\s?(\d+[\.\,]?\d*\s?\w+\/?\w+(\^\d*)?))')
    matches = pattern.findall(description.lower())
    if matches:
        return({match[1]: str(match[2]) for match in matches})


def download_descriptions():
    with open('descriptions.csv', 'w+') as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerow(['nct_id', 'nci_id', 'max_age', 'max_age_number', 'min_age_unit',
                         'max_age_unit', 'max_age_in_years', 'gender', 'min_age', 'min_age_number',
                         'min_age_in_years', 'descriptions', 'hemoglobin', 'platelets', 'leukocytes'])
        for i in range(0, 12200, 50):
            url = 'https://clinicaltrialsapi.cancer.gov/v1/clinical-trials?' \
                  'include=eligibility.unstructured&include=nci_id&'\
                  'include=nct_id&include=eligibility.structured'
            params = {
                'size': 50,
                'from': i
            }
            response = request('GET', url, params=params)
            text = response.json()
            conditions = {
                'hemoglobin': False,
                'platelets': False,
                'leukocytes': False

            }
            for trial in text['trials']:
                trial.update(trial['eligibility'].get('structured'))
                parser = parse(f'$.eligibility.unstructured[?inclusion_indicator=true].description')
                # [print(match.value) for match in parser.find(trial)]
                trial['descriptions'] = ' '.join([match.value.replace('\r\n', ' ') for match in parser.find(trial)])
                del trial['eligibility']
                trial_conditions = find_conditions(trial['descriptions'])
                if trial_conditions:
                    conditions.update(trial_conditions)
                trial.update(conditions)
                writer.writerow(trial.values())

download_descriptions()