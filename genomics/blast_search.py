"""
BLAST Search — NCBI BLAST integration via Biopython for sequence similarity search.

Performs remote BLAST queries against NCBI databases and returns parsed results
with alignment scores, e-values, and hit descriptions for genomic context.
"""

import io
import logging
from typing import Optional

from Bio.Blast import NCBIWWW, NCBIXML

logger = logging.getLogger(__name__)


class BlastSearch:
    """NCBI BLAST sequence similarity search via Biopython."""

    SUPPORTED_PROGRAMS = ["blastn", "blastp", "blastx", "tblastn", "tblastx"]
    SUPPORTED_DATABASES = ["nt", "nr", "refseq_rna", "refseq_protein", "swissprot"]

    def __init__(self):
        self._last_results = None

    def search(
        self,
        sequence: str,
        program: str = "blastn",
        database: str = "nt",
        max_hits: int = 10,
        e_value_threshold: float = 0.05,
    ) -> dict:
        """
        Run a BLAST search against NCBI databases.

        Args:
            sequence: Nucleotide or protein sequence to search
            program: BLAST program (blastn, blastp, blastx, tblastn, tblastx)
            database: NCBI database to search (nt, nr, refseq_rna, etc.)
            max_hits: Maximum number of hits to return
            e_value_threshold: E-value cutoff for significance

        Returns:
            Dict with: query_info, hits, summary
        """
        if program not in self.SUPPORTED_PROGRAMS:
            return {"error": f"Unsupported BLAST program: {program}. Use: {self.SUPPORTED_PROGRAMS}"}

        if database not in self.SUPPORTED_DATABASES:
            return {"error": f"Unsupported database: {database}. Use: {self.SUPPORTED_DATABASES}"}

        # Clean sequence
        clean_seq = self._clean_sequence(sequence)
        if len(clean_seq) < 10:
            return {"error": "Sequence too short. Minimum 10 residues required."}

        try:
            logger.info(
                f"Running BLAST: program={program}, db={database}, "
                f"seq_length={len(clean_seq)}"
            )

            # Submit BLAST query to NCBI
            result_handle = NCBIWWW.qblast(
                program=program,
                database=database,
                sequence=clean_seq,
                hitlist_size=max_hits,
                expect=e_value_threshold,
            )

            # Parse XML results
            blast_records = NCBIXML.parse(result_handle)
            blast_record = next(blast_records)
            result_handle.close()

            # Extract hits
            hits = self._parse_hits(blast_record, max_hits)

            result = {
                "query_info": {
                    "program": program,
                    "database": database,
                    "query_length": len(clean_seq),
                    "num_hits": len(hits),
                },
                "hits": hits,
                "summary": self._generate_summary(hits),
            }

            self._last_results = result
            logger.info(f"BLAST search complete: {len(hits)} hits found.")
            return result

        except Exception as e:
            logger.error(f"BLAST search failed: {e}")
            return {
                "error": str(e),
                "query_info": {"program": program, "database": database},
                "hits": [],
                "summary": f"BLAST search failed: {e}",
            }

    def _parse_hits(self, blast_record, max_hits: int) -> list[dict]:
        """Parse BLAST XML record into structured hit dicts."""
        hits = []

        for alignment in blast_record.alignments[:max_hits]:
            best_hsp = alignment.hsps[0] if alignment.hsps else None
            if not best_hsp:
                continue

            hit = {
                "title": alignment.title[:200],
                "accession": alignment.accession,
                "length": alignment.length,
                "e_value": best_hsp.expect,
                "score": best_hsp.score,
                "bit_score": best_hsp.bits,
                "identity_percent": (
                    (best_hsp.identities / best_hsp.align_length * 100)
                    if best_hsp.align_length > 0
                    else 0
                ),
                "alignment_length": best_hsp.align_length,
                "query_coverage": {
                    "start": best_hsp.query_start,
                    "end": best_hsp.query_end,
                },
                "subject_coverage": {
                    "start": best_hsp.sbjct_start,
                    "end": best_hsp.sbjct_end,
                },
            }
            hits.append(hit)

        return hits

    def _generate_summary(self, hits: list[dict]) -> str:
        """Generate a human-readable summary of BLAST results."""
        if not hits:
            return "No significant hits found."

        top = hits[0]
        return (
            f"Top hit: {top['title'][:100]} "
            f"(E-value: {top['e_value']:.2e}, "
            f"Identity: {top['identity_percent']:.1f}%, "
            f"Score: {top['bit_score']:.1f} bits). "
            f"Total significant hits: {len(hits)}."
        )

    def format_for_prompt(self, results: Optional[dict] = None) -> str:
        """
        Format BLAST results into a string for LLM prompt injection.

        Args:
            results: BLAST results dict from search(). Uses last results if None.

        Returns:
            Formatted context string
        """
        results = results or self._last_results
        if not results or "error" in results:
            return "No BLAST results available."

        hits = results.get("hits", [])
        if not hits:
            return "BLAST search returned no significant hits."

        parts = [
            f"## BLAST Results ({results['query_info']['program']} vs {results['query_info']['database']})",
            f"Query length: {results['query_info']['query_length']} residues",
            f"Significant hits: {len(hits)}\n",
        ]

        for i, hit in enumerate(hits[:5], 1):  # Top 5 only for token efficiency
            parts.append(
                f"**Hit {i}**: {hit['title'][:120]}\n"
                f"  - Accession: {hit['accession']}\n"
                f"  - E-value: {hit['e_value']:.2e} | "
                f"Identity: {hit['identity_percent']:.1f}% | "
                f"Score: {hit['bit_score']:.0f} bits"
            )

        return "\n".join(parts)

    @staticmethod
    def _clean_sequence(sequence: str) -> str:
        """Remove whitespace, numbers, and FASTA headers from sequence."""
        lines = sequence.strip().split("\n")
        clean_lines = [
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith(">")
        ]
        # Remove non-letter characters
        import re
        return re.sub(r"[^A-Za-z]", "", "".join(clean_lines))
