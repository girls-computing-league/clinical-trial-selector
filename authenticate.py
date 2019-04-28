import json
from pprint import pformat as pf

from flask import Flask, g
from flask_oidc import OpenIDConnect

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
        "patient/Patient.read"
    ],
    'OIDC_CLIENT_SECRETS': 'client_secrets.json',
    'OIDC_ID_TOKEN_COOKIE_SECURE': False,
    'OIDC_REQUIRE_VERIFIED_EMAIL': False,
    'OIDC_INSTROSPECTION_AUTH_METHOD': 'client_secret_basic',
    'OIDC_RESOURCE_CHECK_AUD': True,
    'OIDC_CALLBACK_ROUTE': '/varedirect'
})
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
    return pf(oidc.credentials_store)

@app.route('/')
def va_home():
    if oidc.user_loggedin:
        return nl('Hello, ' + fullname() + "  (Username: %s) " % username()) \
            + nl('<a href="/authenticate">Re-authenticate</a> ') \
            + nl('<a href="/logout">Log out</a>')
    else:
        return nl('Welcome anonymous,') \
            + nl('<a href="/authenticate">Authenticate</a>') 

@app.route('/authenticate')
@oidc.require_login
def auth():
    filename = 'accesscodes/' + subject() + ".json"
    tokenfile = open(filename, "w")
    tokenfile.write(oidc.get_access_token())
    tokenfile.close()
    return nl('Hello, ' + fullname()) \
        + nl('Subject: ' + subject()) \
        + nl('Token saved in ' + filename) \
        + nl('<a href="/">Return</a>') \
        + nl("") \
        + nl("Credentials:") \
        + nl("") \
        + nl(credentials())

@app.route('/savetoken')
def hello_save():
    tokenfile = open("accesstoken.txt", "w")
    tokenfile.write(g.__bool__oidc.get_access_token())
    tokenfile.close()
    return('Token saved in accesstoken.txt</br><a href="/">Return</a>')

@app.route('/api')
@oidc.accept_token(True, ['openid'])
def hello_api():
    return json.dumps({'hello': 'Welcome %s' % g.oidc_token_info['sub']})


@app.route('/logout')
def logout():
    oidc.logout()
    return 'Hi, you have been logged out! <a href="/">Home</a>'

@app.route('/token')
def retrieve_token():
    return "Credentials: </br></br>" + str(oidc.credentials_store)

if __name__ == '__main__':
    app.run()
