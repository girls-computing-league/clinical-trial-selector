class LabTest:

    def __init__(self, name: str, aliases=[], loincs=[], units=[]):
        self.name = name
        self.aliases = set(aliases)
        self.aliases.add(name)
        self.loincs = set(loincs)
        self.units = set(units)

class labs:
    tests = [
        LabTest("hemoglobin", aliases=["hgb"], loincs=["1234"], units=["mg/dl"]),
        LabTest("platelets", aliases=["plt"], loincs=["2345"], units=["cells/microliter"])
    ]
    by_name = {}
    by_alias = {}
    by_loinc = {}

    @classmethod
    def create_maps(cls):
        for test in cls.tests:
            cls.by_name[test.name] = test
            for alias in test.aliases:
                cls.by_alias[alias] = test
            for loinc in test.loincs:
                cls.by_loinc[loinc] = test

labs.create_maps()
