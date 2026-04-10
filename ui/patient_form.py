"""
Patient Input Form — Streamlit form for capturing patient data.

Provides structured inputs for symptoms, demographics, medical history,
and optional genetic data upload.
"""

import streamlit as st


# Common symptoms for the multi-select dropdown
COMMON_SYMPTOMS = [
    "Chest pain",
    "Shortness of breath",
    "Fever",
    "Cough",
    "Fatigue",
    "Headache",
    "Nausea",
    "Vomiting",
    "Abdominal pain",
    "Diarrhea",
    "Dizziness",
    "Palpitations",
    "Weight loss",
    "Joint pain",
    "Skin rash",
    "Swelling",
    "Back pain",
    "Muscle weakness",
    "Night sweats",
    "Blurred vision",
    "Numbness/tingling",
    "Difficulty swallowing",
    "Blood in urine",
    "Blood in stool",
    "Frequent urination",
    "Confusion",
    "Seizures",
    "Loss of consciousness",
]


def render_patient_form() -> dict | None:
    """
    Render the patient input form and return submitted data.

    Returns:
        Dict with patient data if form submitted, None otherwise
    """

    with st.form("patient_form", clear_on_submit=False):
        st.markdown("### 📋 Patient Information")

        # ── Demographics ──────────────────────────────────────────────
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input(
                "Age",
                min_value=0,
                max_value=120,
                value=45,
                step=1,
                help="Patient's age in years",
            )
        with col2:
            sex = st.selectbox(
                "Biological Sex",
                options=["Male", "Female", "Other / Not specified"],
                index=0,
            )

        st.markdown("---")

        # ── Symptoms ──────────────────────────────────────────────────
        st.markdown("### 🩺 Presenting Symptoms")

        selected_symptoms = st.multiselect(
            "Select symptoms from common list",
            options=COMMON_SYMPTOMS,
            default=[],
            help="Select one or more symptoms",
        )

        custom_symptoms = st.text_area(
            "Additional symptoms (one per line)",
            value="",
            height=80,
            placeholder="Enter any symptoms not in the list above...\ne.g., radiating left arm pain\ne.g., worsens with exertion",
        )

        st.markdown("---")

        # ── Medical History ───────────────────────────────────────────
        st.markdown("### 📂 Medical History")

        medical_history = st.text_area(
            "Past medical history, medications, allergies",
            value="",
            height=100,
            placeholder="e.g., Type 2 diabetes (10 years), Hypertension\n"
            "Medications: Metformin 500mg BID, Lisinopril 10mg daily\n"
            "Allergies: Penicillin (rash)",
        )

        additional_context = st.text_area(
            "Additional clinical context (optional)",
            value="",
            height=80,
            placeholder="e.g., Recent travel history, family history of cancer,\n"
            "occupational exposures, recent procedures...",
        )

        st.markdown("---")

        # ── Genetic Data ──────────────────────────────────────────────
        st.markdown("### 🧬 Genetic / Variant Data (Optional)")

        genetic_input_method = st.radio(
            "Input method",
            options=["None", "Text input", "File upload"],
            index=0,
            horizontal=True,
        )

        genetic_data = ""

        if genetic_input_method == "Text input":
            genetic_data = st.text_area(
                "Enter variant data",
                value="",
                height=100,
                placeholder="Supported formats:\n"
                "HGVS: BRCA1:c.5266dupC\n"
                "VCF-like: chr17 7577120 G A\n"
                "FASTA: >seq1\\nATCGATCG...",
            )

        elif genetic_input_method == "File upload":
            uploaded_file = st.file_uploader(
                "Upload FASTA, VCF, or text file",
                type=["fasta", "fa", "fna", "vcf", "txt"],
            )
            if uploaded_file:
                genetic_data = uploaded_file.getvalue().decode("utf-8")
                st.success(f"📄 Loaded: {uploaded_file.name} ({len(genetic_data)} chars)")

        st.markdown("---")

        # ── Submit ────────────────────────────────────────────────────
        submitted = st.form_submit_button(
            "🔬 Run Clinical Analysis",
            use_container_width=True,
        )

        if submitted:
            # Combine symptoms
            all_symptoms = list(selected_symptoms)
            if custom_symptoms.strip():
                all_symptoms.extend(
                    s.strip()
                    for s in custom_symptoms.strip().split("\n")
                    if s.strip()
                )

            if not all_symptoms:
                st.error("⚠️ Please enter at least one symptom.")
                return None

            return {
                "symptoms": all_symptoms,
                "age": age,
                "sex": sex,
                "medical_history": medical_history,
                "additional_context": additional_context,
                "genetic_data": genetic_data,
            }

    return None
