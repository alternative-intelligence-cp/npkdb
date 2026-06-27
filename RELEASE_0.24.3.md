# NPKDB 0.24.3 Release Notes

## Code Quality & Warning Remediation

- **Type Casting Warnings:** Replaced all instances of `cast_unchecked<` with the strict `@cast_unchecked<` syntax to silence Nitpick compiler warnings.
- **Variable Shadowing:** Renamed shadowed loop variables (e.g., `sort_idx` in `src/storage/compaction.npk` and multiple instances in `controllers.npk`) to prevent shadowing warnings.
- **Error Handling:** Surfaced and handled error codes from `sys(MKDIR)` in `src/storage/catalog.npk`, preventing silent directory creation failures.

## Bug Fixes

### String FFI ABI Corruption (`test_skiplist`, `test_sstable_read`)
Fixed a severe ABI mismatch in the C bindings for Nitpick's string FFI that caused memory corruption, silent read/write failures, and missing records during WAL replay and SSTable reads.

**Root Causes & Fixes:**
1. **ABI Signature Mismatch:** The `npk_mem_write_string` and `npk_mem_read_string` C functions were incorrectly defined to take/return `AriaString` structs by value. Nitpick's FFI, however, decays string parameters to `char*` and expects string returns to be `char*` (which it subsequently processes via `strlen`). This mismatch resulted in reading misaligned memory and silent database storage failures.
2. **Memory Leak Prevention:** When reading a non-null-terminated string from an SSTable, returning a newly `malloc`'d string leaked memory because Nitpick's FFI boundary copies the returned buffer but never calls `free` on the native pointer.
3. **Fix:** Rewrote `npk_mem_read_string` and `npk_mem_write_string` in `mem_primitives.c` to use the correct `char*` signatures. Implemented an auto-growing thread-local buffer in `npk_mem_read_string` to safely append null terminators and return strings to the Nitpick runtime without leaking memory.

## Implementation Details
- `src/storage/catalog.npk`: Added checks for `EEXIST` when making directories.
- `src/storage/compaction.npk` & `src/network/controllers.npk`: Variable renaming for scope hygiene and strict compliance.
- `libnitpick_runtime.a` (`src/runtime/allocators/mem_primitives.c`): Corrected FFI signatures for string primitives and utilized thread-local storage for safe reads.
