# Phase 1: Context & Data Ingestion Pipeline - Validation

1. Dimension 1 (Types): Dataframe columns map strongly to proper Polars primitives (Float32/64 for OHLC, Int32/64 for Volume, Datetime for Timestamps).
2. Dimension 2 (Edge): Verify daylight savings boundaries maintain exactly 24-hours or 23/25 hours correctly without shifting session start rules.
3. Dimension 3 (Integration): Script should expose a generator/iterator mechanism to yield session-sliced chunks cleanly to downstream phases.
4. Dimension 8 (Nyquist): Are there implicit assumptions? Do all data points exist? Ensure we filter weekends properly if data gaps exist.
