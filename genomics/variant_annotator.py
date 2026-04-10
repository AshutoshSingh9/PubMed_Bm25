"""
Variant Annotator — Maps known pathogenic variants to clinical conditions.

Built-in lookup table of clinically significant variants (ClinVar-derived)
to provide immediate clinical context without external API calls.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Clinically Significant Variants Database ───────────────────────────────────
# Curated from ClinVar / ACMG guidelines — well-established pathogenic variants
VARIANT_DATABASE = {
    # ── Cancer Predisposition ──
    "BRCA1": {
        "full_name": "BRCA1 DNA Repair Associated",
        "chromosome": "17q21.31",
        "conditions": [
            "Hereditary Breast and Ovarian Cancer Syndrome",
            "Increased risk of pancreatic cancer",
            "Fanconi anemia (biallelic)",
        ],
        "inheritance": "Autosomal Dominant",
        "clinical_significance": "Pathogenic variants confer 60-80% lifetime risk of breast cancer "
                                 "and 40-60% risk of ovarian cancer.",
        "key_variants": {
            "c.5266dupC": "Frameshift, founder mutation (Ashkenazi Jewish)",
            "c.68_69delAG": "Frameshift, founder mutation (Ashkenazi Jewish)",
            "c.181T>G": "Missense, pathogenic",
        },
        "management": "Enhanced screening (MRI + mammography), risk-reducing surgery discussion, "
                      "PARP inhibitor eligibility",
    },
    "BRCA2": {
        "full_name": "BRCA2 DNA Repair Associated",
        "chromosome": "13q13.1",
        "conditions": [
            "Hereditary Breast and Ovarian Cancer Syndrome",
            "Increased risk of prostate, pancreatic, and melanoma",
            "Fanconi anemia (biallelic)",
        ],
        "inheritance": "Autosomal Dominant",
        "clinical_significance": "Pathogenic variants confer 45-70% lifetime risk of breast cancer "
                                 "and 10-30% risk of ovarian cancer.",
        "key_variants": {
            "c.6174delT": "Frameshift, founder mutation (Ashkenazi Jewish)",
            "c.5946delT": "Frameshift, pathogenic",
        },
        "management": "Enhanced screening, risk-reducing surgery discussion, PARP inhibitor eligibility",
    },
    "TP53": {
        "full_name": "Tumor Protein P53",
        "chromosome": "17p13.1",
        "conditions": [
            "Li-Fraumeni Syndrome",
            "Early-onset multiple cancers (breast, sarcoma, brain, adrenocortical)",
        ],
        "inheritance": "Autosomal Dominant",
        "clinical_significance": "Near 100% lifetime cancer risk. Early onset and multiple primary tumors.",
        "key_variants": {
            "p.R248W": "Hotspot missense, gain-of-function, most common TP53 mutation",
            "p.R175H": "Hotspot missense, gain-of-function",
            "p.R273H": "Hotspot missense, DNA contact mutation",
        },
        "management": "Comprehensive cancer surveillance (Toronto protocol), whole-body MRI",
    },
    # ── Cardiovascular ──
    "LDLR": {
        "full_name": "Low Density Lipoprotein Receptor",
        "chromosome": "19p13.2",
        "conditions": [
            "Familial Hypercholesterolemia",
            "Premature atherosclerotic cardiovascular disease",
        ],
        "inheritance": "Autosomal Dominant (co-dominant)",
        "clinical_significance": "Heterozygous: LDL-C 190-400 mg/dL. Homozygous: LDL-C >500 mg/dL. "
                                 "Major risk factor for premature coronary artery disease.",
        "key_variants": {},
        "management": "High-intensity statins, PCSK9 inhibitors, LDL apheresis (homozygous)",
    },
    # ── Cystic Fibrosis ──
    "CFTR": {
        "full_name": "Cystic Fibrosis Transmembrane Conductance Regulator",
        "chromosome": "7q31.2",
        "conditions": [
            "Cystic Fibrosis",
            "Congenital Bilateral Absence of Vas Deferens (monoallelic)",
            "CFTR-related metabolic syndrome",
        ],
        "inheritance": "Autosomal Recessive",
        "clinical_significance": "Most common lethal autosomal recessive disease in Caucasians. "
                                 "Affects lungs, pancreas, GI tract, reproductive system.",
        "key_variants": {
            "p.F508del": "Most common CF mutation (~70% of alleles worldwide)",
            "p.G551D": "Gating mutation, responsive to ivacaftor",
            "p.G542X": "Nonsense mutation, Class I",
        },
        "management": "CFTR modulators (elexacaftor/tezacaftor/ivacaftor for eligible genotypes), "
                      "pulmonary care, pancreatic enzyme replacement",
    },
    # ── Hemoglobinopathies ──
    "HBB": {
        "full_name": "Hemoglobin Subunit Beta",
        "chromosome": "11p15.4",
        "conditions": [
            "Sickle Cell Disease (HbS)",
            "Beta-Thalassemia",
        ],
        "inheritance": "Autosomal Recessive",
        "clinical_significance": "HbS (p.E6V): sickle cell disease in homozygotes. "
                                 "Multiple beta-thal mutations cause reduced/absent beta-globin.",
        "key_variants": {
            "p.E6V": "Sickle cell mutation (HbS)",
            "c.93-21G>A": "IVS-1-110, common beta-thalassemia mutation",
        },
        "management": "Hydroxyurea, voxelotor, crizanlizumab (SCD); transfusions, "
                      "iron chelation (thalassemia); gene therapy emerging",
    },
    # ── Pharmacogenomics ──
    "CYP2D6": {
        "full_name": "Cytochrome P450 2D6",
        "chromosome": "22q13.2",
        "conditions": [
            "Altered drug metabolism (codeine, tramadol, tamoxifen, antidepressants)",
        ],
        "inheritance": "Autosomal Co-dominant",
        "clinical_significance": "Poor metabolizers: risk of drug toxicity or therapeutic failure. "
                                 "Ultra-rapid metabolizers: risk of toxicity from prodrugs (e.g., codeine→morphine).",
        "key_variants": {
            "*4": "Non-functional allele, most common in Caucasians",
            "*5": "Gene deletion",
            "*1xN": "Gene duplication, ultra-rapid metabolizer",
        },
        "management": "Pharmacogenomic-guided prescribing per CPIC guidelines",
    },
    # ── Neurological ──
    "APOE": {
        "full_name": "Apolipoprotein E",
        "chromosome": "19q13.32",
        "conditions": [
            "Alzheimer's Disease (risk factor)",
            "Cardiovascular disease risk modifier",
        ],
        "inheritance": "Complex/Risk factor",
        "clinical_significance": "APOE ε4: 3x (heterozygous) to 12x (homozygous) increased Alzheimer's risk. "
                                 "APOE ε2: protective.",
        "key_variants": {
            "ε4": "Risk allele for late-onset Alzheimer's disease",
            "ε2": "Protective allele",
        },
        "management": "No specific treatment; informs risk counseling and clinical trial eligibility",
    },
}


class VariantAnnotator:
    """Annotates genetic variants with clinical significance using a built-in database."""

    def __init__(self):
        self.database = VARIANT_DATABASE

    def annotate(self, variants: list[dict]) -> list[dict]:
        """
        Annotate a list of parsed variants with clinical information.

        Args:
            variants: List of variant dicts from VariantParser

        Returns:
            List of annotated variant dicts with added clinical context
        """
        annotated = []

        for variant in variants:
            gene = self._extract_gene(variant)
            annotation = {
                **variant,
                "annotated": False,
                "clinical_info": None,
            }

            if gene and gene in self.database:
                db_entry = self.database[gene]
                annotation["annotated"] = True
                annotation["clinical_info"] = {
                    "gene": gene,
                    "full_name": db_entry["full_name"],
                    "chromosome": db_entry["chromosome"],
                    "conditions": db_entry["conditions"],
                    "inheritance": db_entry["inheritance"],
                    "clinical_significance": db_entry["clinical_significance"],
                    "management": db_entry["management"],
                }

                # Check for specific variant match
                change = variant.get("change", "")
                if change in db_entry.get("key_variants", {}):
                    annotation["clinical_info"]["specific_variant"] = {
                        "notation": change,
                        "description": db_entry["key_variants"][change],
                    }

            annotated.append(annotation)

        logger.info(
            f"Annotated {len(annotated)} variants, "
            f"{sum(1 for a in annotated if a['annotated'])} matched database."
        )
        return annotated

    def _extract_gene(self, variant: dict) -> Optional[str]:
        """Extract gene name from a variant dict."""
        if "gene" in variant:
            return variant["gene"].upper()

        # Try to find gene name in text description
        if "description" in variant:
            desc_upper = variant["description"].upper()
            for gene in self.database:
                if gene in desc_upper:
                    return gene

        return None

    def format_for_prompt(self, annotated_variants: list[dict]) -> str:
        """
        Format annotated variants into a string for LLM prompt injection.

        Args:
            annotated_variants: Output from annotate()

        Returns:
            Formatted clinical context string
        """
        if not annotated_variants:
            return "No variant annotations available."

        parts = []
        for var in annotated_variants:
            if var.get("annotated") and var.get("clinical_info"):
                info = var["clinical_info"]
                parts.append(
                    f"### {info['gene']} ({info['full_name']})\n"
                    f"- **Chromosome**: {info['chromosome']}\n"
                    f"- **Inheritance**: {info['inheritance']}\n"
                    f"- **Associated Conditions**: {', '.join(info['conditions'])}\n"
                    f"- **Clinical Significance**: {info['clinical_significance']}\n"
                    f"- **Management**: {info['management']}"
                )
                if "specific_variant" in info:
                    sv = info["specific_variant"]
                    parts.append(
                        f"- **Specific Variant Match**: {sv['notation']} — {sv['description']}"
                    )
                parts.append("")
            else:
                parts.append(f"- Variant '{var.get('raw', 'unknown')}': No database match\n")

        return "\n".join(parts)

    def get_gene_info(self, gene_name: str) -> Optional[dict]:
        """Look up a specific gene in the database."""
        return self.database.get(gene_name.upper())

    def list_genes(self) -> list[str]:
        """List all genes in the database."""
        return sorted(self.database.keys())
