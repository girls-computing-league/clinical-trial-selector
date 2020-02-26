"""
Clinical Trials Selector
"""
# Monkey patch needed for proper websocket behavior
# Must be first line before any other imports
from gevent import monkey
monkey.patch_all()

import csv
import io
import json
import argparse
import logging, sys
import ssl
from flask_socketio import SocketIO, disconnect
from flask import Flask, session, redirect, render_template, request, flash, make_response
from flask_session import Session
from authlib.integrations.flask_client import OAuth
import hacktheworld as hack
from patient import get_lab_observations_by_patient, filter_by_inclusion_criteria
from infected_patients import (get_infected_patients, get_authenticate_bcda_api_token, get_diseases_icd_codes,
                               EXPORT_URL, submit_get_patients_job, get_infected_patients_info)
from wtforms import Form, StringField, validators
from concurrent.futures import ThreadPoolExecutor, as_completed

args = {}
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--local", help="Run application from localhost", action="store_const", const="development", default=argparse.SUPPRESS)
    parser.add_argument("--log", help="Log level", default=argparse.SUPPRESS)
    args = vars(parser.parse_args())

app = Flask(__name__)
app.secret_key = "***REMOVED***"
app.config.from_pyfile("config/default.cfg")
if args.get("local", app.env) == "development":
    app.config.from_pyfile("config/local.cfg")
else:
    app.config.from_pyfile("config/aws.cfg")
log_level = args.get("log", app.config["CTS_LOGLEVEL"])

logging.getLogger().setLevel(log_level)
logging.info("Clinical Trial Selector starting...")

app.logger.setLevel(log_level)
app.logger.info("Flask starting")
app.logger.debug("Debug level logging")

Session(app)
oauth = OAuth(app)
oauth.register("va")
oauth.register("cms")
socketio = SocketIO(app)

keys_fp = open("keys.json", "r")
keys_dict = json.load(keys_fp)
event_name = 'update_progress'

callback_urlbase = app.config["CTS_CALLBACK_URLBASE"]


def save_access_code(filename, mrn, token):
# creates a new file and gives permissions to write in it
# creates a dictionary with the medical record number and the token to enter into the file
# enters information in dictionary into file in json format
# saves and closes file
    fp = open(filename, 'w')
    acc = {"patient": mrn, "access_code": token}
    json.dump(acc, fp)
    fp.close()
    return

def authentications():
    auts = []
    if ('va_patient' in session): auts.append('va')
    if ('cms_patient' in session): auts.append('cms')
    return auts

@app.route('/')
def showtrials():
    return render_template('welcome.html', form=FilterForm(request.form), trials_selection="current")

@app.route('/cms/authenticate')
def cmsauthenticate():
    app.logger.info("Authenticting via CMS...")
    return oauth.cms.authorize_redirect(f'{callback_urlbase}/cmsredirect')

@app.route('/va/authenticate')
def vaauthenticate():
    app.logger.info("Authenticating via VA...")
    return oauth.va.authorize_redirect(f'{callback_urlbase}/varedirect')

@app.route('/cmsredirect')
def cmsredirect():
    app.logger.info("Redirected from CMS authentication")
    resp = oauth.cms.authorize_access_token()
    combined = session.get("combined_patient", hack.CombinedPatient())
    session['cms_access_token'] = resp['access_token']
    session['cms_patient'] = resp['patient']
    session.pop("trials", None)
    pat_token = {"mrn": resp["patient"], "token": resp["access_token"]}
    pat = hack.CMSPatient(resp['patient'], pat_token)
    pat.load_demographics()
    session['cms_gender'] = pat.gender
    session['cms_birthdate'] = pat.birthdate
    session['cms_name'] = pat.name
    combined.CMSPatient = pat
    combined.loaded = False
    session['combined_patient'] = combined
    return redirect('/cms/authenticated')

@app.route('/varedirect')
def varedirect():
    app.logger.info("Redirected from VA authentication")
    resp = oauth.va.authorize_access_token()
    combined = session.get("combined_patient", hack.CombinedPatient())
    session['va_access_token'] = resp['access_token']
    session['va_patient'] = resp['patient']
    session.pop("trials", None)
    pat_token = {"mrn": resp["patient"], "token": resp["access_token"]}
    pat = hack.Patient(resp['patient'], pat_token)
    pat.load_demographics()
    session['va_gender'] = pat.gender
    session['va_birthdate'] = pat.birthdate
    session['va_name'] = pat.name
    session['va_zipcode'] = pat.zipcode
    combined.VAPatient = pat
    combined.loaded = False
    session['combined_patient'] = combined
    return redirect('/va/authenticated')

@app.route('/cms/authenticated')
def cmsauthenticated():
    token = session.get('cms_access_token')
    mrn = session.get('cms_patient')
    filename = 'accesscodes/cms/' + mrn + '.json'
    save_access_code(filename, mrn, token)
    return redirect("/")

@app.route('/va/authenticated')
def vaauthenticated():
    token = session.get('va_access_token')
    mrn = session.get('va_patient')
    filename = 'accesscodes/va/' + mrn + '.json'
    save_access_code(filename, mrn, token)
    return redirect("/")

@app.route('/getInfo')
def getInfo():
    print("GETTING INFO NOW")
    combined = session.get("combined_patient", hack.CombinedPatient())
    auts = authentications()
    socketio.emit(event_name, {"data": 15}, broadcast=False)
    if (not auts):
        return redirect("/")
    combined.load_data()
    socketio.emit(event_name, {"data": 50}, broadcast=False)
    
    patient_id = session.get('va_patient')
    token = session.get('va_access_token')

    session['codes'] = combined.ncit_codes
    session['trials'] = combined.trials
    session['numTrials'] = combined.numTrials
    session['index'] = 0
    session["combined_patient"] = combined
    socketio.emit(event_name, {"data": 70}, broadcast=False)

    if patient_id is not None and token is not None:
        session['Laboratory_Results'] = get_lab_observations_by_patient(patient_id, token)
        print("FROM SESSION", session['Laboratory_Results'])
    socketio.emit(event_name, {"data": 95}, broadcast=False)
    socketio.emit('disconnect', {"data": 100}, broadcast=False)

    return redirect("/")

@app.route('/trials')
def show_all_trials():
    return render_template('welcome.html', form=FilterForm(request.form), trials_selection="current")

@app.route('/excluded')
def show_excluded():
    return render_template('welcome.html', form=FilterForm(request.form), excluded_selection="current")

@app.route('/conditions')
def show_conditions():
    return render_template('welcome.html', form=FilterForm(request.form), conditions_selection="current")

@app.route('/matches')
def show_matches():
    return render_template('welcome.html', form=FilterForm(request.form), matches_selection="current")

@app.route('/nomatches')
def show_nomatches():
    return render_template('welcome.html', form=FilterForm(request.form), nomatches_selection="current")

@app.route('/download_trials')
def download_trails():
    combined_patient = session['combined_patient']
    header = ['id', 'code_ncit', 'title', 'pi','official','summary','description']


    si = io.StringIO()
    cw = csv.writer(si)

    data = []
    for trial_by_ncit in combined_patient.trials_by_ncit:
        for trial in trial_by_ncit.get("trials", []):
            data.append([getattr(trial, attribute) for attribute in header])

    cw.writerow(header)
    cw.writerows(data)

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=info.csv"
    output.headers["Content-type"] = "text/csv"
    return output


class FilterForm(Form):
    hemoglobin = StringField('hemoglobin ', [validators.Length(max=25)])
    leukocytes = StringField('leukocytes ', [validators.Length(max=25)])
    platelets = StringField('platelets ', [validators.Length(max=25)])


@app.route('/filter_by_lab_results', methods=['GET', 'POST'])
def filter_by_lab_results():
    """
    A view that filters trials based on:
    Filter1 -> Filters the DB tables based on nci_id of trials. We only show the results with matching records in DB.
    Filter2 -> Filters results based on inclusion condition and value from the Observation API.
    """

    form = FilterForm(request.form)

    if request.method == 'POST':
        form.validate()
        lab_results = {key: (value.split()[0], value.split()[1]) for key, value in form.data.items()}
    else:
        lab_results = session['Laboratory_Results']

    combined_patient = session['combined_patient']
    trials_by_ncit = combined_patient.trials_by_ncit
    socketio.emit(event_name, {"data": 20}, broadcast=False)

    filter_trails_by_inclusion_criteria, excluded_trails_by_inclusion_criteria = \
        filter_by_inclusion_criteria(trials_by_ncit, lab_results)
    socketio.emit(event_name, {"data": 65}, broadcast=False)

    session['combined_patient'].trials_by_ncit = filter_trails_by_inclusion_criteria
    session['combined_patient'].numTrials = sum([len(x['trials']) for x in filter_trails_by_inclusion_criteria])
    session['combined_patient'].num_conditions_with_trials = len(filter_trails_by_inclusion_criteria)

    session['excluded'] = excluded_trails_by_inclusion_criteria
    session['combined_patient'].filtered = True
    session['excluded_num_trials'] = sum([len(x['trials']) for x in excluded_trails_by_inclusion_criteria])
    session['excluded_num_conditions_with_trials'] = len(excluded_trails_by_inclusion_criteria)
    socketio.emit(event_name, {"data": 95}, broadcast=False)
    socketio.emit('disconnect', {"data": 100}, broadcast=False)
    return redirect('/')


class InfectedPatientsForm(Form):
    trial_nci_id = StringField('NCI Trial ID ', [validators.Length(max=25)])


@app.route('/doctor_login')
def doctor_login():
    # TODO implement doctor login client ids are changing
    # TODO use this to enable authentication with client_id, client_secret tokens
    # get client id and client secret by authentication by redirecting to doctor authentication page
    # below are the dev tokens we got from https://sandbox.bcda.cms.gov/user_guide.html#authentication-and-authorization
    doc_client_id = '***REMOVED***c'
    doc_client_secret = '***REMOVED***'
    session['bcda_doc_token'] = get_authenticate_bcda_api_token(client_id=doc_client_id,
                                                                client_secret=doc_client_secret)
    return redirect("/infected_patients")


@app.route('/doctor_logout')
def doctor_logout():
    session['bcda_doc_token'] = None
    session['infected_patients'] = None
    return redirect("/infected_patients")


@app.route('/infected_patients', methods=['GET', 'POST'])
def infected_patients():
    form = InfectedPatientsForm(request.form)
    bcda_doc_token = session.get('bcda_doc_token', None)

    if not request.method == 'POST' or not form.validate():
        return render_template("infected_patients.html", form=form)

    if not bcda_doc_token:
        flash('Sign in using  Doctor Login button')
        return render_template("infected_patients.html", form=form)

    event_name = 'update_progress'
    nci_trial_id = form.trial_nci_id.data or 'NCT02750826'
    socketio.emit(event_name, {"data": 5}, broadcast=False)
    try:
        futures = {}
        progress = 15
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures[executor.submit(get_diseases_icd_codes, nci_trial_id)]= 'codes'
            futures[executor.submit(submit_get_patients_job, EXPORT_URL.format(data_type='ExplanationOfBenefit' ),
                                    bcda_doc_token)] = 'patients'
            futures[executor.submit(get_infected_patients_info, bcda_doc_token)] = 'patient_info'
            result = {}
            for future in as_completed(futures):
                result[futures[future]] = future.result()
                socketio.emit(event_name, {"data": progress}, broadcast=False)
                progress += 25
        patients = get_infected_patients(**result)
        session['infected_patients'] = patients
        socketio.emit(event_name, {"data": 100}, broadcast=False)

        socketio.emit('disconnect', {"data": 100}, broadcast=False)
    except Exception as exc:
        print(exc)
        flash(f'Failed to process NCT ID: {nci_trial_id}')

    return render_template("infected_patients.html", form=form)


@app.route('/infected_patients_info')
def display_infected_patients():
    return render_template('patients_info.html')

@app.route('/trial')
def trial():
    return render_template('trial.html', trial_selection="current")

@app.route('/measures')
def measures():
    return render_template('trial.html', measures_selection="current")

@app.route('/diseases')
def diseases():
    return render_template('trial.html', diseases_selection="current")

@app.route('/locations')
def locations():
    return render_template('trial.html', locations_selection="current")

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")

# @cms.tokengetter
# def get_cms_token(token=None):
#     return session.get('cms_access_token')

# @va.tokengetter
# def get_va_token(token=None):
#     return session.get('va_access_token')

@app.route('/generalprivacypolicy.html')
def privacy_policy():
    session.clear()
    return render_template("generalprivacypolicy.html")

@app.route('/generaltermsofuse.html')
def consumerpolicynotice():
    session.clear()
    return render_template("generaltermsofuse.html")

if __name__ == '__main__':
    context = ssl.SSLContext()
    context.load_cert_chain('cert/cert.pem', keyfile='cert/key.pem')
    socketio.run(app, host="0.0.0.0", port = app.config['CTS_PORT'], debug=False, ssl_context=context)
