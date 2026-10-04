# Known-seed sensitivity and scope test list — NOT EXECUTED

Use these records to test each final database-specific EI and EO route before the formal searches. Prior public reconnaissance established the records, but **no five-database query has been run in this task**. Thus platform-specific discoverability is `UNKNOWN`, not “found” or “missed.” A DOI/PubMed record seen in web reconnaissance does not establish that all five databases index it or that the draft query retrieves it.

For each seed, record separately:
1. Does the specific database contain the bibliographic record?
2. Does the exact EI route retrieve it?
3. Does the exact EO route retrieve it?
4. Was it retrieved through direct query, citation chasing, or an unrelated/manual route?
5. Does it meet v2 core A, support B, context, or separate frontier scope after human full-text screening?

| ID | Seed record | Role | Expected route(s) to test | Expected v2 eligibility decision | Why test it | Actual database detection |
|---|---|---|---|---|---|---|
| POS-A1 | Yu et al., *Molecular Choreography of Acute Exercise* (PMID 32470399; DOI 10.1016/j.cell.2020.04.043) | Positive acute multi-omic/immune-linked candidate | EI and EO | Core A candidate, subject to eligibility/full-text confirmation | Acute exercise and molecular profile; test retrieval through both the direct immune and omics blocks. | UNKNOWN — NOT TESTED |
| POS-A2 | *Single-Cell RNA Sequencing Analysis Reveals Exercise-Induced Transcriptional Dynamics in Half-Marathon Runners* (PMID 39817606; DOI 10.1111/sms.70018) | Positive acute immune-cell transcriptomics candidate | EI and EO | Core A candidate if baseline/comparator and population rules are met | Tests RNA-seq/single-cell terms and acute race wording. | UNKNOWN — NOT TESTED |
| POS-A3 | Wenzel et al., *Immunological Protein Signature During Acute Exercise* (PMID 41163346; DOI 10.1111/apha.70125) | Positive targeted immune-protein candidate | EI; EO is not required | Core A targeted-assay candidate | A targeted Olink PEA panel is not necessarily indexed as omics; it must be retrievable through EI. Prevent an incorrect assumption that all protein assays are “proteomics.” | UNKNOWN — NOT TESTED |
| POS-S1 | Xu et al., *Identification of Urinary Biomarkers for Exercise-Induced Immunosuppression by iTRAQ Proteomics* (PMID 32047808; DOI 10.1155/2020/3030793) | Positive search-sensitivity seed; boundary for v2 eligibility | EI and EO | Background/boundary unless timing can establish A or repeated-bout B | Strong title matches both routes, but repeated training and unknown final-bout timing do not automatically satisfy acute A/B. Pooled iTRAQ n and same-study ELISA are not screening search criteria. | UNKNOWN — NOT TESTED |
| POS-S2 | *Body Fluid Proteomic Landscape of Acute Exercise* (bioRxiv DOI 10.1101/2025.05.28.656705) | Positive frontier/preprint search-sensitivity seed | EO; EI if indexed metadata carries immune terms | Separate preprint/frontier register if substantive criteria are met; never peer-reviewed core by preprint status alone | Tests broad body-fluid omics and the separate preprint workflow. Coverage may vary by database. | UNKNOWN — NOT TESTED |
| POS-S3 | MoTrPAC, *Blood Biochemical Responses to Acute Exercise* (PMID 41835387; DOI 10.64898/2026.03.02.704798, v2) | Positive human acute multi-omics frontier seed | EI and EO if indexed metadata carries immune/omics terms | Separate frontier/preprint register; recheck peer-review status at formal search/update | Tests broad multi-omics coverage and cohort/version linkage; do not count as peer-reviewed core while preprint-only. | UNKNOWN — NOT TESTED |
| NEG-E1 | CIMA regular-physical-activity immune multi-omics study (PMID 42758809; bioRxiv lineage DOI 10.64898/2026.01.13.699221) | Negative eligibility/boundary seed; should often be discoverable | EI and EO | Background only: cross-sectional habitual activity, not acute A or repeated-bout B | Search sensitivity should not be reduced to exclude it; screening applies acute-exposure design. Published/preprint reports are one lineage, not independent cohorts. | UNKNOWN — NOT TESTED |
| NEG-E2 | MoTrPAC rat training multi-omic study, *Temporal dynamics of the multi-omic response to endurance exercise training* (DOI 10.1038/s41586-023-06877-w) | Negative eligibility/specificity seed | EO | Exclude from main human map: animal-only; may be retained as background | Broad E&O strategy may retrieve general exercise omics. Human eligibility belongs at screening, so do not apply a human limiter to search. | UNKNOWN — NOT TESTED |

## Interpreting test results

- “Positive” means an expected sensitive search seed, not a guarantee of core inclusion. Xu is intentionally positive for retrieval but a v2 eligibility boundary.
- “Negative eligibility” means the record is expected to be found and then excluded from the main A/B map; it is **not** a negative retrieval control.
- Actual discovery is database/platform-specific and must be recorded only after the test. Do not infer a query miss from absence in a database that does not index the source type/version.
- A title-lookup or exact DOI/PubMed lookup may confirm database presence but is a separate diagnostic; test the complete route query itself and save the exact results page/strategy history.
- Add additional independently identified seeds during pilot calibration, including null/negative exercise findings and non-English indexed records. Use a saved randomized seed for the separate 50-record human screening pilot.
