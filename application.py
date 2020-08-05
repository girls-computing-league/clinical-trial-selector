"""
Clinical Trial Selector
""" 
# Monkey patch needed for proper websocket behavior
# Must be first line before any other imports
from gevent import monkey
monkey.patch_all()

import csv
import io
import argparse
import logging, sys
import ssl
import filter
import json
from datetime import datetime
from flask_socketio import SocketIO, join_room
from flask import Flask, session, redirect, render_template, request, flash, make_response
from flask_session import Session
from flask_talisman import Talisman
from authlib.integrations.flask_client import OAuth
import hacktheworld as hack
from infected_patients import (get_infected_patients, get_authenticate_bcda_api_token, get_diseases_icd_codes,
                               EXPORT_URL, submit_get_patients_job, get_infected_patients_info)
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, validators
from concurrent.futures import ThreadPoolExecutor, as_completed
from labtests import labs
from typing import Dict

args: dict = {}
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--local", help="Run application from localhost", action="store_const", const="development", default=argparse.SUPPRESS)
    parser.add_argument("--log", help="Log level", default=argparse.SUPPRESS)
    parser.add_argument("-r", "--reload", help="Reload automatically after changes", action="store_true")
    args = vars(parser.parse_args())

app = Flask(__name__)

def read_config(environment: str):
    app.config.from_pyfile(f"config/{environment}.cfg")
    app.config.from_pyfile(f"secrets/{environment}_keys.cfg")

env = 'local' if args.get('local', app.env) == 'development' else ('test_aws' if app.env == 'test' else 'aws')
read_config(env)
read_config('default')

log_level = args.get("log", app.config["CTS_LOGLEVEL"]).upper()

formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(name)-23s %(message)s')
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
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

def combined_from_session() -> hack.CombinedPatient:
    return session.setdefault('combined_patient', hack.CombinedPatient())

@app.route('/')
def showtrials():
    if not session.get("combined_patient", None):
        return welcome()
    return render_template('welcome.html', form=FilterForm(), welcome_selection="current", labs = labs)

@app.route('/welcome')
def welcome():
    return render_template('welcome.html', welcome_selection="current")

@app.route("/authenticate/<source>", methods=["POST"])
def authenticate(source):
    app.logger.info(f"Authenticating via {source.upper()}...")
    return getattr(oauth, source).authorize_redirect(f'{callback_urlbase}/{source}redirect')

@app.route('/<source>redirect')
def oauth_redirect(source):
    app.logger.info(f"Redirected from {source.upper()} authentication")
    resp: Dict[str, str] = getattr(oauth,source).authorize_access_token()
    app.logger.debug(f"Response: {resp}")
    combined = combined_from_session()
    mrn = resp['patient']
    token = resp['access_token']
    combined.login_patient(source, mrn, token)
    return redirect('/')

@app.route('/getInfo', methods=['POST'])
def getInfo():
    app.logger.info("GETTING INFO NOW")
    combined = combined_from_session()
    socketio.emit(event_name, {"data": 15}, room=session.sid)
    if not combined.has_patients():
        return redirect("/")
    app.logger.info("loading data...")
    combined.load_data()
    socketio.emit(event_name, {"data": 50}, room=session.sid)
    app.logger.info("loading test results...")
    combined.load_test_results()
    socketio.emit(event_name, {"data": 95}, room=session.sid)
    socketio.emit('disconnect', {"data": 100}, room=session.sid)
    return redirect("/")

@app.route('/trials')
def show_all_trials():
    if not session.get("combined_patient", None):
        return welcome()
    lab_names = [filter.value_dict[lab]['display_name'] for lab in filter.value_dict.keys()]
    unit_names  = [filter.value_dict[lab]['default_unit_name'] for lab in filter.value_dict.keys()]
    return render_template('welcome.html', form=FilterForm(), trials_selection="current", labs=labs, lab_names=lab_names, unit_names=unit_names)

@app.route('/excluded')
def show_excluded():
    if not session.get("combined_patient", None):
        return welcome()
    return render_template('welcome.html', form=FilterForm(), excluded_selection="current")

@app.route('/conditions')
def show_conditions():
    if not session.get("combined_patient", None):
        return welcome()
    return render_template('welcome.html', form=FilterForm(), conditions_selection="current")

@app.route('/addlab')
def show_addlab():
    if not session.get("combined_patient", None):
        return welcome()
    lab_names = [filter.value_dict[lab]['display_name'] for lab in filter.value_dict.keys()]
    unit_names  = [filter.value_dict[lab]['default_unit_name'] for lab in filter.value_dict.keys()]
    return render_template('welcome.html', form=FilterForm(), addlab_selection="current", lab_names=lab_names, unit_names=unit_names)

@app.route('/addcondition')
def show_addcondition():
    if not session.get("combined_patient", None):
        return welcome()
    return render_template('welcome.html', form=FilterForm(), addcondition_selection="current")


@app.route('/matches')
def show_matches():
    if not session.get("combined_patient", None):
        return welcome()
    return render_template('welcome.html', form=FilterForm(), matches_selection="current")

@app.route('/nomatches')
def show_nomatches():
    if not session.get("combined_patient", None):
        return welcome()
    return render_template('welcome.html', form=FilterForm(), nomatches_selection="current")

@app.route('/test')
def test():
    return render_template('modal_test.html', form=FilterForm())

@app.route('/download_trials')
def download_trails():
    if not session.get("combined_patient", None):
        return welcome()
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


@app.route('/add_lab_result', methods=['POST'])
def add_lab_result():
    body = dict(request.form)
    combined_patient = session['combined_patient']
    combined_patient.latest_results[body['labType']] = hack.TestResult(test_name=filter.reverse_value_dict[body['labType']],
                                                                       datetime=datetime.now(), value=body['labValue'],
                                                                       unit=body['unitValue'])

    #logging.info("NEW PATIENT LAB VALUES")
    #logging.info(combined_patient.latest_results)
    return redirect('/trials')

@app.route('/add_condition', methods=['POST'])
def add_condition():
    body = dict(request.form)
    combined_patient = session['combined_patient']
    combined_patient.add_extra_code(body['newCode'])
    return getInfo()


@app.route('/filter_by_lab_results', methods=['POST'])
def filter_by_lab_results():
    """
    A view that filters trials based on:
    Filter1 -> Filters the DB tables based on nci_id of trials. We only show the results with matching records in DB.
    Filter2 -> Filters results based on inclusion condition and value from the Observation API.
    """

    form = FilterForm()

    combined_patient = session['combined_patient']
    socketio.emit(event_name, {"data": 20}, room=session.sid)
    filter_trails_by_inclusion_criteria, excluded_trails_by_inclusion_criteria = combined_patient.filter_by_criteria(form)

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
    return render_template("generalprivacypolicy.html")

@app.route('/generaltermsofuse.html')
def terms_use():
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
