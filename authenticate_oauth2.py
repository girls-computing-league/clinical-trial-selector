from flask import Flask, session, jsonify, redirect
from flask_oauthlib.client import OAuth
import json

app = Flask(__name__)
app.secret_key = "development"

oauth = OAuth(app)

cms = oauth.remote_app(
    'cms',
    base_url = "https://sandbox.bluebutton.cms.gov/v1/o",
    consumer_key = "***REMOVED***",
    consumer_secret = "***REMOVED***",
    request_token_params = {'scope': 'profile'},
    request_token_url = None,
    access_token_url = "https://sandbox.bluebutton.cms.gov/v1/o/token/",
    authorize_url = "https://sandbox.bluebutton.cms.gov/v1/o/authorize",
    access_token_method = 'POST'
)

va = oauth.remote_app(
    'va',
    base_url = "https://dev-api.vets.gov/",
    consumer_key = "***REMOVED***",
    consumer_secret = "***REMOVED***",
    request_token_params = {'scope': 'openid offline_access profile email launch/patient veteran_status.read patient/Patient.read patient/Condition.read', "state": "12345"},
    request_token_url = None,
    access_token_url = "https://dev-api.va.gov/oauth2/token",
    authorize_url = "https://dev-api.va.gov/oauth2/authorization/",
    access_token_method = 'POST'
)

def nl(line):
    return(line + "</br>")

def save_access_code(filename, mrn, token):
    fp = open(filename, 'w')
    acc = {"patient": mrn, "access_code": token}
    json.dump(acc, fp)
    fp.close()
    return

def success_msg(filename, mrn, token):
    html = nl("Success!")
    html += nl('')
    html += nl("Credentials stored in: " + filename)
    html += nl('')
    html += nl("Access token:")
    html += nl(token)
    html += nl('')
    html += nl("Patient ID:")
    html += nl(mrn)
    html += '<a href="/">Home</a>'
    return html

@app.route('/')
def home():
    html = nl('Hello')
    html += nl('<a href="/cms/authenticate">Authenticate at CMS Blue Button</a>')
    html += nl('<a href="/va/authenticate">Authenticate at VA Argonaut</a>')
    return html

@app.route('/cms/authenticate')
def cmsauthenticate():
    return cms.authorize(callback='http://localhost:5000/cmsredirect')

@app.route('/va/authenticate')
def vaauthenticate():
    return va.authorize(callback='http://localhost:5000/varedirect')

@app.route('/cmsredirect')
def cmsredirect():
    resp = cms.authorized_response()
    session['cms_access_token'] = resp['access_token']
    session['cms_patient'] = resp['patient']
    return redirect('/cms/authenticated')

@app.route('/varedirect')
def varedirect():
    resp = va.authorized_response()
    session['va_access_token'] = resp['access_token']
    session['va_patient'] = resp['patient']
    return redirect('/va/authenticated')

@app.route('/cms/authenticated')
def cmsauthenticated():
    token = session.get('cms_access_token')
    mrn = session.get('cms_patient')
    filename = 'accesscodes/cms/' + mrn + '.json'
    save_access_code(filename, mrn, token)
    return success_msg(filename, mrn, token)

@app.route('/va/authenticated')
def vaauthenticated():
    token = session.get('va_access_token')
    mrn = session.get('va_patient')
    filename = 'accesscodes/va/' + mrn + '.json'
    return success_msg(filename, mrn, token)

@cms.tokengetter
def get_cms_token(token=None):
    return session.get('cms_access_token')

@va.tokengetter
def get_va_token(token=None):
    return session.get('va_access_token')