"""
Variant Parser — Parses FASTA sequences and VCF-like variant data using Biopython.

Handles file uploads and text input to extract structured variant information
for injection into the clinical reasoning pipeline.
"""

import io
import logging
import re
from typing import Optional

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

logger = logging.getLogger(__name__)


class VariantParser:
    """Parses genetic/variant data from multiple input formats."""

    # Common variant notation pattern: e.g., BRCA1:c.5266dupC, TP53:p.R248W
    HGVS_PATTERN = re.compile(
        r"(?P<gene>[A-Z0-9]+)"
        r"[:\s]+"
        r"(?P<type>[cgpnmr])\."
        r"(?P<change>.+)",
        re.IGNORECASE,
    )

    # Simple VCF-like: CHROM POS REF ALT
    VCF_LINE_PATTERN = re.compile(
        r"(?P<chrom>chr[\dXYMT]+|[\dXYMT]+)\s+"
        r"(?P<pos>\d+)\s+"
        r"(?P<ref>[ACGT]+)\s+"
        r"(?P<alt>[ACGT]+)",
        re.IGNORECASE,
    )

    def parse_fasta(self, fasta_input: str) -> list[dict]:
        """
        Parse FASTA format sequences.

        Args:
            fasta_input: FASTA formatted string (may contain multiple sequences)

        Returns:
            List of dicts with: id, name, description, sequence, length
        """
        sequences = []
        try:
            handle = io.StringIO(fasta_input)
            for record in SeqIO.parse(handle, "fasta"):
                sequences.append({
                    "id": record.id,
                    "name": record.name,
                    "description": record.description,
                    "sequence": str(record.seq),
                    "length": len(record.seq),
                    "gc_content": self._gc_content(record.seq),
                })
            logger.info(f"Parsed {len(sequences)} FASTA sequences.")
        except Exception as e:
            logger.error(f"FASTA parsing failed: {e}")

        return sequences

    def parse_variants(self, variant_text: str) -> list[dict]:
        """
        Parse variant notation from free text input.

        Supports:
            - HGVS notation: BRCA1:c.5266dupC, TP53:p.R248W
            - Simple VCF-like: chr17 7577120 G A
            - Plain text descriptions: "BRCA1 pathogenic variant"

        Args:
            variant_text: Raw text containing variant information

        Returns:
            List of parsed variant dicts
        """
        variants = []

        for line in variant_text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Try HGVS pattern
            hgvs_match = self.HGVS_PATTERN.search(line)
            if hgvs_match:
                variants.append({
                    "format": "HGVS",
                    "gene": hgvs_match.group("gene").upper(),
                    "change_type": hgvs_match.group("type"),
                    "change": hgvs_match.group("change"),
                    "raw": line,
                })
                continue

            # Try VCF-like pattern
            vcf_match = self.VCF_LINE_PATTERN.search(line)
            if vcf_match:
                variants.append({
                    "format": "VCF",
                    "chromosome": vcf_match.group("chrom"),
                    "position": int(vcf_match.group("pos")),
                    "reference": vcf_match.group("ref"),
                    "alternate": vcf_match.group("alt"),
                    "raw": line,
                })
                continue

            # Fallback: treat as plain text description
            if len(line) > 3:
                variants.append({
                    "format": "text",
                    "description": line,
                    "raw": line,
                })

        logger.info(f"Parsed {len(variants)} variants from input.")
        return variants

    def parse_upload(self, file_content: str, filename: str = "") -> dict:
        """
        Auto-detect format and parse uploaded file content.

        Args:
            file_content: Raw file content as string
            filename: Original filename for format detection

        Returns:
            Dict with: format, sequences (if FASTA), variants (if VCF/text)
        """
        result = {"format": "unknown", "sequences": [], "variants": []}

        # Detect FASTA
        if file_content.strip().startswith(">") or filename.endswith((".fasta", ".fa", ".fna")):
            result["format"] = "fasta"
            result["sequences"] = self.parse_fasta(file_content)
            return result

        # Detect VCF
        if filename.endswith(".vcf") or file_content.strip().startswith("##fileformat=VCF"):
            result["format"] = "vcf"
            result["variants"] = self.parse_variants(file_content)
            return result

        # Default: try variant parsing
        result["format"] = "text"
        result["variants"] = self.parse_variants(file_content)
        return result

    def format_for_prompt(
        self,
        sequences: list[dict] = None,
        variants: list[dict] = None,
    ) -> str:
        """
        Format parsed genomic data into a string for LLM prompt injection.

        Args:
            sequences: Parsed FASTA sequences
            variants: Parsed variants

        Returns:
            Formatted string describing the genetic data
        """
        parts = []

        if sequences:
            parts.append("## Sequence Data")
            for seq in sequences[:3]:  # Limit to 3 sequences
                parts.append(
                    f"- Sequence: {seq['id']} ({seq['length']} bp, "
                    f"GC content: {seq['gc_content']:.1%})"
                )
                # Include first 100 chars of sequence for context
                if seq["length"] > 100:
                    parts.append(f"  Preview: {seq['sequence'][:100]}...")
                else:
                    parts.append(f"  Full: {seq['sequence']}")

        if variants:
            parts.append("## Variant Data")
            for var in variants[:10]:  # Limit to 10 variants
                if var["format"] == "HGVS":
                    parts.append(
                        f"- {var['gene']}:{var['change_type']}.{var['change']} (HGVS)"
                    )
                elif var["format"] == "VCF":
                    parts.append(
                        f"- {var['chromosome']}:{var['position']} "
                        f"{var['reference']}>{var['alternate']} (VCF)"
                    )
                else:
                    parts.append(f"- {var['description']}")

        if not parts:
            return "No genetic/variant data provided."

        return "\n".join(parts)

    @staticmethod
    def _gc_content(seq) -> float:
        """Calculate GC content of a sequence."""
        seq_str = str(seq).upper()
        if not seq_str:
            return 0.0
        gc_count = seq_str.count("G") + seq_str.count("C")
        return gc_count / len(seq_str)
