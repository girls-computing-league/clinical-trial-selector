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
            units=["g/dL"]),
        LabTest("platelets", 
            aliases=["plt", "platelet count"], 
            loincs=["777-3"], 
            units=["cells/microliter"])
    ]
    by_name: dict = {}
    by_alias: dict = {}
    by_loinc: dict = {}
    alias_regex: dict = {}
    criteria_regex: dict = {}

    _all_aliases: list = []

    @classmethod
    def create_maps(cls):
        for test in cls.tests:
            cls.by_name[test.name] = test
            cls._all_aliases.extend(test.aliases)
            for alias in test.aliases:
                cls.by_alias[alias] = test
            for loinc in test.loincs:
                cls.by_loinc[loinc] = test

    @classmethod
    def create_regex(cls):
        alias_pattern  = f"({'|'.join(cls._all_aliases)})"
        cls.alias_regex = re.compile(alias_pattern, re.IGNORECASE)
        abbreviation_pattern = "(?:\(\w+\))?"
        compare_pattern = "(<|<=|=|>=|>|≥)"
        number_pattern = "(\d+(?:,\d{3})*(?:.\d*)?)"
        combined_pattern = "\s*".join([alias_pattern, abbreviation_pattern, compare_pattern, number_pattern])
        cls.criteria_regex = re.compile(f"({combined_pattern})", re.IGNORECASE)
    
labs.create_maps()
labs.create_regex()