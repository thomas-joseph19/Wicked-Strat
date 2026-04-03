# Phase 1: Context & Data Ingestion Pipeline - Research

## Technical Approach
Python with Polars will be utilized to ingest the `nq_1min_10y.parquet`. Since Polars has excellent built-in lazy evaluation and fast timezone manipulations, we will parse the UTC timestamps and bind them to US/Eastern timezone boundaries.

## Key Challenges
1. Timezone offset differences (DST changes) between UTC and EST/EDT across 10 years.
2. Slicing the Globex session properly. A new day session begins at 18:00 ET the calendar day prior.
3. Managing precision loss handling the 0.25 tick distributions.

## Validation Architecture
Testing will focus on dataframe invariants: checking row counts, schema typing, and validating that the derived `session_id` logic perfectly maps known DST transition days.
