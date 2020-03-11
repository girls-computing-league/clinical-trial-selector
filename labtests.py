import re

class LabTest:

    def __init__(self, name: str, aliases=[], loincs=[], units=[]):
        self.name = name
        self.aliases = set(aliases)
        self.aliases.add(name)
        self.loincs = set(loincs)
        self.units = set(units)

class labs:
    tests = [
        LabTest("hemoglobin", 
            aliases=["hgb"], 
            loincs=["718-7"], 
            units=["mg/dl"]),
        LabTest("platelets", 
            aliases=["plt", "platelet count"], 
            loincs=["777-3"], 
            units=["cells/microliter"])
    ]
    by_name = {}
    by_alias = {}
    by_loinc = {}
    alias_regex = {}

    @classmethod
    def create_maps(cls):
        all_aliases = []
        for test in cls.tests:
            cls.by_name[test.name] = test
            all_aliases.extend(test.aliases)
            for alias in test.aliases:
                cls.by_alias[alias] = test
            for loinc in test.loincs:
                cls.by_loinc[loinc] = test
        cls.alias_regex = re.compile(f"({'|'.join(all_aliases)})")
    
labs.create_maps()
