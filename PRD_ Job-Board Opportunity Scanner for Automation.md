<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# PRD: Job-Board Opportunity Scanner for Automation Lead Generation

## Overview

Build a lead-generation system that monitors job postings and identifies companies hiring for workflows that are likely partially automatable, then produces scored outreach-ready leads for sales review.[^1][^2]

The product is not a generic scraper and not a job application tool. Its purpose is to convert hiring signals into business-development opportunities by detecting repetitive, process-heavy operational roles and estimating whether an automation audit or pilot could be sold to the hiring company.[^1]

The initial geographic and regulatory focus should be France, with France Travail as the primary data source because it offers an official jobs API for active listings, while Indeed shows restrictive crawl guidance in its robots file and should not be the system backbone.[^2][^3][^1]

## Product goal

The system should answer one question reliably: “Which companies are currently hiring for repetitive operational work that could be reduced, accelerated, or standardized through automation?”[^1]

The output should help a sales operator prioritize outreach, not replace judgment. Every lead should include the original job signal, a machine-generated hypothesis about the likely workflow pain point, and a confidence score indicating automation fit.[^1]

## Users

Primary user: founder, solo operator, or sales researcher looking for outbound leads for automation services.

Secondary user: developer or analyst maintaining source connectors, scoring rules, and enrichment pipelines.

## Core use cases

1. Fetch new job listings from approved sources on a schedule and normalize them into a common schema.[^2][^1]
2. Detect listings whose duties imply repetitive, structured, and measurable workflows, such as administrative processing, reporting, data handling, recruiting coordination, CRM upkeep, order entry, or marketing operations.[^1]
3. Score each listing for automation potential and group them by company.[^1]
4. Enrich the company with domain, location, company size proxy, industry, and public contact points.
5. Generate an outreach hypothesis explaining what part of the role appears automatable and what type of offer could be pitched.
6. Present a review queue where a human can approve, reject, or edit leads before outreach.

## Non-goals

- Applying to jobs automatically.
- Bypassing paywalls, authentication, CAPTCHAs, or anti-bot controls.
- Mass unsolicited emailing directly from the first version.
- Claiming a job can be fully replaced; the system should frame opportunities as workflow improvement.
- Full legal compliance automation; compliance review remains a human responsibility.[^3][^4]


## Success criteria

The MVP should produce a daily or weekly list of companies with a high probability of benefiting from an automation audit, with enough context for human review and outreach drafting.[^1]

Suggested success metrics:

- Source freshness: new listings ingested within 24 hours of publication when the source supports it.[^1]
- Classification precision: at least 70 percent of “high automation fit” leads judged useful by human reviewer during pilot.
- Lead completeness: at least 80 percent of approved leads contain company name, source URL, job title, location, summary of automatable workflow, and outreach angle.
- Review efficiency: human reviewer can triage one lead in under 60 seconds on average.


## Data sources

### Primary sources

- France Travail API Offres d’emploi for active listings in France.[^2][^1]
- Employer career pages discovered from company domains.


### Secondary sources

- Public company directories and registries for legal name, address, website, and sector.
- Public web search results for enrichment such as company site, contact page, LinkedIn page, and general business description.


### Restricted or cautionary sources

- Indeed should be treated as a research reference, not the core ingestion layer, because its robots guidance indicates restrictions around job paths and related crawling patterns.[^3]
- Any source requiring account login, protected APIs without permission, or technical bypassing should be excluded from MVP.[^4]


## Functional requirements

### 1. Source ingestion

The system shall support scheduled ingestion from France Travail API using keyword, geography, contract type, and pagination parameters where available.[^2][^1]

The system shall store the raw source payload and also map it into a normalized job schema.

The system shall deduplicate listings using a combination of source ID, canonical URL, company name, title, and normalized publish date.

### 2. Normalization

The system shall normalize each listing into fields such as:

- Source name.
- Source job ID.
- Source URL.
- Job title.
- Company name.
- Company website if available.
- Location.
- Posting date.
- Contract type.
- Full description.
- Language.
- Salary if present.
- Tags extracted from text.


### 3. Automation-fit scoring

The system shall compute an automation-fit score from 0 to 100.

The score should combine weighted signals such as:

- Repetitive task indicators, for example saisie, reporting, coordination, processing, scheduling, relances, CRM updates, support back-office.
- Structured input indicators, for example documents, PDFs, spreadsheets, CRM, ERP, email inbox, forms, candidate records.
- Measurable output indicators, for example turnaround, volume, follow-up cadence, reporting frequency.
- Software stack indicators, for example Excel, Google Sheets, HubSpot, Salesforce, ATS, ERP, email tools.
- Human-judgment dampeners, for example strategic leadership, therapy, enterprise sales ownership, bespoke creative direction.

Suggested scoring bands:

- 80 to 100: strong automation opportunity.
- 60 to 79: moderate opportunity requiring review.
- Below 60: low automation relevance.


### 4. Opportunity hypothesis generation

For each lead, the system shall generate a short structured hypothesis:

- Likely workflow being hired for.
- Why it appears repetitive or process-heavy.
- Candidate automation angle.
- Possible first offer, such as audit, pilot, internal tool, workflow redesign, or reporting automation.
- Risk note if the role appears sensitive or relationship-heavy.

Example output structure:

- “This role appears to cover recurring reporting, document handling, and CRM hygiene.”
- “A suitable pitch could be a workflow audit plus pilot that reduces manual updates and follow-ups.”


### 5. Company enrichment

The system shall enrich approved or high-scoring companies with:

- Domain.
- Company description.
- Industry.
- Headquarters or local office.
- Company size proxy if available.
- Careers page.
- Contact page.
- Public social/profile links.


### 6. Lead review queue

The system shall provide a reviewer interface or export view where each lead can be:

- Approved.
- Rejected.
- Snoozed.
- Edited.
- Tagged by vertical.
- Assigned outreach status.


### 7. Exports

The system shall export approved leads to CSV and optionally to a lightweight CRM-friendly format.

Required export fields:

- Lead ID.
- Date found.
- Company.
- Domain.
- Job title.
- Source.
- Source URL.
- Location.
- Automation-fit score.
- Opportunity hypothesis.
- Suggested outreach angle.
- Reviewer status.
- Notes.


## Keyword and pattern strategy

The MVP should begin with a rule-based approach before introducing machine learning. Rule-based classification is easier to audit and adjust during early sales discovery.

Initial positive clusters should include:

- Administrative support: assistant administratif, back-office, office manager support, data entry, dossier processing.
- Recruiting operations: talent coordinator, recruitment assistant, sourcing support, interview scheduling, ATS updates.
- Sales and CRM operations: lead qualification support, CRM hygiene, sales admin, pipeline reporting.
- Finance and reporting ops: invoice processing, bookkeeping support, reconciliation prep, recurring reporting.
- Ecommerce and catalog ops: product data updates, order processing, inventory sync.
- Marketing ops: campaign setup, email operations, list management, reporting dashboards.

Initial negative or dampening clusters should include:

- Executive leadership.
- Pure relationship sales.
- High-stakes legal advice.
- Senior strategy consulting.
- Highly bespoke art direction or concept development.


## User stories

- As a founder, a daily list of high-fit automation leads is needed so time is spent on companies with visible operational pain.
- As a reviewer, a plain-language explanation is needed for why a listing scored highly so outreach can be personalized quickly.
- As a developer, source rules and scoring weights need configuration so the system can adapt by country and vertical without code rewrites.
- As an operator, exportable approved leads are needed so outreach can be managed in existing sales workflows.


## Recommended system architecture

### Components

1. Source connector service.
2. Normalization pipeline.
3. Scoring engine.
4. Enrichment service.
5. Lead repository/database.
6. Review dashboard or admin table.
7. Export service.

### Suggested flow

1. Scheduler triggers source ingestion.
2. Connector fetches new listings from approved source APIs or allowed public pages.[^2][^1]
3. Raw payload saved.
4. Normalizer maps fields to common schema.
5. Deduper merges repeats.
6. Scoring engine assigns automation-fit score.
7. Enrichment service attaches company metadata.
8. Hypothesis generator creates outreach-ready explanation.
9. Leads move into review queue.
10. Approved leads exported to CSV or CRM.

## Technical requirements

### Backend

- Python or Node.js acceptable.
- Job scheduler required, for example cron or queue-based workers.
- PostgreSQL recommended for structured storage.
- Optional vector search only if later adding semantic matching; not required for MVP.


### Frontend/admin

- Simple internal dashboard acceptable for MVP.
- Features needed: filter by score, source, date, region, keyword cluster, and reviewer status.
- Lead detail view should show raw description, extracted signals, company enrichment, and outreach hypothesis.


### AI/NLP layer

The first version should use deterministic rules plus lightweight NLP extraction, not a fully opaque model.

Acceptable MVP methods:

- Keyword and phrase dictionaries by workflow type.
- Named-entity extraction for software tools and company references.
- Sentence classification for repetitive-task detection.
- Template-based hypothesis generation.

Future version options:

- LLM-assisted summarization of pain points.
- Embedding-based similarity search against previously successful leads.
- Vertical-specific classifiers.


## Suggested database schema

### jobs

- id
- source
- source_job_id
- source_url
- title
- company_name
- company_domain
- location_text
- country_code
- language
- contract_type
- posted_at
- description_raw
- description_clean
- salary_text
- created_at
- updated_at


### companies

- id
- company_name
- domain
- industry
- location
- size_proxy
- website_url
- careers_url
- linkedin_url
- contact_url
- notes
- created_at
- updated_at


### lead_scores

- id
- job_id
- automation_score
- repetitive_signal_score
- structured_input_score
- measurable_output_score
- human_judgment_penalty
- explanation_json
- generated_hypothesis
- created_at


### review_queue

- id
- job_id
- company_id
- reviewer_status
- reviewer_notes
- outreach_angle
- next_action_date
- created_at
- updated_at


## API requirements

### Internal endpoints

- `GET /leads`
- `GET /leads/{id}`
- `POST /leads/{id}/approve`
- `POST /leads/{id}/reject`
- `POST /leads/{id}/snooze`
- `POST /rescore`
- `GET /export/csv`


### Connector abstraction

Each source connector should implement:

- `fetch_listings(params)`
- `normalize(raw_listing)`
- `get_rate_limit_policy()`
- `supports_incremental_sync()`


## Ranking logic

Suggested weighted formula for MVP:

- Repetitive task signals: 30 percent.
- Structured inputs/tools signals: 25 percent.
- Measurable outputs/workload signals: 20 percent.
- Operational role/title match: 15 percent.
- Negative human-judgment signals: minus up to 20 percent.
- Enrichment confidence bonus: plus up to 10 percent.

All weights should be configurable in admin settings or a config file.

## Compliance and risk requirements

The system must log the source of every listing and retain the original URL for auditability.[^1]

The system must not include features intended to evade crawl restrictions, anti-bot systems, or authentication barriers.[^4][^3]

The system should prioritize officially documented APIs and permitted access patterns, especially for France-based operations where France Travail offers structured access to active job data.[^2][^1]

The system should display a compliance note for each data source indicating whether it is API-based, public-page-based, or restricted-use.

## MVP scope

### In scope

- One primary source connector for France Travail API.[^2][^1]
- Rule-based scoring engine.
- Company enrichment via public web metadata.
- Internal review dashboard or equivalent table UI.
- CSV export.
- Configurable keyword dictionaries in French and English.


### Out of scope

- Automated email sending.
- Multi-country source expansion beyond a configurable foundation.
- LLM-heavy autonomous decisioning.
- Full CRM integration.
- Indeed-first scraping architecture.[^3]


## Phase 2 roadmap

- Multi-source expansion with permitted job sources.
- Semantic clustering of similar operational roles.
- Vertical playbooks, such as recruiting ops, finance ops, ecommerce ops, and marketing ops.
- Outreach draft generation by company and role.
- Closed-loop learning from approved leads and reply outcomes.


## QA and evaluation plan

The development team should prepare a labeled test set of 100 to 300 historical job ads across categories and mark each for low, medium, or high automation fit.

Evaluation should measure:

- Precision of high-score leads.
- Recall on known useful opportunities.
- Duplicate rate.
- Enrichment completeness.
- Reviewer time to decision.

False positives should be analyzed by category so keyword rules and penalties can be tuned.

## Example lead record

- Company: Example PME RH
- Job title: Assistant administratif et reporting
- Source: France Travail
- Score: 86
- Signals: recurring reporting, document intake, spreadsheet handling, CRM updates
- Hypothesis: company is hiring manual coordination capacity for recurring back-office workflows that may be partially automated
- Offer angle: reporting and document-flow audit plus pilot automation
- Reviewer status: pending


## Delivery expectations for development

The developer should deliver:

- Source connector module for France Travail API.[^2][^1]

<div align="center">⁂</div>

[^1]: https://www.data.gouv.fr/dataservices/api-offres-demploi

[^2]: https://api.gouv.fr/producteurs/france-travail

[^3]: https://www.indeed.com/robots.txt

[^4]: https://en.blog.mantiks.io/is-job-scraping-legal/

