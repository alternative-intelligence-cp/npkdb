# NPKDB

**A high-performance, AI-native, multi-model database engine written in [Nitpick](https://github.com/alternative-intelligence-cp/nitpick)**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![CI](https://github.com/alternative-intelligence-cp/npkdb/actions/workflows/ci.yml/badge.svg)](https://github.com/alternative-intelligence-cp/npkdb/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/alternative-intelligence-cp/npkdb)](https://github.com/alternative-intelligence-cp/npkdb/releases/latest)

---

## Overview

NPKDB is a ground-up database engine written entirely in the [Nitpick](https://github.com/alternative-intelligence-cp/nitpick) programming language. It is purpose-built for **AI and RAG (Retrieval-Augmented Generation) pipelines**, combining JSON document storage, dense vector embedding retrieval, and structured querying in a single, unified engine.

The core problem NPKDB solves is one of operational complexity: modern AI applications need to query vector embeddings *and* their associated JSON metadata atomically, at low latency, and without synchronization lag between two separate systems. NPKDB treats JSON documents and their high-dimensional vector representations as **co-located, first-class entities** within a single storage substrate.

Beyond its functional goals, NPKDB is a flagship demonstration of the Nitpick ecosystem's capability to implement **serious, high-performance systems software** — proving that Nitpick's deterministic memory model, compile-time Z3 verification, native SIMD types, and lock-free concurrency primitives are sufficient to build production-grade infrastructure from scratch.

> **Status: Active Development (v0.25)** — Core engine, LSM-Tree, HNSW Vector Index, and HTTP API are implemented and stable. See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) and [CHANGELOG.md](CHANGELOG.md).

---

## Architecture at a Glance

NPKDB is built on a layered, research-backed architecture. Every design decision is derived from proven techniques used in production systems like WiredTiger, ScyllaDB, FAISS, and Qdrant.

### Storage Engine — LSM-Tree

The foundation is a **Log-Structured Merge-Tree (LSM-Tree)**, chosen specifically to transform the random-write workloads of AI vector ingestion into efficient, sequential disk I/O.

```
┌────────────────────────────────────────────────────────────────────┐
│                         Write Path                                  │
│                                                                     │
│  Client ──► WAL (sys/fsync) ──► Memtable (lock-free Skip List)    │
│                                       │                             │
│                               [threshold reached]                   │
│                                       ▼                             │
│                       SSTable Flush (Slotted Pages, 8KB)           │
│                                       │                             │
│                         Background Compaction                       │
│                      L0 → L1 → L2 → ... (10x fan-out)             │
└────────────────────────────────────────────────────────────────────┘
```

- **Write-Ahead Log (WAL):** Mutations are appended via direct `sys(SYS_WRITE)` / `sys(SYS_FSYNC)` syscalls. Nitpick's sticky `Result<T>` error types halt the transaction immediately on any I/O failure, preventing silent data corruption.
- **Memtable:** A lock-free concurrent buffer (adaptive Skip List or ART) protected by atomic Compare-And-Swap operations — no global mutex, maximum parallelism.
- **SSTables:** Immutable, sorted on-disk files using the industry-standard **Slotted Page** layout (8KB pages with forward-growing slot arrays and backward-growing tuple regions). `limit<Rules>` type refinements and Z3 verification enforce page boundary safety at compile time.
- **Compaction:** Background threads merge overlapping SSTables, discard stale record versions, and drive physical page reordering for locality optimization.

### Vector Index — HNSW + LSM-VEC

Vector similarity search uses a **Hierarchical Navigable Small World (HNSW)** graph extended with the **LSM-VEC** disk-hybrid architecture for billion-scale embeddings without full-RAM residency.

```
┌────────────────────────────────────────────────────────────────────┐
│                   HNSW Multi-Layer Graph                            │
│                                                                     │
│   L3 (sparse)  ○ ─────── ○                   [RAM: routing]       │
│   L2           ○ ── ○ ── ○ ── ○                                   │
│   L1           ○─○─○─○─○─○─○─○─○                                  │
│   L0 (dense)   ████████████████████████████  [Disk: LSM-VEC]      │
│                                                                     │
│   Query enters L3 → descends → exits L0 with k-nearest neighbors  │
└────────────────────────────────────────────────────────────────────┘
```

- **Single-Stage Integrated Filtering:** Metadata predicates and vector distance are evaluated *concurrently* during HNSW graph traversal — no pre-filter fragmentation, no post-filter waste. This is the key innovation for high-recall, deterministic-latency AI workloads.
- **Connectivity-Aware Reordering:** Compaction threads analyze traversal statistics and co-locate frequently co-accessed vectors into contiguous pages, turning random disk reads into cache-warm sequential accesses.
- **SIMD Distance Computation:** Uses Nitpick's native `simd<tfp64, 16>` types (16 dimensions per clock cycle via AVX-512/NEON) and deterministic `tfp64` floating-point for bit-identical results across architectures.

### Concurrency — Lock-Free, Wait-Free Reads

| Component | Mechanism |
|-----------|-----------|
| Primary key index | Lock-free Adaptive Radix Tree (CAS atomics) |
| Safe memory reclamation | Epoch-Based Reclamation (EBR) — zero overhead on readers |
| Graph node lifetime | `Handle<T>` generational arenas — stale handles return `ERR`, never crash |
| Inter-thread communication | Nitpick Channels — deadlock-free message passing |
| WAL durability guarantee | Unbuffered channel (synchronous rendezvous on commit) |

### Memory Safety — No Garbage Collector

NPKDB opts out of any garbage-collected runtime. All memory safety is achieved through Nitpick language features:

- **`Handle<T>` Generational Arenas:** HNSW nodes hold logical handles instead of raw pointers. Arena resizes increment a global generation counter; stale handles return a `Result<T>` error on dereference.
- **`astack` / `ahash`:** mmap-backed ephemeral scratch memory for query state — zero heap allocation cost, destroyed instantly on function return.
- **`limit<Rules>` + Z3 Verification:** Page boundary invariants proven at compile time. If the solver cannot prove safety, a runtime check is inserted. The database crashes gracefully rather than corrupting data.
- **Sticky TBB Error Propagation:** Corrupted values (e.g., bad sensor embedding) propagate the error sentinel through arithmetic — computation halts before a corrupted vector reaches the index.

---

## Building and Installation

### Prerequisites

- **Nitpick compiler** (`npkc`) — [nitpick](https://github.com/alternative-intelligence-cp/nitpick)
- **Nitpick build system** (`npkbld`) — [nitpick-build](https://github.com/alternative-intelligence-cp/nitpick-build)
- **LLVM 20**
- Linux (x86-64 or ARM64)

### Build from Source

```bash
git clone https://github.com/alternative-intelligence-cp/npkdb.git
cd npkdb

# Build the database engine
npkbld build

# Debug build (enables Z3 contract verification)
npkbld build --debug

# Run the comprehensive test suite
npkbld test tests/
```

### Install

Once built, you can install the binary globally:

```bash
sudo cp ./build/npkdb /usr/local/bin/
```

### Usage

NPKDB runs as a standalone server, communicating via a RESTful HTTP API.

```bash
# Start the NPKDB server (default: HTTP API on :7373)
npkdb --config config.toml

# Or run directly from the build directory
./build/npkdb --config config.toml
```

---

## Configuration

NPKDB is configured via a TOML file:

```toml
[server]
host = "0.0.0.0"
port = 7373

[storage]
data_dir = "/var/lib/npkdb"
page_size_kb = 8
wal_sync_mode = "group_commit"   # or "per_write"
compaction_threads = 4

[vector]
dimensions = 1536
distance_metric = "cosine"       # or "inner_product", "l2"
hnsw_m = 16                      # HNSW connectivity parameter
hnsw_ef_construction = 200       # Build-time search depth

[concurrency]
thread_pool_size = 0             # 0 = auto (hardware_concurrency)
ebr_limbo_max_depth = 10000      # EBR safety threshold
```

---

## API

NPKDB exposes a RESTful HTTP/1.1 API.

### Insert a document + vector

```bash
curl -X POST http://localhost:7373/collections/docs/insert \
  -H "Content-Type: application/json" \
  -d '{
    "id": "doc_001",
    "vector": [0.12, -0.34, 0.56, ...],
    "metadata": {
      "title": "Q1 2026 Financial Report",
      "sector": "renewable_energy",
      "year": 2026
    }
  }'
```

### Semantic search with metadata filter

```bash
curl -X POST http://localhost:7373/collections/docs/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.10, -0.30, 0.52, ...],
    "top_k": 10,
    "filter": {
      "sector": "renewable_energy",
      "year": { "$gte": 2025 }
    }
  }'
```

### Point lookup by ID

```bash
curl http://localhost:7373/collections/docs/get/doc_001
```

---

## Performance Targets

| Operation | Target Latency | Notes |
|-----------|---------------|-------|
| Vector insert (single) | < 1 ms | Memtable write + WAL append |
| Batch insert (1K vectors) | < 50 ms | Buffered channel ingestion |
| ANN search (top-10, 1M vectors) | < 5 ms | HNSW traversal, RAM-resident L1+ |
| ANN + metadata filter (1M vectors) | < 10 ms | Single-stage integrated filtering |
| Point lookup by ID | < 0.5 ms | ART primary index → SSTable |

---

## Related Projects

| Project | Description |
|---------|-------------|
| [nitpick](https://github.com/alternative-intelligence-cp/nitpick) | The Nitpick programming language compiler |
| [nitpick-build](https://github.com/alternative-intelligence-cp/nitpick-build) | Build system for Nitpick projects |
| [nitpick-packages](https://github.com/alternative-intelligence-cp/nitpick-packages) | Standard library packages (networking, threads, channels) |
| [nitpick-libc](https://github.com/alternative-intelligence-cp/nitpick-libc) | Pure Nitpick libc / POSIX implementation |
| [nitpick-posix](https://github.com/alternative-intelligence-cp/nitpick-posix) | POSIX utility suite in Nitpick |
| [nikos](https://github.com/alternative-intelligence-cp/nikos) | Static analyzer (NASA IKOS fork) |
| [nitty](https://github.com/alternative-intelligence-cp/nitty) | Native terminal emulator in Nitpick |

---

## Known Issues

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for the current list of tracked limitations and deferred work.

---

## Contributing

NPKDB is developed by the Alternative Intelligence CP team. The project is in early development — architectural feedback, algorithmic improvements, and implementation contributions are all welcome.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

---

## License

Licensed under the **GNU Affero General Public License v3.0** — see [LICENSE](LICENSE) for full terms.

---

## References

This project is grounded in peer-reviewed research and production system design:

- Malkov & Yashunin — *HNSW: Efficient and Robust Approximate Nearest Neighbor Search* (2018)
- Mohan et al. — *ARIES: A Transaction Recovery Method* (1992)
- O'Neil et al. — *The Log-Structured Merge-Tree* (1996)
- Michael — *Hazard Pointers: Safe Memory Reclamation for Lock-Free Objects* (2004)
- Leis et al. — *The Adaptive Radix Tree: ARTful Indexing for Main-Memory Databases* (2013)

See [`META/NPKDB/REFERENCES.md`](https://github.com/alternative-intelligence-cp/npkdb) for the full annotated bibliography.


---

## Nitpick Ecosystem

This repository is part of the [Nitpick](https://github.com/alternative-intelligence-cp/nitpick) ecosystem. 
- 🌍 **[Nitpick-Lang Hub](https://github.com/alternative-intelligence-cp/nitpick-lang)** — The central hub connecting all Nitpick projects.
- 📖 **[Official Web Documentation](https://ai-liberation-platform.org/nitpick/docs/)** — Guides, references, and language specifications.
- 🛠️ **[Nitpick Compiler](https://github.com/alternative-intelligence-cp/nitpick)** — The core language and toolchain.
