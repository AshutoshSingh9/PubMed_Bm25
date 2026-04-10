import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import io

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from genomics.variant_parser import VariantParser
from genomics.blast_search import BlastSearch
from genomics.variant_annotator import VariantAnnotator

# ── 1. Variant Parser Tests ──

def test_parse_hgvs():
    parser = VariantParser()
    variants = parser.parse_variants("BRCA1:c.5266dupC\nTP53:p.R248W")
    assert len(variants) == 2
    assert variants[0] == {
        "format": "HGVS",
        "gene": "BRCA1",
        "change_type": "c",
        "change": "5266dupC",
        "raw": "BRCA1:c.5266dupC"
    }
    assert variants[1]["gene"] == "TP53"

def test_parse_vcf():
    parser = VariantParser()
    variants = parser.parse_variants("chr17 7577120 G A")
    assert len(variants) == 1
    assert variants[0] == {
        "format": "VCF",
        "chromosome": "chr17",
        "position": 7577120,
        "reference": "G",
        "alternate": "A",
        "raw": "chr17 7577120 G A"
    }

def test_parse_fasta():
    parser = VariantParser()
    fasta_block = ">seq1 description\nATGCGT\n>seq2\nCGTA"
    seqs = parser.parse_fasta(fasta_block)
    assert len(seqs) == 2
    assert seqs[0]["id"] == "seq1"
    assert seqs[0]["sequence"] == "ATGCGT"
    assert seqs[0]["length"] == 6

# ── 2. BlastSearch Mocks ──

DUMMY_BLAST_XML = """<?xml version="1.0"?>
<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "http://www.ncbi.nlm.nih.gov/dtd/NCBI_BlastOutput.dtd">
<BlastOutput>
  <BlastOutput_program>blastn</BlastOutput_program>
  <BlastOutput_db>nt</BlastOutput_db>
  <BlastOutput_query-def>No definition line</BlastOutput_query-def>
  <BlastOutput_query-len>12</BlastOutput_query-len>
  <BlastOutput_param>
    <Parameters>
      <Parameters_expect>0.05</Parameters_expect>
      <Parameters_sc-match>1</Parameters_sc-match>
      <Parameters_sc-mismatch>-2</Parameters_sc-mismatch>
      <Parameters_gap-open>0</Parameters_gap-open>
      <Parameters_gap-extend>0</Parameters_gap-extend>
      <Parameters_filter>L;m;</Parameters_filter>
    </Parameters>
  </BlastOutput_param>
  <BlastOutput_iterations>
    <Iteration>
      <Iteration_iter-num>1</Iteration_iter-num>
      <Iteration_query-ID>Query_1</Iteration_query-ID>
      <Iteration_query-def>No definition line</Iteration_query-def>
      <Iteration_query-len>12</Iteration_query-len>
      <Iteration_hits>
        <Hit>
          <Hit_num>1</Hit_num>
          <Hit_id>gi|12345|ref|NM_000123.4|</Hit_id>
          <Hit_def>Homo sapiens dummy gene (DUMMY), mRNA</Hit_def>
          <Hit_accession>NM_000123</Hit_accession>
          <Hit_len>5000</Hit_len>
          <Hit_hsps>
            <Hsp>
              <Hsp_num>1</Hsp_num>
              <Hsp_bit-score>50.5</Hsp_bit-score>
              <Hsp_score>100</Hsp_score>
              <Hsp_evalue>0.001</Hsp_evalue>
              <Hsp_query-from>1</Hsp_query-from>
              <Hsp_query-to>12</Hsp_query-to>
              <Hsp_hit-from>100</Hsp_hit-from>
              <Hsp_hit-to>111</Hsp_hit-to>
              <Hsp_query-frame>1</Hsp_query-frame>
              <Hsp_hit-frame>1</Hsp_hit-frame>
              <Hsp_identity>12</Hsp_identity>
              <Hsp_positive>12</Hsp_positive>
              <Hsp_gaps>0</Hsp_gaps>
              <Hsp_align-len>12</Hsp_align-len>
              <Hsp_qseq>ATGCGTATGCGT</Hsp_qseq>
              <Hsp_hseq>ATGCGTATGCGT</Hsp_hseq>
              <Hsp_midline>||||||||||||</Hsp_midline>
            </Hsp>
          </Hit_hsps>
        </Hit>
      </Iteration_hits>
      <Iteration_stat>
        <Statistics>
          <Statistics_db-num>100</Statistics_db-num>
          <Statistics_db-len>1000000</Statistics_db-len>
          <Statistics_hsp-len>0</Statistics_hsp-len>
          <Statistics_eff-space>0</Statistics_eff-space>
          <Statistics_kappa>0.41</Statistics_kappa>
          <Statistics_lambda>0.625</Statistics_lambda>
          <Statistics_entropy>0.85</Statistics_entropy>
        </Statistics>
      </Iteration_stat>
    </Iteration>
  </BlastOutput_iterations>
</BlastOutput>
"""

@patch('genomics.blast_search.NCBIWWW.qblast')
def test_blast_search(mock_qblast):
    # Mock network call to return local string buffer
    mock_qblast.return_value = io.StringIO(DUMMY_BLAST_XML)
    
    blaster = BlastSearch()
    result = blaster.search("ATGCGTATGCGT", program="blastn", database="nt", max_hits=1)
    
    assert "error" not in result
    assert result["query_info"]["num_hits"] == 1
    assert result["hits"][0]["accession"] == "NM_000123"
    assert result["hits"][0]["e_value"] == 0.001
    assert result["hits"][0]["bit_score"] == 50.5
    assert result["hits"][0]["identity_percent"] == 100.0

# ── 3. Variant Annotator ──

def test_variant_annotator_format():
    annotator = VariantAnnotator()
    # Mock ClinVar fallback testing format response directly
    sample_variant = {"gene": "BRCA1", "change": "c.5266dupC"}
    ann = annotator.annotate([sample_variant])
    
    assert isinstance(ann, list)
    assert ann[0]["gene"] == "BRCA1"
    
    prompt_str = annotator.format_for_prompt(ann)
    assert "BRCA1" in prompt_str
