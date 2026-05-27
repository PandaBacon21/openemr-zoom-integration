"""
Pre-canned clinical content used by the demo past-encounter seeding flow.

PAST_ENCOUNTER_NOTE is the SOAP body written to form_soap + form_clinical_notes.
PAST_ENCOUNTER_CARE_PLAN and PAST_ENCOUNTER_CLINICAL_INSTRUCTIONS are attached
as their own forms on the same locked encounter. DEMO_ICD_PROBLEMS and
DEMO_CPT_CODES drive the issue_encounter linkages and the billing rows so
the chart matches the encounter narrative end-to-end.

Section headers (Subjective / Objective / Assessment / Plan) match what
SOAP_SECTION_MAP in services/openemr/note.py recognizes, so the same
production parser handles this content unchanged.

Future expansion: add specialty-specific variants (e.g. CHRONIC_CARE_NOTE,
BEHAVIORAL_HEALTH_NOTE, MAT_NOTE) and let get_note_for_category branch on
the Zoom appointment category that the seeded encounter is tied to.
"""

PAST_ENCOUNTER_NOTE = """
Chief Complaint
Follow-up for type 2 diabetes mellitus with routine glucose management review.

History of Present Illness
The patient returned for scheduled telehealth follow-up and ongoing medication management of type 2 diabetes mellitus, diagnosed approximately two years ago. She reports home fasting glucose readings averaging 118–124 mg/dL and postprandial readings of 145–155 mg/dL, representing meaningful improvement since her metformin dose was titrated to 1000 mg twice daily four months ago. She reports consistent adherence with no missed doses and denies gastrointestinal side effects, which had been a concern at initiation. She also notes improved energy throughout the day and reduced frequency of afternoon fatigue, which she previously attributed to blood sugar fluctuations.

Review of Systems
Endocrine: Negative for polyuria, polydipsia, or unexplained weight loss.
Neurologic: Negative for peripheral tingling, numbness, or burning in the feet or hands.
Ophthalmologic: Negative for blurred vision or visual changes.
Cardiovascular: Negative for chest pain, palpitations, or lower extremity swelling.
Integumentary: Negative for slow-healing wounds or skin changes.

Past Medical History
Type 2 diabetes mellitus
Overweight (BMI 28.4 at last in-person visit)
Mild hypertriglyceridemia
Seasonal allergic rhinitis

Medications
Metformin 1000 mg by mouth twice daily with meals
Cetirizine 10 mg by mouth daily as needed for allergies

Social History
She works a sedentary desk job and has made deliberate efforts to incorporate movement into her daily routine, including standing breaks and lunchtime walks. She prepares most meals at home and has reduced dining out to once or twice per week. She reports occasional alcohol consumption, approximately two to three drinks per week, which was discussed in the context of blood sugar management and caloric intake. She is a non-smoker. She lives with her spouse, who has been supportive of the dietary changes they have adopted together.
Diet and Nutrition
She has transitioned to lower glycemic index foods and reduced refined carbohydrate and added sugar intake. She has begun tracking carbohydrate intake using a mobile application, which she reports has improved her awareness of portion sizes. She continues to reduce saturated fats and limit processed foods.

Results
Most recent HbA1c: 7.1%, down from 8.4% at last visit three months ago.
Fasting lipid panel: Mild hypertriglyceridemia at 182 mg/dL; LDL 108 mg/dL; HDL 49 mg/dL.
Comprehensive metabolic panel: Renal function within normal limits. Liver enzymes within normal limits.
Urine microalbumin: Negative for microalbuminuria.

Assessment
Type 2 diabetes mellitus is trending toward improved glycemic control on metformin 1000 mg twice daily, with HbA1c improving from 8.4% to 7.1% over six months and home glucose readings approaching target range. Mild hypertriglyceridemia noted on recent lipid panel, likely contributed to by dietary refined carbohydrate and added sugar intake as well as alcohol consumption. No evidence of end-organ involvement at this time, with renal function within normal limits and urine microalbumin negative.

Plan
Continue metformin 1000 mg twice daily with meals. Target HbA1c of 7.0% or lower reviewed with patient. Repeat HbA1c in three months to assess continued trajectory.
Repeat fasting lipid panel in six months to reassess hypertriglyceridemia following dietary and lifestyle modifications.
Annual dilated eye exam referral placed; patient instructed to schedule with ophthalmology.
Renal function and urine microalbumin to be rechecked at six-month interval.
Long-term physical activity goal of 150 minutes of moderate-intensity aerobic exercise weekly reviewed with patient.
Counseling provided regarding carbohydrate awareness, glycemic index, hydration, alcohol moderation, and hypoglycemia recognition.
Return telehealth visit in three months or sooner if glucose readings worsen or new symptoms develop.

Patient Recommendations
Continue taking metformin 1000 mg twice daily with meals as prescribed.
Maintain use of carbohydrate tracking application and continue focusing on low glycemic index food choices.
Reduce intake of refined carbohydrates, added sugars, and sugary beverages.
Continue brisk walking five days per week and work toward at least 150 minutes of moderate aerobic exercise weekly.
Reduce alcohol consumption to support triglyceride management and blood sugar stability.
Stay well hydrated, particularly during physical activity.
Schedule dilated eye exam with ophthalmology.
Monitor for signs of hypoglycemia including shakiness, sweating, or confusion, and report any episodes promptly.
Return for follow-up telehealth visit in three months or sooner if readings worsen or new symptoms develop.
"""


PAST_ENCOUNTER_CARE_PLAN = """Patient: {patient_name}
Date: {date}
Provider: {provider_name}
Diagnoses: Type 2 Diabetes Mellitus (E11.9), Hypertriglyceridemia (E78.1)

Goals
- Achieve and maintain HbA1c at or below 7.0%
- Reduce fasting glucose to consistently within 80130 mg/dL
- Reduce postprandial glucose to under 180 mg/dL at 2 hours
- Normalize triglyceride levels through dietary and lifestyle modification
- Achieve and sustain 150 minutes of moderate aerobic exercise per week
- Reduce alcohol intake to support metabolic goals

Barriers to Care
- Sedentary occupational environment limiting physical activity during the day
- History of GI intolerance at metformin initiation requiring gradual titration
- Alcohol consumption contributing to triglyceride elevation

Interventions
- Metformin 1000 mg twice daily with meals — continue and monitor
- Home glucose monitoring with log review at each visit
- Carbohydrate tracking via mobile application
- Dietary counseling: low glycemic index foods, reduced refined carbohydrates and added sugars
- Physical activity plan: brisk walking progressing toward 150 min/week
- Alcohol reduction counseling

Care Team & Referrals
- Primary care provider: ongoing quarterly follow-up
- Ophthalmology: annual dilated eye exam referral placed
- Registered dietitian: consider referral if dietary goals are not met in next 6 months
- Diabetes self-management education (DSME) program: consider referral if adherence or knowledge gaps emerge

Monitoring Schedule
- HbA1c: Every 3 months
- Fasting lipid panel: Every 6 months
- Comprehensive metabolic panel: Every 6 months
- Urine microalbumin: Annually
- Dilated eye exam: Annually
- Foot exam: Each in-person visit

Patient Engagement
Patient is actively engaged, using carbohydrate tracking tools, self-monitoring glucose at home, and making meaningful dietary changes. Spouse is supportive. Patient verbalized understanding of goals and agreed to the plan.
"""


PAST_ENCOUNTER_CLINICAL_INSTRUCTIONS = """Patient: {patient_name}
Visit Date: {date}
Provider: {provider_name}

Medications
- Continue taking metformin 1000 mg twice daily — take with breakfast and dinner to reduce stomach upset
- Do not skip doses; if a dose is missed, take it as soon as you remember unless it is almost time for the next dose
- Continue cetirizine 10 mg as needed for allergy symptoms

Blood Sugar Monitoring
- Check fasting glucose each morning before eating and log your readings
- Target fasting glucose: 80-130 mg/dL
- Target glucose 2 hours after meals: under 180 mg/dL
- Bring your glucose log or share your app data at your next visit

Diet
- Focus on low glycemic index foods: vegetables, legumes, whole grains, lean proteins
- Reduce refined carbohydrates: white bread, white rice, pasta, sugary cereals
- Reduce added sugars: sodas, juices, desserts, flavored coffee drinks
- Continue using your carbohydrate tracking app
- Limit alcohol to support both blood sugar and triglyceride levels

Physical Activity
- Continue brisk walking 5 days per week
- Work toward a goal of 150 minutes of moderate exercise total per week
- Even short activity breaks during your workday are beneficial

Warning Signs — Contact Us If You Experience
- Fasting glucose consistently above 200 mg/dL
- Signs of hypoglycemia: shakiness, sweating, confusion, rapid heartbeat
- Blurred vision or sudden visual changes
- Numbness, tingling, or burning in your feet or hands
- Any wounds or sores on your feet that are slow to heal

Upcoming Appointments & Labs
- Schedule your annual dilated eye exam with an ophthalmologist
- Labs due before your next visit in 3 months: HbA1c, comprehensive metabolic panel
- Labs due at your 6-month visit: fasting lipid panel, urine microalbumin, renal function

Next Visit
- Telehealth follow-up in 3 months
- Contact the office sooner if your readings worsen or new symptoms develop
"""


# ICD-10 codes linked to each seeded past encounter as issue_encounter rows.
# Order matters only for display; OpenEMR doesn't impose a primary.
# Each entry: (icd_code, title) — the title goes into lists.title and is what
# the patient/provider sees in the Issues panel.
DEMO_ICD_PROBLEMS = [
    ("E11.9",   "Type 2 diabetes mellitus without complications"),
    ("E78.1",   "Pure hypertriglyceridemia"),
    ("Z79.84",  "Long-term (current) use of oral hypoglycemic drugs (metformin)"),
    ("Z71.3",   "Dietary counseling and surveillance"),
    ("Z71.89",  "Lifestyle and behavioral counseling"),
]


# CPT codes billed for each seeded past encounter. The '95' modifier marks
# the service as synchronous telehealth. 99457 + 99458 are the RPM (remote
# physiologic monitoring) codes for home-glucose review — they map to the
# diabetes-themed encounter narrative.
DEMO_CPT_CODES = [
    ("99214", "Office visit, established patient, moderate complexity, telehealth", "95"),
    ("99457", "Remote physiologic monitoring, first 20 minutes",                    "95"),
    ("99458", "Remote physiologic monitoring, each additional 20 minutes",          "95"),
]


def get_note_for_category(category_name: str) -> str:
    """
    Return the locked SOAP/clinical note body for a given Zoom appointment
    category.

    Currently returns the same body for all categories. Future work will
    branch by category_name (e.g. "Zoom Behavioral Health" → BH variant,
    "Zoom MAT (Suboxone)" → MAT variant) once per-specialty content is
    authored.
    """
    return PAST_ENCOUNTER_NOTE


def get_care_plan_for_category(
    category_name: str,
    *,
    patient_name: str,
    date: str,
    provider_name: str,
) -> str:
    """
    Care plan body — single variant for now. Substitutes patient_name, date,
    and provider_name into the long-form template body.
    """
    return PAST_ENCOUNTER_CARE_PLAN.format(
        patient_name=patient_name, date=date, provider_name=provider_name
    )


def get_clinical_instructions_for_category(
    category_name: str,
    *,
    patient_name: str,
    date: str,
    provider_name: str,
) -> str:
    """
    Clinical instructions body — single variant for now. Substitutes
    patient_name, date, and provider_name into the long-form template body.
    """
    return PAST_ENCOUNTER_CLINICAL_INSTRUCTIONS.format(
        patient_name=patient_name, date=date, provider_name=provider_name
    )
