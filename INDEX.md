# RID_Completed — Index

This folder contains the **completed RID proof bundle**: one main document and this index. No more than 10 documents are placed here.

## Start here

- **RID_Complete.md** — Single all-in-one document: framework, implementation, internal and external consistency, application, reproducibility, limitations, references, appendix (formulas), and verification checklist. Use this for submission or review.

## Where scripts and code live

All verification scripts and the RID package live in the **parent directory** `RID/` (sibling to this folder). Run commands from the **project root** (the directory that contains `RID/`, e.g. `L:\Steel_Brain`).

| Script | Purpose |
|--------|---------|
| `python -m RID --extract-pdf` | Extract text from 9 PDFs → RID/extracted_text/ |
| `python RID/run_all_verification.py` | Full verification (check, pytest, doc verifier, example, external consistency); writes report. Run `--extract-pdf` first. |
| `python RID/verify_accomplishments_doc.py` | Doc vs code (internal + external doc–code consistency) |
| `python RID/verify_external_consistency.py` | Code vs source specs (external consistency) |
| `python RID/check_artifact_completeness.py` | All required artifacts present and report passed |

See **RID_Complete.md** Section 10 for the full checklist and Section 4 for the three consistency layers (internal, doc–code, code–spec).
