# Architecture

## MVP Scope Decision

The MVP monitoring scope is limited to a single canton.

### Selected canton
Zürich

### Scope policy
The system monitors only manually curated official canton level web sources for the selected canton.

The purpose of monitoring is not to directly confirm finished real world changes.
The purpose is to generate deterministic leads for potential TLM relevant changes that can be prioritized for manual validation.

### Included in MVP
- one canton only
- manual source curation
- official canton level web sources
- project and publication pages that may indicate planned, ongoing, or completed infrastructure changes
- versioned scope configuration in Git
- deterministic source selection from config
- deterministic candidate discovery from configured sources
- deterministic downstream lead generation from processed content

### Explicitly excluded from MVP
- municipalities
- unofficial media sources
- associations and private organizations
- social media channels
- automatic source discovery
- cross canton support in runtime behavior
- automatic confirmation that a detected lead corresponds to a finished TLM relevant change

### Rationale
The MVP prioritizes determinism, reviewability, and low operational complexity.

A narrow and explicit source boundary is required so that the same configuration always resolves to the same source set.

For TLM relevant changes, official project and infrastructure pages are often more useful than generic news pages because they provide earlier and more persistent signals about possible future geometry changes.

The MVP therefore focuses on lead generation instead of final change confirmation.
This allows earlier awareness of potentially relevant real world developments, while keeping manual review in the loop.

### Extensibility
The configuration model must be designed so that additional cantons can be added later without changing the core logic.

This means canton specific scope and source registries are data driven, not hardcoded.

## Configuration Model

The monitoring configuration is separated into scope definition and source registry.

### Scope definition

The file `config/scope.yaml` defines the active monitoring context for a run.

Current fields:
- `version`: integer representing the schema version of the scope configuration
- `canton_id`: selected canton identifier
- `languages`: allowed language set for the monitoring scope
- `time_window_days`: defines the temporal lookback window applied during data collection and filtering steps
- `source_registry`: name of the source registry file to load
- `source_policy`: policy label describing which source types are intended to be allowed

This file defines the scope of monitoring, but not the concrete source endpoints.

### Source registry

The file `config/sources/<registry>.yaml` defines the concrete source entries for the selected registry.

The source registry is the single explicit source of truth for which official sources belong to the monitored source set.

It defines the concrete source endpoints and discovery rules that are allowed for the active monitoring scope.

Only sources explicitly listed in the versioned source registry may be used by the pipeline.

Each source entry contains:
- `source_id`
- `name`
- `base_url`
- `crawl_type`
- `crawl_frequency_hours`
- `active`
- optional `include_patterns` for pattern based discovery sources

For `html_pattern` sources, `include_patterns` is required and defines which discovered URLs belong to the monitored source surface.

This file defines which exact source endpoints belong to the monitored source set.

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

- `source_id`
- `base_url`
- `crawl_type`
- `active`

Additional required fields for `html_pattern` sources:

- `include_patterns`

Optional fields ignored by discovery:

- `name`
- `crawl_frequency_hours`

### Source selection for discovery

Only sources fulfilling all of the following are passed to discovery:

- `active` is true
- `crawl_type` equals `html_pattern`

All other sources are ignored by discovery.

### Assumptions and limitations

The MVP discovery model assumes:

- a single HTML entry point per source (`base_url`)
- static HTML content accessible via HTTP GET
- no JavaScript rendering required
- no pagination handling
- no API based discovery

Sources that do not satisfy these constraints are not supported in the MVP.

### What discovery does

- fetch HTML from each active source `base_url`
- extract hyperlinks from the HTML
- normalize and canonicalize URLs
- filter URLs using `include_patterns` for `html_pattern` sources
- remove duplicate URLs within a run
- attach metadata (`source_id`, `discovered_at`)
- persist discovered URLs as structured records

### What discovery does NOT do

- no fetching of discovered project pages
- no extraction of page content
- no semantic relevance filtering
- no scoring or ranking
- no classification
- no geographic reasoning

### HTML fetch helper

Discovery uses a dedicated HTML fetch helper to retrieve the source page at `base_url`.

The fetch helper is responsible only for technical HTTP access.

Expected behavior:

- perform an HTTP GET request to the configured `base_url`
- use a defined timeout
- return HTML text only for successful responses
- treat non successful HTTP status codes as failures
- surface network and request errors explicitly to the caller

The fetch helper must not silently suppress failures.

Failure handling and logging remain the responsibility of the discovery step.

### MVP fetch limitations

For the MVP, the fetch helper assumes:

- standard HTTP GET access is sufficient
- one request per source entry point is sufficient
- no JavaScript rendering is required
- no retry logic is required
- no authentication is required

### Link extraction

Discovery uses a dedicated HTML parsing step to extract hyperlink references from fetched source HTML.

The link extraction step is responsible for reading raw `href` values from anchor elements.

Expected behavior:

- parse HTML content
- extract `href` values from `<a>` elements
- ignore missing or empty `href` attributes
- ignore non navigational references such as fragment only links
- ignore non HTTP navigation schemes such as `mailto:` and `javascript:`

The extraction step returns raw link candidates only.

It must not perform URL normalization, pattern filtering, deduplication, or semantic relevance decisions.

### MVP parsing assumptions

For the MVP, link extraction assumes:

- relevant links are present in standard anchor tags
- source HTML is parseable with a standard HTML parser
- only anchor based hyperlink extraction is required
- no JavaScript generated links are supported

### URL normalization

Discovery uses a dedicated normalization step to convert raw link candidates into stable absolute URLs.

The normalization step is responsible for technical URL canonicalization only.

Expected behavior:

- resolve relative links against the configured `base_url`
- preserve absolute HTTP and HTTPS links
- remove URL fragments
- discard unusable or invalid link values
- return canonical absolute URL strings

For the MVP, normalization must not apply semantic filtering.

In particular, it must not decide whether a URL is relevant to the monitored source surface.

### MVP normalization rules

For the MVP, the following rules apply:

- only `http` and `https` URLs are retained
- fragment identifiers are removed
- query strings are preserved
- trailing slashes are not rewritten
- domain based inclusion or exclusion is not handled in normalization

Normalization produces technical URL candidates that are filtered in later steps.

### Include pattern filtering

Discovery uses `include_patterns` to restrict normalized URLs to the configured source surface.

This is a configuration driven filtering step and represents an explicit system design decision.

Expected behavior:

- each normalized URL is checked against the configured `include_patterns`
- a URL is retained if it matches at least one configured pattern
- a URL is discarded if it matches no configured pattern
- matching is deterministic and string based

For the MVP, `include_patterns` are interpreted as substring matches against the normalized URL string.

No regex evaluation, semantic interpretation, or content based filtering is applied at this step.

### MVP filtering assumptions

For the MVP, pattern filtering assumes:

- the configured patterns are sufficiently specific to represent the intended source surface
- pattern selection is maintained manually in the source registry
- false positives and false negatives caused by coarse URL patterns are possible and must be reviewed during source configuration

### Deduplication

Discovery applies deduplication after normalization and include pattern filtering.

Deduplication is performed within a single discovery run and within each `source_id`.

Expected behavior:

- identical normalized URLs discovered from the same source are retained only once
- identical normalized URLs discovered from different sources are kept as separate records
- deduplication must preserve stable output order

For the MVP, URL equality is determined by exact string equality after normalization.

No semantic URL equivalence beyond normalization is applied.

### MVP deduplication assumptions

For the MVP, deduplication assumes:

- normalization has already produced stable canonical URL strings
- the source of discovery remains part of the record identity for traceability
- cross source duplication is not collapsed

### Metadata attachment

After normalization, include pattern filtering, and deduplication, discovery attaches record metadata to each retained URL.

Expected behavior:

- each retained URL receives the originating `source_id`
- each retained URL receives a discovery timestamp in UTC
- optional traceability fields such as `base_url` and `matched_pattern` may be attached

If multiple include patterns match the same URL, the first matching pattern in source registry order is stored as `matched_pattern`.

For the MVP, `discovered_at` is assigned once per discovery run and reused for all records created in that run.

This ensures stable and comparable output records within the same execution.

### MVP metadata assumptions

For the MVP, discovery metadata is limited to source level provenance and run time traceability.

No document identity, crawl status, content metadata, or downstream processing metadata is attached at this stage.

### Discovery persistence boundary

Discovery persists only the final retained discovery records of a run.

The persisted output contains the structured `DiscoveredUrlRecord` dataset after:

- HTML fetch
- link extraction
- URL normalization
- include pattern filtering
- deduplication
- metadata attachment

Discovery does not persist intermediate parsing or filtering artefacts as part of the MVP contract.

Expected behavior:

- output is written in a structured and inspectable format
- output path is deterministic within the run context
- persisted records can be reloaded for downstream crawling steps

For the MVP, JSONL is the preferred persistence format.
CSV may be supported as an additional export format.

### MVP persistence assumptions

For the MVP, discovery persistence is limited to final discovery outputs.

Raw source HTML, fetched project page HTML, content hashes, and extraction outputs belong to later pipeline steps and are not part of the discovery persistence contract.

### Discovery logging

Discovery must produce structured and human readable logs at source level and run level.

The purpose of logging is to make discovery behavior traceable and failures diagnosable.

Expected logging includes at least:

- discovery start for each `source_id`
- fetch success or fetch failure
- number of raw links extracted from source HTML
- number of valid normalized URLs
- number of URLs retained after include pattern filtering
- number of final unique URLs after deduplication
- persistence success including output path and written record count

Failures must be logged with source context and error type.

Logging must not stop the full run unless failure handling is explicitly configured otherwise.

### MVP logging assumptions

For the MVP, discovery logging is focused on operational traceability.

Logging is aggregated at source level by default.

Per URL debug logging may be added later but is not required for the MVP contract.

### Monitoring over time

Discovery logging describes behavior within a single run.

Long term source monitoring requires additional state that is outside the MVP discovery contract.

This includes for example:

- last successful discovery time per source
- last discovery failure per source
- known discovered URLs from previous runs
- newly discovered URLs compared with previous runs
- unexpected drops or spikes in discovery volume

This cross run monitoring state is not part of the initial discovery implementation.
It is a later extension for incremental monitoring operation.

### Determinism requirement

Discovery must be deterministic given:

- identical source registry configuration
- identical HTML input at `base_url`

The same input must always produce the same set of discovered URLs.

### Discovery output schema

Discovery produces one structured record per discovered candidate URL.

Each record contains the following required fields:

- `source_id`: stable identifier of the configured source that produced the URL
- `url`: canonical absolute URL of the discovered candidate page
- `discovered_at`: timestamp of the discovery run in UTC

Optional fields may be added for traceability:

- `base_url`: source entry URL from which discovery started
- `matched_pattern`: first matching include pattern in source registry order

The discovery output must not contain content level fields such as page title, extracted text, HTTP status, or content hash.

Those belong to later pipeline steps.

The output is stored as a structured dataset in JSONL or CSV format.

### Discovery data model location

The discovery output schema should be implemented as an explicit application level data model.

For the MVP, discovery records may be represented in a dedicated module such as `src/changescout/models.py`.

This avoids implicit dictionary based contracts and makes validation, testing, and persistence more reliable.

### Boundary to crawling

Discovery outputs only URLs and metadata.

The crawling step is responsible for:

- fetching discovered URLs
- storing raw HTML of project pages

No content level processing is allowed in discovery.

### Design note on include_patterns

`include_patterns` defines which URLs are considered part of the monitored source surface.

This introduces an explicit, configuration driven filtering layer.

Pattern selection must be treated as part of the system design and reviewed accordingly.

## Crawling Architecture

### Responsibility

The crawling step is responsible for fetching discovered URLs from discovery output and storing raw HTML plus fetch metadata for later processing.

Crawling operates on discovered project page URLs and does not interpret page content.

### Crawling input contract

Crawling consumes structured discovery output records.

Required fields per discovered URL record:

- `source_id`
- `url`
- `discovered_at`

Optional discovery traceability fields may be present:

- `base_url`
- `matched_pattern`

Crawling uses only the required fields for fetch and persistence behavior.

Optional fields may be preserved for traceability, but they are not required for the crawling contract.

Crawling must fail explicitly if required discovery fields are missing.

### Assumptions and limitations

The MVP crawling model assumes:

- discovered URLs are accessible via standard HTTP GET
- raw HTML content can be captured without JavaScript rendering
- redirects may occur and are handled by the HTTP client
- no authentication is required
- no retry logic is required
- each fetched page is handled independently

Pages that do not satisfy these constraints are not fully supported in the MVP.

### What crawling does

- load discovered URL records from structured discovery output
- fetch each discovered URL via HTTP GET
- capture HTTP status and fetch timestamp
- store raw HTML response bodies for successful fetches
- compute a stable content hash from stored HTML
- attach fetch metadata to structured crawl records
- persist crawl records as structured output
- continue processing when individual page fetches fail

### What crawling does NOT do

- no URL discovery
- no extraction of page text
- no HTML cleaning or normalization of content
- no semantic relevance filtering
- no scoring or ranking
- no classification
- no geographic reasoning
- no interpretation of whether a page indicates a true change
- no downstream lead generation

### Page fetch helper

Crawling uses a dedicated page fetch helper to retrieve each discovered URL.

The fetch helper is responsible only for technical HTTP access.

Expected behavior:

- perform an HTTP GET request to the discovered `url`
- use a defined timeout
- allow redirects
- capture response status code
- return response body for successful fetches
- surface network and request errors explicitly to the caller
- preserve non successful HTTP responses as structured outcomes

The fetch helper must not silently suppress failures.

Failure handling and logging remain the responsibility of the crawling step.

### MVP fetch limitations

For the MVP, the fetch helper assumes:

- standard HTTP GET access is sufficient
- one request per discovered URL is sufficient
- no JavaScript rendering is required
- no retry logic is required
- no authentication is required

### HTML storage layout

Crawling stores raw HTML response content in a deterministic and inspectable file layout.

Expected behavior:

- each stored HTML document is written to a stable path within the crawl run output
- storage layout separates runs and sources
- unrelated pages must not overwrite each other
- stored files remain directly inspectable for debugging and downstream processing

An example layout is:

- `data/crawling/<run_id>/<source_id>/<content_hash>.html`

The exact root path may vary by environment, but the storage structure must remain deterministic within the run context.

### HTML persistence

Crawling persists raw HTML exactly as fetched, without content interpretation.

Expected behavior:

- HTML is stored as UTF 8 text
- empty or missing bodies are handled explicitly
- persistence failures are surfaced and logged
- stored file paths are attached to crawl output records

For the MVP, crawling stores raw page artefacts only.
Parsed text, extracted metadata, and cleaned content belong to later pipeline steps.

### Content hash generation

Crawling computes a stable content hash for fetched HTML content.

Expected behavior:

- the same HTML content always produces the same hash
- different HTML content produces a different hash
- the hash is derived from raw stored HTML content
- the hash is recorded in the structured crawl output

For the MVP, the content hash acts as a deterministic page identity signal within crawling output.
It is not a semantic deduplication mechanism.

### Crawl record creation

After fetch and persistence, crawling creates one structured record per attempted page fetch.

Each record contains at least:

- `source_id`
- `url`
- `fetched_at`
- `status_code`
- `content_hash`
- `html_path`

Optional fields may be added for traceability and error capture:

- `error`
- `discovered_at`

If a fetch fails before HTML storage is possible, the record may omit `content_hash` and `html_path` and instead contain an `error` field describing the failure.

### Crawl persistence boundary

Crawling persists only the final structured crawl records of a run plus raw stored HTML files.

The persisted crawl output contains the structured page fetch dataset after:

- discovery input loading
- page fetch
- HTML persistence
- content hash generation
- metadata attachment

Crawling does not persist downstream parsing, extraction, classification, or lead scoring artefacts as part of the MVP contract.

Expected behavior:

- structured crawl output is written in a structured and inspectable format
- output path is deterministic within the run context
- persisted records can be reloaded for downstream processing steps

For the MVP, JSONL is the preferred persistence format.
CSV may be supported as an additional export format for metadata only.

### MVP persistence assumptions

For the MVP, crawling persistence is limited to raw HTML storage and final crawl records.

Extracted text, page titles, cleaned page content, semantic labels, and lead assessment outputs belong to later pipeline steps and are not part of the crawling persistence contract.

### Crawling logging

Crawling must produce structured and human readable logs at page level and run level.

The purpose of logging is to make crawling behavior traceable and failures diagnosable.

Expected logging includes at least:

- crawl start
- input record count
- fetch success or fetch failure per URL
- HTTP status code for completed responses
- HTML persistence success including output path
- final crawl record count
- run completion summary

Failures must be logged with source context, URL, and error type.

Logging must not stop the full run unless failure handling is explicitly configured otherwise.

### MVP logging assumptions

For the MVP, crawling logging is focused on operational traceability and failure diagnosis.

Logging is aggregated at run level and page level as needed to understand fetch outcomes.

Detailed downstream content inspection logs are not part of the MVP crawling contract.

### Monitoring over time

Crawling logging describes behavior within a single run.

Long term crawl monitoring requires additional state that is outside the MVP crawling contract.

This includes for example:

- last successful fetch time per URL
- repeated fetch failures for the same URL
- content hash changes across runs
- newly failing URLs compared with previous runs
- unexpected drops in crawl success rate

This cross run monitoring state is not part of the initial crawling implementation.
It is a later extension for incremental monitoring operation.

### Determinism requirement

Crawling must be deterministic given:

- identical discovery input
- identical HTTP response behavior for each discovered URL

The same input must always produce the same crawl records and stored HTML artefacts.

### Crawling output schema

Crawling produces one structured record per attempted page fetch.

Each record contains the following required fields for successful fetches:

- `source_id`: stable identifier of the configured source that originally produced the URL
- `url`: canonical absolute URL of the fetched page
- `fetched_at`: timestamp of the crawl run in UTC
- `status_code`: HTTP response status code
- `content_hash`: stable hash of the fetched raw HTML content
- `html_path`: persisted path to the stored raw HTML file

Optional fields may be added for traceability and failure handling:

- `discovered_at`: timestamp originally attached during discovery
- `error`: structured or string error description for failed fetches

The crawling output must not contain downstream interpretation fields such as extracted text, page title, semantic labels, relevance score, or lead decision.

Those belong to later pipeline steps.

The output is stored as a structured dataset in JSONL or CSV format.

### Crawling data model location

The crawling output schema should be implemented as an explicit application level data model.

For the MVP, crawl records may be represented in a dedicated module such as `src/changescout/models.py`.

This avoids implicit dictionary based contracts and makes validation, testing, and persistence more reliable.

### Boundary to downstream processing

Crawling outputs only raw HTML artefacts and fetch metadata.

Later processing steps are responsible for:

- parsing stored HTML
- extracting text or metadata
- classifying pages
- generating or scoring leads

No interpretation logic is allowed in crawling.

## HTML Cleaning Architecture

### Responsibility

The HTML cleaning step is responsible for transforming stored raw HTML pages into normalized text documents for downstream processing.

HTML cleaning operates on crawl output records and stored raw HTML files.

### Input contract

HTML cleaning consumes structured crawl records.

Required fields per crawl record:

- `source_id`
- `url`
- `fetched_at`
- `status_code`
- `content_hash`
- `html_path`

Only successful crawl records with HTTP status code `200` and a valid `html_path` are eligible for cleaning.

### What HTML cleaning does

- load raw HTML from `html_path`
- parse HTML content
- extract a document title
- isolate the main content area
- remove obvious boilerplate such as navigation, footer, contact, feedback, breadcrumbs, and related content
- extract lead text and main content sections
- normalize whitespace and duplicate text blocks
- detect document language
- enforce a minimum text length
- persist normalized documents as JSONL
- persist excluded documents with exclusion reasons
- create a cleaning report

### What HTML cleaning does NOT do

- no semantic relevance filtering
- no structural change classification
- no scoring or ranking
- no geographic reasoning
- no lead generation
- no confirmation of real world changes

### Source specific extraction

For the MVP, HTML cleaning uses source specific extraction logic for the selected Zürich sources.

This is acceptable because the MVP source set is manually curated and intentionally narrow.

The extraction logic prioritizes recall over precision.
It should preserve potentially relevant infrastructure information even if some descriptive or process related text remains.

### Normalized document schema

HTML cleaning produces one normalized document per included crawl record.

Each normalized document contains at least:

- `document_id`
- `source_id`
- `url`
- `title`
- `clean_text`
- `language`
- `crawl_timestamp`
- `html_path`
- `clean_text_length`

The normalized document schema is the input contract for downstream filtering, scoring, classification, and lead generation.

### Exclusion reasons

Documents may be excluded during HTML cleaning for technical quality reasons only.

Supported exclusion reasons include:

- `crawl_failed`
- `missing_html_path`
- `no_main_text`
- `extraction_failed`
- `too_short`
- `unsupported_language`

These exclusions are not semantic relevance decisions.

### Persistence

HTML cleaning writes:

- `artifacts/cleaned.jsonl`
- `artifacts/excluded.jsonl`
- `artifacts/html_cleaning_report.json`

Generated artefacts are not versioned in Git.

## Hard Filtering Boundary

### Responsibility

The hard filtering step removes only clearly irrelevant normalized documents before downstream scoring and classification.

It is a safety filter, not a relevance model.

### Filter policy

Hard filtering must preserve all plausible infrastructure project documents.

This includes soft or ambiguous infrastructure changes such as:

- road renovation
- safety improvements
- noise reduction
- bus stop redesign
- cycle infrastructure
- construction phase updates

These documents may later receive a lower score or be classified as non structural, but they must not be removed by hard filtering.

### What hard filtering may remove

Hard filtering may remove documents that are clearly outside the monitored domain, for example:

- cultural events
- job pages
- generic administration pages
- political pages without infrastructure content
- pure media overview pages
- unrelated downloads or service pages

### What hard filtering must not remove

Hard filtering must not remove documents merely because they are weak, soft, indirect, or ambiguous infrastructure signals.

In particular, terms such as `Sanierung`, `Sicherheit`, or `Lärmschutz` are not sufficient exclusion reasons.

### Boundary to scoring and classification

Structural versus non structural distinction belongs to downstream scoring and classification.

Hard filtering may compute simple rule based signals for later stages, but those signals must not be used as final exclusion logic in the MVP.

### Filtering output

The hard filtering step produces three artefacts:

- `artifacts/filtered.jsonl`: normalized documents that passed the hard filter
- `artifacts/filtered_excluded.jsonl`: documents excluded by the hard filter including exclusion reason and matched rule
- `artifacts/filter_report.json`: summary statistics of the filtering run

### Filtered document enrichment

Documents in `filtered.jsonl` may be enriched with a `filter_signals` field.

This field contains simple rule based signals such as:

- keyword hits for structural change indicators
- keyword hits for soft change indicators
- text length indicators

These signals are not used for hard exclusion in the MVP.

They serve as input for downstream scoring and ranking.

### Determinism

Given identical input (`cleaned.jsonl`) and identical filter configuration (`config/filter.yaml`), the filtering step must produce identical outputs.

### Boundary

The filtering step:

- does not remove documents based on structural versus non structural interpretation
- does not perform scoring or ranking
- does not classify documents

Its sole responsibility is conservative removal of clearly irrelevant documents and generation of simple signals.


## Thematic Scoring

### Responsibility

The thematic scoring step ranks normalized documents by their likelihood of describing structural infrastructure changes.

Scoring is not a filtering step.
It does not remove documents.

### Scoring policy

The scoring step must preserve all documents from the filtering stage.

Its purpose is to assign a relative score that reflects how strongly a document indicates a structural change in the transport network.

Structural change indicators include for example:

- new construction
- road expansion
- junction redesign
- bridge or tunnel construction
- network relevant modifications

Soft change indicators include for example:

- maintenance
- safety improvements
- noise reduction
- temporary traffic changes

Soft indicators may reduce the score but must not exclude documents.

### Score computation

The final `thematic_score` is computed as:

`thematic_score = rule_weight * rule_score + retrieval_weight * retrieval_score`

Weights are defined in `config/scoring.yaml` and must sum to 1.

The `rule_score` is normalized using a fixed rule based scale.

The `retrieval_score` is a run relative BM25 score.

Raw BM25 scores are normalized per scoring run using min max normalization across all documents:

`retrieval_score = (bm25_raw_score - min_bm25_raw_score) / (max_bm25_raw_score - min_bm25_raw_score)`

If all BM25 raw scores are identical, all retrieval scores are set to 0.

This means retrieval scores are comparable within one run, but not directly comparable across different corpora, cantons, or source sets.

For the MVP, rule based and retrieval based scoring rely on overlapping vocabularies.

Retrieval scoring mainly introduces weighting by term frequency and document specificity rather than new semantic signals.

### MVP scoring limitation

The initial thematic scoring configuration is calibrated on the selected Zürich Tiefbau source set.

The keyword lists and weights reflect the terminology observed in this MVP corpus.

Scores are therefore suitable for ranking documents within the current MVP scope, but they should not be treated as canton independent relevance scores.

The `thematic_score` is the final hybrid score.

It is computed as a weighted combination of:

- `rule_score`: rule based score derived from structural, soft, and title based signals
- `retrieval_score`: BM25 based lexical retrieval score derived from configured query terms

For the MVP, BM25 query terms are intentionally aligned with the structural keyword list.

This keeps the initial scoring configuration simple and traceable.

When additional cantons or source types are added, both keyword lists and BM25 query terms must be reviewed and may need to diverge.

Retrieval terms may need to be broader or source specific, while rule based structural keywords should remain precise.

When additional cantons or source types are added, the scoring configuration must be reviewed and recalibrated.

### Boundary to filtering

Filtering removes clearly non domain content.

Scoring operates only on documents that passed filtering and must not remove additional documents.

### Boundary to classification

Scoring does not perform a final semantic decision.

It provides a continuous relevance signal.

The decision whether a document represents a structural change belongs to classification.

### Boundary to lead generation

No fixed relevance threshold is defined in the scoring step.

Scores are used for deterministic ranking only.

Thresholding, top k selection, or lead inclusion decisions are deferred to the lead generation stage.

### Determinism

Given identical input (`filtered.jsonl`) and identical scoring configuration, the scoring step must produce identical scores.

### Output

Each document receives:

- `thematic_score`: final normalized score between 0 and 1
- `rule_score`: normalized rule based score
- `retrieval_score`: normalized BM25 retrieval score
- `scoring_signals`: explanation fields including:
  - structural keyword hits
  - soft keyword hits
  - title based keyword hits

The `thematic_score` is a weighted combination of `rule_score` and `retrieval_score` as defined in the scoring configuration.

The output dataset must preserve all input documents and enrich them with scoring metadata.


## Lead generation model

The system generates candidate leads from the monitored source set.

A lead is an item from an official source that may indicate a TLM relevant real world change, such as:
- a planned road project
- an infrastructure upgrade
- a junction redesign
- a bridge replacement
- a new road section
- another potentially geometry relevant transport infrastructure change

A lead is not treated as confirmed truth.

The MVP does not automatically determine whether the corresponding real world change is already finished or already visible in the target data.

Lead assessment and later confirmation remain separate steps.

## Design rationale

This separation keeps monitoring scope stable while allowing controlled updates to the concrete source list.

Additional cantons should be added through new registry files and configuration, not by changing application logic.