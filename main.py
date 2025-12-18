#!/usr/bin/env python3

from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from enum import Enum
import json
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FHIRVersion(Enum):
    R4 = "4.0.1"
    STU3 = "3.0.2"
    DSTU2 = "1.0.2"

class Coding:
    def __init__(self, system: str, code: str, display: Optional[str] = None):
        self.system = system
        self.code = code
        self.display = display
    
    def to_dict(self) -> Dict:
        result = {"system": self.system, "code": self.code}
        if self.display:
            result["display"] = self.display
        return result

class Quantity:
    def __init__(self, value: Decimal, unit: str, system: Optional[str] = None, code: Optional[str] = None):
        self.value = value
        self.unit = unit
        self.system = system
        self.code = code
    
    def to_dict(self) -> Dict:
        result = {"value": float(self.value), "unit": self.unit}
        if self.system:
            result["system"] = self.system
        if self.code:
            result["code"] = self.code
        return result

class FHIRGenerator:
    def __init__(self, fhir_version: FHIRVersion = FHIRVersion.R4):
        self.fhir_version = fhir_version
        self.resources = []
    
    def _generate_id(self) -> str:
        return str(uuid.uuid4())
    
    def _format_date(self, dt: date) -> str:
        return dt.isoformat()
    
    def _format_datetime(self, dt: datetime) -> str:
        return dt.isoformat()
    
    def create_patient(self, patient_id: str, name: str, birth_date: date, gender: str) -> Dict:
        name_parts = name.split()
        given = name_parts[:-1] if len(name_parts) > 1 else [name]
        family = name_parts[-1] if len(name_parts) > 1 else ""
        
        patient = {
            "resourceType": "Patient",
            "id": patient_id,
            "identifier": [{
                "system": "http://hospital.example.org/patients",
                "value": patient_id
            }],
            "name": [{
                "use": "official",
                "family": family,
                "given": given
            }],
            "gender": gender.lower(),
            "birthDate": self._format_date(birth_date)
        }
        
        self.resources.append(patient)
        return patient
    
    def create_practitioner(self, practitioner_id: str, name: str, qualification: Optional[str] = None) -> Dict:
        name_parts = name.split()
        given = name_parts[:-1] if len(name_parts) > 1 else [name]
        family = name_parts[-1] if len(name_parts) > 1 else ""
        
        practitioner = {
            "resourceType": "Practitioner",
            "id": practitioner_id,
            "identifier": [{
                "system": "http://hospital.example.org/practitioners",
                "value": practitioner_id
            }],
            "name": [{
                "use": "official",
                "family": family,
                "given": given
            }]
        }
        
        if qualification:
            practitioner["qualification"] = [{
                "code": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0360",
                        "code": qualification
                    }]
                }
            }]
        
        self.resources.append(practitioner)
        return practitioner
    
    def create_medication(self, medication_code: str, name: str, form: str, strength: str) -> Dict:
        form_codes = {
            "TAB": "385055001",
            "CAP": "385056000",
            "SYR": "385057009",
            "SUS": "421026006",
            "INJ": "394899003",
            "CRE": "385058004",
            "OIN": "385059007",
            "SUP": "385060002",
            "SOL": "385061003",
            "POW": "385062005",
            "GEL": "385063000",
            "LOT": "385064006",
            "AER": "385065007",
            "PAS": "421031004",
            "FIL": "421032006",
            "IMP": "421033001"
        }
        
        medication = {
            "resourceType": "Medication",
            "id": self._generate_id(),
            "code": {
                "coding": [{
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": medication_code,
                    "display": name
                }]
            },
            "form": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": form_codes.get(form, "385055001"),
                    "display": form
                }]
            }
        }
        
        if strength:
            strength_value = 1.0
            strength_unit = "mg"
            try:
                parts = strength.split()
                strength_value = float(parts[0])
                if len(parts) > 1:
                    strength_unit = parts[1]
            except (ValueError, IndexError):
                logger.warning(f"Could not parse strength '{strength}', using defaults")
            
            medication["ingredient"] = [{
                "itemCodeableConcept": {
                    "coding": [{
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": medication_code,
                        "display": name
                    }]
                },
                "strength": {
                    "numerator": {
                        "value": strength_value,
                        "unit": strength_unit
                    },
                    "denominator": {
                        "value": 1,
                        "unit": "unit"
                    }
                }
            }]
        
        self.resources.append(medication)
        return medication
    
    def create_medication_request(self, 
                                 patient_id: str, 
                                 practitioner_id: str, 
                                 medication_id: str,
                                 intent: str = "order",
                                 status: str = "active",
                                 dosage_instruction: str = "",
                                 quantity: Optional[Quantity] = None,
                                 refills: Optional[int] = None,
                                 substitution_allowed: bool = True) -> Dict:
        
        medication_request = {
            "resourceType": "MedicationRequest",
            "id": self._generate_id(),
            "status": status,
            "intent": intent,
            "authoredOn": self._format_datetime(datetime.now()),
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "requester": {
                "reference": f"Practitioner/{practitioner_id}"
            },
            "medicationReference": {
                "reference": f"Medication/{medication_id}"
            }
        }
        
        if dosage_instruction:
            medication_request["dosageInstruction"] = [{
                "text": dosage_instruction,
                "timing": {
                    "repeat": {
                        "frequency": 1,
                        "period": 1,
                        "periodUnit": "d"
                    }
                }
            }]
        
        if quantity:
            if "dispenseRequest" not in medication_request:
                medication_request["dispenseRequest"] = {}
            medication_request["dispenseRequest"]["quantity"] = quantity.to_dict()
        
        if refills is not None:
            if "dispenseRequest" not in medication_request:
                medication_request["dispenseRequest"] = {}
            medication_request["dispenseRequest"]["numberOfRepeatsAllowed"] = refills
        
        medication_request["substitution"] = {
            "allowedBoolean": substitution_allowed
        }
        
        self.resources.append(medication_request)
        return medication_request
    
    def create_observation(self, 
                          patient_id: str, 
                          code: Coding, 
                          value: Any,
                          effective_datetime: datetime) -> Dict:
        
        observation = {
            "resourceType": "Observation",
            "id": self._generate_id(),
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                }]
            }],
            "code": {
                "coding": [code.to_dict()]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": self._format_datetime(effective_datetime)
        }
        
        if isinstance(value, (int, float, Decimal)):
            observation["valueQuantity"] = {"value": float(value)}
            if code.code == "29463-7":
                observation["valueQuantity"]["unit"] = "kg"
                observation["valueQuantity"]["system"] = "http://unitsofmeasure.org"
                observation["valueQuantity"]["code"] = "kg"
            elif code.code == "8302-2":
                observation["valueQuantity"]["unit"] = "cm"
                observation["valueQuantity"]["system"] = "http://unitsofmeasure.org"
                observation["valueQuantity"]["code"] = "cm"
        elif isinstance(value, str):
            observation["valueString"] = value
        elif isinstance(value, bool):
            observation["valueBoolean"] = value
        
        self.resources.append(observation)
        return observation
    
    def create_allergy_intolerance(self, 
                                  patient_id: str, 
                                  substance: str, 
                                  clinical_status: str = "active") -> Dict:
        
        allergy = {
            "resourceType": "AllergyIntolerance",
            "id": self._generate_id(),
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                    "code": clinical_status
                }]
            },
            "verificationStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                    "code": "confirmed"
                }]
            },
            "code": {
                "text": substance
            },
            "patient": {
                "reference": f"Patient/{patient_id}"
            }
        }
        
        self.resources.append(allergy)
        return allergy
    
    def create_condition(self, 
                        patient_id: str, 
                        code: str, 
                        display: str, 
                        clinical_status: str = "active") -> Dict:
        
        condition_display = display if display else code
        
        condition = {
            "resourceType": "Condition",
            "id": self._generate_id(),
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": clinical_status
                }]
            },
            "verificationStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed"
                }]
            },
            "code": {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/icd-10",
                    "code": code,
                    "display": condition_display
                }]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            }
        }
        
        self.resources.append(condition)
        return condition
    
    def create_bundle(self, 
                     bundle_type: str = "collection",
                     timestamp: Optional[datetime] = None) -> Dict:
        
        bundle = {
            "resourceType": "Bundle",
            "id": self._generate_id(),
            "type": bundle_type,
            "timestamp": self._format_datetime(timestamp or datetime.now()),
            "entry": []
        }
        
        for resource in self.resources:
            bundle["entry"].append({
                "resource": resource
            })
        
        return bundle
    
    def clear_resources(self):
        self.resources = []
    
    def to_json(self, indent: int = 2) -> str:
        bundle = self.create_bundle()
        return json.dumps(bundle, indent=indent, default=str)
    
    def save_to_file(self, filename: str) -> None:
        with open(filename, 'w') as f:
            f.write(self.to_json())
        logger.info(f"FHIR Bundle saved to {filename}")

class PrescriptionFHIRGenerator:
    def __init__(self):
        self.generator = FHIRGenerator()
        self.patient_ref = None
        self.practitioner_ref = None
        self.prescription_data = None
        self.created_medications = {}
    
    def _validate_prescription_data(self, prescription_data: Dict):
        required_fields = ["patient", "prescribing_doctor", "items"]
        for field in required_fields:
            if field not in prescription_data:
                raise ValueError(f"Missing required field: {field}")
        
        patient_required = ["patient_id", "name", "date_of_birth", "gender"]
        for field in patient_required:
            if field not in prescription_data["patient"]:
                raise ValueError(f"Missing required patient field: {field}")
        
        doctor_required = ["id", "name"]
        for field in doctor_required:
            if field not in prescription_data["prescribing_doctor"]:
                raise ValueError(f"Missing required doctor field: {field}")
    
    def create_prescription(self, prescription_data: Dict) -> str:
        self.prescription_data = prescription_data
        self._validate_prescription_data(prescription_data)
        
        patient_data = prescription_data["patient"]
        doctor_data = prescription_data["prescribing_doctor"]
        
        try:
            birth_date = datetime.strptime(patient_data["date_of_birth"], "%Y%m%d").date()
        except ValueError:
            raise ValueError(f"Invalid date format: {patient_data['date_of_birth']}. Expected YYYYMMDD")
        
        patient = self.generator.create_patient(
            patient_id=patient_data["patient_id"],
            name=patient_data["name"],
            birth_date=birth_date,
            gender=patient_data["gender"]
        )
        self.patient_ref = patient_data["patient_id"]
        
        practitioner = self.generator.create_practitioner(
            practitioner_id=doctor_data["id"],
            name=doctor_data["name"],
            qualification=doctor_data.get("qualification")
        )
        self.practitioner_ref = doctor_data["id"]
        
        if patient_data.get("weight_kg"):
            try:
                weight_value = Decimal(patient_data["weight_kg"])
                self.generator.create_observation(
                    patient_id=self.patient_ref,
                    code=Coding(
                        system="http://loinc.org",
                        code="29463-7",
                        display="Body weight"
                    ),
                    value=weight_value,
                    effective_datetime=datetime.now()
                )
            except Exception as e:
                logger.warning(f"Could not create weight observation: {e}")
        
        if patient_data.get("height_cm"):
            try:
                height_value = Decimal(patient_data["height_cm"])
                self.generator.create_observation(
                    patient_id=self.patient_ref,
                    code=Coding(
                        system="http://loinc.org",
                        code="8302-2",
                        display="Body height"
                    ),
                    value=height_value,
                    effective_datetime=datetime.now()
                )
            except Exception as e:
                logger.warning(f"Could not create height observation: {e}")
        
        for allergy in patient_data.get("allergies", []):
            if allergy and allergy.strip():
                self.generator.create_allergy_intolerance(
                    patient_id=self.patient_ref,
                    substance=allergy.strip()
                )
        
        icd10_display_map = {
            "I10": "Essential (primary) hypertension",
            "E11.9": "Type 2 diabetes mellitus without complications"
        }
        
        for diagnosis in patient_data.get("diagnoses", []):
            if diagnosis and diagnosis.strip():
                display_text = icd10_display_map.get(diagnosis.strip(), diagnosis.strip())
                self.generator.create_condition(
                    patient_id=self.patient_ref,
                    code=diagnosis.strip(),
                    display=display_text
                )
        
        for item in prescription_data["items"]:
            try:
                medication = self.generator.create_medication(
                    medication_code=item["medication_code"],
                    name=item["medication_name"],
                    form=item["form"],
                    strength=item["strength"]
                )
                
                self.created_medications[medication["id"]] = {
                    "name": item["medication_name"],
                    "code": item["medication_code"],
                    "strength": item["strength"]
                }
                
                quantity = Quantity(
                    value=Decimal(str(item["quantity"])),
                    unit=item.get("unit", item["form"]),
                    system="http://unitsofmeasure.org"
                )
                
                self.generator.create_medication_request(
                    patient_id=self.patient_ref,
                    practitioner_id=self.practitioner_ref,
                    medication_id=medication["id"],
                    dosage_instruction=item["dosage_instruction"],
                    quantity=quantity,
                    refills=item.get("refills"),
                    substitution_allowed=item.get("substitution_allowed", True)
                )
            except Exception as e:
                logger.error(f"Error creating medication for {item.get('medication_name', 'unknown')}: {e}")
                raise
        
        return self.generator.to_json()
    
    def create_edifact_like_response(self) -> Dict:
        if not self.prescription_data:
            raise ValueError("No prescription data available. Call create_prescription first.")
        
        patient_data = self.prescription_data["patient"]
        doctor_data = self.prescription_data["prescribing_doctor"]
        
        segments = []
        
        unh_segment = {
            "segment": "UNH",
            "description": "Message Header",
            "fields": [
                {"tag": "0062", "value": "PRESCR01"},
                {"tag": "S009", "value": [
                    {"tag": "0065", "value": "PRESCR"},
                    {"tag": "0052", "value": "D"},
                    {"tag": "0054", "value": "96A"},
                    {"tag": "0051", "value": "UN"}
                ]}
            ]
        }
        segments.append(unh_segment)
        
        bgm_segment = {
            "segment": "BGM",
            "description": "Beginning of Message",
            "fields": [
                {"tag": "C002", "value": [
                    {"tag": "1001", "value": "230"}
                ]},
                {"tag": "1004", "value": f"PRES{datetime.now().strftime('%Y%m%d%H%M%S')}"},
                {"tag": "1225", "value": "9"}
            ]
        }
        segments.append(bgm_segment)
        
        dtm_segment = {
            "segment": "DTM",
            "description": "Date/Time/Period",
            "fields": [
                {"tag": "C507", "value": [
                    {"tag": "2005", "value": "137"},
                    {"tag": "2380", "value": datetime.now().strftime('%Y%m%d%H%M')},
                    {"tag": "2379", "value": "203"}
                ]}
            ]
        }
        segments.append(dtm_segment)
        
        nad_segment_prescriber = {
            "segment": "NAD",
            "description": "Prescriber Information",
            "fields": [
                {"tag": "3035", "value": "PZ"},
                {"tag": "C082", "value": [
                    {"tag": "3039", "value": doctor_data["id"]},
                    {"tag": "1131", "value": "91"}
                ]},
                {"tag": "C080", "value": [
                    {"tag": "3036", "value": doctor_data["name"]}
                ]},
                {"tag": "C059", "value": [
                    {"tag": "3042", "value": "MEDICAL CENTER"}
                ]}
            ]
        }
        segments.append(nad_segment_prescriber)
        
        nad_segment_patient = {
            "segment": "NAD",
            "description": "Patient Information",
            "fields": [
                {"tag": "3035", "value": "PT"},
                {"tag": "C082", "value": [
                    {"tag": "3039", "value": patient_data["patient_id"]},
                    {"tag": "1131", "value": "PAT"}
                ]},
                {"tag": "C080", "value": [
                    {"tag": "3036", "value": patient_data["name"]}
                ]},
                {"tag": "C059", "value": [
                    {"tag": "3042", "value": "RESIDENCE"}
                ]}
            ]
        }
        segments.append(nad_segment_patient)
        
        dtm_segment_patient = {
            "segment": "DTM",
            "description": "Patient Date of Birth",
            "fields": [
                {"tag": "C507", "value": [
                    {"tag": "2005", "value": "329"},
                    {"tag": "2380", "value": patient_data["date_of_birth"]},
                    {"tag": "2379", "value": "102"}
                ]}
            ]
        }
        segments.append(dtm_segment_patient)
        
        pat_segment = {
            "segment": "PAT",
            "description": "Patient Demographic Information",
            "fields": [
                {"tag": "C056", "value": [
                    {"tag": "3494", "value": patient_data["gender"].upper()}
                ]}
            ]
        }
        segments.append(pat_segment)
        
        if patient_data.get("allergies"):
            alc_segment = {
                "segment": "ALC",
                "description": "Allergy Information",
                "fields": [
                    {"tag": "5463", "value": "3"}
                ]
            }
            segments.append(alc_segment)
            
            for allergy in patient_data["allergies"]:
                pcd_segment = {
                    "segment": "PCD",
                    "description": "Allergy Details",
                    "fields": [
                        {"tag": "C501", "value": [
                            {"tag": "1045", "value": "ALG"},
                            {"tag": "1131", "value": allergy}
                        ]}
                    ]
                }
                segments.append(pcd_segment)
        
        if patient_data.get("diagnoses"):
            diag_segment = {
                "segment": "DGS",
                "description": "Diagnosis Information",
                "fields": [
                    {"tag": "C078", "value": [
                        {"tag": "1153", "value": "ICD10"}
                    ]}
                ]
            }
            segments.append(diag_segment)
            
            for diagnosis in patient_data["diagnoses"]:
                pcd_segment = {
                    "segment": "PCD",
                    "description": "Diagnosis Details",
                    "fields": [
                        {"tag": "C501", "value": [
                            {"tag": "1045", "value": "DG"},
                            {"tag": "1131", "value": diagnosis}
                        ]}
                    ]
                }
                segments.append(pcd_segment)
        
        for item in self.prescription_data["items"]:
            lin_segment = {
                "segment": "LIN",
                "description": "Line Item",
                "fields": [
                    {"tag": "1082", "value": str(self.prescription_data["items"].index(item) + 1)},
                    {"tag": "C212", "value": [
                        {"tag": "7140", "value": item["medication_code"]},
                        {"tag": "7143", "value": "RXNORM"}
                    ]}
                ]
            }
            segments.append(lin_segment)
            
            imd_segment = {
                "segment": "IMD",
                "description": "Item Description",
                "fields": [
                    {"tag": "C273", "value": [
                        {"tag": "7008", "value": item["medication_name"]}
                    ]}
                ]
            }
            segments.append(imd_segment)
            
            mea_segment = {
                "segment": "MEA",
                "description": "Measurements",
                "fields": [
                    {"tag": "C502", "value": [
                        {"tag": "6313", "value": "STR"}
                    ]},
                    {"tag": "C174", "value": [
                        {"tag": "6411", "value": "UT"},
                        {"tag": "6314", "value": item["strength"]}
                    ]}
                ]
            }
            segments.append(mea_segment)
            
            qty_segment = {
                "segment": "QTY",
                "description": "Quantity",
                "fields": [
                    {"tag": "C186", "value": [
                        {"tag": "6063", "value": "1"},
                        {"tag": "6060", "value": str(item["quantity"])},
                        {"tag": "6411", "value": item.get("unit", "TAB")}
                    ]}
                ]
            }
            segments.append(qty_segment)
            
            rff_segment = {
                "segment": "RFF",
                "description": "Prescription Reference",
                "fields": [
                    {"tag": "C506", "value": [
                        {"tag": "1153", "value": "RF"},
                        {"tag": "1154", "value": str(item.get("refills", 0))}
                    ]}
                ]
            }
            segments.append(rff_segment)
            
            ftx_segment = {
                "segment": "FTX",
                "description": "Free Text Instructions",
                "fields": [
                    {"tag": "4451", "value": "INS"},
                    {"tag": "C107", "value": [
                        {"tag": "4441", "value": "1"}
                    ]},
                    {"tag": "C108", "value": [
                        {"tag": "4440", "value": item["dosage_instruction"]}
                    ]}
                ]
            }
            segments.append(ftx_segment)
            
            if item.get("special_instructions"):
                ftx_special_segment = {
                    "segment": "FTX",
                    "description": "Special Instructions",
                    "fields": [
                        {"tag": "4451", "value": "SPI"},
                        {"tag": "C107", "value": [
                            {"tag": "4441", "value": "2"}
                        ]},
                        {"tag": "C108", "value": [
                            {"tag": "4440", "value": item["special_instructions"]}
                        ]}
                    ]
                }
                segments.append(ftx_special_segment)
        
        unt_segment = {
            "segment": "UNT",
            "description": "Message Trailer",
            "fields": [
                {"tag": "0074", "value": str(len(segments) + 1)},
                {"tag": "0062", "value": f"PRES{datetime.now().strftime('%Y%m%d%H%M%S')}"}
            ]
        }
        segments.append(unt_segment)
        
        edifact_response = {
            "message_type": "PRESCR",
            "message_version": "96A",
            "message_release": "D",
            "controlling_agency": "UN",
            "interchange_control_reference": f"PRES{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "segments": segments,
            "segment_count": len(segments),
            "summary": {
                "patient": {
                    "id": patient_data["patient_id"],
                    "name": patient_data["name"],
                    "date_of_birth": patient_data["date_of_birth"],
                    "gender": patient_data["gender"]
                },
                "prescriber": {
                    "id": doctor_data["id"],
                    "name": doctor_data["name"],
                    "qualification": doctor_data.get("qualification", "")
                },
                "items_count": len(self.prescription_data["items"]),
                "total_quantity": sum(int(item["quantity"]) for item in self.prescription_data["items"]),
                "allergies_count": len(patient_data.get("allergies", [])),
                "diagnoses_count": len(patient_data.get("diagnoses", []))
            }
        }
        
        return edifact_response
    
    def get_dual_response(self) -> Dict:
        fhir_json = json.loads(self.generator.to_json())
        edifact_json = self.create_edifact_like_response()
        
        return {
            "response": {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "response_id": str(uuid.uuid4())
            },
            "formats": {
                "fhir": {
                    "format": "FHIR R4",
                    "bundle_type": fhir_json.get("type", "collection"),
                    "resource_count": len(fhir_json.get("entry", [])),
                    "data": fhir_json
                },
                "edifact": {
                    "format": "EDIFACT-like JSON",
                    "message_type": "PRESCR",
                    "segment_count": edifact_json.get("segment_count", 0),
                    "data": edifact_json
                }
            },
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "patient_id": self.patient_ref,
                "practitioner_id": self.practitioner_ref,
                "medication_count": len(self.created_medications)
            }
        }

def main():
    prescription_data = {
        "prescribing_doctor": {
            "id": "DOC987654321",
            "name": "Dr. Jane Smith",
            "qualification": "MD"
        },
        "patient": {
            "patient_id": "PAT123456789",
            "name": "John Doe",
            "date_of_birth": "19800515",
            "gender": "M",
            "weight_kg": "85.5",
            "height_cm": "180.0",
            "allergies": ["Penicillin", "Sulfa drugs"],
            "diagnoses": ["I10", "E11.9"]
        },
        "items": [
            {
                "medication_code": "206765",
                "medication_name": "Lisinopril",
                "form": "TAB",
                "strength": "10 mg",
                "quantity": "30",
                "unit": "TAB",
                "dosage_instruction": "Take 1 tablet once daily in the morning",
                "route": "PO",
                "duration_days": 30,
                "refills": 3,
                "special_instructions": "Take with food if stomach upset occurs",
                "substitution_allowed": True
            },
            {
                "medication_code": "861007",
                "medication_name": "Metformin",
                "form": "TAB",
                "strength": "500 mg",
                "quantity": "60",
                "unit": "TAB",
                "dosage_instruction": "Take 1 tablet twice daily with meals",
                "route": "PO",
                "duration_days": 30,
                "refills": 3,
                "special_instructions": "Monitor blood glucose levels regularly",
                "substitution_allowed": True
            }
        ]
    }
    
    try:
        fhir_generator = PrescriptionFHIRGenerator()
        
        print("\n" + "="*80)
        print("GENERATING FHIR PRESCRIPTION")
        print("="*80)
        fhir_bundle = fhir_generator.create_prescription(prescription_data)
        
        print("\n" + "="*80)
        print("GENERATING EDIFACT-LIKE RESPONSE")
        print("="*80)
        edifact_response = fhir_generator.create_edifact_like_response()
        
        print("\n" + "="*80)
        print("DUAL FORMAT RESPONSE (FHIR + EDIFACT-like)")
        print("="*80)
        dual_response = fhir_generator.get_dual_response()
        
        with open("prescription_fhir.json", "w") as f:
            f.write(fhir_bundle)
        print("\nFHIR Bundle saved to prescription_fhir.json")
        
        with open("prescription_edifact.json", "w") as f:
            json.dump(edifact_response, f, indent=2)
        print("EDIFACT-like response saved to prescription_edifact.json")
        
        with open("prescription_dual_response.json", "w") as f:
            json.dump(dual_response, f, indent=2)
        print("Dual format response saved to prescription_dual_response.json")
        
        print("\n" + "="*80)
        print("RESPONSE SUMMARY")
        print("="*80)
        
        fhir_data = json.loads(fhir_bundle)
        resource_types = [entry["resource"]["resourceType"] for entry in fhir_data["entry"]]
        print(f"\nFHIR Resources: {len(resource_types)}")
        print("FHIR Resource types:", ", ".join(sorted(set(resource_types))))
        
        print(f"\nEDIFACT Segments: {edifact_response['segment_count']}")
        segment_types = set(seg['segment'] for seg in edifact_response['segments'])
        print("EDIFACT Segment types:", ", ".join(sorted(segment_types)))
        
        print(f"\nPatient: {prescription_data['patient']['name']} (ID: {prescription_data['patient']['patient_id']})")
        print(f"Prescriber: {prescription_data['prescribing_doctor']['name']}")
        print(f"Medications: {len(prescription_data['items'])} items")
        print(f"Allergies: {len(prescription_data['patient']['allergies'])}")
        print(f"Diagnoses: {len(prescription_data['patient']['diagnoses'])}")
        
        print("\n" + "="*80)
        print("SAMPLE EDIFACT SEGMENTS (first 5):")
        print("="*80)
        for i, segment in enumerate(edifact_response['segments'][:5]):
            print(f"\n{segment['segment']} - {segment['description']}")
            for field in segment['fields']:
                if isinstance(field['value'], list):
                    subfields = []
                    for subfield in field['value']:
                        subfields.append(f"{subfield['tag']}: {subfield['value']}")
                    print(f"  {field['tag']}: [{', '.join(subfields)}]")
                else:
                    print(f"  {field['tag']}: {field['value']}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
