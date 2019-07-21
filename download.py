from requests import request
from jsonpath_rw import parse
import csv


def download_descriptions():
    with open('descriptions.csv', 'w+') as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerow(['nct_id', 'nci_id', 'max_age', 'max_age_number', 'min_age_unit',
                         'max_age_unit', 'max_age_in_years', 'gender', 'min_age', 'min_age_number',
                         'min_age_in_years', 'descriptions'])
        for i in range(0, 12250, 50):
            url = 'https://clinicaltrialsapi.cancer.gov/v1/clinical-trials?' \
                  'include=eligibility.unstructured.description&include=nci_id&'\
                  'include=nct_id&include=eligibility.structured'
            params = {
                'eligibility.unstructured.inclusion_indicator': True,
                'size': 50,
                'from': i
            }
            response = request('GET', url, params=params)
            text = response.json()
            for trial in text['trials']:
                trial.update(trial['eligibility'].get('structured'))
                parser = parse('$.eligibility.unstructured[*].description')
                trial['descriptions'] = ' '.join([match.value.replace('\r\n', ' ') for match in parser.find(trial)])
                del trial['eligibility']
                writer.writerow(trial.values())

download_descriptions()