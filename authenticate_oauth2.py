from flask import Flask, session, jsonify, redirect, render_template, request
from flask_session import Session
from flask_oauthlib.client import OAuth
from flask_bootstrap import Bootstrap
import hacktheworld as hack
from patient import get_lab_observations_by_patient, filter_by_inclusion_criteria
from infected_patients import get_infected_patients, set_authenticate_bcda_api_token
import json
from wtforms import Form, StringField, validators

# creates the flask webserver and the secret key of the web server
app = Flask(__name__)
app.secret_key = "development" 

# runs the app with the OAuthentication protocol
SESSION_TYPE = 'filesystem'
app.config.from_object(__name__)
Session(app)
Bootstrap(app)
oauth = OAuth(app)

keys_fp = open("keys.json", "r")
keys_dict = json.load(keys_fp)

# specifies possible parameters for the protocol dealing with the CMS
cms = oauth.remote_app(
    'cms',
    base_url = "https://sandbox.bluebutton.cms.gov/v1/o",
    consumer_key = keys_dict["cms_key"],
    consumer_secret = keys_dict["cms_secret"],
    request_token_params = {'scope': 'profile'},
    request_token_url = None,
    access_token_url = "https://sandbox.bluebutton.cms.gov/v1/o/token/",
    authorize_url = "https://sandbox.bluebutton.cms.gov/v1/o/authorize/",
    access_token_method = 'POST'
)

va = oauth.remote_app(
    'va',
    base_url="https://dev-api.va.gov/",
    consumer_key = keys_dict["va_key"],
    consumer_secret = keys_dict["va_secret"],
    request_token_params={
        'scope': 'openid offline_access profile email launch/patient veteran_status.read patient/Observation.read patient/Patient.read patient/Condition.read', "state": "12345"},
    request_token_url=None,
    access_token_url="https://dev-api.va.gov/oauth2/token/",
    authorize_url="https://dev-api.va.gov/oauth2/authorization/",
    access_token_method='POST'
)


def nl(line):
    return(line + "</br>")

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

def success_msg(filename, mrn, token):
# displays success message that shows file where credentials are stored, token, and mrn
# makes new line to show each credential
    html = nl("Success!")
    html += nl('')
    html += nl("Credentials stored in: " + filename)
    html += nl('')
    html += nl("Access token:")
    html += nl(token)
    html += nl('')
    html += nl("Patient ID:")
    html += nl(mrn)
    html += nl('')
    html += '<a href="/">Home</a>'
    return html


@app.route('/old')
# creates home page with links to authenticate with the VA and CMS
def home():
    auts = authentications()
    html = nl('Welcome!') + nl('')
    if ('va' in auts):
        html += nl('Your VA patient number is: ' +
                   session["va_patient"]) + nl('')
    else:
        html += nl('<button type="button" onclick="location.href = &quot;/va/authenticate&quot;;" id="VAButton2">Authenticate with VA ID.me</button>')
    if ('cms' in auts):
        html += nl('Your CMS patient number is: ' + session["cms_patient"]) + nl('')
    else:
        html += nl('<button type="button" onclick="location.href = &quot;/cms/authenticate&quot;;" id="CMSButton2">Authenticate with CMS</button>')

    if auts:
        if('trials' not in session):
            html += nl('<button type="button" onclick="location.href = &quot;/getInfo&quot;;" id="infoButton">Find Clinical Trials</button>')
        else:
            html += nl('<button type="button" onclick="location.href = &quot;/displayInfo&quot;;" id="infoButton">View Matched Clinical Trials</button>')
        html += nl('<button type="button" onclick="location.href = &quot;/logout&quot;;" id="logoutButton">Logout</button>')

    return html

@app.route('/')
def showtrials():
    return render_template('welcome.html')

@app.route('/cms/authenticate')
def cmsauthenticate():
    return cms.authorize(callback='http://localhost:5000/cmsredirect')

@app.route('/va/authenticate')
def vaauthenticate():
    return va.authorize(callback='http://localhost:5000/varedirect')

@app.route('/cmsredirect')
def cmsredirect():
    resp = cms.authorized_response()
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
    resp = va.authorized_response()
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
    if (not auts):
        return redirect("/")
    combined.load_data()
    
    patient_id = session.get('va_patient')
    token = session.get('va_access_token')

    session['codes'] = combined.ncit_codes
    session['trials'] = combined.trials
    session['numTrials'] = combined.numTrials
    session['index'] = 0
    session["combined_patient"] = combined

    if patient_id is not None and token is not None:
        session['Laboratory_Results'] = get_lab_observations_by_patient(patient_id, token)
        print("FROM SESSION", session['Laboratory_Results'])

    return redirect("/")


@app.route('/filter_by_lab_results')
def filter_by_lab_results():
    """
    A view that filters trials based on:
    Filter1 -> Filters the DB tables based on nci_id of trials. We only show the results with matching records in DB.
    Filter2 -> Filters results based on inclusion condition and value from the Observation API.
    """
    combined_patient = session['combined_patient']
    lab_results = session['Laboratory_Results']
    trials_by_ncit = combined_patient.trials_by_ncit

    filter_trails_by_inclusion_criteria, excluded_trails_by_inclusion_criteria = \
        filter_by_inclusion_criteria(trials_by_ncit, lab_results)

    session['combined_patient'].trials_by_ncit = filter_trails_by_inclusion_criteria
    session['combined_patient'].numTrials = sum([len(x['trials']) for x in filter_trails_by_inclusion_criteria])
    session['combined_patient'].num_conditions_with_trials = len(filter_trails_by_inclusion_criteria)

    session['excluded'] = excluded_trails_by_inclusion_criteria
    session['combined_patient'].filtered = True
    session['excluded_num_trials'] = sum([len(x['trials']) for x in excluded_trails_by_inclusion_criteria])
    session['excluded_num_conditions_with_trials'] = len(excluded_trails_by_inclusion_criteria)
    return redirect('/')


class InfectedPatientsForm(Form):
    trial_nci_id = StringField('Trial ID ', [validators.Length(max=25)])


@app.route('/infected_patients', methods=['GET', 'POST'])
def infected_patients():
    form = InfectedPatientsForm(request.form)
    if request.method == 'POST' and form.validate():
        nci_trial_id = form.trial_nci_id.data or 'NCT02194738'
        # TODO use this to enable authentication with client_id, client_secret tokens
        set_authenticate_bcda_api_token(client_id='09869a7f-46ce-4908-a914-6129d080a2ae',
                                        client_secret='64916fe96f71adc79c5735e49f4e72f18ff941d0dd62cf43ee1ae0857e204f173ba10e4250c12c48')
        patients = get_infected_patients(nci_trial_id)
        session['infected_patients'] = patients
        return render_template("infected_patients.html", form=form)
    return render_template("infected_patients.html", form=form)


@app.route('/infected_patients_info')
def display_infected_patients():
    return render_template('patients_info.html')


@app.route('/trial')
def trial():
    return render_template('trial.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")

@cms.tokengetter
def get_cms_token(token=None):
    return session.get('cms_access_token')


@va.tokengetter
def get_va_token(token=None):
    return session.get('va_access_token')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
