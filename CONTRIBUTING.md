# Contributing

Contributions in Arabic or English are welcome.

1. Fork and create a branch: `git checkout -b feat/short-name`
2. Install: `pip install -e ".[dev]"`
3. Run tests: `pytest -q`
4. Open a pull request.

Most useful contributions:

- **Claim patterns** (`listing_writer_ae/checks.py`, `CLAIM_RULES`): new Arabic or English phrasings of
  exaggerated claims, especially Gulf-dialect variants. Add a positive *and* a negative test case in
  `tests/test_checks.py`, so the rule doesn't flag neutral copy.
- **Compliance rules**: only with an official source (Dubai Land Department / RERA page, circular or guide).
  Add it to `listing_writer_ae/sources.py` with the date you read it. Press reports may be cited only as
  secondary sources and must be labelled as such.
- **Glossary** (`listing_writer_ae/glossary.py`): Arabic names of communities, views and features.
- Other emirates (Abu Dhabi ADREC, Sharjah, ...) as separate rule profiles.

Rules of the road:

- Keep the core package dependency-free (standard library only).
- Keep the LLM out of the decision: models write prose, code checks it and writes the compliance footer.
- Never commit real listings, real permit numbers, phone numbers or client data. Samples must have
  `"sample": true`, use `SAMPLE-` permit numbers and fictional names.
