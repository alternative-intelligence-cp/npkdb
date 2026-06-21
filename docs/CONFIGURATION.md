# NPKDB Configuration Reference

NPKDB is configured primarily through a standard TOML file (`npkdb.toml`) placed in the working directory from which the server is launched. The configuration file dictates thread pool sizes, disk flushing behavior, and the construction parameters for the HNSW vector index.

If `npkdb.toml` is not present, or if specific keys are missing, the database will fall back to sensible defaults.

---

## Example `npkdb.toml`
```toml
[server]
http_port = 8080
max_threads = 8

[storage]
memtable_flush_bytes = 1048576

[vector]
hnsw_m = 16
hnsw_ef_construction = 200
```

---

## [server] Block

### `server.http_port`
- **Type:** Integer
- **Default:** `8080`
- **Description:** The TCP port that the HTTP server will bind to and listen on for incoming API requests (`/collections`, `/search`).

### `server.max_threads`
- **Type:** Integer
- **Default:** `hardware_concurrency() * 2` (minimum `4`)
- **Description:** The number of worker threads to spawn for the HTTP connection pool. These threads cooperatively handle request parsing, LSM-Tree Memtable inserts, and HNSW graph traversals.

---

## [storage] Block

### `storage.memtable_flush_bytes`
- **Type:** Integer
- **Default:** `1048576` (1 MB)
- **Description:** The capacity threshold for the active, memory-resident Memtable. When the total size of inserted JSON documents and vectors exceeds this byte limit, the Memtable is marked immutable and flushed to the disk-backed LSM-Tree as a new SSTable. Increasing this value reduces background I/O operations (fewer flushes) at the cost of higher RAM usage and longer flush durations.

---

## [vector] Block

These parameters directly influence the shape and accuracy of the Hierarchical Navigable Small World (HNSW) index used for Approximate Nearest Neighbor (ANN) search.

### `vector.hnsw_m`
- **Type:** Integer
- **Default:** `16`
- **Description:** Defines the maximum number of bi-directional graph connections (edges) created for each new node during insertion. Higher values create a denser graph, which can improve recall accuracy (especially for datasets with high intrinsic dimensionality) but increases memory consumption and insertion time. Typical ranges are between 12 and 48.

### `vector.hnsw_ef_construction`
- **Type:** Integer
- **Default:** `200`
- **Description:** Controls the size of the dynamic candidate list evaluated during the construction of the graph (when inserting a new vector). A larger `ef_construction` means the algorithm explores more potential neighbors before committing to the final `M` links. This drastically improves the quality of the index (better recall during search) at the expense of significantly slower ingestion speeds. Typical ranges are between 100 and 500.
