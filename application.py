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
from flask_socketio import SocketIO, join_room
from flask import Flask, session, redirect, render_template, request, flash, make_response
from flask_session import Session 
from flask_talisman import Talisman
from authlib.integrations.flask_client import OAuth
import hacktheworld as hack
from infected_patients import (get_infected_patients, get_authenticate_bcda_api_token, get_diseases_icd_codes,
                               EXPORT_URL, submit_get_patients_job, get_infected_patients_info)
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.csrf import CSRFError
from wtforms import Form, StringField, validators
from concurrent.futures import ThreadPoolExecutor, as_completed
from labtests import labs

args: dict = {}
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--local", help="Run application from localhost", action="store_const", const="development", default=argparse.SUPPRESS)
    parser.add_argument("--log", help="Log level", default=argparse.SUPPRESS)
    parser.add_argument("-r", "--reload", help="Reload automatically after changes", action="store_true")
    args = vars(parser.parse_args())

app = Flask(__name__)
if args.get("local", app.env) == "development":
    app.config.from_pyfile("config/local.cfg")
    app.config.from_pyfile("secrets/local_keys.cfg")
elif app.env == "test":
    app.config.from_pyfile("config/test_aws.cfg")
    app.config.from_pyfile("secrets/test_aws_keys.cfg")
else:
    app.config.from_pyfile("config/aws.cfg")
    app.config.from_pyfile("secrets/aws_keys.cfg")
log_level = args.get("log", app.config["CTS_LOGLEVEL"]).upper()
app.config.from_pyfile("config/default.cfg")
app.config.from_pyfile("secrets/default_keys.cfg")

from patient import get_lab_observations_by_patient, filter_by_inclusion_criteria

logging.getLogger().setLevel(log_level)
logging.info("Clinical Trial Selector starting...")
logging.warning(f"app.env = {app.env}")

app.logger.setLevel(log_level)
app.logger.info("Flask starting")
app.logger.debug("Debug level logging")

Session(app)
oauth = OAuth(app)
oauth.register("va")
oauth.register("cms")
csrf = CSRFProtect(app)
socketio = SocketIO(app, manage_session=False)

event_name = 'update_progress'

callback_urlbase = app.config["CTS_CALLBACK_URLBASE"]

def authentications():
    auts = []
    if ('va_patient' in session): auts.append('va')
    if ('cms_patient' in session): auts.append('cms')
    return auts

@app.route('/')
def showtrials():
    return render_template('welcome.html', form=FilterForm(), trials_selection="current", labs = labs)

@app.route("/authenticate/<source>", methods=["POST"])
def authenticate(source):
    app.logger.info(f"Authenticating via {source.upper()}...")
    return getattr(oauth, source).authorize_redirect(f'{callback_urlbase}/{source}redirect')

@app.route('/<source>redirect')
def oauth_redirect(source):
    app.logger.info(f"Redirected from {source.upper()} authentication")
    resp = getattr(oauth,source).authorize_access_token()
    app.logger.debug(f"Response: {resp}")
    combined = session.get("combined_patient", hack.CombinedPatient())
    session[f'{source}_access_token'] = resp['access_token']
    session[f'{source}_patient'] = resp['patient']
    session.pop("trials", None)
    pat_token = {"mrn": resp["patient"], "token": resp["access_token"]}
    if source == 'va':
        pat = hack.Patient(resp['patient'], pat_token)
    else:
        pat = hack.CMSPatient(resp['patient'], pat_token)
    pat.load_demographics()
    session[f'{source}_gender'] = pat.gender
    session[f'{source}_birthdate'] = pat.birthdate
    session[f'{source}_name'] = pat.name
    if source == 'va':
        session[f'va_zipcode'] = pat.zipcode
        combined.VAPatient = pat
    else:
        combined.CMSPatient = pat
    combined.loaded = False
    session['combined_patient'] = combined
    return redirect('/')

@app.route('/getInfo', methods=['POST'])
def getInfo():
    app.logger.info("GETTING INFO NOW")
    combined: hack.CombinedPatient = session.get("combined_patient", hack.CombinedPatient())
    auts = authentications()
    socketio.emit(event_name, {"data": 15}, room=session.sid)
    if (not auts):
        return redirect("/")
    combined.load_data()
    socketio.emit(event_name, {"data": 50}, room=session.sid)
    
    patient_id = session.get('va_patient')
    token = session.get('va_access_token')

    session['codes'] = combined.ncit_codes
    session['trials'] = combined.trials
    session['numTrials'] = combined.numTrials
    session['index'] = 0
    session["combined_patient"] = combined
    socketio.emit(event_name, {"data": 70}, room=session.sid)

    if patient_id is not None and token is not None:
        session['Laboratory_Results'] = get_lab_observations_by_patient(patient_id, token)
        app.logger.debug("FROM SESSION", session['Laboratory_Results'])
        combined.VAPatient.load_test_results()
        combined.results = combined.VAPatient.results
        combined.latest_results = combined.VAPatient.latest_results
        # for trial in combined.trials:
        #     trial.determine_filters()
    socketio.emit(event_name, {"data": 95}, room=session.sid)
    socketio.emit('disconnect', {"data": 100}, room=session.sid)

    return redirect("/")

@app.route('/trials')
def show_all_trials():
    return render_template('welcome.html', form=FilterForm(), trials_selection="current", labs=labs)

@app.route('/excluded')
def show_excluded():
    return render_template('welcome.html', form=FilterForm(), excluded_selection="current")

@app.route('/conditions')
def show_conditions():
    return render_template('welcome.html', form=FilterForm(), conditions_selection="current")

@app.route('/matches')
def show_matches():
    return render_template('welcome.html', form=FilterForm(), matches_selection="current")

@app.route('/nomatches')
def show_nomatches():
    return render_template('welcome.html', form=FilterForm(), nomatches_selection="current")

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


class FilterForm(FlaskForm):
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

    form = FilterForm()

    if form.validate_on_submit():
        for key, value in form.data.items():
            if key != "csrf_token":
                # lab_results = {key: (value.split()[0], value.split()[1])}
                lab_results = {key: value}
    else:
        lab_results = session['Laboratory_Results']

    combined_patient = session['combined_patient']
    trials_by_ncit = combined_patient.trials_by_ncit
    socketio.emit(event_name, {"data": 20}, room=session.sid)

    filter_trails_by_inclusion_criteria, excluded_trails_by_inclusion_criteria = \
        filter_by_inclusion_criteria(trials_by_ncit, lab_results)
    socketio.emit(event_name, {"data": 65}, room=session.sid)

    session['combined_patient'].trials_by_ncit = filter_trails_by_inclusion_criteria
    session['combined_patient'].numTrials = sum([len(x['trials']) for x in filter_trails_by_inclusion_criteria])
    session['combined_patient'].num_conditions_with_trials = len(filter_trails_by_inclusion_criteria)

    session['excluded'] = excluded_trails_by_inclusion_criteria
    session['combined_patient'].filtered = True
    session['excluded_num_trials'] = sum([len(x['trials']) for x in excluded_trails_by_inclusion_criteria])
    session['excluded_num_conditions_with_trials'] = len(excluded_trails_by_inclusion_criteria)
    socketio.emit(event_name, {"data": 95}, room=session.sid)
    socketio.emit('disconnect', {"data": 100}, room=session.sid)
    return redirect('/')


class InfectedPatientsForm(FlaskForm):
    trial_nci_id = StringField('NCI Trial ID ', [validators.Length(max=25)])


@app.route('/doctor_login')
def doctor_login():
    # TODO implement doctor login client ids are changing
    # TODO use this to enable authentication with client_id, client_secret tokens
    # get client id and client secret by authentication by redirecting to doctor authentication page
    # below are the dev tokens we got from https://sandbox.bcda.cms.gov/user_guide.html#authentication-and-authorization
    doc_client_id = app.config["DOC_CLIENT_ID"]
    doc_client_secret = app.config["DOC_CLIENT_SECRET"]
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
    form = InfectedPatientsForm()
    bcda_doc_token = session.get('bcda_doc_token', None)

    if not request.method == 'POST' or not form.validate():
        return render_template("infected_patients.html", form=form)

    if not bcda_doc_token:
        flash('Sign in using  Doctor Login button')
        return render_template("infected_patients.html", form=form)

    event_name = 'update_progress'
    nci_trial_id = form.trial_nci_id.data or 'NCT02750826'
    socketio.emit(event_name, {"data": 5}, room=session.sid)
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
                socketio.emit(event_name, {"data": progress}, room=session.sid)
                progress += 25
        patients = get_infected_patients(**result)
        session['infected_patients'] = patients
        socketio.emit(event_name, {"data": 100}, room=session.sid)

        socketio.emit('disconnect', {"data": 100}, room=session.sid)
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

@app.route('/logout', methods=["POST"])
def logout():
    session.clear()
    return redirect("/")

@app.route('/generalprivacypolicy.html')
def privacy_policy():
    session.clear()
    return render_template("generalprivacypolicy.html")

@app.route('/generaltermsofuse.html')
def consumerpolicynotice():
    session.clear()
    return render_template("generaltermsofuse.html")

@socketio.on("connect")
def connect_socket():
    app.logger.info(f"Socket connected, socket id: {request.sid}, socket room: {session.sid}")
    join_room(session.sid)

if __name__ == '__main__':
    if args.get("local", app.env) != "development":
        csp = {
            'script-src': [
                '\'self\'',
                '*.va.gov',
                '*.googleapis.com',
                '*.cloudflare.com'
            ]
        }
        Talisman(app, content_security_policy = csp)
        context = ssl.SSLContext()
        context.load_cert_chain('cert/fullchain.pem', keyfile='cert/privkey.pem')
        socketio.run(app, host="0.0.0.0", port = app.config['CTS_PORT'], debug=False, ssl_context= context)
        # socketio.run(app, host="0.0.0.0", port = app.config['CTS_PORT'], debug=False, certfile='cert/fullchain.pem', keyfile='cert/privkey.pem')
    else:
        if args.get("reload"):
            app.config["TEMPLATES_AUTO_RELOAD"] = True
        socketio.run(app, host="0.0.0.0", port = app.config['CTS_PORT'], use_reloader=args.get("reload"), debug=False)
