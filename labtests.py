import re
from typing import Dict, List, Set, Pattern

class LabTest:

    def __init__(self, name: str, aliases: List[str] = [], loincs: List[str] = [], units: List[str] = []):
        self.name = name
        self.aliases: Set[str] = set(aliases)
        self.aliases.add(name)
        self.loincs: Set[str] = set(loincs)
        self.units: Set[str] = set(units)

class labs:
    tests: List[LabTest] = [
        LabTest("hemoglobin", 
            aliases=["hgb"], 
            loincs=["718-7"], 
            units=["g/dl", "gm/dl", "g/l", "mmol/l", "g/ul", "mg/dl", "gram/deciliter", "gr/dl"]),
        LabTest("leukocytes",
            aliases = ["white blood", 
                "wbc", 
                "white blood cells", 
                "white blood cell",
                "white blood cell count",
                "white blood count"],
            loincs = ["6690-2"],
            units=["10*3/uL", "/mcL", "/mm^3", "/ul", "cells/mm^3", "/mm(3)", "cells/uL", "/μl", "/ μl", "k/mcL", "x 10^9/l", "x 10^6 cells/ml"]),
        LabTest("platelets", 
            aliases=["plt", "platelet", "platelet count"], 
            loincs=["777-3"],
            units=["cells/microliter", "10*3/uL", "/mcL", "/mm^3", "/ul", "cells/mm^3", "/mm(3)", "cells/uL", "/μl", "/ μl", "K/mcL", "x 10^9/l", "x 10^6 cells/ml", "/microliter", "x 109/L", "platelet/mm^3", "k/ul", "/mm3", "cell/ul", "/microl", "x 10E3/µL", "/mm³", "per mm^3"])
    ]
    by_name: dict = {}
    by_alias: dict = {}
    by_loinc: Dict[str, LabTest] = {}
    alias_regex: Pattern
    criteria_regex: Pattern

    _all_aliases: list = []

    @classmethod
    def create_maps(cls) -> None:
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
        equality_pattern = "(?:\:|of|is|must be|value|level|level of|count|counts)?"
        compare_pattern = "(<|<=|=<|=|>=|=>|>|≥|greater than|less than|greater than or equal to|above|more than|less than|more than or equal to|less than or equal to)"
        number_pattern = "(\d+(?:,\d{3})*(?:.\d+)?)"
        unit_pattern = "(\S+\s+\S+\s+\S+)"
        combined_pattern = "\s*".join([alias_pattern, abbreviation_pattern, equality_pattern, compare_pattern, number_pattern, unit_pattern])
        cls.criteria_regex = re.compile(f"({combined_pattern})", re.IGNORECASE)
    
labs.create_maps()
labs.create_regex()