#!/usr/bin/env python3

from datetime import datetime, date
from typing import Dict, List, Optional, Any
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
            except:
                pass
            
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
        
        condition = {
            "resourceType": "Condition",
            "id": self._generate_id(),
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": clinical_status
                }]
            },
            "code": {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/icd-10",
                    "code": code,
                    "display": display
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
    
    def create_prescription(self, prescription_data: Dict) -> str:
        patient_data = prescription_data["patient"]
        doctor_data = prescription_data["prescribing_doctor"]
        
        patient = self.generator.create_patient(
            patient_id=patient_data["patient_id"],
            name=patient_data["name"],
            birth_date=datetime.strptime(patient_data["date_of_birth"], "%Y%m%d").date(),
            gender=patient_data["gender"]
        )
        self.patient_ref = patient["id"]
        
        practitioner = self.generator.create_practitioner(
            practitioner_id=doctor_data["id"],
            name=doctor_data["name"],
            qualification=doctor_data.get("qualification")
        )
        self.practitioner_ref = practitioner["id"]
        
        if patient_data.get("weight_kg"):
            self.generator.create_observation(
                patient_id=self.patient_ref,
                code=Coding(
                    system="http://loinc.org",
                    code="29463-7",
                    display="Body weight"
                ),
                value=Decimal(patient_data["weight_kg"]),
                effective_datetime=datetime.now()
            )
        
        if patient_data.get("height_cm"):
            self.generator.create_observation(
                patient_id=self.patient_ref,
                code=Coding(
                    system="http://loinc.org",
                    code="8302-2",
                    display="Body height"
                ),
                value=Decimal(patient_data["height_cm"]),
                effective_datetime=datetime.now()
            )
        
        for allergy in patient_data.get("allergies", []):
            self.generator.create_allergy_intolerance(
                patient_id=self.patient_ref,
                substance=allergy
            )
        
        for diagnosis in patient_data.get("diagnoses", []):
            self.generator.create_condition(
                patient_id=self.patient_ref,
                code=diagnosis,
                display=""
            )
        
        for item in prescription_data["items"]:
            medication = self.generator.create_medication(
                medication_code=item["medication_code"],
                name=item["medication_name"],
                form=item["form"],
                strength=item["strength"]
            )
            
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
        
        return self.generator.to_json()

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
        fhir_bundle = fhir_generator.create_prescription(prescription_data)
        
        print("\n" + "="*80)
        print("FHIR R4 BUNDLE - Medication Prescription")
        print("="*80)
        print(fhir_bundle[:1000] + "...\n")
        
        with open("prescription_fhir.json", "w") as f:
            f.write(fhir_bundle)
        
        print("FHIR Bundle saved to prescription_fhir.json")
        
        data = json.loads(fhir_bundle)
        resource_types = [entry["resource"]["resourceType"] for entry in data["entry"]]
        print(f"\nTotal resources: {len(resource_types)}")
        print("Resource types:", ", ".join(sorted(set(resource_types))))
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()#!/usr/bin/env python3

from datetime import datetime, date
from typing import Dict, List, Optional, Any
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
            except:
                pass
            
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
        
        condition = {
            "resourceType": "Condition",
            "id": self._generate_id(),
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": clinical_status
                }]
            },
            "code": {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/icd-10",
                    "code": code,
                    "display": display
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
    
    def create_prescription(self, prescription_data: Dict) -> str:
        patient_data = prescription_data["patient"]
        doctor_data = prescription_data["prescribing_doctor"]
        
        patient = self.generator.create_patient(
            patient_id=patient_data["patient_id"],
            name=patient_data["name"],
            birth_date=datetime.strptime(patient_data["date_of_birth"], "%Y%m%d").date(),
            gender=patient_data["gender"]
        )
        self.patient_ref = patient["id"]
        
        practitioner = self.generator.create_practitioner(
            practitioner_id=doctor_data["id"],
            name=doctor_data["name"],
            qualification=doctor_data.get("qualification")
        )
        self.practitioner_ref = practitioner["id"]
        
        if patient_data.get("weight_kg"):
            self.generator.create_observation(
                patient_id=self.patient_ref,
                code=Coding(
                    system="http://loinc.org",
                    code="29463-7",
                    display="Body weight"
                ),
                value=Decimal(patient_data["weight_kg"]),
                effective_datetime=datetime.now()
            )
        
        if patient_data.get("height_cm"):
            self.generator.create_observation(
                patient_id=self.patient_ref,
                code=Coding(
                    system="http://loinc.org",
                    code="8302-2",
                    display="Body height"
                ),
                value=Decimal(patient_data["height_cm"]),
                effective_datetime=datetime.now()
            )
        
        for allergy in patient_data.get("allergies", []):
            self.generator.create_allergy_intolerance(
                patient_id=self.patient_ref,
                substance=allergy
            )
        
        for diagnosis in patient_data.get("diagnoses", []):
            self.generator.create_condition(
                patient_id=self.patient_ref,
                code=diagnosis,
                display=""
            )
        
        for item in prescription_data["items"]:
            medication = self.generator.create_medication(
                medication_code=item["medication_code"],
                name=item["medication_name"],
                form=item["form"],
                strength=item["strength"]
            )
            
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
        
        return self.generator.to_json()

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
        fhir_bundle = fhir_generator.create_prescription(prescription_data)
        
        print("\n" + "="*80)
        print("FHIR R4 BUNDLE - Medication Prescription")
        print("="*80)
        print(fhir_bundle[:1000] + "...\n")
        
        with open("prescription_fhir.json", "w") as f:
            f.write(fhir_bundle)
        
        print("FHIR Bundle saved to prescription_fhir.json")
        
        data = json.loads(fhir_bundle)
        resource_types = [entry["resource"]["resourceType"] for entry in data["entry"]]
        print(f"\nTotal resources: {len(resource_types)}")
        print("Resource types:", ", ".join(sorted(set(resource_types))))
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
