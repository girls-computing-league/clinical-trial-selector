import logging
import subprocess
import os
import json

l1 = ['ecog', 'gleason_score', 'nyha', 'cps', 'fitzpatrick_skin_type', 'fitzpatrick_wrinkle_scale', 'age', 'height', 'weight', 'bmi', 'waist_circumference', 'arm_circumference', 'life_expectancy', 'body_temperature', 'daily_opioid_dose', 'sbp', 'dbp', 'sbp/dbp', 'lvef', 'cqt', 'troponin_level', 'a1c', 'fasting_blood_sugar_level', 'fructosamine', 'hb_count', 'wbc', 'platelet_count', 'potassium_level', 'total_bilirubin_level', 'anc', 'bal', 'urinary_albumin', 'ast', 'alt', 'ast/alt', 'ast_alt_ratio', 'creatinine_level', 'calculated_creatinine_clearance', 'testosterone_level', 'glomerular_filtration_rate', 'aec', 'lfts', 'ferritin_level', 'magnesium_level', 'calcium_level', 'total_cholesterol', 'ldl_cholesterol', 'hdl_cholesterol', 'non_hdl_cholesterol', 'ldl_hdl_ratio', 'fasting_triglyceride_level', 'triglyceride_level', 'karnofsky_score', 'fish_ratio', 'psa_level', 'tumor_size', 'lesion_size', 'inr', 'iop', 'respiratory_rate', 'heart_rate', 'po2', 'spo2', 'pf_ratio', 'peep', 'sofa', 'news2_score', 'd_dimer_level', 'c_reactive_protein_level', 'lactate_dehydrogenase_level', 'pulmonary_infiltrate_level']
l2 = ['ECOG', 'Gleason score', 'NYHA', 'Child-Pugh score', 'Fitzpatrick skin type', 'Fitzpatrick wrinkle scale', 'Age', 'Height', 'Weight', 'BMI', 'Waist circumference', 'Arm circumference', 'Life expectancy', 'Body temperature', 'Daily opioid dose', 'SBP', 'DBP', 'Blood pressure', 'LVEF', 'cQT', 'Troponin level', 'A1c', 'Fasting blood sugar level', 'Fructosamine', 'Hb count', 'WBC', 'Platelet count', 'Potassium level', 'Bilirubin level', 'ANC', 'BAL', 'Urinary albumin', 'AST', 'ALT', 'AST/ALT', 'AST/ALT ratio', 'Creatinine level', 'Calculated creatinine clearance', 'Testosterone level', 'Glomerular filtration rate', 'AEC', 'LFTs', 'Ferritin level', 'Magnesium level', 'Calcium level', 'Total cholesterol', 'LDL cholesterol', 'HDL cholesterol', 'Non-HDL cholesterol', 'LDL/HDL ratio', 'Fasting triglyceride level', 'Triglyceride level', 'Karnofsky score', 'FISH ratio', 'PSA', 'Tumor size', 'Lesion size', 'INR', 'IOP', 'Respiratory rate', 'Heart rate', 'pO2', 'SpO2', 'P/F ratio', 'PEEP', 'SOFA', 'NEWS-2 score', 'D-dimer level', 'C-reactive protein level', 'Lactate dehydrogenase level', 'Pulmonary infiltrate']

value_dict = {
    "ecog": {
        "results_key": "ecog",
        "name": "ECOG"
    },
    "gleason_score": {
        "results_key": "gleason_score",
        "name": "Gleason score"
    },
    "nyha": {
        "results_key": "nyha",
        "name": "NYHA"
    },
    "cps": {
        "results_key": "cps",
        "name": "Child-Pugh score"
    },
    "fitzpatrick_skin_type": {
        "results_key": "fitzpatrick_skin_type",
        "name": "Fitzpatrick skin type"
    },
    "fitzpatrick_wrinkle_scale": {
        "results_key": "fitzpatrick_wrinkle_scale",
        "name": "Fitzpatrick wrinkle scale"
    },
    "age": {
        "results_key": "age",
        "name": "Age"
    },
    "height": {
        "results_key": "height",
        "name": "Height"
    },
    "weight": {
        "results_key": "weight",
        "name": "Weight"
    },
    "bmi": {
        "results_key": "bmi",
        "name": "BMI"
    },
    "waist_circumference": {
        "results_key": "waist_circumference",
        "name": "Waist circumference"
    },
    "arm_circumference": {
        "results_key": "arm_circumference",
        "name": "Arm circumference"
    },
    "life_expectancy": {
        "results_key": "life_expectancy",
        "name": "Life expectancy"
    },
    "body_temperature": {
        "results_key": "body_temperature",
        "name": "Body temperature"
    },
    "daily_opioid_dose": {
        "results_key": "daily_opioid_dose",
        "name": "Daily opioid dose"
    },
    "sbp": {
        "results_key": "sbp",
        "name": "SBP"
    },
    "dbp": {
        "results_key": "dbp",
        "name": "DBP"
    },
    "sbp/dbp": {
        "results_key": "sbp/dbp",
        "name": "Blood pressure"
    },
    "lvef": {
        "results_key": "lvef",
        "name": "LVEF"
    },
    "cqt": {
        "results_key": "cqt",
        "name": "cQT"
    },
    "troponin_level": {
        "results_key": "troponin_level",
        "name": "Troponin level"
    },
    "a1c": {
        "results_key": "a1c",
        "name": "A1c"
    },
    "fasting_blood_sugar_level": {
        "results_key": "fasting_blood_sugar_level",
        "name": "Fasting blood sugar level"
    },
    "fructosamine": {
        "results_key": "fructosamine",
        "name": "Fructosamine"
    },
    "hb_count": {
        "results_key": "hemoglobin",
        "name": "Hb count"
    },
    "wbc": {
        "results_key": "leukocytes",
        "name": "WBC"
    },
    "platelet_count": {
        "results_key": "platelets",
        "name": "Platelet count"
    },
    "potassium_level": {
        "results_key": "potassium_level",
        "name": "Potassium level"
    },
    "total_bilirubin_level": {
        "results_key": "total_bilirubin_level",
        "name": "Bilirubin level"
    },
    "anc": {
        "results_key": "anc",
        "name": "ANC"
    },
    "bal": {
        "results_key": "bal",
        "name": "BAL"
    },
    "urinary_albumin": {
        "results_key": "urinary_albumin",
        "name": "Urinary albumin"
    },
    "ast": {
        "results_key": "ast",
        "name": "AST"
    },
    "alt": {
        "results_key": "alt",
        "name": "ALT"
    },
    "ast/alt": {
        "results_key": "ast/alt",
        "name": "AST/ALT"
    },
    "ast_alt_ratio": {
        "results_key": "ast_alt_ratio",
        "name": "AST/ALT ratio"
    },
    "creatinine_level": {
        "results_key": "creatinine_level",
        "name": "Creatinine level"
    },
    "calculated_creatinine_clearance": {
        "results_key": "calculated_creatinine_clearance",
        "name": "Calculated creatinine clearance"
    },
    "testosterone_level": {
        "results_key": "testosterone_level",
        "name": "Testosterone level"
    },
    "glomerular_filtration_rate": {
        "results_key": "glomerular_filtration_rate",
        "name": "Glomerular filtration rate"
    },
    "aec": {
        "results_key": "aec",
        "name": "AEC"
    },
    "lfts": {
        "results_key": "lfts",
        "name": "LFTs"
    },
    "ferritin_level": {
        "results_key": "ferritin_level",
        "name": "Ferritin level"
    },
    "magnesium_level": {
        "results_key": "magnesium_level",
        "name": "Magnesium level"
    },
    "calcium_level": {
        "results_key": "calcium_level",
        "name": "Calcium level"
    },
    "total_cholesterol": {
        "results_key": "total_cholesterol",
        "name": "Total cholesterol"
    },
    "ldl_cholesterol": {
        "results_key": "ldl_cholesterol",
        "name": "LDL cholesterol"
    },
    "hdl_cholesterol": {
        "results_key": "hdl_cholesterol",
        "name": "HDL cholesterol"
    },
    "non_hdl_cholesterol": {
        "results_key": "non_hdl_cholesterol",
        "name": "Non-HDL cholesterol"
    },
    "ldl_hdl_ratio": {
        "results_key": "ldl_hdl_ratio",
        "name": "LDL/HDL ratio"
    },
    "fasting_triglyceride_level": {
        "results_key": "fasting_triglyceride_level",
        "name": "Fasting triglyceride level"
    },
    "triglyceride_level": {
        "results_key": "triglyceride_level",
        "name": "Triglyceride level"
    },
    "karnofsky_score": {
        "results_key": "karnofsky_score",
        "name": "Karnofsky score"
    },
    "fish_ratio": {
        "results_key": "fish_ratio",
        "name": "FISH ratio"
    },
    "psa_level": {
        "results_key": "psa_level",
        "name": "PSA"
    },
    "tumor_size": {
        "results_key": "tumor_size",
        "name": "Tumor size"
    },
    "lesion_size": {
        "results_key": "lesion_size",
        "name": "Lesion size"
    },
    "inr": {
        "results_key": "inr",
        "name": "INR"
    },
    "iop": {
        "results_key": "iop",
        "name": "IOP"
    },
    "respiratory_rate": {
        "results_key": "respiratory_rate",
        "name": "Respiratory rate"
    },
    "heart_rate": {
        "results_key": "heart_rate",
        "name": "Heart rate"
    },
    "po2": {
        "results_key": "po2",
        "name": "pO2"
    },
    "spo2": {
        "results_key": "spo2",
        "name": "SpO2"
    },
    "pf_ratio": {
        "results_key": "pf_ratio",
        "name": "P/F ratio"
    },
    "peep": {
        "results_key": "peep",
        "name": "PEEP"
    },
    "sofa": {
        "results_key": "sofa",
        "name": "SOFA"
    },
    "news2_score": {
        "results_key": "news2_score",
        "name": "NEWS-2 score"
    },
    "d_dimer_level": {
        "results_key": "d_dimer_level",
        "name": "D-dimer level"
    },
    "c_reactive_protein_level": {
        "results_key": "c_reactive_protein_level",
        "name": "C-reactive protein level"
    },
    "lactate_dehydrogenase_level": {
        "results_key": "lactate_dehydrogenase_level",
        "name": "Lactate dehydrogenase level"
    },
    "pulmonary_infiltrate_level": {
        "results_key": "pulmonary_infiltrate_level",
        "name": "Pulmonary infiltrate"
    }
}

reverse_value_dict = dict([(value_dict[lab]["name"],lab) for lab in value_dict])


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
                        if value_dict[value_type]['results_key'] not in patient_data:
                            continue
                        if json_obj['name'] == value_type:
                            found = True
                            filter_condition += value_dict[value_type]['name'] + ": "
                            lab_val = patient_data[value_dict[value_type]['results_key']]
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
