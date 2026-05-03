# Architecture

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

HTML cleaning writes:

* `artifacts/cleaned.jsonl`
* `artifacts/excluded.jsonl`
* `artifacts/html_cleaning_report.json`

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

The thematic scoring step ranks normalized documents by their likelihood of describing a TLM relevant geometry change in the road and path network.

Scoring is not a final classifier.

Scoring is not a filtering step.

Scoring must preserve all documents that passed hard filtering.

### Scoring policy

The purpose of scoring is to assign a relative signal that helps prioritize documents for downstream relevance assessment.

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

This configuration is frozen as the rule based scoring baseline.

The scoring is used as a high recall candidate ranking and filtering signal.

It is not intended to be the final TLM relevance classifier.

The current baseline threshold for evaluation is `0.10`.

Evaluation against the reviewed annotation dataset produced the following result, excluding review cases and records removed before scoring by the current hard filtering stage:

* threshold: `0.10`
* precision: `0.758`
* recall: `0.932`
* false positives: `22`
* false negatives: `5`

One annotated non relevant newsletter record is currently removed before scoring.

This is expected because it is clearly outside the lead generation domain.

This result shows that rule based scoring is useful for prioritizing candidate sources and reducing irrelevant records.

It also shows that scoring alone is not sufficient as a final semantic relevance decision.

Further optimization of the rule based scoring should only address clear generic blind spots.

It should not be tuned further to individual examples in the current annotation dataset, because this would risk overfitting to the current source mix.

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

## Baseline Classification Architecture

### Responsibility

The baseline classification step predicts whether a document is TLM relevant.

The classification target is `tlm_relevant`.

The classifier is trained only on reviewed annotation records where `review_required` is false.

Review cases are excluded from core training and evaluation because they do not represent clean ground truth.

### Input

The classifier consumes the reviewed annotation dataset and the scored document pool.

Required annotation fields:

* `url`: document URL used for joining
* `tlm_relevant`: target label
* `review_required`: uncertainty flag

Required scored document fields:

* `document_id`: stable document identifier
* `source_id`: source registry identifier
* `url`: document URL
* `title`: extracted document title
* `clean_text`: normalized document text
* `thematic_score`: scoring baseline value

Annotations are joined to scored documents by `url`.

### Dataset status

Current dataset status:

* total annotations: `166`
* missing scored records: `1`
* evaluable records: `125`
* review records: `40`
* train records: `100`
* test records: `25`

The missing scored record is a newsletter page that is now correctly removed by hard filtering before scoring.

### Baseline model

The first baseline model uses TF IDF text features and Logistic Regression.

The model input text is built from document title and cleaned text.

The model produces:

1. binary prediction
2. probability for `tlm_relevant`
3. evaluation metrics on a reproducible train test split

### Baseline result

The first TF IDF Logistic Regression baseline was evaluated against the same test split as the scoring baseline.

Result on the test set:

* TF IDF Logistic Regression precision: `0.917`
* TF IDF Logistic Regression recall: `0.733`
* TF IDF Logistic Regression F1: `0.815`
* TF IDF Logistic Regression false positives: `1`
* TF IDF Logistic Regression false negatives: `4`
* Scoring v10 precision at threshold `0.10`: `0.750`
* Scoring v10 recall at threshold `0.10`: `1.000`
* Scoring v10 F1 at threshold `0.10`: `0.857`
* Scoring v10 false positives at threshold `0.10`: `5`
* Scoring v10 false negatives at threshold `0.10`: `0`

The learned baseline is more precise, but less recall oriented.

It does not outperform the rule based scoring baseline for the current MVP goal.

The main observed classifier errors are missed relevant project pages and false positives on domain language without concrete TLM relevance.

### Boundary to scoring

Classification is evaluated against the rule based scoring baseline.

The scoring baseline remains a ranking and filtering signal.

The classifier is a learned decision baseline.

### Boundary to lead generation

Classification does not generate final leads.

Lead generation consumes classifier predictions, probabilities, thematic scores, and document metadata to produce actionable review candidates.

### Output

The baseline classification script writes:

1. train split
2. test split
3. review set
4. test predictions
5. metrics comparing classifier and scoring baseline

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

For the MVP baseline, a document is included as a lead if:

`thematic_score >= 0.10`

This threshold follows the scoring v10 baseline evaluation.

The classifier output is not used as the primary inclusion criterion yet, because the first TF IDF baseline had lower recall than scoring v10.

Classifier predictions and probabilities may be attached as additional review signals.

Current baseline output after reprocessing:

* input documents: `165`
* generated leads: `109`
* threshold: `0.10`

The output is intentionally broad because the threshold is recall oriented.

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