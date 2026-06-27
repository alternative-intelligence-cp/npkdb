# NPKDB 0.24.2 Release Notes

## Bug Fixes

### HNSW Single-Stage Filter Regression (`test_single_stage_filter`)
Fixed a severe regression in single-stage filtering during HNSW searches that resulted in `pq_size == 0` (no results found) when the entry point or early neighbors did not match the given filter.

**Root Causes & Fixes:**
1. **Search Traversal Stall:** In `hnsw_search_layer`, nodes that failed the single-stage filter were incorrectly omitted from the `candidates` queue. This caused the graph traversal to stall prematurely if the entry point or early nodes didn't match the filter. The search layer now correctly pushes all evaluated nodes to the `candidates` queue to continue spatial exploration, but only pushes to the result max-heap `W` if they successfully match the filter.
2. **Missing Visited Set Clear:** Fixed a bug in `test_single_stage_filter/main.npk` where the traversal visited set (`visited_set`) was not cleared after creation. Due to the uninitialized state, the search considered all nodes as already visited and immediately aborted traversal. 
3. **Invalid Slot vs Doc ID Check:** Fixed test validation logic in `test_single_stage_filter/main.npk` that erroneously assumed HNSW arena slots were identical to document IDs. The test now correctly calculates the `doc_id` from the vector offset for assertions.

## Implementation Details
- `src/vector/hnsw_search.npk`: Refactored candidate and neighbor queue insertion logic to ensure graph traversal is completely independent of filter results. Added proper `evaluate_filter` execution.
- `tests/test_single_stage_filter/main.npk`: Added missing `hnsw_visited_clear` before initiating searches and implemented accurate document ID retrieval based on the graph's dynamic vector dimension.
