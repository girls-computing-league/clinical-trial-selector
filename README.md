# hackworld-poc
Proof of Concept for HackTheWorld

### Clone the Repo
```bash
git clone https://github.com/neeyanthkvk/hackworld-poc.git
```

### Working on git branch
```bash
git checkout -b <branch_name>
git add <files>
git commit -m '<commit message>'
git push origin <branch_name>
```
- Make sure to submit your pull request. 

### Setup Virtual environment
```bash
pip install virtualenv
virtualenv -p python3.5 <env_name>
source activate <env_name>/bin/activate
```

### Install requirements
```bash
pip install -r requirements.txt
```

### Run locally

```bash
cd path_to/hackworl_poc
python authenticate_ouath2.py
```

- Use [bcda url](https://bcda.cms.gov/sandbox/user-guide/) and get Client ID and Client Secret 