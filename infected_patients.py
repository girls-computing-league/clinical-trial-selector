from __future__ import print_function
from time import sleep
import binascii
import os
import ndjson
import requests
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from requests import request
from jsonpath_rw_ext import parse
from base64 import b64encode
from typing import Dict, List
from umls import Authentication

GCM_NONCE_SIZE = 12
GCM_TAG_SIZE = 16
BCDA_URL = 'https://sandbox.bcda.cms.gov/'
EXPORT_URL = 'https://sandbox.bcda.cms.gov/api/v1/{data_type}/$export'
CLINICAL_TRIALS_URL = 'https://clinicaltrialsapi.cancer.gov/v1/clinical-trial/'
CROSS_WALK_URL = 'https://uts-ws.nlm.nih.gov/rest/crosswalk/current/source/'


def get_authenticate_bcda_api_token(client_id: str, client_secret: str):
    token_url = f'{BCDA_URL}auth/token'
    encoded_auth = b64encode(f'{client_id}:{client_secret}'.encode()).decode()
    headers = {
        'Authorization': f'Basic {encoded_auth}'
    }
    try:
        response = request("POST", token_url, headers=headers)
        response.raise_for_status()
        bearer_token = response.json().get('access_token', '')
    except Exception as e:
        raise Exception(f'authentication failed: {e}')
    return bearer_token


def decrypt_cipher(ct: 'File', key: str):
    nonce = ct.read(GCM_NONCE_SIZE)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce, mac_len=GCM_TAG_SIZE)
    ciphertext = ct.read()
    return cipher.decrypt_and_verify(
        ciphertext[:-GCM_TAG_SIZE],
        ciphertext[-GCM_TAG_SIZE:]
    )


def decrypt(ek: str, filepath: str,  pk: str = 'ATO_private.pem'):
    encrypted_key = binascii.unhexlify(ek)
    with open(pk, 'r') as fh:
        private_key = RSA.importKey(fh.read())
    fh.close()
    base = os.path.basename(filepath)
    cipher = PKCS1_OAEP.new(key=private_key, hashAlgo=SHA256, label=base.encode('utf-8'))
    decrypted_key = cipher.decrypt(encrypted_key)

    with open(filepath, 'rb') as fh:
        result = decrypt_cipher(fh, decrypted_key).decode("utf-8")
    return result


def submit_get_patients_job(url: str, token: str) -> List:
    submit_header = {
        'Accept': "application/fhir+json",
        'Prefer': "respond-async",
        'Authorization': f'Bearer {token}'
    }
    job_attempts = 0
    try:
        response = request("GET", url, headers=submit_header)
        response.raise_for_status()
        job_url = response.headers['Content-Location']
        while job_attempts < 20:
            job_response = request('GET', job_url, headers={
                'Authorization': f'Bearer {token}'
            })
            job_attempts += 1
            if job_response.status_code == 200:
                job_response.raise_for_status()
                output = job_response.json().get('output', None)
                if output:
                    patients = get_patients(output[0], token)
                    print('job_done')
                    return patients
            print(f'response code {job_response.status_code} Waiting 2sec  for the job to complete')
            sleep(2)
        raise Exception(f'Failed to get response from the url: {job_url} after {job_attempts} attempts')
    except Exception as exc:
        print(f'Failed due to : {exc}')
        raise Exception(exc)


def get_patients(body: Dict, token: str) -> List:
    encrypted_key = body['encryptedKey']
    patients_url = body['url']
    file_name = patients_url.split('/')[-1]
    response = request('GET', patients_url, headers={
        'Authorization': f'Bearer {token}'
    })
    tmp_dir = tempfile.mkdtemp()
    file_path = os.path.join(tmp_dir, file_name)
    try:
        with open(file_path, 'wb') as f:
            f.write(response.content)
        nd_patients = decrypt(encrypted_key, file_path)
    except Exception as e:
        raise Exception(e)
    else:
        os.remove(file_path)
    finally:
        print(f'removing files {file_path}')
        os.rmdir(tmp_dir)
    patients = ndjson.loads(nd_patients)
    return patients


def get_infected_patients(codes: List, patients: List[Dict], patient_info: Dict):
    # codes = ['4011']  # TODO use this to get more patients

    infected_patients = {}
    diagnosis = {}
    try:
        for patient in patients:
            patient_id = patient['patient']['reference'].split('/-')[-1]
            if patient_id not in diagnosis:
                diagnosis[patient_id] = {}
            for disease in patient['diagnosis']:
                if 'diagnosisCodeableConcept' in disease:
                    icd_code = disease['diagnosisCodeableConcept']['coding'][0]['code']
                    if icd_code not in ['9999999', 'XX000']:
                        diagnosis[patient_id][icd_code] = disease
                    if icd_code in codes:
                        # Matches disease
                        diagnosis[patient_id][icd_code]['match'] = True
                        patient_bene_data = {
                            'status': patient['status'],
                            'diagnosis': diagnosis[patient_id]
                        }
                        if patient_id in infected_patients:
                            infected_patients[patient_id].update(patient_bene_data)
                        else:
                            infected_patients[patient_id] = patient_bene_data
                            infected_patients[patient_id]['demo_info'] = patient_info.get(patient_id, None)
    except Exception as e:
        print(e)
        raise Exception(e)
    return infected_patients


def get_infected_patients_info(token: str):
    url = EXPORT_URL.format(
        data_type='Patient'
    )
    patients = submit_get_patients_job(url=url, token=token)
    infected_patients = {}
    for patient in patients:
        patient_id = patient['id'].replace('-', '')
        infected_patients[patient_id] = patient
    return infected_patients


def get_nci_thesaurus_concept_ids(code: str):
    try:
        diseases = requests.get(CLINICAL_TRIALS_URL+code).json()['diseases']
        nci_thesaurus_concept_ids = [disease['nci_thesaurus_concept_id'] for disease in diseases]
    except Exception as exc:
        raise Exception(exc)
    return nci_thesaurus_concept_ids


def get_diseases_icd_codes(code: str):
    auth = Authentication("***REMOVED***")
    icd_codes = []
    nci_thesaurus_concept_ids = get_nci_thesaurus_concept_ids(code)
    print(f'Getting Icd codes for NCT id {code} with disease codes {nci_thesaurus_concept_ids}')
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(process_codes, auth, nci_thesaurus_concept_id): nci_thesaurus_concept_id
            for nci_thesaurus_concept_id in nci_thesaurus_concept_ids
        }
        for future in as_completed(futures):
            codes = future.result()
            if codes:
                icd_codes.extend(codes)
    print(icd_codes)
    return icd_codes


def process_codes(auth: 'Authentication', nci_thesaurus_concept_id: str):
    codeset = 'NCI'
    url = f'{CROSS_WALK_URL}{codeset}/'
    params = {'targetSource': 'ICD9CM'}
    target = auth.gettgt()
    ticket = auth.getst(target)
    params['ticket'] = ticket
    res = requests.get(url + nci_thesaurus_concept_id, params=params)
    icd_codes = []
    try:
        res.raise_for_status()
    except:
        return
    for result in res.json()["result"]:
        if result["ui"] not in ("TCGA", "OMFAQ", "MPN-SAF"):
            code_ncit = result["ui"].replace('.', '')
            icd_codes.append(code_ncit)
    return icd_codes
