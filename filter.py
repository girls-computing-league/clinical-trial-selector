import logging
import subprocess
import os
import json


value_dict = {
    "ecog": {
    "#variable_id": 100,
    "variable_type": "ordinal",
    "variable_name": "ecog",
    "display_name": "ECOG",
    "aliases": "ecog|eastern cooperative oncology group|ecog performance grade|ecog performance status|ecog ps|eastern cooperative oncology group performance status",
    "bounds": "0|1|2|3|4",
    "default_unit_name": "first_default",
    "question": "What is your ECOG performance status?"
  },
  "gleason_score": {
    "#variable_id": 101,
    "variable_type": "ordinal",
    "variable_name": "gleason_score",
    "display_name": "Gleason score",
    "aliases": "gleason|gleason score|gleason grade",
    "bounds": "1|2|3|4|5|6|7|8|9|10",
    "default_unit_name": "",
    "question": "What is your Gleason score?"
  },
  "nyha": {
    "#variable_id": 102,
    "variable_type": "ordinal",
    "variable_name": "nyha",
    "display_name": "NYHA",
    "aliases": "nyha|new york heart association|new york heart association classification",
    "bounds": "1|2|3|4",
    "default_unit_name": "",
    "question": "What is your NYHA class?"
  },
  "cps": {
    "#variable_id": 103,
    "variable_type": "ordinal",
    "variable_name": "cps",
    "display_name": "Child-Pugh score",
    "aliases": "child pugh|child-pugh|child-pugh score",
    "bounds": "5|6|7|8|9|10|11|12|13|14|15",
    "default_unit_name": "",
    "question": "What is your Child-Pugh score?"
  },
  "fitzpatrick_skin_type": {
    "#variable_id": 104,
    "variable_type": "ordinal",
    "variable_name": "fitzpatrick_skin_type",
    "display_name": "Fitzpatrick skin type",
    "aliases": "fitzpatrick skin type*|Fitzpatrick phototype*|fitzpatrick",
    "bounds": "1|2|3|4|5|6",
    "default_unit_name": "",
    "question": "What is your Fitzpatrick skin type?"
  },
  "fitzpatrick_wrinkle_scale": {
    "#variable_id": 105,
    "variable_type": "ordinal",
    "variable_name": "fitzpatrick_wrinkle_scale",
    "display_name": "Fitzpatrick wrinkle scale",
    "aliases": "fitzpatrick wrinkle",
    "bounds": "1|2|3|4|5|6|7|8|9",
    "default_unit_name": "",
    "question": "What is your Fitzpatrick wrinkle scale?"
  },
  "age": {
    "#variable_id": 200,
    "variable_type": "numerical",
    "variable_name": "age",
    "display_name": "Age",
    "aliases": "age|ages|aged",
    "bounds": "0.0|120.0",
    "default_unit_name": "year",
    "question": "How old are you?"
  },
  "height": {
    "#variable_id": 201,
    "variable_type": "numerical",
    "variable_name": "height",
    "display_name": "Height",
    "aliases": "heigh*",
    "bounds": "0.0|500.0",
    "default_unit_name": "",
    "question": "What is your height?"
  },
  "weight": {
    "#variable_id": 202,
    "variable_type": "numerical",
    "variable_name": "weight",
    "display_name": "Weight",
    "aliases": "weigh*|body weigh*",
    "bounds": "0.0|300.0",
    "default_unit_name": "",
    "question": "What is your weight?"
  },
  "bmi": {
    "#variable_id": 203,
    "variable_type": "numerical",
    "variable_name": "bmi",
    "display_name": "BMI",
    "aliases": "bmi|body mass index",
    "bounds": "0.0|100.0",
    "default_unit_name": "kg/m2",
    "question": "What is your BMI?"
  },
  "waist_circumference": {
    "#variable_id": 204,
    "variable_type": "numerical",
    "variable_name": "waist_circumference",
    "display_name": "Waist circumference",
    "aliases": "waist|waist circumference",
    "bounds": "0.0|200.0",
    "default_unit_name": "",
    "question": "What is your waist circumference?"
  },
  "arm_circumference": {
    "#variable_id": 205,
    "variable_type": "numerical",
    "variable_name": "arm_circumference",
    "display_name": "Arm circumference",
    "aliases": "arm_circumference",
    "bounds": "1.0|100.0",
    "default_unit_name": "",
    "question": "What is your arm circumference?"
  },
  "life_expectancy": {
    "#variable_id": 206,
    "variable_type": "numerical",
    "variable_name": "life_expectancy",
    "display_name": "Life expectancy",
    "aliases": "life expectancy",
    "bounds": "0.0|120.0",
    "default_unit_name": "",
    "question": "What is your life expectancy?"
  },
  "body_temperature": {
    "#variable_id": 207,
    "variable_type": "numerical",
    "variable_name": "body_temperature",
    "display_name": "Body temperature",
    "aliases": "temperature|temperature measurement|fever",
    "bounds": "10.0|120",
    "default_unit_name": "",
    "question": "What is your body temperature?"
  },
   "daily_opioid_dose": {
    "#variable_id": 208,
    "variable_type": "numerical",
    "variable_name": "daily_opioid_dose",
    "display_name": "Daily opioid dose",
    "aliases": "daily opioid dose",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your daily opioid dose?"
  },
  "sbp": {
    "#variable_id": 300,
    "variable_type": "numerical",
    "variable_name": "sbp",
    "display_name": "SBP",
    "aliases": "sbp|systolic blood pressure|systolic bp|systolic",
    "bounds": "10.0|300.0",
    "default_unit_name": "mmhg",
    "question": "What is your blood pressure?"
  },
  "dbp": {
    "#variable_id": 301,
    "variable_type": "numerical",
    "variable_name": "dbp",
    "display_name": "DBP",
    "aliases": "dbp|diastolic blood pressure|diastolic bp|diastolic",
    "bounds": "10.0|150.0",
    "default_unit_name": "mmhg",
    "question": "What is your blood pressure?"
  },
  "sbp/dbp": {
    "#variable_id": 302,
    "variable_type": "numerical",
    "variable_name": "sbp/dbp",
    "display_name": "Blood pressure",
    "aliases": "bp|blood pressure",
    "bounds": "10.0|300.0",
    "default_unit_name": "mmgh",
    "question": "What is your blood pressure?"
  },
  "lvef": {
    "#variable_id": 303,
    "variable_type": "numerical",
    "variable_name": "lvef",
    "display_name": "LVEF",
    "aliases": "lvef|left ventricular ejection fraction|cardiac ejection fraction",
    "bounds": "0.0|100.0",
    "default_unit_name": "%",
    "question": "What is your left ventricular ejection fraction?"
  },
  "cqt": {
    "#variable_id": 304,
    "variable_type": "numerical",
    "variable_name": "cqt",
    "display_name": "cQT",
    "aliases": "corrected qt interval|qtc interval|qtc",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your corrected QT interval?"
  },
  "troponin_level": {
    "#variable_id": 305,
    "variable_type": "numerical",
    "variable_name": "troponin_level",
    "display_name": "Troponin level",
    "aliases": "troponin level|serum tropinin|troponin",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your troponin level?"
  },
  "a1c": {
    "#variable_id": 400,
    "variable_type": "numerical",
    "variable_name": "a1c",
    "display_name": "A1c",
    "aliases": "a1c|hba1c|hgba1c|hga1c|hgb-a1c|hemoglobin a1c|glycosylated hemoglobin|glycated hemoglobin|glycohemoglobin|hga1c blood test",
    "bounds": "0.0|15.0",
    "default_unit_name": "%",
    "question": "What is your hemoglobin A1c?"
  },
  "fasting_blood_sugar_level": {
    "#variable_id": 401,
    "variable_type": "numerical",
    "variable_name": "fasting_blood_sugar_level",
    "display_name": "Fasting blood sugar level",
    "aliases": "blood sugar level*|blood sugar|plasma glucose level*|blood glucose level*|plasma glucose|fasting plasma glucose|fasting glucose|fpg",
    "bounds": "0.0|1000.0",
    "default_unit_name": "",
    "question": "What is your fasting blood sugar level?"
  },
  "fructosamine": {
    "#variable_id": 402,
    "variable_type": "numerical",
    "variable_name": "fructosamine",
    "display_name": "Fructosamine",
    "aliases": "fructosamine|serum fructosamine",
    "bounds": "1.0|1000.0",
    "default_unit_name": "",
    "question": "What is your fructosamine level?"
  },
  "hb_count": {
    "#variable_id": 403,
    "variable_type": "numerical",
    "variable_name": "hemoglobin",
    "display_name": "Hb count",
    "aliases": "hemoglobin count|hb count|hemoglobin concentration|hemoglobin level*|hgb|hb|hemoglobin",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your hemoglobin count?"
  },
  "wbc": {
    "#variable_id": 404,
    "variable_type": "numerical",
    "variable_name": "leukocytes",
    "display_name": "WBC",
    "aliases": "wbc|white blood cell count|white blood cell|leukocytes|leucocytes|leukopenia",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your white blood cell count?"
  },
  "platelet_count": {
    "#variable_id": 405,
    "variable_type": "numerical",
    "variable_name": "platelets",
    "display_name": "Platelet count",
    "aliases": "platelet count|platelet|platelets",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your platelet count?"
  },
  "potassium_level": {
    "#variable_id": 406,
    "variable_type": "numerical",
    "variable_name": "potassium_level",
    "display_name": "Potassium level",
    "aliases": "potassium|potassium level",
    "bounds": "0.0|15.0",
    "default_unit_name": "",
    "question": "What is your potassium level?"
  },
  "total_bilirubin_level": {
    "#variable_id": 407,
    "variable_type": "numerical",
    "variable_name": "total_bilirubin_level",
    "display_name": "Bilirubin level",
    "aliases": "bilirubin",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your total bilirubin level?"
  },
  "anc": {
    "#variable_id": 408,
    "variable_type": "numerical",
    "variable_name": "anc",
    "display_name": "ANC",
    "aliases": "anc|absolute neutrophil count|neutrocyte count|absolute neutrophil|blood neutrophil|neutrophil|neutrophils|neutrocytes|heterophils",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your absolute neutrophil count?"
  },
  "bal": {
    "#variable_id": 409,
    "variable_type": "numerical",
    "variable_name": "bal",
    "display_name": "BAL",
    "aliases": "bal|blood albumin level|serum albumin|albumin",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your blood albumin level?"
  },
  "urinary_albumin": {
    "#variable_id": 410,
    "variable_type": "numerical",
    "variable_name": "urinary_albumin",
    "display_name": "Urinary albumin",
    "aliases": "urinary albumin level|urinary albumin",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your urinary albumin level?"
  },
  "ast": {
    "#variable_id": 411,
    "variable_type": "numerical",
    "variable_name": "ast",
    "display_name": "AST",
    "aliases": "ast|aspartate aminotransferase|sgot",
    "bounds": "0.0|20.0",
    "default_unit_name": "",
    "question": "What are your ALT and AST values?"
  },
  "alt": {
    "#variable_id": 412,
    "variable_type": "numerical",
    "variable_name": "alt",
    "display_name": "ALT",
    "aliases": "alt|alanine aminotransferase|sgpt",
    "bounds": "0.0|20.0",
    "default_unit_name": "",
    "question": "What are your ALT and AST values?"
  },
  "ast/alt": {
    "#variable_id": 413,
    "variable_type": "numerical",
    "variable_name": "ast/alt",
    "display_name": "AST/ALT",
    "aliases": "ast/alt|asat/alat|sgot/sgpt|ast and alt|ast or alt|sgot or sgpt|aspartate aminotransferase or alanine aminotransferase",
    "bounds": "0.0|20.0",
    "default_unit_name": "",
    "question": "What are your ALT and AST values?"
  },
  "ast_alt_ratio": {
    "#variable_id": 414,
    "variable_type": "numerical",
    "variable_name": "ast_alt_ratio",
    "display_name": "AST/ALT ratio",
    "aliases": "ast/alt ratio|sgot/sgpt ratio",
    "bounds": "0.0|20.0",
    "default_unit_name": "",
    "question": "What is your AST/ALT ratio?"
  },
  "creatinine_level": {
    "#variable_id": 415,
    "variable_type": "numerical",
    "variable_name": "creatinine_level",
    "display_name": "Creatinine level",
    "aliases": "serum creatinine|creatinine|creatinine level",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your creatinine level?"
  },
  "calculated_creatinine_clearance": {
    "#variable_id": 416,
    "variable_type": "numerical",
    "variable_name": "calculated_creatinine_clearance",
    "display_name": "Calculated creatinine clearance",
    "aliases": "crcl|creatinine clearance|calculated creatinine clearance|cr clearance|cockcroft-gault",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your calculated creatinine clearance?"
  },
  "testosterone_level": {
    "#variable_id": 417,
    "variable_type": "numerical",
    "variable_name": "testosterone_level",
    "display_name": "Testosterone level",
    "aliases": "testosterone level|castrate testosterone level|castrate levels of testosterone|castrate level of serum testosterone|baseline testosterone|serum testosterone|serum total testosterone concentration",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your castrate testosterone level?"
  },
  "glomerular_filtration_rate": {
    "#variable_id": 418,
    "variable_type": "numerical",
    "variable_name": "glomerular_filtration_rate",
    "display_name": "Glomerular filtration rate",
    "aliases": "gfr|egfr|glomerular filtration rate|estimated glomerular filtration rate",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your estimated glomerular filtration rate?"
  },
  "aec": {
    "#variable_id": 419,
    "variable_type": "numerical",
    "variable_name": "aec",
    "display_name": "AEC",
    "aliases": "absolute eosinophil count|aec",
    "bounds": "0.0|10000",
    "default_unit_name": "",
    "question": "What is your absolute eosinophil count?"
  },
  "lfts": {
    "#variable_id": 420,
    "variable_type": "numerical",
    "variable_name": "lfts",
    "display_name": "LFTs",
    "aliases": "liver function tests|lfts|lfs",
    "bounds": "",
    "default_unit_name": "",
    "question": "What are your liver function tests?"
  },
  "ferritin_level": {
    "#variable_id": 421,
    "variable_type": "numerical",
    "variable_name": "ferritin_level",
    "display_name": "Ferritin level",
    "aliases": "ferritin",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your ferretin level?"
  },
  "magnesium_level": {
    "#variable_id": 422,
    "variable_type": "numerical",
    "variable_name": "magnesium_level",
    "display_name": "Magnesium level",
    "aliases": "magnesium|magnesium level",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your magnesium level?"
  },
  "calcium_level": {
    "#variable_id": 423,
    "variable_type": "numerical",
    "variable_name": "calcium_level",
    "display_name": "Calcium level",
    "aliases": "calcium|calcium level",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your calcium level?"
  },
  "total_cholesterol": {
    "#variable_id": 500,
    "variable_type": "numerical",
    "variable_name": "total_cholesterol",
    "display_name": "Total cholesterol",
    "aliases": "plasma total cholesterol|total cholesterol|serum cholesterol|cholesterol",
    "bounds": "0.0|500.0",
    "default_unit_name": "",
    "question": "What is your total cholesterol level?"
  },
  "ldl_cholesterol": {
    "#variable_id": 501,
    "variable_type": "numerical",
    "variable_name": "ldl_cholesterol",
    "display_name": "LDL cholesterol",
    "aliases": "ldl|ldl-cholesterol|ldl cholesterol|ldl-c|low-density lipoprotein cholesterol|low density lipoprotein cholesterol",
    "bounds": "0.0|500.0",
    "default_unit_name": "",
    "question": "What is your LDL cholesterol level?"
  },
  "hdl_cholesterol": {
    "#variable_id": 502,
    "variable_type": "numerical",
    "variable_name": "hdl_cholesterol",
    "display_name": "HDL cholesterol",
    "aliases": "hdl|hdl-cholesterol|hdl cholesterol|hdl-c|high-density lipoprotein cholesterol|high density lipoprotein cholesterol",
    "bounds": "0.0|500.0",
    "default_unit_name": "",
    "question": "What is your HDL cholesterol level?"
  },
  "non_hdl_cholesterol": {
    "#variable_id": 503,
    "variable_type": "numerical",
    "variable_name": "non_hdl_cholesterol",
    "display_name": "Non-HDL cholesterol",
    "aliases": "non-hdl-cholesterol|non-hdl cholesterol|non-hdl-c|non-high-density lipoprotein cholesterol",
    "bounds": "0.0|500.0",
    "default_unit_name": "",
    "question": "What is your non-HDL cholesterol level?"
  },
  "ldl_hdl_ratio": {
    "#variable_id": 504,
    "variable_type": "numerical",
    "variable_name": "ldl_hdl_ratio",
    "display_name": "LDL/HDL ratio",
    "aliases": "ldl/hdl ratio",
    "bounds": "0.0|10.0",
    "default_unit_name": "",
    "question": "What is your cholesterol LDL/HDL ratio?"
  },
  "fasting_triglyceride_level": {
    "#variable_id": 505,
    "variable_type": "numerical",
    "variable_name": "fasting_triglyceride_level",
    "display_name": "Fasting triglyceride level",
    "aliases": "fasting triglyceride level*|fasting triglyceride*|fasting plasma triglyceride*|fasting blood glucose level*|fasting triglyceride|fasting triglycerides",
    "bounds": "0.0|1000.0",
    "default_unit_name": "",
    "question": "What is your fasting triglyceride level?"
  },
  "triglyceride_level": {
    "#variable_id": 506,
    "variable_type": "numerical",
    "variable_name": "triglyceride_level",
    "display_name": "Triglyceride level",
    "aliases": "triglyceride level*|triglyceride*|plasma triglyceride*|blood glucose level*|triglyceride|triglycerides",
    "bounds": "0.0|1000.0",
    "default_unit_name": "",
    "question": "What is your triglyceride level?"
  },
  "karnofsky_score": {
    "#variable_id": 600,
    "variable_type": "numerical",
    "variable_name": "karnofsky_score",
    "display_name": "Karnofsky score",
    "aliases": "kps|karnofsky|karnofsky performance score|karnofsky score|lansky|lansky score",
    "bounds": "0.0|100.0",
    "default_unit_name": "",
    "question": "What is your Karnofsky score?"
  },
  "fish_ratio": {
    "#variable_id": 601,
    "variable_type": "numerical",
    "variable_name": "fish_ratio",
    "display_name": "FISH ratio",
    "aliases": "fish ratio",
    "bounds": "0.0|10.0",
    "default_unit_name": "",
    "question": "What is your FISH ratio?"
  },
  "psa_level": {
    "#variable_id": 602,
    "variable_type": "numerical",
    "variable_name": "psa_level",
    "display_name": "PSA",
    "aliases": "psa|prostate specific antigen|prostate-specific antigen|psa progression",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your PSA level?"
  },
  "tumor_size": {
    "#variable_id": 603,
    "variable_type": "numerical",
    "variable_name": "tumor_size",
    "display_name": "Tumor size",
    "aliases": "tumor size",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your tumor size?"
  },
  "lesion_size": {
    "#variable_id": 604,
    "variable_type": "numerical",
    "variable_name": "lesion_size",
    "display_name": "Lesion size",
    "aliases": "lesion size",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your lesion size?"
  },
  "inr": {
    "#variable_id": 700,
    "variable_type": "numerical",
    "variable_name": "inr",
    "display_name": "INR",
    "aliases": "international normalized ratio|inr",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your international normalized ratio?"
  },
  "iop": {
    "#variable_id": 800,
    "variable_type": "numerical",
    "variable_name": "iop",
    "display_name": "IOP",
    "aliases": "intraocular pressure|iop",
    "bounds": "0.0|50.0",
    "default_unit_name": "",
    "question": "What is your intraocular pressure?"
  },
  "respiratory_rate": {
    "#variable_id": 900,
    "variable_type": "numerical",
    "variable_name": "respiratory_rate",
    "display_name": "Respiratory rate",
    "aliases": "respiratory rate|respiratory frequency|rr",
    "bounds": "",
    "default_unit_name": "breaths/min",
    "question": "What is your respiratory rate?"
  },
  "heart_rate": {
    "#variable_id": 901,
    "variable_type": "numerical",
    "variable_name": "heart_rate",
    "display_name": "Heart rate",
    "aliases": "heart rate|hr",
    "bounds": "",
    "default_unit_name": "beats/min",
    "question": "What is your heart rate?"
  },
  "po2": {
    "#variable_id": 902,
    "variable_type": "numerical",
    "variable_name": "po2",
    "display_name": "pO2",
    "aliases": "po2|partial presure of oxygen",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your pO2?"
  },
  "spo2": {
    "#variable_id": 903,
    "variable_type": "numerical",
    "variable_name": "spo2",
    "display_name": "SpO2",
    "aliases": "spo2|oxygen saturation",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your SpO2?"
  },
  "pf_ratio": {
    "#variable_id": 904,
    "variable_type": "numerical",
    "variable_name": "pf_ratio",
    "display_name": "P/F ratio",
    "aliases": "p/f ratio|pao2/fio2|pao2/fio2 ratio|partial pressure of oxygen/oxygen concentration|partial pressure of oxygen/fraction of inspired oxygen|partial pressure of arterial oxygen to fraction of inspired oxygen ratio",
    "bounds": "",
    "default_unit_name": "mmhg",
    "question": "What is your P/F ratio?"
  },
  "peep": {
    "#variable_id": 905,
    "variable_type": "numerical",
    "variable_name": "peep",
    "display_name": "PEEP",
    "aliases": "positive end-expiratory pressure|positive end expiratory pressure|peep",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is the PEEP value?"
  },
  "sofa": {
    "#variable_id": 906,
    "variable_type": "numerical",
    "variable_name": "sofa",
    "display_name": "SOFA",
    "aliases": "sofa|sequential organ failure assessment score",
    "bounds": "0|24",
    "default_unit_name": "",
    "question": "What is your SOFA score?"
  },
  "news2_score": {
    "#variable_id": 907,
    "variable_type": "numerical",
    "variable_name": "news2_score",
    "display_name": "NEWS-2 score",
    "aliases": "news-2 score|news 2|news-2",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your NEWS-2 score?"
  },
  "d_dimer_level": {
    "#variable_id": 908,
    "variable_type": "numerical",
    "variable_name": "d_dimer_level",
    "display_name": "D-dimer level",
    "aliases": "d-dimer|d dimer",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your D-dimer level?"
  },
  "c_reactive_protein_level": {
    "#variable_id": 909,
    "variable_type": "numerical",
    "variable_name": "c_reactive_protein_level",
    "display_name": "C-reactive protein level",
    "aliases": "c-reactive protein|crp",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your C-reactive protein level?"
  },
  "lactate_dehydrogenase_level": {
    "#variable_id": 910,
    "variable_type": "numerical",
    "variable_name": "lactate_dehydrogenase_level",
    "display_name": "Lactate dehydrogenase level",
    "aliases": "lactate dehydrogenase|ldh",
    "bounds": "",
    "default_unit_name": "",
    "question": "What is your lactate dehydrogenase level?"
  },
  "pulmonary_infiltrate_level": {
    "#variable_id": 911,
    "variable_type": "numerical",
    "variable_name": "pulmonary_infiltrate_level",
    "display_name": "Pulmonary infiltrate",
    "aliases": "pulmonary infiltrate|lung infiltrates",
    "bounds": "",
    "default_unit_name": "unit",
    "question": "What is your pulmonary infiltrate level?"
  }
}

reverse_value_dict = dict([(value_dict[lab]["display_name"],lab) for lab in value_dict])


class TestFilter:

    def __init__(self):
        pass


class FacebookFilter:
    def __init__(self, mode):
        self.mode = mode

    def generate_results(self, trial):
        logging.info(f"Parsing trial {trial.id}")
        input_line = "parser_io/inputs/" + trial.id + ".csv"
        output_line = "parser_io/outputs/" + trial.id + ".csv"

        header = "#nct_id,title,has_us_facility,conditions,eligibility_criteria"
        trial_info = trial.id + "," + trial.title + ",false,disease," + trial.eligibility_combined
        print(header + "\n" + trial_info, file=open(input_line, "w"))

        command_line = ['parser_io/cfg', '-conf', 'parser_io/cfg.conf', '-o', output_line,
                        '-i', input_line]

        subprocess.run(command_line)

    def filter_trial(self, trial, patient_data) -> bool:
        logging.info(patient_data)
        output_line = "parser_io/outputs/" + trial.id + ".csv"
        if trial.eligibility_combined == "" or trial.eligibility_combined is None:
            return True
        if not os.path.exists(output_line):
            self.generate_results(trial)
        else:
            logging.info(f"Cached parsed trial {trial.id}")

        obj = {}
        elg = True
        if os.path.exists(output_line):
            with open(output_line, "r") as output_csv:
                output_csv_lines = output_csv.readlines()
                output_split = [line.split("\t") for line in output_csv_lines]

                for i in range(len(output_split[0])):
                    obj[output_split[0][i].strip()] = [split[i] for split in output_split[1:]]

                for i in range(len(output_split) - 1):
                    var_type = obj['variable_type'][i]
                    json_obj = json.loads(obj['relation'][i])
                    consists = True
                    found = False
                    filter_condition = ""

                    for value_type in value_dict:
                        if value_dict[value_type]['variable_name'] not in patient_data:
                            continue
                        if json_obj['name'] == value_type:
                            found = True
                            filter_condition += value_dict[value_type]['display_name'] + ": "
                            lab_val = patient_data[value_dict[value_type]['variable_name']]
                            if var_type == 'numerical':
                                if 'lower' in json_obj:
                                    val = float(json_obj['lower']['value'].replace(' ', ''))
                                    filter_condition += "Must be greater than " + str(val) + ". "
                                    if json_obj['lower']['incl'] and float(lab_val) < val:
                                        consists = False
                                    if not json_obj['lower']['incl'] and float(lab_val) <= val:
                                        consists = False
                                if 'upper' in json_obj:
                                    val = float(json_obj['upper']['value'].replace(' ', ''))
                                    filter_condition += "Must be less than " + str(val) + ". "
                                    if json_obj['upper']['incl'] and float(lab_val) > val:
                                        consists = False
                                    if not json_obj['upper']['incl'] and float(lab_val) >= val:
                                        consists = False
                            elif var_type == 'ordinal':
                                allowed_values = [float(val.replace(' ', '')) for val in json_obj.value]
                                filter_condition += "Must be one of: " + ", ".join(
                                    [str(value) for value in allowed_values])
                                if float(lab_val) not in allowed_values:
                                    consists = False

                    if not found:
                        continue

                    if not consists:
                        elg = False

                    trial.filter_condition.append((filter_condition, consists))
        if elg:
            logging.info('passed')
            return True
        else:
            logging.info('not passed')
            return False
