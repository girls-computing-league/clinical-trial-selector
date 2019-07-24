import json
from pprint import pformat as pf
import os
import hacktheworld as hack

from flask import Flask, g, redirect, session
from flask_oidc import OpenIDConnect
from flask_session import Session

app = Flask(__name__)
app.config.update({
	'SECRET_KEY': 'SomethingNotEntirelySecret',
	'TESTING': True,
	'DEBUG': True,
	'OIDC_SCOPES': [
		"openid",
		"offline_access",
		"profile",
		"email",
		"launch/patient",
		"veteran_status.read",
		"patient/Patient.read",
		"patient/Observation.read",
		"patient/Condition.read"
	],
	'OIDC_CLIENT_SECRETS': 'client_secrets.json',
	'OIDC_ID_TOKEN_COOKIE_SECURE': False,
	'OIDC_REQUIRE_VERIFIED_EMAIL': False,
	'OIDC_INSTROSPECTION_AUTH_METHOD': 'client_secret_basic',
	'OIDC_RESOURCE_CHECK_AUD': True,
	'OIDC_CALLBACK_ROUTE': '/varedirect'
})
SESSION_TYPE = 'filesystem'
app.config.from_object(__name__)
Session(app)
oidc = OpenIDConnect(app)
def nl(line):
	return(line + "</br>")

def username():
	return str(oidc.user_getfield('email'))

def fullname():
	return str(oidc.user_getfield('name'))

def subject():
	return str(oidc.user_getfield('sub'))

def credentials():
	return str(oidc.credentials_store)

def token():
	return oidc.get_access_token()

def token_response():
	cred_json = oidc.credentials_store[subject()]
	cred = json.loads(cred_json)
	return cred['token_response']

def mrn():
	cred_json = oidc.credentials_store[subject()]
	cred = json.loads(cred_json)
	return cred['token_response']['patient']

def access_json_dump(fp):
	acc = {"patient": mrn(), "access_token": token()}
	return json.dump(acc, fp)

@app.route('/')
def va_home():
	if oidc.user_loggedin:
		s = nl('Hello, ' + fullname() + "  (Username: %s) " % username())
		if('trials' not in session):
			s += nl('<button type="button" onclick="location.href = &quot;/getInfo&quot;;" id="infoButton">Find Clinical Trials</button>')
		else:
			s += nl('<button type="button" onclick="location.href = &quot;/displayInfo&quot;;" id="infoButton">View Matched Clinical Trials</button>')
		s += nl('<button type="button" onclick="location.href = &quot;/logout&quot;;" id="logoutButton">Logout</button>')
		return s
	else:
		return nl('Welcome!') \
			+ nl('<button type="button" onclick="location.href = &quot;/authenticate&quot;;" id="VAButton2">Authenticate with VA ID.me</button>') \
			+ nl('<button type="button" onclick="location.href = &quot;/authenticate2&quot;;" id="CMSButton2">Authenticate with CMS</button>')

@app.route('/authenticate')
@oidc.require_login
def auth():
	filename = 'accesscodes/' + subject() + ".json"
	tokenfile = open(filename, "w")
	access_json_dump(tokenfile)
	tokenfile.close()

	credfile = open('credentials.json', 'w')
	credfile.write(oidc.credentials_store[subject()])
	credfile.close()
	
	

	return nl('Hello, ' + fullname()) \
		+ nl('Subject: ' + subject()) \
		+ nl('Your patient token was saved in ' + filename + ".") \
		+ nl('<a href="/">Return</a>') \
		+ nl("") \
		+ nl("Token Response:") \
		+ nl("") \
		+ nl(json.dumps(token_response())) \
		+ nl("") \
		+ nl("Patient: ") \
		+ nl(str(mrn()))

@app.route('/logout')
def logout():
	oidc.logout()
	return 'Hi, you have been logged out! <a href="/">Home</a>'

@app.route('/getInfo')
@oidc.require_login
def get_info():
	loader = hack.PatientLoader()
	p = loader.patients[0]
	p.load_all()
	trials = p.get_trials()
	print(type(trials))
	session['trials'] = trials
	session['numTrials'] = len(trials)
	session['index'] = 0
	return redirect("/displayInfo")

@app.route('/displayInfo')
def display_info():
	trials = session.get('trials', None)
	index = session['index']
	curTrial = trials[session['index']]
	b1, b2, b3, b4 = False, False, False, False
	if(index != 0):
		b2 = True
	if(index >= 2):
		b1 = True
	if(index != len(trials)-1):
		b3 = True
	if(index <= len(trials)-3):
		b4 = True
	s = ""
	if(b1):
		inDif = min(5, index)
		s += nl('<button type="button" onclick="location.href = &quot;/backFive&quot;;" id="logoutButton">Go back '+str(inDif)+'</button>')
	if(b2):
		s += nl('<button type="button" onclick="location.href = &quot;/backOne&quot;;" id="logoutButton">Go back 1</button>')
	if(b3):
		s += nl('<button type="button" onclick="location.href = &quot;/forOne&quot;;" id="logoutButton">Go forward 1</button>')
	if(b4):
		inDif = min(5, len(trials)-1-index)
		s += nl('<button type="button" onclick="location.href = &quot;/forFive&quot;;" id="logoutButton">Go forward '+str(inDif)+'</button>')
	s += nl('<button type="button" onclick="location.href = &quot;/&quot;;" id="logoutButton">Back to Home</button>')
	return nl("Trial Code: " + curTrial.id) \
			+ nl("Trial Title: " + curTrial.title) \
			+ nl("Trial Summary: " + curTrial.summary) \
			+ s

@app.route('/backOne')
def back_one():
	session['index'] = session['index'] - 1
	return redirect("/displayInfo")
	
@app.route('/forOne')
def for_one():
	session['index'] = session['index'] + 1
	return redirect("/displayInfo")

@app.route('/backFive')
def back_five():
	session['index'] = session['index'] - 5
	session['index'] = max(0, session['index'])
	return redirect("/displayInfo")
	
@app.route('/forFive')
def for_five():
	session['index'] = session['index'] + 5
	session['index'] = min(session['numTrials']-1, session['index'])
	return redirect("/displayInfo")

	
if __name__ == '__main__':
	app.run()
