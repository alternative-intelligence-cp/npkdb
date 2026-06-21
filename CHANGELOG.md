# NPKDB Changelog

All notable changes to this project will be documented in this file.

## [v1.0.0-rc1]

This marks the first Release Candidate for NPKDB, a high-performance, AI-native multi-model database featuring Single-Stage Filtered Vector Search, written entirely in Nitpick.

### Features
- **Storage Substrate (LSM-Tree):** Implemented a high-throughput storage engine utilizing a Write-Ahead Log (WAL) with group commit, an in-memory lock-free Skip List (Memtable), and leveled compaction to 8KB Slotted Pages on disk.
- **LSM-VEC Architecture:** HNSW graphs are constructed in memory and continuously flushed to immutable SSTables alongside their vector embeddings.
- **Single-Stage Filtered Search:** Metadata filters (AST JSON predicates) are evaluated concurrently during HNSW graph traversal. The algorithm efficiently routes around filtered nodes, avoiding the recall-destroying penalties of pre-filtering and the CPU-wasting penalties of post-filtering.
- **JSON Document Model:** Zero-copy JSON parser with bounds-checked, deep-nesting limits.
- **REST API:** Thread-pooled HTTP/1.1 REST interface for bulk document insertion (`PUT /collections/:name/docs`) and single-stage filtered search queries (`POST /search`).
- **TOML Configuration:** Tunable parameters for memory limits, port bindings, thread pools, and HNSW index density (`hnsw_m`, `hnsw_ef_construction`).

### Performance Optimizations
- **Hardware SIMD Acceleration:** Critical paths in Euclidean (L2) and Cosine distance functions are fully optimized using native `simd<float32, 16>` intrinsics, completely bypassing loop-level FFI overhead.
- **TLC Allocator:** Utilizes the Thread-Local Cached (TLC) `npk_tlc_alloc` Nitpick memory allocator, outperforming `ptmalloc2` (glibc) in concurrent allocation/deallocation microbenchmarks.
- **WAL Group Commit:** Batches `fsync` calls during rapid document ingestion to minimize OS-level I/O bottlenecks.

### Stability & Security
- **Z3 Formal Verification:** The entire codebase has been verified against the Nitpick Z3 SMT solver (`--verify-contracts`). Pointer arithmetic within Slotted Page offsets and HNSW graph node dereferencing are mathematically proven safe from buffer overflows.
- **Fuzzing Campaigns:** Extensively hardened against malformed JSON, corrupted WAL entries, and random disk-level block omissions.
- **Slowloris Mitigation:** Implemented socket-level timeout mechanisms (`SO_RCVTIMEO`) on the HTTP workers to thwart thread-starvation attacks from slow-feeding connections.
- **Crash Recovery:** Guaranteed ACID durability via WAL replay, successfully tested under simulated arbitrary kill-signals.

### Documentation
- Extracted and formalized the underlying concepts into `docs/ARCHITECTURE.md`.
- Exposed REST payloads and endpoints in `docs/API.md`.
- Documented daemon tunables in `docs/CONFIGURATION.md`.
