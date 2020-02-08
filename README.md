# hackworld-poc
Proof of Concept for HackTheWorld.

## Instructions o run the App locally

### Clone the Repo
```bash
$ git clone https://github.com/neeyanthkvk/hackworld-poc.git
```

### Working on git branch
```bash
$ git checkout -b <branch_name>
$ git add <files>
$ git commit -m '<commit message>'
$ git push origin <branch_name>
```
- Make sure to submit your pull request. 

### Setup Virtual environment
```bash
$ pip install virtualenv
$ virtualenv -p python3.7 <env_name>
$ source <env_name>/bin/activate
```

### Install requirements
```bash
$ cd path_to/hackworl_poc
$ pip install -r requirements.txt
```

### setup aws configuration
```bash
$ aws configure
AWS Access Key ID [None]: ***REMOVED***
AWS Secret Access Key [None]: ***REMOVED***
Default region name [None]: us-east-2
Default output format [None]: json
```

### Run locally
Download keys.json file to the (pathto/hackworld-poc)working directory
```bash
$ python authenticate_oauth2.py 
```

### Notes
- Supported browsers: Google Chrome and Firefox
- If doctor login fails, use [bcda url](https://bcda.cms.gov/sandbox/user-guide/) and get Client ID and Client Secret
- And change lines 255,258 in authenticate_oauth2.py 
```python
doc_client_id = '***REMOVED***c'
doc_client_secret = '***REMOVED***' 
```