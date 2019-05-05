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

def nl(line):
    return(line + "</br>")

@app.route('/')
def home():
    html = nl('Hello')
    html += nl('<a href="/cms/authenticate">Authenticate at CMS Blue Button</a>')
    return html

@app.route('/cms/authenticate')
def cmsauthenticate():
    return cms.authorize(callback='http://localhost:5000/cmsredirect')

@app.route('/cmsredirect')
def cmsredirect():
    resp = cms.authorized_response()
    session['cms_access_token'] = resp['access_token']
    session['cms_patient'] = resp['patient']
    return redirect('/cms/showtoken')

@app.route('/cms/showtoken')
def cmsshowtoken():
    token = session.get('cms_access_token')
    mrn = session.get('cms_patient')
    filename = 'accesscodes/cms/' + mrn + '.json'
    fp = open(filename, 'w')
    acc = {"patient": mrn, "access_code": token}
    json.dump(fp, acc)
    html = nl("Success!")
    html += nl("Access token:")
    html += nl(token)
    html += nl('')
    html += nl("Patient ID:")
    html += nl(mrn)
    html += '<a href="/">Home</a>'
    return html

@cms.tokengetter
def get_cms_token(token=None):
    return session.get('cms_access_token')
