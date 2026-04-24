import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from app.extensions import get_openemr_db_engine

# ---------------------------------------------------------------------------
# SOAP section mapping
# ---------------------------------------------------------------------------
 
# Maps Zoom note section headers to SOAP fields.
# Keys are lowercase for case-insensitive matching.
SOAP_SECTION_MAP = {
    # Subjective
    "chief complaint":                  "subjective",
    "history of present illness":       "subjective",
    "hpi":                              "subjective",
    "review of systems":                "subjective",
    "ros":                              "subjective",
    "symptoms and stressors":           "subjective",
    "subjective narrative":             "subjective",
    "discussion notes":                 "subjective",
    "reason for visit":                 "subjective",
    "past medical history":             "subjective",
    "past psychiatric history":         "subjective",
    "past surgical history":            "subjective",
    "family history":                   "subjective",
    "social history":                   "subjective",
    "medications":                      "subjective",
    "allergies":                        "subjective",
    "immunizations":                    "subjective",
    "development history":              "subjective",
    "anticipatory guidance":            "subjective",
    "diet & nutrition":                 "subjective",
    "diet and nutrition":               "subjective",
 
    # Objective
    "physical exam":                    "objective",
    "vitals":                           "objective",
    "results":                          "objective",
    "mental status exam":               "objective",
    "functional status":                "objective",
    "procedures":                       "objective",
    "hospital / ed course":             "objective",
    "hospital course":                  "objective",
    "ed course":                        "objective",
    "response to therapy":              "objective",
 
    # Assessment
    "assessment":                       "assessment",
    "risk assessment":                  "assessment",
    "problem list":                     "assessment",
    "generated diagnoses & codes":      "assessment",
    "generated diagnoses and codes":    "assessment",
 
    # Plan
    "plan":                             "plan",
    "assessment & plan":                "plan",
    "assessment and plan":              "plan",
    "patient recommendations":          "plan",
    "goals narrative":                  "plan",
    "disposition":                      "plan",
    "advanced directives":              "plan",
}
 
 