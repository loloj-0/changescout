# Architecture

## Product Principle

ChangeScout is a lead prioritization system, not a final relevance authority.

The architecture is designed around a human in the loop review workflow.

The system should identify, rank, and explain candidate sources that may indicate TLM relevant geometry changes.

It should not automatically decide that TLM must be updated.

It should not automatically edit TLM data.

A lead is therefore an actionable review candidate, not a confirmed change.

This principle affects the full architecture:

1. hard filtering must preserve plausible infrastructure content
2. scoring is a ranking signal, not a final classifier
3. classification is evaluated as review support
4. geographic hints are review aids, not verified project locations
5. LLM methods must support triage and explanation rather than replacing domain review

## MVP Scope Decision

The operational MVP monitoring scope is limited to one active canton per run.

### Current operational scope

The active canton is defined by `config/scope.yaml`.

Runtime source selection is controlled by the active scope configuration and the referenced source registry.

### Evaluation corpus

The current annotation and evaluation corpus contains documents from multiple cantons.

This corpus is used to test scoring, classification, and lead generation robustness across different official source styles.

This does not change the operational runtime design.

### Scope policy

The system monitors only manually curated official canton level web sources for the active canton.

The purpose of monitoring is not to directly confirm finished real world changes.

The purpose is to generate deterministic leads for potential TLM relevant changes that can be prioritized for manual validation.

### Included in MVP

* one active canton per configured monitoring run
* manual source curation
* official canton level web sources
* project and publication pages that may indicate planned, ongoing, or completed infrastructure changes
* versioned scope configuration in Git
* deterministic source selection from config
* deterministic candidate discovery from configured sources
* deterministic downstream lead generation from processed content

### Explicitly excluded from MVP

* municipalities
* unofficial media sources
* associations and private organizations
* social media channels
* automatic source discovery
* cross canton runtime monitoring
* automatic confirmation that a detected lead corresponds to a finished TLM relevant change

### Rationale

The MVP prioritizes determinism, reviewability, and low operational complexity.

A narrow and explicit source boundary is required so that the same configuration always resolves to the same source set.

For TLM relevant changes, official project and infrastructure pages are often more useful than generic news pages because they provide earlier and more persistent signals about possible future geometry changes.

The MVP therefore focuses on lead generation instead of final change confirmation.

This allows earlier awareness of potentially relevant real world developments, while keeping manual review in the loop.

### Extensibility

The configuration model must be designed so that additional cantons can be added later without changing the core logic.

Canton specific scope and source registries are data driven, not hardcoded.

## Configuration Model

The monitoring configuration is separated into scope definition and source registry.

### Scope definition

The file `config/scope.yaml` defines the active monitoring context for a run.

Current fields:

* `version`: integer representing the schema version of the scope configuration
* `canton_id`: selected canton identifier
* `languages`: allowed language set for the monitoring scope
* `time_window_days`: temporal lookback window applied during data collection and filtering steps
* `source_registry`: name of the source registry file to load
* `source_policy`: policy label describing which source types are intended to be allowed

This file defines the scope of monitoring, but not the concrete source endpoints.

### Source registry

The file `config/sources/<registry>.yaml` defines the concrete source entries for the selected registry.

The source registry is the single explicit source of truth for which official sources belong to the monitored source set.

It defines the concrete source endpoints and discovery rules that are allowed for the active monitoring scope.

Only sources explicitly listed in the versioned source registry may be used by the pipeline.

Each source entry contains:

* `source_id`
* `name`
* `base_url`
* `crawl_type`
* `crawl_frequency_hours`
* `active`
* optional `include_patterns` for pattern based discovery sources

For `html_pattern` sources, `include_patterns` is required and defines which discovered URLs belong to the monitored source surface.

### Source inclusion rule

A source is included in the monitoring scope only if it is explicitly defined in the versioned source registry.

For the MVP, the `source_policy` field is descriptive and does not automatically include or exclude sources.

All inclusion decisions are made through manual curation of the source registry.

### Determinism requirement

Given the same version of `config/scope.yaml` and the same source registry file, the system must resolve the identical set of active sources in a stable and reproducible order.

The stable order of resolved sources is defined by sorting on `source_id`.

Determinism applies to the transformation logic.

External source content may change over time and is not controlled by the system.

### Reproducibility

Each execution of the pipeline must persist a snapshot of the resolved scope and active source set.

This ensures that every run can be traced back to the exact configuration used.

## Operational Run Orchestration

### Responsibility

The operational run orchestration coordinates the deterministic monitoring stages for one selected source registry.

It is responsible for run scoped execution and artifact layout.

It is not responsible for evaluation dataset construction, model comparison, LLM evaluation, or report package generation.

### Entry point

The operational entry point is:

```bash
PYTHONPATH=src python -m changescout.cli run \
  --config-dir config \
  --source-registry zh \
  --canton-id zh \
  --run-id run_001
```

The `source_registry` and `canton_id` arguments may override the default values from `config/scope.yaml` for the current run.

The override is recorded in the run scope snapshot.

It does not modify the configuration files on disk.

### Candidate selection modes

Operational lead generation supports two selection modes.

| Mode | Input | Meaning |
|---|---|---|
| `score_only` | `scored.jsonl` | Select leads with `thematic_score >= lead_threshold`. |
| `score_or_tfidf` | `scored_with_tfidf.jsonl` | Select leads if `thematic_score >= lead_threshold` or `tfidf_actionable_probability >= tfidf_threshold`. |

`score_only` is the default mode and preserves the deterministic baseline behavior.

`score_or_tfidf` requires an explicitly provided TF IDF model artifact.

LLM predictions are not used as hard exclusion signals.

### Run scoped layout

Operational outputs are written under:

`artifacts/runs/<run_id>/`

The expected layout is:

```text
artifacts/runs/<run_id>/
  scope_snapshot.json
  discovery.jsonl
  crawl.jsonl
  cleaned.jsonl
  excluded.jsonl
  filtered.jsonl
  filtered_excluded.jsonl
  scored.jsonl
  scored_with_tfidf.jsonl
  leads.jsonl
  leads.csv
  leads_with_locations.jsonl
  leads_with_locations.csv
  leads_with_geoadmin_locations.jsonl
  leads_with_geoadmin_locations.csv
  monitoring_summary.json
  monitoring_summary.md
  reports/
    discovery_report.json
    crawl_report.json
    cleaning_report.json
    filter_report.json
    scoring_report.json
    tfidf_inference_report.json
    lead_generation_report.json
    location_hinting_report.json
    geoadmin_location_hinting_report.json
  metadata/
    run_metadata.json
  logs/
    run.log
```

Some files are optional and are written only when the corresponding feature is enabled.

Raw HTML remains stored under:

`data/crawling/<run_id>/<source_id>/<content_hash>.html`

### Stage sequence

The operational pipeline currently runs:

1. resolve scope and active sources
2. write scope snapshot
3. discover URLs from active `html_pattern` sources
4. crawl discovered URLs
5. clean crawled HTML into normalized documents
6. apply conservative hard filtering
7. compute thematic scores
8. optionally apply TF IDF actionable inference
9. select leads with `score_only` or `score_or_tfidf`
10. enrich selected leads with local location hints
11. optionally enrich selected leads with GeoAdmin hints
12. write run metadata and stage reports
13. optionally build a scoped monitoring summary

The stage sequence reuses the existing stage implementations.

The orchestration layer does not duplicate scoring, filtering, crawling, enrichment, or candidate selection logic.

### Separation from evaluation

Operational runs must not write to:

`data/annotation/evaluation/`

Frozen annotation datasets and evaluation artifacts remain separate from operational monitoring.

This separation prevents production or inference runs from overwriting benchmark datasets, method comparisons, hybrid lead selection reports, or LLM explainability evaluation outputs.

### Separation from MVP reproduction

`scripts/operational/run.sh` remains the MVP reproduction entry point.

It reproduces the historical baseline workflow from selected existing artifacts.

It may reference existing canton specific artifact names because its purpose is reproduction.

The operational pipeline must not depend on those hardcoded artifact names.

### Metadata

Each operational run writes:

`artifacts/runs/<run_id>/metadata/run_metadata.json`

The metadata contains:

* run id
* status
* timestamps
* git commit
* git status
* resolved scope
* stage output paths
* report paths
* log path

The metadata allows a completed run to be inspected without relying on implicit file naming conventions.

### Monitoring summary

A scoped monitoring summary can be generated with:

```bash
PYTHONPATH=src python scripts/operational/build_monitoring_summary.py --run-id <run_id>
```

It writes:

* `artifacts/runs/<run_id>/monitoring_summary.json`
* `artifacts/runs/<run_id>/monitoring_summary.md`

The summary reads scoped run metadata and scoped stage reports.

Missing reports generate warnings instead of crashes.

### Acceptance status

The current implementation has been validated with multiple registries.

This confirms that the core pipeline is no longer tied to manually wired canton specific artifact sets for operational runs.

## Discovery Architecture

### Responsibility

The discovery step is responsible for identifying candidate URLs from configured official canton sources.

Discovery operates only on source entry points and does not interpret page content.

### Discovery input contract

Discovery operates only on a subset of fields from the source registry.

Required fields per source:

* `source_id`
* `base_url`
* `crawl_type`
* `active`

Additional required fields for `html_pattern` sources:

* `include_patterns`

Optional fields ignored by discovery:

* `name`
* `crawl_frequency_hours`

### Source selection for discovery

Only sources fulfilling all of the following are passed to discovery:

* `active` is true
* `crawl_type` equals `html_pattern`

All other sources are ignored by discovery.

### Assumptions and limitations

The MVP discovery model assumes:

* a single HTML entry point per source
* static HTML content accessible via HTTP GET
* no JavaScript rendering required
* no pagination handling
* no API based discovery

Sources that do not satisfy these constraints are not supported in the MVP.

### What discovery does

* fetch HTML from each active source `base_url`
* extract hyperlinks from the HTML
* normalize and canonicalize URLs
* filter URLs using `include_patterns` for `html_pattern` sources
* remove duplicate URLs within a run
* attach metadata such as `source_id` and `discovered_at`
* persist discovered URLs as structured records

### What discovery does not do

* no fetching of discovered project pages
* no extraction of page content
* no semantic relevance filtering
* no scoring or ranking
* no classification
* no geographic reasoning

### HTML fetch helper

Discovery uses a dedicated HTML fetch helper to retrieve the source page at `base_url`.

The fetch helper is responsible only for technical HTTP access.

Expected behavior:

* perform an HTTP GET request to the configured `base_url`
* use a defined timeout
* return HTML text only for successful responses
* decode response content as UTF 8 if no explicit charset is declared
* treat non successful HTTP status codes as failures
* surface network and request errors explicitly to the caller

The fetch helper must not silently suppress failures.

Failure handling and logging remain the responsibility of the discovery step.

### MVP fetch limitations

For the MVP, the fetch helper assumes:

* standard HTTP GET access is sufficient
* one request per source entry point is sufficient
* no JavaScript rendering is required
* no retry logic is required
* no authentication is required

### Link extraction

Discovery uses a dedicated HTML parsing step to extract hyperlink references from fetched source HTML.

The link extraction step is responsible for reading raw `href` values from anchor elements.

Expected behavior:

* parse HTML content
* extract `href` values from `<a>` elements
* ignore missing or empty `href` attributes
* ignore fragment only references
* ignore non HTTP navigation schemes such as `mailto:`, `javascript:`, and `tel:`

The extraction step returns raw link candidates only.

It must not perform URL normalization, pattern filtering, deduplication, or semantic relevance decisions.

### URL normalization

Discovery uses a dedicated normalization step to convert raw link candidates into stable absolute URLs.

Expected behavior:

* resolve relative links against the configured `base_url`
* preserve absolute HTTP and HTTPS links
* remove URL fragments
* discard unusable or invalid link values
* return canonical absolute URL strings

For the MVP, normalization must not apply semantic filtering.

### Include pattern filtering

Discovery uses `include_patterns` to restrict normalized URLs to the configured source surface.

Expected behavior:

* each normalized URL is checked against the configured `include_patterns`
* a URL is retained if it matches at least one configured pattern
* a URL is discarded if it matches no configured pattern
* matching is deterministic and string based

For the MVP, `include_patterns` are interpreted as substring matches against the normalized URL string.

No regex evaluation, semantic interpretation, or content based filtering is applied at this step.

### Deduplication

Discovery applies deduplication after normalization and include pattern filtering.

Deduplication is performed within a single discovery run and within each `source_id`.

Expected behavior:

* identical normalized URLs discovered from the same source are retained only once
* identical normalized URLs discovered from different sources are kept as separate records
* deduplication must preserve stable output order

For the MVP, URL equality is determined by exact string equality after normalization.

### Metadata attachment

After normalization, include pattern filtering, and deduplication, discovery attaches record metadata to each retained URL.

Expected behavior:

* each retained URL receives the originating `source_id`
* each retained URL receives a discovery timestamp in UTC
* optional traceability fields such as `base_url` and `matched_pattern` may be attached

If multiple include patterns match the same URL, the first matching pattern in source registry order is stored as `matched_pattern`.

For the MVP, `discovered_at` is assigned once per discovery run and reused for all records created in that run.

### Discovery persistence boundary

Discovery persists only the final retained discovery records of a run.

The persisted output contains the structured `DiscoveredUrlRecord` dataset after:

* HTML fetch
* link extraction
* URL normalization
* include pattern filtering
* deduplication
* metadata attachment

Discovery does not persist intermediate parsing or filtering artefacts as part of the MVP contract.

For the MVP, JSONL is the preferred persistence format.

### Discovery logging

Discovery must produce structured and human readable logs at source level and run level.

Expected logging includes at least:

* discovery start for each `source_id`
* fetch success or fetch failure
* number of raw links extracted from source HTML
* number of valid normalized URLs
* number of URLs retained after include pattern filtering
* number of final unique URLs after deduplication
* persistence success including output path and written record count

Failures must be logged with source context and error type.

Logging must not stop the full run unless failure handling is explicitly configured otherwise.

### Monitoring over time

Discovery logging describes behavior within a single run.

Long term source monitoring requires additional state that is outside the MVP discovery contract.

This includes:

* last successful discovery time per source
* last discovery failure per source
* known discovered URLs from previous runs
* newly discovered URLs compared with previous runs
* unexpected drops or spikes in discovery volume

This cross run monitoring state is not part of the initial discovery implementation.

### Discovery output schema

Discovery produces one structured record per discovered candidate URL.

Each record contains the following required fields:

* `source_id`: stable identifier of the configured source that produced the URL
* `url`: canonical absolute URL of the discovered candidate page
* `discovered_at`: timestamp of the discovery run in UTC

Optional fields may be added for traceability:

* `base_url`: source entry URL from which discovery started
* `matched_pattern`: first matching include pattern in source registry order

The discovery output must not contain content level fields such as page title, extracted text, HTTP status, or content hash.

Those belong to later pipeline steps.

### Boundary to crawling

Discovery outputs only URLs and metadata.

The crawling step is responsible for:

* fetching discovered URLs
* storing raw HTML of project pages

No content level processing is allowed in discovery.

## Crawling Architecture

### Responsibility

The crawling step is responsible for fetching discovered URLs from discovery output and storing raw HTML plus fetch metadata for later processing.

Crawling operates on discovered project page URLs and does not interpret page content.

### Crawling input contract

Crawling consumes structured discovery output records.

Required fields per discovered URL record:

* `source_id`
* `url`
* `discovered_at`

Optional discovery traceability fields may be present:

* `base_url`
* `matched_pattern`

Crawling must fail explicitly if required discovery fields are missing.

### Assumptions and limitations

The MVP crawling model assumes:

* discovered URLs are accessible via standard HTTP GET
* raw HTML content can be captured without JavaScript rendering
* redirects may occur and are handled by the HTTP client
* no authentication is required
* no retry logic is required
* each fetched page is handled independently

Pages that do not satisfy these constraints are not fully supported in the MVP.

### What crawling does

* load discovered URL records from structured discovery output
* fetch each discovered URL via HTTP GET
* decode response content as UTF 8 if no explicit charset is declared
* capture HTTP status and fetch timestamp
* store raw HTML response bodies for successful fetches
* compute a stable content hash from stored HTML
* attach fetch metadata to structured crawl records
* persist crawl records as structured output
* continue processing when individual page fetches fail

### What crawling does not do

* no URL discovery
* no extraction of page text
* no HTML cleaning or normalization of content
* no semantic relevance filtering
* no scoring or ranking
* no classification
* no geographic reasoning
* no interpretation of whether a page indicates a true change
* no downstream lead generation

### Page fetch helper

Crawling uses a dedicated page fetch helper to retrieve each discovered URL.

The fetch helper is responsible only for technical HTTP access.

Expected behavior:

* perform an HTTP GET request to the discovered `url`
* use a defined timeout
* allow redirects
* capture response status code
* decode the response body safely
* return response body for successful fetches
* surface network and request errors explicitly to the caller
* preserve non successful HTTP responses as structured outcomes

If the HTTP response does not declare an explicit charset, the response body is decoded as UTF 8.

This avoids mojibake in sources that serve UTF 8 content without a reliable charset header.

### HTML storage layout

Crawling stores raw HTML response content in a deterministic and inspectable file layout.

Expected behavior:

* each stored HTML document is written to a stable path within the crawl run output
* storage layout separates runs and sources
* unrelated pages must not overwrite each other
* stored files remain directly inspectable for debugging and downstream processing

An example layout is:

`data/crawling/<run_id>/<source_id>/<content_hash>.html`

### HTML persistence

Crawling persists raw HTML exactly as fetched, without content interpretation.

Expected behavior:

* HTML is stored as UTF 8 text
* empty or missing bodies are handled explicitly
* persistence failures are surfaced and logged
* stored file paths are attached to crawl output records

For the MVP, crawling stores raw page artefacts only.

Parsed text, extracted metadata, and cleaned content belong to later pipeline steps.

### Content hash generation

Crawling computes a stable content hash for fetched HTML content.

Expected behavior:

* the same HTML content always produces the same hash
* different HTML content produces a different hash
* the hash is derived from raw stored HTML content
* the hash is recorded in the structured crawl output

For the MVP, the content hash acts as a deterministic page identity signal within crawling output.

It is not a semantic deduplication mechanism.

### Crawl record creation

After fetch and persistence, crawling creates one structured record per attempted page fetch.

Each record contains at least:

* `source_id`
* `url`
* `fetched_at`
* `status_code`
* `content_hash`
* `html_path`

Optional fields may be added for traceability and error capture:

* `error`
* `discovered_at`

If a fetch fails before HTML storage is possible, the record may omit `content_hash` and `html_path` and instead contain an `error` field describing the failure.

### Crawl persistence boundary

Crawling persists only the final structured crawl records of a run plus raw stored HTML files.

The persisted crawl output contains the structured page fetch dataset after:

* discovery input loading
* page fetch
* HTML persistence
* content hash generation
* metadata attachment

Crawling does not persist downstream parsing, extraction, classification, or lead scoring artefacts as part of the MVP contract.

For the MVP, JSONL is the preferred persistence format.

### Crawling logging

Crawling must produce structured and human readable logs at page level and run level.

Expected logging includes at least:

* crawl start
* input record count
* fetch success or fetch failure per URL
* HTTP status code for completed responses
* HTML persistence success including output path
* final crawl record count
* run completion summary

Failures must be logged with source context, URL, and error type.

Logging must not stop the full run unless failure handling is explicitly configured otherwise.

### Monitoring over time

Crawling logging describes behavior within a single run.

Long term crawl monitoring requires additional state that is outside the MVP crawling contract.

This includes:

* last successful fetch time per URL
* repeated fetch failures for the same URL
* content hash changes across runs
* newly failing URLs compared with previous runs
* unexpected drops in crawl success rate

This cross run monitoring state is not part of the initial crawling implementation.

### Crawling output schema

Crawling produces one structured record per attempted page fetch.

Each record contains the following required fields for successful fetches:

* `source_id`: stable identifier of the configured source that originally produced the URL
* `url`: canonical absolute URL of the fetched page
* `fetched_at`: timestamp of the crawl run in UTC
* `status_code`: HTTP response status code
* `content_hash`: stable hash of the fetched raw HTML content
* `html_path`: persisted path to the stored raw HTML file

Optional fields may be added for traceability and failure handling:

* `discovered_at`: timestamp originally attached during discovery
* `error`: structured or string error description for failed fetches

The crawling output must not contain downstream interpretation fields such as extracted text, page title, semantic labels, relevance score, or lead decision.

### Boundary to downstream processing

Crawling outputs only raw HTML artefacts and fetch metadata.

Later processing steps are responsible for:

* parsing stored HTML
* extracting text or metadata
* classifying pages
* generating or scoring leads

No interpretation logic is allowed in crawling.

## HTML Cleaning Architecture

### Responsibility

The HTML cleaning step is responsible for transforming stored raw HTML pages into normalized text documents for downstream processing.

HTML cleaning operates on crawl output records and stored raw HTML files.

### Input contract

HTML cleaning consumes structured crawl records.

Required fields per crawl record:

* `source_id`
* `url`
* `fetched_at`
* `status_code`
* `content_hash`
* `html_path`

Only successful crawl records with HTTP status code `200` and a valid `html_path` are eligible for cleaning.

### What HTML cleaning does

* load raw HTML from `html_path`
* parse HTML content
* extract a document title
* ignore technical JavaScript notice titles when better title candidates exist
* isolate the main content area
* remove obvious boilerplate such as navigation, footer, contact, feedback, breadcrumbs, and related content
* extract lead text and main content sections
* normalize whitespace and duplicate text blocks
* detect document language
* enforce a minimum text length
* persist normalized documents as JSONL
* persist excluded documents with exclusion reasons
* create a cleaning report

### What HTML cleaning does not do

* no semantic relevance filtering
* no structural change classification
* no scoring or ranking
* no geographic reasoning
* no lead generation
* no confirmation of real world changes

### Extraction approach

For the MVP, HTML cleaning uses generic extraction logic with limited source aware fallbacks.

This is acceptable because the monitored source set is manually curated and intentionally constrained.

The extraction logic prioritizes recall over precision.

It should preserve potentially relevant infrastructure information even if some descriptive or process related text remains.

### Normalized document schema

HTML cleaning produces one normalized document per included crawl record.

Each normalized document contains at least:

* `document_id`
* `source_id`
* `url`
* `title`
* `clean_text`
* `language`
* `crawl_timestamp`
* `html_path`
* `clean_text_length`

The normalized document schema is the input contract for downstream filtering, scoring, classification, and lead generation.

### Exclusion reasons

Documents may be excluded during HTML cleaning for technical quality reasons only.

Supported exclusion reasons include:

* `crawl_failed`
* `missing_html_path`
* `no_main_text`
* `extraction_failed`
* `too_short`
* `unsupported_language`

These exclusions are not semantic relevance decisions.

### Persistence

HTML cleaning writes cleaned documents, excluded documents, and a cleaning report.

When the step is run standalone, the default paths are:

* `artifacts/cleaned.jsonl`
* `artifacts/excluded.jsonl`
* `artifacts/html_cleaning_report.json`

When the step is run through the scoped operational pipeline, the outputs are written under:

* `artifacts/runs/<run_id>/cleaned.jsonl`
* `artifacts/runs/<run_id>/excluded.jsonl`
* `artifacts/runs/<run_id>/reports/cleaning_report.json`

Generated artefacts are not versioned in Git.

## Hard Filtering Boundary

### Responsibility

The hard filtering step removes only clearly irrelevant normalized documents before downstream scoring and classification.

It is a safety filter, not a relevance model.

### Filter policy

Hard filtering must preserve all plausible infrastructure project documents.

This includes soft or ambiguous infrastructure changes such as:

* road renovation
* safety improvements
* noise reduction
* bus stop redesign
* cycle infrastructure
* construction phase updates

These documents may later receive a lower score or be classified as not TLM relevant, but they must not be removed by hard filtering.

### What hard filtering may remove

Hard filtering may remove documents that are clearly outside the monitored domain, for example:

* cultural events
* job pages
* generic administration pages
* political pages without infrastructure content
* pure media overview pages
* unrelated downloads or service pages
* newsletter subscription pages

### What hard filtering must not remove

Hard filtering must not remove documents merely because they are weak, soft, indirect, or ambiguous infrastructure signals.

In particular, terms such as `Sanierung`, `Sicherheit`, or `Lärmschutz` are not sufficient exclusion reasons.

### Boundary to scoring and classification

TLM relevance belongs to downstream scoring and classification.

Hard filtering may compute simple rule based signals for later stages, but those signals must not be used as final relevance decisions in the MVP.

### Filtering output

The hard filtering step produces three artefacts:

* `artifacts/filtered.jsonl`: normalized documents that passed the hard filter
* `artifacts/filtered_excluded.jsonl`: documents excluded by the hard filter including exclusion reason and matched rule
* `artifacts/filter_report.json`: summary statistics of the filtering run

### Filtered document enrichment

Documents in `filtered.jsonl` may be enriched with a `filter_signals` field.

This field contains simple rule based signals such as:

* keyword hits for structural change indicators
* keyword hits for soft change indicators
* text length indicators

These signals are not used for hard exclusion in the MVP.

They serve as input for downstream scoring and ranking.

### Determinism

Given identical input and identical filter configuration, the filtering step must produce identical outputs.

### Boundary

The filtering step:

* does not remove documents based on structural versus non structural interpretation
* does not perform scoring or ranking
* does not classify documents

Its sole responsibility is conservative removal of clearly irrelevant documents and generation of simple signals.

## Thematic Scoring

### Responsibility

The thematic scoring step ranks normalized documents by their likelihood of being useful review leads for potential TLM relevant geometry changes in the road and path network.

Scoring is not a final classifier.

Scoring is not a filtering step.

Scoring must preserve all documents that passed hard filtering.

### Scoring policy

The purpose of scoring is to assign a relative signal that helps prioritize documents for human review.

The score is used for candidate ranking and high recall filtering.

It must not be interpreted as confirmed TLM relevance.

Positive scoring signals include terms and patterns that indicate possible TLM geometry changes, for example:

1. new road or path geometry
2. changed road alignment
3. new or changed junctions
4. new roundabouts
5. new accesses, ramps, entries, or exits
6. new tunnels, bridges, or underpasses
7. new physically separated pedestrian or cycling infrastructure
8. mapped road related geometry such as traffic islands or protection islands

Soft or negative scoring signals include terms and patterns that often describe non geometric work, for example:

1. maintenance
2. resurfacing
3. drainage
4. lighting
5. noise protection
6. temporary traffic management
7. markings
8. pure operational or administrative changes

Soft indicators may reduce the score but must not remove a document.

### Baseline status

The current scoring configuration is `config/scoring.yaml` version 10.

This configuration is frozen as the deterministic score baseline.

The scoring baseline is evaluated as a lead prioritization method, not as a final semantic relevance classifier.

The frozen expanded annotation dataset contains 348 manually reviewed sources.

The derived evaluation datasets are:

1. strict binary relevance dataset
2. actionable binary lead dataset
3. three class triage dataset

The strict binary dataset excludes `needs_review` cases.

The actionable binary dataset treats `confirmed_relevant` and `needs_review` as positive review leads.

On the current test split, the score baseline achieved:

| Dataset | Selected threshold | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| strict_binary | 0.25 | 0.864 | 0.760 | 0.809 |
| actionable_binary | 0.05 | 0.771 | 0.881 | 0.822 |

For actionable lead detection, the score baseline also achieved:

| Dataset | N | Precision at N | Recall at N |
|---|---:|---:|---:|
| actionable_binary | 20 | 0.850 | 0.405 |
| actionable_binary | 50 | 0.740 | 0.881 |

This result shows that the deterministic scoring baseline already provides practical value for review queue prioritization.

It also shows that scoring should not be interpreted as confirmed TLM relevance.

The score threshold depends on the workflow goal.

A higher threshold is more suitable for confirmed relevance.

A lower threshold is more suitable for high recall actionable lead detection.

### Score computation

The final `thematic_score` is computed as:

`thematic_score = rule_weight * rule_score + retrieval_weight * retrieval_score`

Weights are defined in `config/scoring.yaml`.

The `rule_score` is based on configured keyword and regex pattern signals.

The `retrieval_score` is based on BM25 term matching using configured query terms.

Raw BM25 scores are normalized per scoring run using min max normalization across all documents:

`retrieval_score = (bm25_raw_score - min_bm25_raw_score) / (max_bm25_raw_score - min_bm25_raw_score)`

If all BM25 raw scores are identical, all retrieval scores are set to `0`.

This means retrieval scores are comparable within one run, but not directly comparable across different corpora, cantons, or source sets.

### MVP scoring limitation

The thematic scoring configuration is calibrated on the current annotated MVP source mix.

Scores are suitable for ranking documents within the current MVP context.

Scores should not be treated as canton independent or source independent relevance probabilities.

When additional cantons or source types are added, the scoring configuration must be reviewed and recalibrated.

### Boundary to filtering

Filtering removes clearly non domain content.

Scoring operates only on documents that passed filtering.

Scoring must not remove additional documents.

### Boundary to classification

Scoring does not perform a final semantic decision.

It provides a continuous relevance signal.

The decision whether a document is TLM relevant belongs to classification or downstream review.

### Boundary to lead generation

Scoring does not generate final leads.

Lead generation may use scoring as one ranking signal together with classifier predictions, probabilities, metadata, and optional geographic hints.

### Determinism

Given identical input and identical scoring configuration, the scoring step must produce identical scores.

### Output

Each scored document receives:

* `thematic_score`: final normalized score between 0 and 1
* `rule_score`: normalized rule based score
* `retrieval_score`: normalized BM25 retrieval score
* `scoring_signals`: explanation fields for matched terms and patterns

The output dataset must preserve all input documents and enrich them with scoring metadata.

## Evaluation Architecture

### Responsibility

The evaluation layer creates stable datasets and reports for comparing lead prioritization and classification methods.

Evaluation is separated from operational monitoring.

Operational monitoring processes configured source registries.

Evaluation uses the frozen annotation dataset.

### Frozen annotation dataset

The frozen expanded annotation dataset is stored under:

`data/annotation/labeled/annotation_dataset_expanded.csv`

The dataset contains 348 manually reviewed sources.

The annotation schema defines:

1. `tlm_relevant`
2. `review_required`
3. `change_type`
4. `notes`
5. derived `triage_class`

The valid derived classes are:

1. `confirmed_relevant`
2. `needs_review`
3. `not_relevant`

The combination `tlm_relevant = true` and `review_required = true` is invalid.

### Evaluation datasets

The evaluation builder creates three datasets.

#### strict_binary

This dataset evaluates confirmed TLM relevance.

Mapping:

| triage_class | target |
|---|---:|
| confirmed_relevant | 1 |
| not_relevant | 0 |
| needs_review | excluded |

#### actionable_binary

This dataset evaluates lead usefulness for review.

Mapping:

| triage_class | target |
|---|---:|
| confirmed_relevant | 1 |
| needs_review | 1 |
| not_relevant | 0 |

#### triage_3class

This dataset evaluates three class review triage.

Classes:

1. `confirmed_relevant`
2. `needs_review`
3. `not_relevant`

### Evaluation metrics

The main metrics depend on the task.

For strict relevance:

1. precision
2. recall
3. F1
4. confusion matrix

For actionable lead detection:

1. recall
2. precision at N
3. recall at N
4. review workload reduction
5. false negative analysis

For three class triage:

1. per class precision
2. per class recall
3. per class F1
4. confusion matrix
5. qualitative error analysis

Accuracy is not sufficient because the production goal is lead prioritization, not autonomous final classification.

### Human in the loop interpretation

False positives increase review workload.

False negatives can cause missed relevant sources.

Therefore, the system should prefer high recall and useful ranking over aggressive automatic exclusion.

The final decision remains with a domain expert.


### Evaluation report package

The evaluation report package is the consolidated output layer for the current MVP evaluation.

It is generated by:

`python scripts/evaluation/build_evaluation_report_package.py`

The output is written to:

`data/annotation/evaluation/report_package/`

It summarizes frozen dataset splits, aligned method comparisons, local LLM runs, hybrid lead selection, explainability output, limitations, and the recommended setup.

It does not replace the source reports.

Detailed confusion matrices, threshold reports, qualitative error analysis, and false negative examples remain in the original evaluation artifact folders and are referenced through `artifact_index.md`.

## Baseline Classification Architecture

### Responsibility

The baseline classification step evaluates learned non LLM text classification methods against the deterministic score baseline.

The purpose is not to create an autonomous final relevance authority.

The purpose is to test whether a simple supervised text model can improve lead prioritization and review support.

The current baseline classifier predicts binary relevance targets derived from the frozen annotation schema.

It is evaluated on the same frozen train and test splits as the score baseline.

### Evaluation targets

The classifier is evaluated on two binary datasets.

#### strict_binary

The strict binary dataset evaluates confirmed TLM relevance.

Mapping:

| triage_class | target_strict_relevant |
|---|---:|
| confirmed_relevant | 1 |
| not_relevant | 0 |
| needs_review | excluded |

This task tests whether a method can distinguish confirmed TLM geometry evidence from non relevant sources.

#### actionable_binary

The actionable binary dataset evaluates whether a source should enter the human review queue.

Mapping:

| triage_class | target_actionable |
|---|---:|
| confirmed_relevant | 1 |
| needs_review | 1 |
| not_relevant | 0 |

This task is closer to the operational ChangeScout workflow because review worthy but not yet confirmed sources are useful leads.

### Input

The classifier consumes the frozen evaluation datasets generated from the expanded annotation dataset.

Current input files:

* `data/annotation/evaluation/strict_binary_dataset.csv`
* `data/annotation/evaluation/actionable_binary_dataset.csv`

Required fields:

* `annotation_id`
* `url`
* `source_id`
* `title`
* `text_full`
* `split`
* `triage_class`
* target column for the selected dataset

The model input text is built from:

1. title
2. full source text

The frozen split column is used directly.

No new random split is created during classifier evaluation.

### Dataset status

The current frozen expanded annotation dataset contains 348 manually reviewed sources.

The derived binary evaluation datasets are:

| Dataset | Rows | Train | Test | Positive definition |
|---|---:|---:|---:|---|
| strict_binary | 264 | 211 | 53 | confirmed_relevant |
| actionable_binary | 348 | 278 | 70 | confirmed_relevant or needs_review |

The train and test splits are stratified and reproducible.

The split was created during evaluation dataset construction.

### Baseline model

The current learned non LLM baseline uses TF IDF features and Logistic Regression.

Configuration:

* word ngrams from 1 to 2
* `max_features = 20000`
* `sublinear_tf = true`
* `max_df = 0.95`
* `class_weight = balanced`
* Logistic Regression with `liblinear`
* `random_state = 42`

The model outputs:

1. binary prediction
2. probability for the positive class
3. evaluation metrics on the frozen test split

### Current result

The TF IDF Logistic Regression baseline was evaluated against the same test splits as the deterministic score baseline.

| Dataset | Method | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| strict_binary | thematic_score | 0.864 | 0.760 | 0.809 | 0.830 | 19 | 3 | 25 | 6 |
| strict_binary | TF IDF Logistic Regression | 0.852 | 0.920 | 0.885 | 0.887 | 23 | 4 | 24 | 2 |
| actionable_binary | thematic_score | 0.771 | 0.881 | 0.822 | 0.771 | 37 | 11 | 17 | 5 |
| actionable_binary | TF IDF Logistic Regression | 0.812 | 0.929 | 0.867 | 0.829 | 39 | 9 | 19 | 3 |

The learned classifier outperforms the deterministic score baseline on both strict relevance and actionable lead detection.

The improvement is especially relevant for recall.

For the ChangeScout workflow, recall is important because false negatives can cause relevant or review worthy sources to be missed.

### Error profile

Qualitative inspection shows that the classifier still makes systematic errors.

Observed false positive types include:

* maintenance and resurfacing with strong infrastructure language
* BehiG bus stop adaptations
* Lärmschutz or retaining structures without road geometry change
* urban redesign language without confirmed TLM geometry effect
* domain heavy project pages where the text does not confirm a mapped road or path change

Observed false negative types include:

* relevant foot and cycle connections embedded in broader planning texts
* programme or funding texts that contain one concrete relevant geometry signal
* review worthy concepts where the signal is plausible but not strongly lexicalized

This means the classifier is a stronger non LLM baseline, but it is still not a final decision system.

It improves the lead prioritization baseline but still requires human review.

### Boundary to scoring

The deterministic score baseline remains useful because it is transparent, reproducible, and does not require labeled training data.

The classifier is a learned decision baseline.

It requires frozen labels and must be revalidated when the source mix changes.

Scoring remains a ranking and prioritization signal.

Classification remains a review support signal.

Neither component confirms that TLM must be updated.

### Boundary to LLM evaluation

LLM methods must be compared against both non LLM baselines:

1. deterministic thematic score
2. TF IDF Logistic Regression

A useful LLM method should improve at least one of the following:

1. recall for confirmed relevant sources
2. recall for actionable review leads
3. recognition of needs_review cases
4. precision at useful review depth
5. evidence quality
6. explanation quality
7. auditability of generated evidence snippets
8. reduction of systematic false positives such as Sanierung, BehiG, Lärmschutz, or temporary traffic management

A higher global F1 alone is not sufficient.

The LLM must improve the human review workflow.

Current local LLM results are split sensitive.

On task specific binary splits, TF IDF Logistic Regression is the strongest learned baseline.

On the aligned triage test split, thematic_score achieves the strongest strict binary F1, while Qwen2.5 14B hierarchical achieves the strongest actionable F1 but with lower actionable recall than TF IDF Logistic Regression and thematic_score. Qwen2.5 14B direct was evaluated as part of the regular prompt comparison and did not improve over Qwen2.5 14B hierarchical.

No evaluated local zero shot LLM is stable enough as a standalone three class triage classifier.

They are therefore treated as candidates for hybrid review support rather than replacements for high recall candidate selection.

### Output

The classical text classifier evaluation writes:

1. `data/annotation/evaluation/classical_text_classifier/classical_text_classifier_metrics.json`
2. `data/annotation/evaluation/classical_text_classifier/classical_text_classifier_predictions.csv`
3. `data/annotation/evaluation/classical_text_classifier/classical_text_classifier_report.md`

The prediction output contains test split predictions, probabilities, labels, scores, notes, and source metadata.

## Local LLM Evaluation Architecture

### Responsibility

The local LLM evaluation layer tests whether instruction tuned Hugging Face models improve lead classification, triage, or explanation quality compared with deterministic scoring and classical ML baselines.

The LLM layer is part of evaluation and review support.

It is not part of automatic TLM update confirmation.

### Input

Local LLM evaluation consumes the frozen three class triage evaluation dataset:

`data/annotation/evaluation/triage_3class_dataset.csv`

Only the test split is used for reported LLM metrics.

Required fields:

* `annotation_id`
* `url`
* `source_id`
* `title`
* `text_full`
* `triage_class`
* `change_type`
* `notes`

The prompt uses the full source text by default.

No source text character limit is applied unless explicitly configured with `--max-input-chars`.

### Output contract

Each LLM prediction is required to return structured JSON with:

* `triage_class`
* `tlm_relevant`
* `review_required`
* `change_type`
* `notes`
* `evidence`

The pipeline parses the JSON output and validates required fields.

The boolean labels are normalized from `triage_class` to enforce the frozen annotation schema.

This prevents inconsistent model output such as `tlm_relevant = true` and `review_required = true`.

### Prompt variants

Two zero shot prompt variants are currently evaluated.

#### direct

The direct prompt asks the model to classify the source directly into one of the three triage classes.

#### hierarchical

The hierarchical prompt mirrors the annotation logic.

It first checks for plausible TLM geometry signals and then checks whether the source confirms the geometry sufficiently.

This is closer to the human annotation workflow, especially for distinguishing confirmed_relevant from needs_review.

### Evaluated models

The current local LLM evaluation includes:

| Model | Prompt |
|---|---|
| Qwen2.5 7B Instruct | direct |
| Qwen2.5 7B Instruct | hierarchical |
| Llama 3.1 8B Instruct | hierarchical |
| Qwen2.5 14B Instruct | hierarchical |
| Qwen2.5 14B Instruct | direct |

All models are loaded locally through Hugging Face Transformers.

No API based LLM calls are used.

### Current local LLM result

| Method | Prompt | Strict precision | Strict recall | Strict F1 | Actionable precision | Actionable recall | Actionable F1 | Triage accuracy |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5 7B Instruct | hierarchical | 1.000 | 0.640 | 0.780 | 1.000 | 0.548 | 0.708 | 0.671 |
| Qwen2.5 7B Instruct | direct | 1.000 | 0.600 | 0.750 | 1.000 | 0.619 | 0.765 | 0.657 |
| Llama 3.1 8B Instruct | hierarchical | 0.929 | 0.520 | 0.667 | 0.923 | 0.571 | 0.706 | 0.586 |
| Qwen2.5 14B Instruct | hierarchical |
| Qwen2.5 14B Instruct | direct | 1.000 | 0.120 | 0.214 | 0.969 | 0.738 | 0.838 | 0.571 |

### Findings

All evaluated local LLM runs produced valid structured output with parse success rate 1.0.

The tested local LLMs are generally conservative.

They achieve high precision but lower recall than the deterministic score baseline and the TF IDF Logistic Regression classifier.

The most important observed error patterns are:

* confirmed_relevant sources downgraded to needs_review
* confirmed_relevant sources missed as not_relevant
* needs_review sources missed as not_relevant
* strong rejection of not_relevant sources

Qwen2.5 14B improves actionable lead detection compared with smaller local LLMs because many confirmed_relevant cases are at least retained as needs_review.

Qwen2.5 14B direct is included as part of the regular direct versus hierarchical prompt comparison. It did not improve over Qwen2.5 14B hierarchical and showed lower actionable F1 and lower triage accuracy.

However, this behavior makes 14B variants unsuitable for strict confirmed relevance classification.

### Error analysis finding

The error analysis shows that the dominant local LLM failure modes are:

* `needs_review` mapped to `not_relevant`
* `confirmed_relevant` mapped to `needs_review`
* `confirmed_relevant` mapped to `not_relevant`

This supports a hybrid architecture.

LLM predictions can enrich, explain, and reprioritize leads.

They should not be used as hard exclusion signals because false negatives remain too frequent.

An LLM prediction of `not_relevant` may downgrade a candidate, but it should not remove a candidate if deterministic score or TF IDF signals indicate actionable relevance.

### Boundary to classical ML

The current TF IDF Logistic Regression baseline remains the strongest standalone binary classifier on the frozen test split.

The local LLMs do not replace the classical classifier.

They may still add value in hybrid workflows because they provide structured notes and evidence snippets.

### Boundary to hybrid lead selection

The most plausible LLM role is downstream of cheap high recall candidate selection.

Candidate selection can be done by:

1. deterministic score threshold
2. score rank
3. TF IDF classifier probability
4. uncertainty bands

The LLM can then be used for:

1. evidence generation
2. explanation
3. precision filtering
4. triage support

This supports the ChangeScout principle that lead generation remains human in the loop.

## Hybrid Lead Selection Architecture

### Responsibility

The hybrid lead selection layer evaluates practical review queue strategies that combine cheap high recall candidate selection with optional LLM based triage, notes, and evidence.

Hybrid lead selection is not a final TLM relevance authority.

It creates ranked review candidates and explains why they should be inspected.

### Input

Hybrid lead selection evaluation consumes aligned evaluation artefacts:

* `data/annotation/evaluation/triage_3class_dataset.csv`
* `data/annotation/evaluation/aligned_method_comparison/aligned_tfidf_predictions.csv`
* `data/annotation/evaluation/local_llm/<model>/<prompt_variant>/llm_triage_predictions.jsonl`

The target is actionable lead detection.

Positive actionable leads are:

1. `confirmed_relevant`
2. `needs_review`

### Evaluated modes

The current evaluation supports these modes:

| Mode | Meaning |
|---|---|
| `score_only` | rank by deterministic thematic score |
| `tfidf_only` | rank by TF IDF actionable probability |
| `llm_only` | rank by LLM triage signal |
| `score_or_tfidf` | rank by the maximum of thematic score and TF IDF probability |
| `hybrid_weighted` | weighted combination of thematic score, TF IDF probability, and LLM signal |
| `hybrid_recall_guard` | weighted hybrid score with recall oriented boosts for strong score or TF IDF signals |

### LLM boundary

LLM predictions are enrichment and reprioritization signals.

They are not hard exclusion signals.

An LLM prediction of `not_relevant` may downgrade a candidate, but it must not remove a candidate when deterministic score or TF IDF signals indicate actionable relevance.

This boundary follows directly from the observed LLM false negative behavior.

### Current result

Hybrid lead selection was evaluated across Qwen2.5 14B hierarchical, Qwen2.5 14B direct, Qwen2.5 7B direct, and Qwen2.5 7B hierarchical LLM outputs.

Qwen2.5 14B variants are treated as upper bound signals because they are computationally heavier and required CPU offload in the current environment.

Qwen2.5 7B variants are treated as more production oriented local LLM signals.

Best modes by review depth:

| Review depth | Best mode | LLM dependency | Precision at N | Recall at N | False negatives |
|---:|---|---|---:|---:|---:|
| 10 | `tfidf_only` | not applicable | 1.000 | 0.238 | 32 |
| 20 | `hybrid_recall_guard` | Qwen2.5 7B or 14B signal | 1.000 | 0.476 | 22 |
| 50 | `score_or_tfidf` | not applicable | 0.780 | 0.929 | 3 |
| 70 | `score_or_tfidf` | not applicable | 0.600 | 1.000 | 0 |

### Interpretation

For very small review queues, LLM based ranking can improve precision preserving prioritization.

For broader review queues, the measurable high recall gain mainly comes from combining the deterministic thematic score and TF IDF probability.

The recommended production oriented strategy is therefore:

1. use `score_or_tfidf` as the high recall candidate selection layer
2. use a production feasible local LLM such as Qwen2.5 7B for evidence generation, triage notes, and optional priority support
3. use Qwen2.5 14B variants only as upper bound evaluation signals, not as default production models

### False negative profile

At top 50, the recommended `score_or_tfidf` strategy missed 3 actionable records.

These remaining false negatives are mainly broad or aggregated government communication pages.

Their relevant TLM signal is not prominent enough for the current score, TF IDF, or LLM signals.

This supports keeping ChangeScout human in the loop and treating LLM `not_relevant` as a downgrade signal rather than a hard exclusion.

### Output

Hybrid lead selection evaluation writes:

* `data/annotation/evaluation/hybrid_lead_selection_<llm_variant>/hybrid_lead_selection_metrics.csv`
* `data/annotation/evaluation/hybrid_lead_selection_<llm_variant>/hybrid_leads.csv`
* `data/annotation/evaluation/hybrid_lead_selection_<llm_variant>/hybrid_eval_records.csv`
* `data/annotation/evaluation/hybrid_lead_selection_<llm_variant>/hybrid_lead_selection_report.md`
* `data/annotation/evaluation/hybrid_lead_selection_comparison/hybrid_lead_selection_comparison.md`
* `data/annotation/evaluation/hybrid_lead_selection_comparison/score_or_tfidf_top50_false_negatives.md`

### Boundary to lead generation

Hybrid lead selection currently belongs to the evaluation layer.

It identifies the preferred strategy for future production lead generation.

Operational lead generation can later consume the selected strategy, but it should preserve the human in the loop boundary.


## LLM Explainability Architecture

### Responsibility

The LLM explainability layer generates concise, auditable review explanations for already selected leads.

It supports human review.

It does not select leads.

It does not remove leads.

It does not confirm that TLM must be updated.

### Input

The explainability layer consumes selected leads from hybrid lead selection.

The current evaluation input is the top 50 `score_or_tfidf` review queue from the Qwen2.5 7B direct hybrid setup.

Required input fields include:

* `annotation_id`
* `source_id`
* `url`
* `title`
* `text_full`
* `thematic_score_eval`
* `tfidf_actionable_probability`
* `llm_triage_class` when available

### Explanation output contract

The dedicated explanation prompt returns structured JSON with these fields:

* `evidence_type`
* `explanation_note`
* `evidence_snippet`
* `geometry_signal`
* `audit_warning`

The allowed `evidence_type` values are:

* `confirmed_geometry`
* `plausible_review_signal`
* `no_geometry_evidence`
* `unclear`

The JSON keys and evidence type enum are stable and English.

The reviewer note and audit warning are generated in German.

The evidence snippet should stay in the original source wording.

### Explanation policy

The model must use only the provided source text.

It must not infer geometry changes that are not stated.

It must not invent locations, objects, or project details.

The explanation must distinguish confirmed geometry evidence from plausible but unconfirmed review signals.

If no geometry evidence is found, the output should use `no_geometry_evidence` and explain the limitation.

### Audit fields

The evaluation layer validates generated explanations with audit fields.

Current audit fields include:

* parse success
* evidence snippet found in source
* missing evidence snippet
* requires manual explanation check

A manual check is required when evidence is missing, not exactly found in source, weak, negative, or unclear.

### Current evaluation result

Reusing local LLM triage outputs as explanations was evaluated first.

This approach was not sufficient because many selected leads received `not_relevant` explanations despite being selected by score or TF IDF.

A dedicated explanation prompt was then evaluated on the top 50 `score_or_tfidf` leads.

Current Qwen2.5 7B result:

| Metric | Value |
|---|---:|
| records | 50 |
| parse success rate | 1.000 |
| missing evidence snippets | 0 |
| evidence snippets found exactly in source | 45 |
| explanations requiring manual check | 19 |

Evidence type distribution:

| Evidence type | Count |
|---|---:|
| confirmed_geometry | 22 |
| plausible_review_signal | 14 |
| no_geometry_evidence | 14 |

### Interpretation

The dedicated explanation prompt substantially improves review usability compared with reusing triage outputs.

However, explanation output remains auditable support, not trusted automation.

Some generated evidence snippets are close paraphrases rather than exact source substrings.

Some explanations extract a useful snippet but assign an overly conservative evidence type.

Some explanation failures are caused by weak extracted source text.

Therefore, explanations should be attached to lead exports together with audit flags.

They should not be treated as authoritative proof that a source is or is not TLM relevant.

### Boundary to hybrid lead selection

Hybrid lead selection determines which records enter the review queue.

The explainability layer explains selected leads after selection.

It must not be used as a hard exclusion stage.

### Output

LLM explainability evaluation writes:

* `data/annotation/evaluation/llm_explainability/llm_explainability_leads.csv`
* `data/annotation/evaluation/llm_explainability/llm_explainability_report.md`
* `data/annotation/evaluation/llm_explainability_generated/llm_explainability_generated.jsonl`
* `data/annotation/evaluation/llm_explainability_generated/llm_explainability_generated.csv`
* `data/annotation/evaluation/llm_explainability_generated/llm_explainability_generated_report.md`
* `data/annotation/evaluation/llm_explainability_generated/explainability_manual_review_notes.md`

### Future prompt refinement

The current explanation prompt should be treated as version 1.

Future prompt versions may incorporate guideline aligned refinements from manual error analysis.

Those refinements should be evaluated separately to avoid optimizing on the current test examples.


## Evaluation Report Package Architecture

### Responsibility

The evaluation report package consolidates the current MVP evaluation outputs into report ready tables and interpretation notes.

It is a reporting layer.

It does not run new models.

It does not change evaluation metrics.

It reads stored evaluation artifacts and writes a reproducible package under:

`data/annotation/evaluation/report_package/`

### Input artifacts

The package reads the frozen evaluation datasets and the current evaluation result artifacts.

Key inputs include:

* `data/annotation/evaluation/triage_3class_dataset.csv`
* `data/annotation/evaluation/strict_binary_dataset.csv`
* `data/annotation/evaluation/actionable_binary_dataset.csv`
* `data/annotation/evaluation/aligned_method_comparison/aligned_method_comparison.csv`
* `data/annotation/evaluation/local_llm/comparison/local_llm_comparison.csv`
* `data/annotation/evaluation/hybrid_lead_selection_comparison/hybrid_lead_selection_comparison.csv`
* `data/annotation/evaluation/llm_explainability_generated/llm_explainability_generated_report.json`

### Output artifacts

The package writes:

* `dataset_summary.csv`
* `method_comparison_aligned.csv`
* `local_llm_comparison.csv`
* `hybrid_summary.csv`
* `explainability_summary.csv`
* `artifact_index.md`
* `limitations.md`
* `recommended_setup.md`
* `evaluation_report_package.md`

### Interpretation boundary

The report package is a derived summary.

It does not replace the source reports.

Detailed confusion matrices, threshold selection reports, qualitative error analysis, and false negative examples remain in the original evaluation artifact folders.

The package references these source artifacts through `artifact_index.md`.

### Recommended setup summary

The current recommended setup is:

1. use `score_or_tfidf` as high recall candidate selection
2. use Qwen2.5 7B as a production feasible explanation and review support layer
3. keep LLM predictions out of hard exclusion logic
4. preserve human review as the final decision point

This summary follows the current evaluation results and remains subject to revalidation when the source mix or annotation dataset changes.

### Boundary to operational pipeline

The report package belongs to evaluation and reporting.

It is not part of operational monitoring.

Operational runs may later use the recommended strategy, but the package itself only summarizes stored evaluation evidence.

## Lead Generation Architecture

### Responsibility

The lead generation step creates actionable review candidates from scored and optionally classified documents.

A lead is not a confirmed TLM change.

A lead is a document that should be reviewed because it may describe a TLM relevant geometry update.

### Input

Lead generation consumes scored documents.

Required fields:

* `document_id`: stable document identifier
* `source_id`: source registry identifier
* `url`: document URL
* `title`: document title
* `clean_text`: normalized document text
* `thematic_score`: scoring baseline value

If classifier predictions are available, lead generation may also consume:

* `classifier_prediction`: predicted TLM relevance
* `classifier_probability`: probability for `tlm_relevant`

### Baseline inclusion rule

For the original MVP reproduction run, a document is included as a lead if:

`thematic_score >= 0.10`

This threshold is recall oriented and intentionally broad.

It remains useful as a simple deterministic lead generation mode.

The newer frozen evaluation shows that the preferred threshold depends on the workflow goal:

| Evaluation target | Selected score threshold |
|---|---:|
| strict_binary | 0.25 |
| actionable_binary | 0.05 |

For actionable lead detection, the lower score threshold is more suitable because `needs_review` cases should be preserved.

The TF IDF Logistic Regression classifier currently outperforms the score baseline on the frozen binary evaluation datasets.

Classifier predictions and probabilities should therefore be treated as useful additional review signals.

However, lead generation should remain human in the loop.

Neither the score nor the classifier should be interpreted as final confirmation that TLM must be updated.

Current original baseline output after reprocessing:

* input documents: `165`
* generated leads: `109`
* threshold: `0.10`

This output remains a reproducible MVP baseline, not the final recommended production threshold.

### Lead schema

Each lead contains at least:

* `document_id`: stable document identifier
* `source_id`: source registry identifier
* `url`: document URL
* `title`: document title
* `thematic_score`: scoring baseline value
* `lead_reason`: reason why the document was included
* `text_preview`: shortened text excerpt for review

Optional fields:

* `classifier_prediction`: predicted TLM relevance
* `classifier_probability`: probability for `tlm_relevant`

### Sorting

Leads are sorted deterministically by:

1. `thematic_score` descending
2. `title` ascending
3. `url` ascending

### Boundary to classification

Classification predicts TLM relevance.

Lead generation does not train or evaluate classifiers.

It only consumes classifier outputs when available.

### Boundary to final validation

Lead generation does not confirm whether a real world change exists or whether TLM has already been updated.

Final validation remains a manual or downstream process.

### Output

The baseline lead generation script writes:

1. `artifacts/leads.jsonl`
2. `artifacts/leads.csv`
3. `artifacts/lead_generation_report.json`

## Geographic Hinting Architecture

### Responsibility

Geographic hinting attaches optional location hints to generated leads.

The purpose is to help reviewers localize candidate leads more quickly.

Geographic hinting is not geocoding confirmation.

It does not verify whether a detected lead corresponds to a real world geometry change.

It does not validate whether TLM has already been updated.

### Boundary

A location hint is a review aid.

A missing location hint is not an error.

An ambiguous location hint is acceptable if the ambiguity remains visible in the output.

Lead relevance must not depend on location hint availability.

The lead generation threshold and relevance decision remain independent from geographic hinting.

### Staged approach

The MVP uses two hinting stages:

1. local deterministic hinting
2. optional GeoAdmin Search API enrichment

Local hinting provides an offline baseline.

GeoAdmin enrichment provides broader online lookup through official GeoAdmin search.

The default baseline run remains independent of the online API unless GeoAdmin enrichment is explicitly enabled.

### Local hinting

Local hinting uses a simple reference file.

The reference file is stored under:

`data/reference/location_hints_reference.csv`

The local reference schema contains:

* `name`
* `hint_type`
* `canton`
* `source`
* `priority`

The current local reference file is intentionally small.

It acts as a deterministic fallback and testable baseline, not as a complete municipality database.

### Local matching behavior

Local matching runs on lead title and text.

Matching uses normalized text and word boundary based exact matching.

Very short names are ignored unless explicitly handled later.

Multiple hints per lead are allowed.

Repeated matches are aggregated.

Local hinting writes structured JSONL output and flat CSV review columns.

### Local output

Local hinting writes:

* `artifacts/leads_with_locations.jsonl`
* `artifacts/leads_with_locations.csv`
* `artifacts/location_hinting_report.json`

Local enriched leads may contain:

* `location_hints`
* `location_hint_count`
* `location_hint_names`
* `municipality_hints`

### GeoAdmin enrichment

GeoAdmin enrichment is optional.

It uses the GeoAdmin Search API with `type=locations`.

The current configured origins are:

* `gazetteer`
* `gg25`

The API is used for lookup only.

The system stores query metadata and API responses in a local cache.

The cache path is:

`data/reference/geoadmin_search_cache.jsonl`

The cache contains:

* cache key
* timestamp
* query parameters
* status
* error if present
* response payload

The cache is generated runtime data and should not be versioned in Git.

### GeoAdmin query strategy

GeoAdmin queries are short candidate strings.

Candidates are built from:

1. local municipality hints when available
2. title fragments and title tokens
3. limited text fallback candidates when title based candidates are weak

The text fallback uses only the first part of `clean_text` or `text_preview`.

It extracts capitalized name like candidates.

It does not send full document text to the API.

Query candidates are deduplicated and limited.

This reduces API load and avoids uncontrolled geocoding of full source text.

### Text fallback limitation

The text fallback is intentionally conservative.

It may miss locations that appear deep in the document.

This is acceptable for the MVP because location hints are optional.

The fallback is designed to improve recall without turning the module into a full geoparsing system.

### GeoAdmin response parsing

GeoAdmin hits are parsed into structured hints.

Each hint may contain:

* `hint_type`
* `name`
* `object_type`
* `source`
* `origin`
* `query`
* `rank`
* `x`
* `y`
* `detail`

The `object_type` is extracted from the HTML label when the API response contains a label such as `<i>Ort</i>` or `<i>Quartierteil</i>`.

This object type is treated as a heuristic display label.

It is not treated as a stable authoritative enum.

### GeoAdmin ranking

GeoAdmin hints are sorted by heuristic ranking.

The ranking uses:

1. preferred canton inferred from `source_id`
2. API origin
3. extracted object type
4. API rank
5. name

The preferred canton is inferred from source prefixes such as:

* `ag_`
* `be_`
* `sg_`
* `zh_`

The API origin is treated as a stronger signal than display label object type.

`gg25` is preferred over `gazetteer` because it often represents municipality level results.

Object type is used only as an additional ranking hint.

Known broad or low precision object types such as `Grossregion` are ranked lower.

Unknown object types are retained and ranked neutrally.

### GeoAdmin output

GeoAdmin enrichment writes:

* `artifacts/leads_with_geoadmin_locations.jsonl`
* `artifacts/leads_with_geoadmin_locations.csv`
* `artifacts/geoadmin_location_hinting_report.json`

The CSV contains review oriented flattened fields such as:

* `geoadmin_preferred_canton`
* `geoadmin_location_hint_count`
* `geoadmin_top_location_name`
* `geoadmin_location_queries`

The JSONL keeps the full structured `geoadmin_location_hints` list.

### Failure handling

GeoAdmin enrichment must be non blocking.

Timeouts, HTTP errors, empty responses, and malformed responses must not stop lead generation.

If the API call fails, the affected lead receives no GeoAdmin hints or fewer GeoAdmin hints.

The output files should still be written.

### Current result

On the current baseline lead set, GeoAdmin enrichment produced:

* total records: `109`
* records with GeoAdmin hints: `97`
* records without GeoAdmin hints: `12`
* total GeoAdmin hints: `713`
* total GeoAdmin queries: `296`

These numbers are descriptive for the current corpus and cache state.

They are not fixed acceptance thresholds.

### Limitations

GeoAdmin hints may be missing.

GeoAdmin hints may be ambiguous.

Street names and object names can produce false positives.

Object type labels are extracted from API display labels and are heuristic.

The current output does not yet export a final dedicated `best_location_x` and `best_location_y` field.

Coordinates exist inside structured GeoAdmin hints when returned by the API.

A later enhancement may select a single best coordinate candidate with confidence and reason fields.

### Acceptance status

Issue 9 is considered implemented for the MVP when:

* local hinting runs after lead generation
* optional GeoAdmin enrichment can be enabled
* GeoAdmin responses are cached
* hints are attached to leads
* JSONL and CSV outputs are written
* reports are written
* tests pass
* documentation states that hints are optional review aids

## Design rationale

This separation keeps monitoring scope stable while allowing controlled updates to the concrete source list.

Additional cantons should be added through new registry files and configuration, not by changing application logic.