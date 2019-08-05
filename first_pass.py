import requests

from umls import Authentication

URL = 'https://clinicaltrialsapi.cancer.gov/v1/clinical-trial/'


def get_nci_thesaurus_concept_ids(code):
    diseases = requests.get(URL+code).json()['diseases']
    nci_thesaurus_concept_ids = [disease['nci_thesaurus_concept_id'] for disease in diseases]
    print(nci_thesaurus_concept_ids)
    return nci_thesaurus_concept_ids


if __name__ == '__main__':

    auth = Authentication("***REMOVED***")
    target = auth.gettgt()
    ticket = auth.getst(target)
    params = {'targetSource': 'ICD9CM', 'ticket': ticket}
    codeset = 'NCI'

    url = f'https://uts-ws.nlm.nih.gov/rest/crosswalk/current/source/{codeset}/'
    temp = []
    for nci_thesaurus_concept_id in get_nci_thesaurus_concept_ids('NCT02194738'):
        res = requests.get(url + nci_thesaurus_concept_id, params=params)
        import ipdb;ipdb.sset_trace()
        for result in res.json()["result"]:
            if result["ui"] not in ("TCGA", "OMFAQ", "MPN-SAF"):
                name_ncit = result["name"]
                code_ncit = result["ui"]
                temp.append(code_ncit)

    print(temp)