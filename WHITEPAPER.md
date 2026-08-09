# Sharia-AI: An Open, Auditable Toolkit for Sharia-Compliant Fintech Screening in the Arab World

**Working Paper — v0.1 (Alpha)**
**License: MIT** · **Status: Open Source, Community Draft**

---

## Abstract

Financial technology adoption across the Arab world has accelerated
sharply over the past decade, yet the tooling ecosystem for **Sharia
compliance verification** has not kept pace. Existing solutions are
predominantly proprietary, closed-methodology services that function as
black boxes: a company or instrument receives a compliant/non-compliant
label with little to no exposed reasoning, and almost none offer native,
linguistically-aware support for Arabic-language contracts. This paper
introduces **Sharia-AI**, an open-source toolkit combining rule-based
equity screening aligned with AAOIFI and major Islamic index
methodologies, an Arabic natural-language pipeline for detecting *riba*
(interest), *gharar* (excessive uncertainty), and *maysir* (speculation)
in contract text, and a transparent Zakat calculation engine. We describe
the system architecture, the linguistic challenges specific to Arabic
clitic morphology that a naive substring-matching approach fails to
handle correctly, our mitigation strategy, and the empirical validation
performed via a unit-test regression suite. We position this work as an
infrastructure contribution — not a fatwa-issuing authority — intended to
lower the barrier for businesses, researchers, and developers building
Sharia-compliant financial products.

**Keywords:** Islamic finance, Sharia compliance, regtech, Arabic NLP,
AAOIFI, Zakat computation, explainable AI, open-source fintech infrastructure.

---

## 1. Introduction

### 1.1 Motivation

Islamic finance is estimated to represent well over a trillion dollars in
global assets, with the Gulf Cooperation Council (GCC) states, the wider
Levant, and North Africa forming its economic and jurisprudential core.
Despite this scale, the software infrastructure available to companies
seeking to verify or maintain Sharia compliance remains fragmented. Three
structural gaps motivate this work:

1. **Absence of open, auditable screening tools.** Commercial Sharia
   screening services (index providers, compliance consultancies) rarely
   publish their scoring logic in a form developers can inspect, extend,
   or independently verify. This opacity is at odds with the very
   principle such tools are meant to serve: demonstrable, justifiable
   compliance.
2. **Underserved Arabic natural-language processing in fintech tooling.**
   General-purpose compliance and contract-analysis software is
   overwhelmingly built and validated against English-language corpora.
   Arabic's rich morphology — in particular the direct, space-free
   attachment of prepositions and conjunctions to nouns (clitics) —
   causes both false negatives (missed terms) and false positives
   (spurious matches inside unrelated words) when handled with naive
   text-matching techniques imported from Latin-script pipelines.
3. **Opaque compliance methodology.** Businesses frequently cannot
   articulate *why* an instrument was classified as compliant or
   non-compliant, which undermines trust with Sharia Supervisory Boards,
   investors, and regulators alike.

Sharia-AI addresses each of these gaps directly: it is fully open-source
under the MIT license, it implements an Arabic-aware detection pipeline
validated against known morphological edge cases, and every component
produces a rule-by-rule, human-readable justification rather than an
opaque score.

### 1.2 Scope and Non-Goals

This toolkit is explicitly **not** a fatwa-issuing system. It does not
claim jurisprudential authority, and its default thresholds reflect
commonly used index methodologies rather than a singular authoritative
ruling. We view it as **triage infrastructure**: a first-pass, explainable
filter intended to reduce the manual burden on compliance teams and
Sharia Supervisory Boards, who remain the final decision-making authority
in any real-world deployment.

---

## 2. Related Methodologies

The quantitative equity-screening thresholds implemented in this toolkit
are informed by three widely referenced methodological families:

- **AAOIFI Shari'ah Standard No. 21** (Financial Paper — Shares/Bonds),
  published by the Accounting and Auditing Organization for Islamic
  Financial Institutions, which provides guidance on permissible
  financial-ratio bounds for equity instruments.
- **Dow Jones Islamic Market (DJIM) Index Methodology**, one of the
  earliest and most widely cited index-level Sharia screening frameworks,
  combining sector-based exclusion with financial-ratio screening.
- **FTSE Shariah Global Equity Index Series — Ground Rules**, a
  comparable methodology with minor variations in ratio denominators
  (e.g., total assets versus market capitalization).

Our implementation follows the **market-capitalization-denominator**
convention (consistent with DJIM) for simplicity and transparency, while
exposing all thresholds as configurable parameters (`ScreeningThresholds`)
so that an adopting institution can align with whichever methodology its
own Sharia Supervisory Board prefers — including asset-denominator
variants, without modifying the core screening logic.

We note explicitly that these methodologies are **not** in full consensus
with one another, nor with the more conservative thresholds used by some
individual national Sharia boards. This is a known and accepted
limitation of *any* rule-based screening system, and is documented in
`docs/compliance_methodology.md` alongside guidance for institutions
wishing to override defaults.

---

## 3. System Architecture

### 3.1 Design Principles

The system is organized around four ordered priorities, described in
detail in `docs/architecture.md`:

1. **Explainability before raw accuracy** — every result object exposes
   its constituent checks individually.
2. **Offline-first operation** — the core logic (screening, NLP, Zakat,
   pipeline orchestration) depends only on the Python standard library,
   supporting deployment in data-sensitive, air-gapped financial
   environments.
3. **Extensibility without rewriting** — machine-learning components
   attach via structural typing (`Protocol`), not inheritance, so a
   future transformer-based classifier can be added without touching
   pipeline or API code.
4. **Configuration over hardcoding** — all financial thresholds are
   parameters, not embedded constants.

### 3.2 Component Overview

| Component | Responsibility |
|---|---|
| `screening.equity_screener` | Two-stage AAOIFI/DJIM-aligned screening: sectoral exclusion + four financial ratios. |
| `nlp.riba_detector` | Hybrid lexical + optional ML detection of riba/gharar/maysir clauses in Arabic contract text. |
| `zakat.zakat_calculator` | Dynamic Nisab-threshold Zakat computation over declared liquid and near-liquid assets. |
| `pipelines.compliance_pipeline` | Orchestrates the above into a single, JSON-exportable `CompanyComplianceReport`. |
| `api.main` | REST exposure of the pipeline via FastAPI, with auto-generated interactive documentation. |

A full component diagram is provided in `docs/architecture.md`.

---

## 4. The Arabic Clitic Problem in Contract Screening

### 4.1 Problem Statement

Arabic attaches a closed class of single-letter prepositions and
conjunctions — *wa* (و, "and"), *fa* (ف, "then/so"), *bi* (ب, "with/by"),
*ka* (ك, "like/as"), *li* (ل, "for/to") — directly to the following word,
without a space, alongside the definite article *al* (ال). A term such as
*fā'ida* (فائدة, "interest") therefore surfaces in running text most
often as *bi-fā'ida* (بفائدة, "with interest") — a distinct token from
the dictionary form. A naive lexicon-matching approach that checks only
for exact token equality suffers substantial recall loss on precisely the
clauses most relevant to compliance review.

The inverse failure mode is equally serious. A naive **substring**-based
matcher, applied to counter the recall problem above, introduces
dangerous false positives: the three-letter root *r-b-a* (ربا, "riba",
i.e. interest) is a literal substring of *al-arbāḥ* (الأرباح, "the
profits") — an entirely unrelated and, in fact, Sharia-*permitted* term
central to profit-and-loss-sharing contracts (*mudaraba*, *musharaka*).
A substring-matching system would flag a standard profit-sharing clause
as an interest-bearing one, actively undermining the tool's purpose.

### 4.2 Our Approach

We resolve this with word-boundary tokenization combined with a
**candidate-variant generation** strategy (`clitic_variants()`), applied
only to the *observed* text tokens — never to the canonical lexicon
terms, which remain uncorrupted reference forms. For each token
encountered in a contract, we generate a small set of candidate base
forms by conditionally stripping a single leading one-letter
clitic, the definite article, or both in combination, subject to a
minimum residual-length constraint to avoid over-stripping short roots.
A lexicon term is considered matched only if it equals one of these
candidate forms — and multi-word lexicon phrases are matched as
contiguous token sequences, not as raw substrings.

This design was validated empirically during development: an initial
substring-matching implementation incorrectly flagged a standard
profit-and-loss-sharing clause containing *al-arbāḥ* (profits) as
riba-related. The regression is now encoded as a permanent unit test
(`test_no_false_positive_on_profits_word`), and a companion test verifies
that the clitic-stripping mechanism correctly recovers *bi-fā'ida* as a
match for the *fā'ida* lexicon entry
(`test_detects_riba_with_attached_preposition`). We consider this class
of error — high-confidence false positives on legitimate Islamic
finance terminology — one of the more consequential failure modes for
any Arabic-language compliance tool, and treat its prevention as a first-
class design constraint rather than an edge case.

### 4.3 Limitations

The lexical detector remains, by construction, unable to recognize
paraphrased or indirect formulations of interest-bearing arrangements
that do not use its known vocabulary. Section 3.2's `RibaClassifierProtocol`
interface is designed specifically to allow a future fine-tuned Arabic
transformer model (e.g., AraBERT or CAMeLBERT variants) to augment —
not replace — the deterministic lexical layer, preserving auditability
while extending semantic recall. This integration is scoped for a future
release (see `docs/roadmap.md`).

---

## 5. Zakat Computation Methodology

Zakat is computed following the majority classical interpretation: **2.5%
of net zakatable wealth**, assessed against a **Nisab** threshold derived
from the lower of the gold-equivalent (85g) or silver-equivalent (595g)
value at current market prices — the conventional choice that favors
Zakat recipients by lowering the qualifying threshold, and the more
commonly adopted convention among contemporary Zakat calculators. Both
the metal-price inputs and the choice between gold/silver/lower-of-both
are exposed as constructor parameters (`ZakatCalculator`), avoiding silent
assumptions about metal prices that would otherwise become stale.

Eligible assets — cash, collectible receivables, trade inventory at
market value, Sharia-compliant investments, and precious metals — are
summed and reduced by short-term liabilities before the Nisab comparison.
We explicitly document, both in code comments and in
`docs/compliance_methodology.md`, that this implementation does **not**
cover more complex cases such as agricultural Zakat, livestock Zakat, or
mixed long-term partnership assets, which require dedicated jurisprudential
consultation beyond the scope of an automated calculator.

---

## 6. Validation

Given the offline-first design constraint, validation was performed via a
16-case unit-test suite (`tests/`, `unittest`, standard library only —
no network dependency), covering:

- Equity screening: compliant baseline, sectoral exclusion, excessive
  debt ratio, income-purification triggering, and division-by-zero
  robustness on degenerate (zero market cap) inputs.
- Contract screening: correct detection of riba and maysir keywords,
  a clean-text negative control, an empty-input edge case, the
  *al-arbāḥ* false-positive regression described in Section 4.2, and
  correct clitic-attached term recovery.
- Zakat computation: below-Nisab null result, above-Nisab 2.5%
  calculation, liability deduction, correct lower-of-gold/silver Nisab
  selection, and negative-net-wealth clamping.

All 16 tests pass in the current release. We regard this suite less as a
statement of completeness and more as a **living regression contract**:
contributors extending the lexicon or thresholds are required (see
`docs/contributing.md`) to add a corresponding test, including a negative
case guarding against new false positives — the same discipline that
surfaced and resolved the *al-arbāḥ* issue during initial development.

---

## 7. Discussion: Positioning as Infrastructure, Not Authority

We deliberately frame Sharia-AI as **infrastructure** rather than as a
compliance *authority*. Every report generated by the pipeline is labeled
"subject to Sharia Supervisory Board review," every threshold is
overridable, and the codebase and documentation consistently avoid
issuing categorical jurisprudential claims. This positioning reflects a
considered trade-off: a tool that is maximally useful to developers and
businesses building Sharia-compliant products, while remaining
epistemically honest about the limits of what rule-based and NLP-based
screening can determine. We view this as consistent with the broader
principle that automated systems interacting with religious and legal
interpretation should support, not supplant, qualified human judgment.

---

## 8. Future Work

Planned extensions, detailed in `docs/roadmap.md`, include: API
authentication for multi-tenant deployment; integration of a fine-tuned
Arabic transformer classifier for semantic-level contract scoring;
dedicated screening modules for Sukuk (Islamic bonds) and Takaful (Islamic
insurance) structures; PDF export for audit-ready reporting; and — pending
availability of a jurist-annotated dataset — a published benchmark corpus
of Arabic financial-contract clauses to support reproducible research in
Arabic legal NLP beyond this toolkit's immediate scope.

---

## 9. Conclusion

Sharia-AI contributes an open, explainable, and Arabic-linguistically
aware toolkit to a fintech tooling landscape that has, to date, been
dominated by closed and often linguistically under-adapted solutions. By
grounding equity screening in documented AAOIFI/DJIM-aligned methodology,
solving the specific and previously under-addressed Arabic clitic-matching
problem with an auditable, tested approach, and exposing every
compliance decision as an inspectable set of rule checks, the project
aims to lower the barrier for businesses across the Arab world to build,
audit, and trust Sharia-compliant financial products — while explicitly
and consistently deferring final jurisprudential authority to qualified
human Sharia Supervisory Boards.

---

## References (methodological, non-exhaustive)

- Accounting and Auditing Organization for Islamic Financial Institutions
  (AAOIFI), *Shari'ah Standard No. 21: Financial Paper (Shares and Bonds)*.
- S&P Dow Jones Indices, *Dow Jones Islamic Market Index Methodology*.
- FTSE Russell, *FTSE Shariah Global Equity Index Series — Ground Rules*.

## Citation

See [`CITATION.cff`](./CITATION.cff) for machine-readable citation
metadata.

---

*This document is a community working paper distributed under the MIT
license alongside the accompanying source code. It does not constitute
religious, legal, or financial advice.*
