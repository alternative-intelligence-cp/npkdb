# NPKDB HTTP REST API

NPKDB exposes a lightweight, high-performance REST API over HTTP/1.1 for managing collections, inserting vector-embedded documents, and executing single-stage filtered searches.

---

## 1. Create a Collection
*Status: Currently a placeholder endpoint in the `0.4.x` series.*

Creates a new namespace for a set of documents and their corresponding vector index.

**Endpoint:**
`POST /collections`

**Request Body (Future):**
```json
{
  "name": "my_collection",
  "vector_dim": 1536,
  "distance_metric": "cosine"
}
```

**Response (Mock):**
```json
{
  "status": "ok",
  "message": "collection created"
}
```

---

## 2. Ingest Documents
Inserts a batch of documents into the Memtable and Write-Ahead Log (WAL), subsequently routing them to the HNSW vector graph and LSM-Tree storage engine.

**Endpoint:**
`PUT /collections/:name/docs`

**Request Body:**
A single JSON object with a `"docs"` array. Each element in the array represents a document payload. Documents can contain nested JSON structures and arrays. Vector data is stored inline (conventionally under a specific key like `"vector"`, though the exact schema depends on the collection's vector mapping configuration).

**Example Request:**
```json
{
  "docs": [
    {
      "id": "doc123",
      "category": "finance",
      "year": 2026,
      "content": "Quarterly earnings report...",
      "vector": [0.012, -0.043, 0.881, ...]
    },
    {
      "id": "doc124",
      "category": "healthcare",
      "year": 2026,
      "content": "New trial results...",
      "vector": [0.115, 0.003, -0.421, ...]
    }
  ]
}
```

**Response:**
Returns `200 OK` once the batch has been durability committed to the Write-Ahead Log.
```json
{
  "status": "ok"
}
```

---

## 3. Search and Filter
Executes a Single-Stage Filtered vector search. This traverses the HNSW graph while dynamically avoiding nodes that do not satisfy the provided JSON AST filter.

**Endpoint:**
`POST /search`

**Request Body (Conceptual):**
Expects a JSON payload defining the target vector, the collection to search, and the Abstract Syntax Tree (AST) defining the metadata filter.

**AST Filter Syntax:**
NPKDB supports MongoDB-style boolean and comparison operators.
- `$eq`: Equals
- `$gt`, `$gte`: Greater than, Greater than or equal
- `$lt`, `$lte`: Less than, Less than or equal
- `$and`, `$or`: Logical boolean combinators

**Example Request:**
```json
{
  "collection": "my_collection",
  "vector": [0.012, -0.043, 0.881, ...],
  "k": 10,
  "filter": {
    "$and": [
      { "category": { "$eq": "finance" } },
      { "year": { "$gte": 2025 } }
    ]
  }
}
```

**Response (Mock for `0.4.x`):**
Returns the matching document IDs along with their semantic distances.
```json
{
  "status": "ok",
  "results": [
    {
      "document_id": "doc2",
      "distance": 0.02
    }
  ]
}
```
