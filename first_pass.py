import requests

from umls import Authentication

URL = 'https://clinicaltrialsapi.cancer.gov/v1/clinical-trial/'


def get_nci_thesaurus_concept_ids(code):
    diseases = requests.get(URL+code).json()['diseases']
    nci_thesaurus_concept_ids = [disease['nci_thesaurus_concept_id'] for disease in diseases]
    return nci_thesaurus_concept_ids


def get_diseases_icd_codes():
    auth = Authentication("***REMOVED***")
    target = auth.gettgt()
    ticket = auth.getst(target)
    params = {'targetSource': 'ICD9CM', 'ticket': ticket}
    codeset = 'NCI'

    url = f'https://uts-ws.nlm.nih.gov/rest/crosswalk/current/source/{codeset}/'
    icd_codes = []
    for nci_thesaurus_concept_id in get_nci_thesaurus_concept_ids('NCT02194738'):
        res = requests.get(url + nci_thesaurus_concept_id, params=params)
        for result in res.json()["result"]:
            if result["ui"] not in ("TCGA", "OMFAQ", "MPN-SAF"):
                code_ncit = result["ui"].replace('.','')
                icd_codes.append(code_ncit)
    return icd_codes
