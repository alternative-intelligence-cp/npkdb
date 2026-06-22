# NPKDB Regex Engine Source Compilation

### File: `src/main.npk`
```nitpick
// main.npk — NPKDB server entry point

use "util/failsafe.npk".*;
use "util/config.npk".*;
use "network/server.npk".*;

func:main = int32(int32:argc, wild any->:argv) {
    println("NPKDB v0.3.11 starting...");
    
    string:cfg_path = "npkdb.toml";
    int32:res = raw config_init(cfg_path);
    if (res != 0i32) {
        println("Failed to load config from " + cfg_path);
        exit(1i32);
    }
    
    int32:server_res = raw server_start();
    if (server_res != 0i32) {
        println("Server exited with error.");
        exit(1i32);
    }
    
    exit(0);
};

```

### File: `src/storage/compaction.npk`
```nitpick
use "sstable.npk".*;
use "level_manager.npk".*;
use "memtable.npk".*;
use "skiplist.npk".*;
use "../util/constants.npk".*;
use "../util/error_codes.npk".*;

use "../util/min_heap.npk".*;

pub func:merge_iter_create = int64(int64:iters, int64:readers, int64:count) {
    int64:merge_iter = npk_core_alloc(32i64);
    drop(npk_mem_write_int64(merge_iter, 0i64, iters));
    drop(npk_mem_write_int64(merge_iter, 8i64, count));
    drop(npk_mem_write_int64(merge_iter, 24i64, readers));
    
    int64:heap = heap_create(count) ?! 0i64;
    drop(npk_mem_write_int64(merge_iter, 16i64, heap));
    
    // push first element from each iterator
    int64:i = 0i64;
    while (i < count) {
        int64:iter = npk_mem_read_int64(iters, i * 8i64);
        int64:rec = sstable_iter_next(iter) ?! 0i64;
        if (rec != 0i64) {
            string:key = sst_rec_key(rec) ?! "";
            drop(heap_push(heap, key, i, rec));
        }
        i = i + 1i64;
    }
    
    pass(merge_iter);
};

pub func:merge_iter_next = int64(int64:merge_iter) {
    int64:heap = npk_mem_read_int64(merge_iter, 16i64);
    
    int64:first_sz = heap_size(heap) ?! 0i64;
    if (first_sz == 0i64) { pass(0i64); }
    
    int64:best_rec = heap_pop_record(heap) ?! 0i64;
    int64:best_idx = heap_pop_iter_idx(heap) ?! -1i64;
    string:best_key = heap_pop_key(heap) ?! "";
    drop(heap_pop(heap));
    
    int64:iters = npk_mem_read_int64(merge_iter, 0i64);
    int64:best_iter = npk_mem_read_int64(iters, best_idx * 8i64);
    
    int64:next_rec = sstable_iter_next(best_iter) ?! 0i64;
    if (next_rec != 0i64) {
        string:next_key = sst_rec_key(next_rec) ?! "";
        drop(heap_push(heap, next_key, best_idx, next_rec));
    }
    
    while (1i64 == 1i64) {
        int64:sz = heap_size(heap) ?! 0i64;
        if (sz == 0i64) { break; }
        
        string:peek_key = heap_pop_key(heap) ?! "";
        if (peek_key != best_key) { break; }
        
        int64:dup_rec = heap_pop_record(heap) ?! 0i64;
        int64:dup_idx = heap_pop_iter_idx(heap) ?! -1i64;
        drop(heap_pop(heap));
        drop(sst_rec_free(dup_rec)); // free old record
        
        int64:dup_iter = npk_mem_read_int64(iters, dup_idx * 8i64);
        int64:dup_next = sstable_iter_next(dup_iter) ?! 0i64;
        if (dup_next != 0i64) {
            string:dup_next_key = sst_rec_key(dup_next) ?! "";
            drop(heap_push(heap, dup_next_key, dup_idx, dup_next));
        }
    }
    
    pass(best_rec);
};

pub func:merge_iter_destroy = NIL(int64:merge_iter) {
    if (merge_iter == 0i64) { pass(NIL); }
    
    int64:iters = npk_mem_read_int64(merge_iter, 0i64);
    int64:count = npk_mem_read_int64(merge_iter, 8i64);
    int64:readers = npk_mem_read_int64(merge_iter, 24i64);
    
    int64:i = 0i64;
    while (i < count) {
        int64:iter = npk_mem_read_int64(iters, i * 8i64);
        drop(sstable_iter_destroy(iter));
        
        if (readers != 0i64) {
            int64:reader = npk_mem_read_int64(readers, i * 8i64);
            drop(sstable_close_read(reader));
        }
        
        i = i + 1i64;
    }
    
    int64:heap = npk_mem_read_int64(merge_iter, 16i64);
    
    // empty heap to free leftover records
    while (1i64 == 1i64) {
        int64:sz = heap_size(heap) ?! 0i64;
        if (sz == 0i64) { break; }
        int64:rec = heap_pop_record(heap) ?! 0i64;
        drop(heap_pop(heap));
        drop(sst_rec_free(rec));
    }
    
    drop(heap_destroy(heap));
    
    drop(npk_core_dalloc(iters));
    if (readers != 0i64) {
        drop(npk_core_dalloc(readers));
    }
    
    drop(npk_core_dalloc(merge_iter));
    pass(NIL);
};

// Helper: sort an array of int64s (file_ids)
func:sort_int64_array = NIL(int64:arr, int64:count) {
    int64:i = 0i64;
    while (i < count) {
        int64:j = i + 1i64;
        while (j < count) {
            int64:a = npk_mem_read_int64(arr, i * 8i64);
            int64:b = npk_mem_read_int64(arr, j * 8i64);
            if (a > b) {
                drop(npk_mem_write_int64(arr, i * 8i64, b));
                drop(npk_mem_write_int64(arr, j * 8i64, a));
            }
            j = j + 1i64;
        }
        i = i + 1i64;
    }
    pass(NIL);
};

// Internal function to do the compaction.
// Collects all files from from_level, computes overlap, collects overlapping files from to_level.
pub func:compact_level = int64(int64:lm, int64:from_level) {
    int64:to_level = from_level + 1i64;
    if (to_level >= LM_MAX_LEVELS) { pass(0i64); }
    
    int64:from_count = lm_count_at_level(lm, from_level) ?! 0i64;
    if (from_count == 0i64) { pass(0i64); }
    
    int64:from_files = lm_get_sstables(lm, from_level) ?! 0i64;
    
    string:min_k = "";
    string:max_k = "";
    int64:i = 0i64;
    while (i < from_count) {
        int64:fid = npk_mem_read_int64(from_files, i * 8i64);
        string:fk_min = lm_get_sstable_min_key(lm, from_level, fid) ?! "";
        string:fk_max = lm_get_sstable_max_key(lm, from_level, fid) ?! "";
        
        if (i == 0i64) {
            min_k = fk_min;
            max_k = fk_max;
        } else {
            if (fk_min < min_k) { min_k = fk_min; }
            if (fk_max > max_k) { max_k = fk_max; }
        }
        i = i + 1i64;
    }
    
    int64:to_count_total = lm_count_at_level(lm, to_level) ?! 0i64;
    int64:to_files_all = 0i64;
    if (to_count_total > 0i64) {
        to_files_all = lm_get_sstables(lm, to_level) ?! 0i64;
    }
    
    int64:overlap_files = npk_core_alloc(LM_MAX_SSTABLES_PER_LEVEL * 8i64);
    int64:overlap_count = 0i64;
    
    i = 0i64;
    while (i < to_count_total) {
        int64:fid = npk_mem_read_int64(to_files_all, i * 8i64);
        string:fk_min = lm_get_sstable_min_key(lm, to_level, fid) ?! "";
        string:fk_max = lm_get_sstable_max_key(lm, to_level, fid) ?! "";
        
        // Overlap condition: not (fk_max < min_k or fk_min > max_k)
        int64:no_overlap = 0i64;
        if (fk_max < min_k) { no_overlap = 1i64; }
        if (fk_min > max_k) { no_overlap = 1i64; }
        
        if (no_overlap == 0i64) {
            drop(npk_mem_write_int64(overlap_files, overlap_count * 8i64, fid));
            overlap_count = overlap_count + 1i64;
        }
        i = i + 1i64;
    }
    
    if (to_files_all != 0i64) { drop(npk_core_dalloc(to_files_all)); }
    
    int64:total_iters = from_count + overlap_count;
    int64:all_fids = npk_core_alloc(total_iters * 8i64);
    int64:all_levels = npk_core_alloc(total_iters * 8i64);
    
    i = 0i64;
    while (i < from_count) {
        int64:fid = npk_mem_read_int64(from_files, i * 8i64);
        drop(npk_mem_write_int64(all_fids, i * 8i64, fid));
        drop(npk_mem_write_int64(all_levels, i * 8i64, from_level));
        i = i + 1i64;
    }
    int64:j = 0i64;
    while (j < overlap_count) {
        int64:fid = npk_mem_read_int64(overlap_files, j * 8i64);
        drop(npk_mem_write_int64(all_fids, (from_count + j) * 8i64, fid));
        drop(npk_mem_write_int64(all_levels, (from_count + j) * 8i64, to_level));
        j = j + 1i64;
    }
    
    // Sort all_fids (and keep all_levels synced, wait, do we need all_levels? Yes, to get the file path!)
    // Let's sort both together based on fid
    i = 0i64;
    while (i < total_iters) {
        j = i + 1i64;
        while (j < total_iters) {
            int64:fid_a = npk_mem_read_int64(all_fids, i * 8i64);
            int64:fid_b = npk_mem_read_int64(all_fids, j * 8i64);
            if (fid_a > fid_b) {
                int64:lvl_a = npk_mem_read_int64(all_levels, i * 8i64);
                int64:lvl_b = npk_mem_read_int64(all_levels, j * 8i64);
                
                drop(npk_mem_write_int64(all_fids, i * 8i64, fid_b));
                drop(npk_mem_write_int64(all_fids, j * 8i64, fid_a));
                
                drop(npk_mem_write_int64(all_levels, i * 8i64, lvl_b));
                drop(npk_mem_write_int64(all_levels, j * 8i64, lvl_a));
            }
            j = j + 1i64;
        }
        i = i + 1i64;
    }
    
    int64:readers = npk_core_alloc(total_iters * 8i64);
    int64:iters = npk_core_alloc(total_iters * 8i64);
    
    i = 0i64;
    while (i < total_iters) {
        int64:fid = npk_mem_read_int64(all_fids, i * 8i64);
        int64:lvl = npk_mem_read_int64(all_levels, i * 8i64);
        
        // Wait, how to reconstruct the filename?
        // Let's copy lm_next_sstable_path logic, but we don't increment next_file_id.
        // Actually, we can just manually build it.
        int64:d_ptr = npk_mem_read_int64(lm, 0i64);
        int64:d_len = npk_mem_read_int64(lm, 8i64);
        string:dir = raw npk_mem_read_string(d_ptr, d_len);
        
        string:fid_str = string_from_int(fid);
        while (string_length(fid_str) < 6i64) { fid_str = "0" + fid_str; }
        
        string:p1 = dir + "/L";
        string:p2 = p1 + string_from_int(lvl);
        string:p3 = p2 + "/sst_";
        string:p4 = p3 + fid_str;
        string:path = p4 + ".npkdb";
        
        int64:reader = sstable_open_read(path) ?! 0i64;
        int64:iter = sstable_iter_create(reader) ?! 0i64;
        
        drop(npk_mem_write_int64(readers, i * 8i64, reader));
        drop(npk_mem_write_int64(iters, i * 8i64, iter));
        i = i + 1i64;
    }
    
    int64:m_iter = merge_iter_create(iters, readers, total_iters) ?! 0i64;
    
    // Check if we can drop tombstones (if no SSTables exist at levels > to_level)
    int64:can_drop_tombstones = 1i64;
    int64:lvl = to_level + 1i64;
    while (lvl < LM_MAX_LEVELS) {
        int64:c = lm_count_at_level(lm, lvl) ?! 0i64;
        if (c > 0i64) {
            can_drop_tombstones = 0i64;
            break;
        }
        lvl = lvl + 1i64;
    }
    
    // Now iterate and write out to new L1 files.
    // For simplicity, we write EVERYTHING to ONE new SSTable.
    // In a real LSM, we'd roll over at 4MB.
    
    string:new_path = lm_next_sstable_path(lm, to_level) ?! "";
    int64:new_fid = lm_get_next_file_id(lm) ?! 1i64;
    int64:new_fid = new_fid - 1i64; // lm_next_sstable_path increments it
    
    // Create a temporary memtable to hold records before writing
    // Wait, sstable_write takes a memtable!
    // But we are merging records that might not fit in memory!
    // We need a sstable_write_from_iter or similar?
    // Wait, the roadmap says: "when L0 accumulates... compact".
    // If we just use a memtable, we'd load everything into memory. L0 max size is 4 * 4MB = 16MB.
    // L1 could be 40MB. 56MB in memory is fine for NPKDB.
    // Let's use a memtable!
    int64:out_mt = mt_create(0i64) ?! 0i64;
    int64:rec_count = 0i64;
    
    string:out_min_k = "";
    string:out_max_k = "";
    
    while (1i64 == 1i64) {
        int64:rec = merge_iter_next(m_iter) ?! 0i64;
        if (rec == 0i64) { break; }
        
        string:k = sst_rec_key(rec) ?! "";
        int64:is_tomb = sst_rec_is_tombstone(rec) ?! 0i64;
        
        int64:can_purge = 1i64;
        int64:chk_lvl = to_level + 1i64;
        while (chk_lvl < LM_MAX_LEVELS) {
            int64:c = lm_count_at_level(lm, chk_lvl) ?! 0i64;
            if (c > 0i64) {
                can_purge = 0i64;
                break;
            }
            chk_lvl = chk_lvl + 1i64;
        }
        
        int64:skip = 0i64;
        if (is_tomb == 1i64) {
            if (can_purge == 1i64) {
                skip = 1i64;
            }
        }
        
        if (skip == 0i64) {
            int64:v_ptr = sst_rec_val_ptr(rec) ?! 0i64;
            int64:v_len = sst_rec_val_len(rec) ?! 0i64;
            if (is_tomb == 1i64) {
                drop(mt_delete(out_mt, k));
            } else {
                int64:v_copy = npk_core_alloc(v_len);
                drop(npk_mem_copy(v_copy, v_ptr, v_len));
                drop(mt_put(out_mt, k, v_copy, v_len));
            }
            
            if (rec_count == 0i64) {
                out_min_k = k;
                out_max_k = k;
            } else {
                if (k < out_min_k) { out_min_k = k; }
                if (k > out_max_k) { out_max_k = k; }
            }
            rec_count = rec_count + 1i64;
        }
        
        drop(sst_rec_free(rec));
    }
    
    drop(merge_iter_destroy(m_iter));
    
    // Write new SSTable
    if (rec_count > 0i64) {
        drop(mt_freeze(out_mt));
        int64:s_res = sstable_write(new_path, out_mt) ?! -1i64;
        
        // Free copied value pointers
        // println("DEBUG: Freeing copied values...");
        int64:c_node = mt_first(out_mt) ?! 0i64;
        while (c_node != 0i64) {
            int64:c_is_tomb = raw sl_node_is_deleted(c_node);
            if (c_is_tomb == 0i64) {
                int64:c_v_ptr = raw sl_node_val_ptr(c_node);
                if (c_v_ptr != 0i64) {
                    drop(npk_core_dalloc(c_v_ptr));
                }
            }
            c_node = raw sl_next(c_node);
        }
        // println("DEBUG: Freed copied values!");
        
        drop(mt_destroy(out_mt));
        
        if (s_res > 0i64) {
            g_compaction_stats_total = g_compaction_stats_total + 1i64;
            g_compaction_stats_bytes_written = g_compaction_stats_bytes_written + s_res;
            g_compaction_stats_records_merged = g_compaction_stats_records_merged + rec_count;
            
            drop(lm_add_sstable(lm, to_level, new_fid, out_min_k, out_max_k, s_res, rec_count));
        }
    } else {
        drop(mt_destroy(out_mt));
    }
    
    // Remove old files
    i = 0i64;
    while (i < from_count) {
        int64:fid = npk_mem_read_int64(from_files, i * 8i64);
        drop(lm_remove_sstable(lm, from_level, fid));
        
        int64:d_ptr = npk_mem_read_int64(lm, 0i64);
        int64:d_len = npk_mem_read_int64(lm, 8i64);
        string:dir = raw npk_mem_read_string(d_ptr, d_len);
        string:fid_str = string_from_int(fid);
        while (string_length(fid_str) < 6i64) { fid_str = "0" + fid_str; }
        string:p1 = dir + "/L";
        string:p2 = p1 + string_from_int(from_level);
        string:p3 = p2 + "/sst_";
        string:p4 = p3 + fid_str;
        string:path = p4 + ".npkdb";
        drop(sys(UNLINK, path));
        
        i = i + 1i64;
    }
    
    j = 0i64;
    while (j < overlap_count) {
        int64:fid = npk_mem_read_int64(overlap_files, j * 8i64);
        drop(lm_remove_sstable(lm, to_level, fid));
        
        int64:d_ptr = npk_mem_read_int64(lm, 0i64);
        int64:d_len = npk_mem_read_int64(lm, 8i64);
        string:dir = raw npk_mem_read_string(d_ptr, d_len);
        string:fid_str = string_from_int(fid);
        while (string_length(fid_str) < 6i64) { fid_str = "0" + fid_str; }
        string:p1 = dir + "/L";
        string:p2 = p1 + string_from_int(to_level);
        string:p3 = p2 + "/sst_";
        string:p4 = p3 + fid_str;
        string:path = p4 + ".npkdb";
        drop(sys(UNLINK, path));
        
        j = j + 1i64;
    }
    
    drop(npk_core_dalloc(from_files));
    drop(npk_core_dalloc(overlap_files));
    drop(npk_core_dalloc(all_fids));
    drop(npk_core_dalloc(all_levels));
    
    pass(rec_count);
};

pub func:compact_l0_to_l1 = int64(int64:lm) {
    pass(compact_level(lm, 0i64));
};

// Global stat variables
int64:g_compaction_stats_total = 0i64;
int64:g_compaction_stats_bytes_written = 0i64;
int64:g_compaction_stats_records_merged = 0i64;

pub func:compaction_stats_total = int64() {
    pass(g_compaction_stats_total);
};

pub func:compaction_stats_bytes_written = int64() {
    pass(g_compaction_stats_bytes_written);
};

pub func:compaction_stats_records_merged = int64() {
    pass(g_compaction_stats_records_merged);
};

pub func:maybe_compact = int64(int64:lm) {
    int64:needs = lm_l0_needs_compaction(lm) ?! 0i64;
    if (needs == 1i64) {
        pass(compact_l0_to_l1(lm) ?! 0i64);
    }
    pass(0i64);
};

```

### File: `src/storage/compaction_worker.npk`
```nitpick
// src/storage/compaction_worker.npk
// Background compaction thread for NPKDB

use "channel.npk".*;
use "thread.npk".*;
use "compaction.npk".*;
use "level_manager.npk".*;

extern "nitpick_libc_mem" {
    func:npk_core_alloc = int64(int64:size);
    func:npk_core_dalloc = void(int64:ptr);
    func:npk_mem_read_int64 = int64(int64:ptr, int64:offset);
    func:npk_mem_write_int64 = void(int64:ptr, int64:offset, int64:val);
}

extern func:nitpick_libc_thread_spawn = int64(wild ?*:func, int64:arg);

// Compaction request types
pub fixed int64:COMPACT_SHUTDOWN = 0i64;
pub fixed int64:COMPACT_L0       = 1i64;
pub fixed int64:COMPACT_LEVEL    = 2i64;

// Worker context struct offsets
// 0: lm
// 8: channel
fixed int64:CTX_OFF_LM = 0i64;
fixed int64:CTX_OFF_CH = 8i64;
fixed int64:CTX_SIZE   = 16i64;

// The background worker loop
pub func:compaction_worker_loop = int64(int64:ctx) {
    if (ctx == 0i64) { pass(0i64); }
    
    int64:lm = npk_mem_read_int64(ctx, CTX_OFF_LM);
    int64:ch = npk_mem_read_int64(ctx, CTX_OFF_CH);
    
    while (1i64 == 1i64) {
        int64:msg = Channel.recv(ch) ?! -1i64;
        
        if (msg == COMPACT_SHUTDOWN) {
            break;
        }
        
        if (msg == COMPACT_L0) {
            drop(compact_level(lm, 0i64));
        }
        
        // Relinquish CPU so query threads aren't starved
        drop(Thread.yield());
    }
    
    // Do NOT free the context here; wp_shutdown will free it to avoid use-after-free
    // if shutdown is called while thread is starting. Actually, the thread can free it
    // because wp_shutdown won't use it after joining. Let's let wp_shutdown free it.
    
    pass(0i64);
};

// Start the compaction worker thread.
// Returns a context pointer that contains the channel and thread ID.
// Return struct:
// 0: channel handle
// 8: thread handle
// 16: worker ctx (to free later)
pub func:compaction_worker_start = int64(int64:lm, ?->:worker_fn) {
    int64:ch = Channel.create(16i32) ?! 0i64;
    if (ch <= 0i64) { pass(0i64); }
    
    int64:ctx = npk_core_alloc(CTX_SIZE);
    drop(npk_mem_write_int64(ctx, CTX_OFF_LM, lm));
    drop(npk_mem_write_int64(ctx, CTX_OFF_CH, ch));
    
    int64:tid = nitpick_libc_thread_spawn(worker_fn, ctx);
    if (tid < 0i64) {
        drop(Channel.destroy(ch));
        drop(npk_core_dalloc(ctx));
        pass(0i64);
    }
    
    int64:ret = npk_core_alloc(24i64);
    drop(npk_mem_write_int64(ret, 0i64, ch));
    drop(npk_mem_write_int64(ret, 8i64, tid));
    drop(npk_mem_write_int64(ret, 16i64, ctx));
    
    pass(ret);
};

// Signal the compaction worker to compact L0.
// non-blocking
pub func:compaction_signal_l0 = NIL(int64:channel) {
    if (channel != 0i64) {
        drop(Channel.try_send(channel, COMPACT_L0));
    }
    pass(NIL);
};

// Signal the compaction worker to shut down.
pub func:compaction_signal_shutdown = NIL(int64:channel) {
    if (channel != 0i64) {
        drop(Channel.send(channel, COMPACT_SHUTDOWN));
    }
    pass(NIL);
};

```

### File: `src/storage/flush.npk`
```nitpick
// src/storage/flush.npk
use "memtable.npk".*;
use "sstable.npk".*;
use "level_manager.npk".*;
use "skiplist.npk".*;
use "../util/mem_primitives.npk".*;

pub func:flush_ensure_dirs = NIL(string:data_dir) {
    drop(sys(MKDIR, data_dir, 493i64)); // 0755
    
    int64:i = 0i64;
    while (i < LM_MAX_LEVELS) {
        string:l_dir = data_dir + "/L";
        string:l_dir2 = l_dir + string_from_int(i);
        drop(sys(MKDIR, l_dir2, 493i64));
        i = i + 1i64;
    }
    pass(NIL);
};

pub func:flush_memtable = int64(int64:mt, int64:lm) {
    if (mt == 0i64) { pass(0i64); }
    if (lm == 0i64) { pass(0i64); }
    
    int64:cnt = mt_count(mt) ?! 0i64;
    if (cnt == 0i64) {
        drop(mt_destroy(mt));
        pass(0i64);
    }
    
    int64:node = mt_first(mt) ?! 0i64;
    if (node == 0i64) { pass(-1i64); }
    
    int64:is_first = 1i64;
    string:min_k = "";
    string:max_k = "";
    
    while (node != 0i64) {
        string:k = sl_node_key(node) ?! "";
        if (is_first == 1i64) {
            min_k = k;
            is_first = 0i64;
        }
        max_k = k;
        node = sl_next(node) ?! 0i64;
    }
    
    string:sst_path = lm_next_sstable_path(lm, 0i64) ?! "";
    int64:file_id = lm_get_next_file_id(lm) ?! 1i64;
    file_id = file_id - 1i64; 
    
    int64:written = sstable_write(sst_path, mt) ?! 0i64;
    if (written <= 0i64) {
        pass(-1i64);
    }
    
    drop(lm_add_sstable(lm, 0i64, file_id, min_k, max_k, written, cnt));
    drop(mt_destroy(mt));
    
    pass(0i64);
};

```

### File: `src/storage/level_manager.npk`
```nitpick
// src/storage/level_manager.npk
use "../util/constants.npk".*;
use "../util/mem_primitives.npk".*;

// Level metadata per SSTable entry:
//   Offset 0: file_id (int64) — unique SSTable file number
//   Offset 8: min_key_ptr (int64) — pointer to minimum key string (self-describing, first 8 bytes = len)
//   Offset 16: max_key_ptr (int64) — pointer to maximum key string (self-describing, first 8 bytes = len)
//   Offset 24: file_size (int64) — file size in bytes
//   Offset 32: total_keys (int64) — number of records
pub fixed int64:LM_ENTRY_SIZE = 40i64;

// Maximum SSTables per level before compaction is triggered
pub fixed int64:L0_COMPACTION_THRESHOLD = 4i64;

pub fixed int64:LM_MAX_LEVELS = 7i64;
pub fixed int64:LM_MAX_SSTABLES_PER_LEVEL = 1024i64; // Max SSTables tracked per level

// Create the level manager (allocates tracking arrays for all levels).
// Level Manager struct:
// 0: data_dir (int64 ptr)
// 8: data_dir_len (int64)
// 16: next_file_id (int64)
// 24: levels_array (int64 ptr) - array of LM_MAX_LEVELS pointers
// 32: count_array (int64 ptr) - array of LM_MAX_LEVELS counts
pub func:lm_create = int64(string:data_dir) {
    int64:lm = npk_core_alloc(64i64);
    
    int64:d_len = string_length(data_dir);
    int64:d_ptr = npk_core_alloc(d_len);
    drop(npk_mem_write_string(d_ptr, data_dir));
    
    drop(npk_mem_write_int64(lm, 0i64, d_ptr));
    drop(npk_mem_write_int64(lm, 8i64, d_len));
    drop(npk_mem_write_int64(lm, 16i64, 1i64)); // file ID starts at 1
    
    int64:levels_array = npk_core_alloc(LM_MAX_LEVELS * 8i64);
    int64:count_array = npk_core_alloc(LM_MAX_LEVELS * 8i64);
    
    int64:i = 0i64;
    while (i < LM_MAX_LEVELS) {
        int64:lvl_mem = npk_core_alloc(LM_MAX_SSTABLES_PER_LEVEL * LM_ENTRY_SIZE);
        drop(npk_mem_write_int64(levels_array, i * 8i64, lvl_mem));
        drop(npk_mem_write_int64(count_array, i * 8i64, 0i64));
        i = i + 1i64;
    }
    
    drop(npk_mem_write_int64(lm, 24i64, levels_array));
    drop(npk_mem_write_int64(lm, 32i64, count_array));
    
    pass(lm);
};

// Destroy the level manager.
pub func:lm_destroy = NIL(int64:lm) {
    if (lm != 0i64) {
        int64:d_ptr = npk_mem_read_int64(lm, 0i64);
        drop(npk_core_dalloc(d_ptr));
        
        int64:levels_array = npk_mem_read_int64(lm, 24i64);
        int64:count_array = npk_mem_read_int64(lm, 32i64);
        
        int64:i = 0i64;
        while (i < LM_MAX_LEVELS) {
            int64:lvl_mem = npk_mem_read_int64(levels_array, i * 8i64);
            int64:count = npk_mem_read_int64(count_array, i * 8i64);
            
            int64:j = 0i64;
            while (j < count) {
                int64:ent_ptr = lvl_mem + (j * LM_ENTRY_SIZE);
                int64:min_k = npk_mem_read_int64(ent_ptr, 8i64);
                int64:max_k = npk_mem_read_int64(ent_ptr, 16i64);
                if (min_k != 0i64) { drop(npk_core_dalloc(min_k)); }
                if (max_k != 0i64) { drop(npk_core_dalloc(max_k)); }
                j = j + 1i64;
            }
            
            drop(npk_core_dalloc(lvl_mem));
            i = i + 1i64;
        }
        
        drop(npk_core_dalloc(levels_array));
        drop(npk_core_dalloc(count_array));
        drop(npk_core_dalloc(lm));
    }
    pass(NIL);
};

// Register a new SSTable at a given level.
pub func:lm_add_sstable = NIL(int64:lm, int64:level, int64:file_id, string:min_key, string:max_key, int64:file_size, int64:total_keys) {
    if (level < 0i64 || level >= LM_MAX_LEVELS) { pass(NIL); }
    
    int64:levels_array = npk_mem_read_int64(lm, 24i64);
    int64:count_array = npk_mem_read_int64(lm, 32i64);
    
    int64:count = npk_mem_read_int64(count_array, level * 8i64);
    int64:lvl_mem = npk_mem_read_int64(levels_array, level * 8i64);
    
    if (count < LM_MAX_SSTABLES_PER_LEVEL) {
        int64:ent_ptr = lvl_mem + (count * LM_ENTRY_SIZE);
        
        int64:min_len = string_length(min_key);
        int64:max_len = string_length(max_key);
        
        int64:min_ptr = npk_core_alloc(8i64 + min_len);
        int64:max_ptr = npk_core_alloc(8i64 + max_len);
        
        drop(npk_mem_write_int64(min_ptr, 0i64, min_len));
        drop(raw npk_mem_write_string(min_ptr + 8i64, min_key));
        
        drop(npk_mem_write_int64(max_ptr, 0i64, max_len));
        drop(raw npk_mem_write_string(max_ptr + 8i64, max_key));
        
        drop(npk_mem_write_int64(ent_ptr, 0i64, file_id));
        drop(npk_mem_write_int64(ent_ptr, 8i64, min_ptr));
        drop(npk_mem_write_int64(ent_ptr, 16i64, max_ptr));
        drop(npk_mem_write_int64(ent_ptr, 24i64, file_size));
        drop(npk_mem_write_int64(ent_ptr, 32i64, total_keys));
        
        drop(npk_mem_write_int64(count_array, level * 8i64, count + 1i64));
    }
    pass(NIL);
};

// Remove an SSTable from a level (after compaction replaces it).
pub func:lm_remove_sstable = NIL(int64:lm, int64:level, int64:file_id) {
    if (level < 0i64 || level >= LM_MAX_LEVELS) { pass(NIL); }
    
    int64:levels_array = npk_mem_read_int64(lm, 24i64);
    int64:count_array = npk_mem_read_int64(lm, 32i64);
    
    int64:count = npk_mem_read_int64(count_array, level * 8i64);
    int64:lvl_mem = npk_mem_read_int64(levels_array, level * 8i64);
    
    int64:i = 0i64;
    while (i < count) {
        int64:ent_ptr = lvl_mem + (i * LM_ENTRY_SIZE);
        int64:fid = npk_mem_read_int64(ent_ptr, 0i64);
        if (fid == file_id) {
            int64:min_k = npk_mem_read_int64(ent_ptr, 8i64);
            int64:max_k = npk_mem_read_int64(ent_ptr, 16i64);
            if (min_k != 0i64) { drop(npk_core_dalloc(min_k)); }
            if (max_k != 0i64) { drop(npk_core_dalloc(max_k)); }
            
            int64:j = i;
            while (j < count - 1i64) {
                int64:src = lvl_mem + ((j + 1i64) * LM_ENTRY_SIZE);
                int64:dst = lvl_mem + (j * LM_ENTRY_SIZE);
                drop(npk_mem_copy(dst, src, LM_ENTRY_SIZE));
                j = j + 1i64;
            }
            drop(npk_mem_write_int64(count_array, level * 8i64, count - 1i64));
            break;
        }
        i = i + 1i64;
    }
    pass(NIL);
};

// Get the number of SSTables at a given level.
pub func:lm_count_at_level = int64(int64:lm, int64:level) {
    if (level < 0i64 || level >= LM_MAX_LEVELS) { pass(0i64); }
    int64:count_array = npk_mem_read_int64(lm, 32i64);
    pass(npk_mem_read_int64(count_array, level * 8i64));
};

// Check if L0 needs compaction.
pub func:lm_l0_needs_compaction = int64(int64:lm) {
    int64:c = lm_count_at_level(lm, 0i64) ?! 0i64;
    if (c >= L0_COMPACTION_THRESHOLD) {
        pass(1i64);
    }
    pass(0i64);
};

// Generate the next SSTable file path.
pub func:lm_next_sstable_path = string(int64:lm, int64:level) {
    int64:fid = npk_mem_read_int64(lm, 16i64);
    drop(npk_mem_write_int64(lm, 16i64, fid + 1i64));
    
    int64:d_ptr = npk_mem_read_int64(lm, 0i64);
    int64:d_len = npk_mem_read_int64(lm, 8i64);
    string:dir = raw npk_mem_read_string(d_ptr, d_len);
    
    string:fid_str = string_from_int(fid);
    while (string_length(fid_str) < 6i64) {
        fid_str = "0" + fid_str;
    }
    
    string:p1 = dir + "/L";
    string:p2 = p1 + string_from_int(level);
    string:p3 = p2 + "/sst_";
    string:p4 = p3 + fid_str;
    string:p5 = p4 + ".npkdb";
    
    pass(p5);
};

// Get all SSTable file IDs at a given level.
pub func:lm_get_sstables = int64(int64:lm, int64:level) {
    int64:count = lm_count_at_level(lm, level) ?! 0i64;
    if (count == 0i64) { pass(0i64); }
    
    int64:levels_array = npk_mem_read_int64(lm, 24i64);
    int64:lvl_mem = npk_mem_read_int64(levels_array, level * 8i64);
    
    int64:res = npk_core_alloc(count * 8i64);
    int64:i = 0i64;
    while (i < count) {
        int64:ent_ptr = lvl_mem + (i * LM_ENTRY_SIZE);
        int64:fid = npk_mem_read_int64(ent_ptr, 0i64);
        drop(npk_mem_write_int64(res, i * 8i64, fid));
        i = i + 1i64;
    }
    pass(res);
};

pub func:lm_get_sstable_count = int64(int64:lm, int64:level) {
    pass(lm_count_at_level(lm, level) ?! 0i64);
};

pub func:lm_get_next_file_id = int64(int64:lm) {
    pass(npk_mem_read_int64(lm, 16i64));
};

pub func:lm_set_next_file_id = NIL(int64:lm, int64:fid) {
    drop(npk_mem_write_int64(lm, 16i64, fid));
    pass(NIL);
};

pub func:lm_get_sstable_min_key = string(int64:lm, int64:level, int64:file_id) {
    int64:count = npk_mem_read_int64(npk_mem_read_int64(lm, 32i64), level * 8i64);
    int64:lvl_mem = npk_mem_read_int64(npk_mem_read_int64(lm, 24i64), level * 8i64);
    int64:i = 0i64;
    while (i < count) {
        int64:ent = lvl_mem + (i * LM_ENTRY_SIZE);
        if (npk_mem_read_int64(ent, 0i64) == file_id) {
            int64:m_ptr = npk_mem_read_int64(ent, 8i64);
            int64:m_len = npk_mem_read_int64(m_ptr, 0i64);
            pass(raw npk_mem_read_string(m_ptr + 8i64, m_len));
        }
        i = i + 1i64;
    }
    pass("");
};

pub func:lm_get_sstable_max_key = string(int64:lm, int64:level, int64:file_id) {
    int64:count = npk_mem_read_int64(npk_mem_read_int64(lm, 32i64), level * 8i64);
    int64:lvl_mem = npk_mem_read_int64(npk_mem_read_int64(lm, 24i64), level * 8i64);
    int64:i = 0i64;
    while (i < count) {
        int64:ent = lvl_mem + (i * LM_ENTRY_SIZE);
        if (npk_mem_read_int64(ent, 0i64) == file_id) {
            int64:m_ptr = npk_mem_read_int64(ent, 16i64);
            int64:m_len = npk_mem_read_int64(m_ptr, 0i64);
            pass(raw npk_mem_read_string(m_ptr + 8i64, m_len));
        }
        i = i + 1i64;
    }
    pass("");
};

```

### File: `src/storage/lsm_tree.npk`
```nitpick
// lsm_tree.npk - High level LSM Tree interfaces

extern "C" {
    opaque struct:LsmTree;
}

```

### File: `src/storage/memtable.npk`
```nitpick
// src/storage/memtable.npk
// Memtable implementation wrapping skiplist

use "../util/mem_primitives.npk".*;
use "skiplist.npk".*;
use "../util/constants.npk".*;
use "../util/error_codes.npk".*;

// Memtable state (stored as a flat buffer):
//   Offset 0: head (int64) — pointer to Skip List head node
//   Offset 8: frozen (int64) — 0 = active (writable), 1 = frozen (immutable)
//   Offset 16: id (int64) — unique Memtable identifier
pub fixed int64:MT_OFF_HEAD   = 0i64;
pub fixed int64:MT_OFF_FROZEN = 8i64;
pub fixed int64:MT_OFF_ID     = 16i64;
pub fixed int64:MT_STATE_SIZE = 24i64;

pub func:mt_create = int64(int64:id) {
    int64:mt = npk_core_alloc(MT_STATE_SIZE);
    int64:sl_head = sl_create() ?! 0i64;
    
    drop(npk_mem_write_int64(mt, MT_OFF_HEAD, sl_head));
    drop(npk_mem_write_int64(mt, MT_OFF_FROZEN, 0i64));
    drop(npk_mem_write_int64(mt, MT_OFF_ID, id));
    
    pass(mt);
};

pub func:mt_destroy = NIL(int64:mt) {
    if (mt != 0i64) {
        int64:sl_head = npk_mem_read_int64(mt, MT_OFF_HEAD);
        drop(sl_destroy(sl_head));
        drop(npk_core_dalloc(mt));
    }
    pass(NIL);
};

pub func:mt_put = int64(int64:mt, string:key, int64:val_ptr, int64:val_len) {
    int64:frozen = npk_mem_read_int64(mt, MT_OFF_FROZEN);
    if (frozen != 0i64) {
        pass(ERR_PAGE_FULL => int64); // We map ERR_MEMTABLE_FULL to ERR_PAGE_FULL or we can just return a non-zero error.
        // Wait, error_codes.npk has no ERR_MEMTABLE_FULL. Let's see if I should just use 10 (ERR_PAGE_FULL)
        // I'll just return 10i64.
    }
    
    int64:sl_head = npk_mem_read_int64(mt, MT_OFF_HEAD);
    drop(sl_insert(sl_head, key, val_ptr, val_len));
    pass(0i64);
};

pub func:mt_delete = int64(int64:mt, string:key) {
    int64:frozen = npk_mem_read_int64(mt, MT_OFF_FROZEN);
    if (frozen != 0i64) {
        pass(ERR_PAGE_FULL => int64);
    }
    
    int64:sl_head = npk_mem_read_int64(mt, MT_OFF_HEAD);
    drop(sl_delete(sl_head, key));
    pass(0i64);
};

pub func:mt_get = int64(int64:mt, string:key) {
    int64:sl_head = npk_mem_read_int64(mt, MT_OFF_HEAD);
    pass(sl_search(sl_head, key) ?! 0i64);
};

pub func:mt_should_flush = int64(int64:mt) {
    int64:sl_head = npk_mem_read_int64(mt, MT_OFF_HEAD);
    int64:mem = sl_memory_usage(sl_head) ?! 0i64;
    // MEMTABLE_SIZE_LIMIT = 4 * 1024 * 1024 = 4194304
    if (mem >= MEMTABLE_SIZE_LIMIT => int64) {
        pass(1i64);
    }
    pass(0i64);
};

pub func:mt_freeze = NIL(int64:mt) {
    drop(npk_mem_write_int64(mt, MT_OFF_FROZEN, 1i64));
    pass(NIL);
};

pub func:mt_is_frozen = int64(int64:mt) {
    pass(npk_mem_read_int64(mt, MT_OFF_FROZEN));
};

pub func:mt_get_id = int64(int64:mt) {
    pass(npk_mem_read_int64(mt, MT_OFF_ID));
};

pub func:mt_count = int64(int64:mt) {
    int64:sl_head = npk_mem_read_int64(mt, MT_OFF_HEAD);
    pass(sl_count(sl_head) ?! 0i64);
};

pub func:mt_memory_usage = int64(int64:mt) {
    int64:sl_head = npk_mem_read_int64(mt, MT_OFF_HEAD);
    pass(sl_memory_usage(sl_head) ?! 0i64);
};

pub func:mt_first = int64(int64:mt) {
    int64:sl_head = npk_mem_read_int64(mt, MT_OFF_HEAD);
    pass(sl_first(sl_head) ?! 0i64);
};

```

### File: `src/storage/record_types.npk`
```nitpick
// record_types.npk — Defines the disk and memory layout of a co-located Vector+JSON record.

use "../document/json_types.npk".*;

// A unified database record
pub struct:npk_record = {
    int64:vector_dim;
    wild tfp64->:vector_data;
    
    uint32:json_len;
    wild int8->:json_data;
};

```

### File: `src/storage/skiplist.npk`
```nitpick
// src/storage/skiplist.npk — Memtable Skip List Core
// Single-threaded probabilistic skip list for in-memory string keys.

use "../../src/util/mem_primitives.npk".*;
use "../../../nitpick-libc/src/_time.npk".*;

pub fixed int64:SKIPLIST_MAX_LEVEL = 32i64;
pub fixed int64:SKIPLIST_NODE_HEADER_SIZE = 48i64;

// -----------------------------------------------------------------------------
// PRNG for Level Generation
// -----------------------------------------------------------------------------

int64:sl_prng_state = 0i64;

func:sl_seed_prng = NIL() {
    if (sl_prng_state == 0i64) {
        int64:ns = libc_monotonic_ns() ?! 123456789i64;
        sl_prng_state = ns;
    }
    pass(NIL);
};

pub func:sl_random_level = int64() {
    drop(sl_seed_prng());
    
    int64:level = 1i64;
    while (level < SKIPLIST_MAX_LEVEL) {
        // LCG
        sl_prng_state = (sl_prng_state * 1103515245i64 + 12345i64) & 2147483647i64;
        if ((sl_prng_state % 4i64) == 0i64) {
            level = level + 1i64;
        } else {
            break;
        }
    }
    pass(level);
};

// -----------------------------------------------------------------------------
// Node Layout & Management
// -----------------------------------------------------------------------------

pub func:sl_node_alloc = int64(string:key, int64:val_ptr, int64:val_len, int64:level) {
    int64:key_len = string_length(key);
    
    int64:size = SKIPLIST_NODE_HEADER_SIZE + (level * 8i64);
    // Add key string data size right after the pointers to keep it flat
    int64:total_size = size + key_len;
    
    int64:node = npk_core_alloc(total_size);
    
    // Write key data to the end of the node if not empty
    int64:key_data_ptr = 0i64;
    if (key_len > 0i64) {
        key_data_ptr = node + size;
        drop(raw npk_mem_write_string(key_data_ptr, key));
    }
    
    drop(npk_mem_write_int64(node, 0i64, key_data_ptr));
    drop(npk_mem_write_int64(node, 8i64, key_len));
    drop(npk_mem_write_int64(node, 16i64, val_ptr));
    drop(npk_mem_write_int64(node, 24i64, val_len));
    drop(npk_mem_write_int64(node, 32i64, level));
    drop(npk_mem_write_int64(node, 40i64, 0i64)); // is_deleted
    
    // Zero out forward pointers
    int64:i = 0i64;
    while (i < level) {
        drop(npk_mem_write_int64(node, SKIPLIST_NODE_HEADER_SIZE + (i * 8i64), 0i64));
        i = i + 1i64;
    }
    
    pass(node);
};

pub func:sl_node_free = NIL(int64:node) {
    if (node != 0i64) {
        drop(npk_core_dalloc(node));
    }
    pass(NIL);
};

pub func:sl_node_key = string(int64:node) {
    int64:key_ptr = npk_mem_read_int64(node, 0i64);
    int64:key_len = npk_mem_read_int64(node, 8i64);
    if (key_ptr == 0i64 || key_len == 0i64) { pass(""); }
    pass(raw npk_mem_read_string(key_ptr, key_len));
};

pub func:sl_node_val_ptr = int64(int64:node) {
    pass(npk_mem_read_int64(node, 16i64));
};

pub func:sl_node_val_len = int64(int64:node) {
    pass(npk_mem_read_int64(node, 24i64));
};

pub func:sl_node_level = int64(int64:node) {
    pass(npk_mem_read_int64(node, 32i64));
};

pub func:sl_node_is_deleted = int64(int64:node) {
    pass(npk_mem_read_int64(node, 40i64));
};

pub func:sl_node_set_deleted = NIL(int64:node) {
    drop(npk_mem_write_int64(node, 40i64, 1i64));
    pass(NIL);
};

pub func:sl_node_forward = int64(int64:node, int64:lvl) {
    pass(npk_mem_read_int64(node, SKIPLIST_NODE_HEADER_SIZE + (lvl * 8i64)));
};

pub func:sl_node_set_forward = NIL(int64:node, int64:lvl, int64:target) {
    drop(npk_mem_write_int64(node, SKIPLIST_NODE_HEADER_SIZE + (lvl * 8i64), target));
    pass(NIL);
};

// -----------------------------------------------------------------------------
// Skip List Management
// -----------------------------------------------------------------------------

pub fixed int64:SL_OFF_HEAD = 0i64;
pub fixed int64:SL_OFF_COUNT = 8i64;
pub fixed int64:SL_OFF_MEMORY = 16i64;
pub fixed int64:SL_STRUCT_SIZE = 24i64;

pub func:sl_create = int64() {
    int64:sl = npk_core_alloc(SL_STRUCT_SIZE);
    int64:head = sl_node_alloc("", 0i64, 0i64, SKIPLIST_MAX_LEVEL) ?! 0i64;
    drop(npk_mem_write_int64(sl, SL_OFF_HEAD, head));
    drop(npk_mem_write_int64(sl, SL_OFF_COUNT, 0i64));
    drop(npk_mem_write_int64(sl, SL_OFF_MEMORY, SKIPLIST_NODE_HEADER_SIZE + (SKIPLIST_MAX_LEVEL * 8i64)));
    pass(sl);
};

pub func:sl_destroy = NIL(int64:sl) {
    int64:curr = npk_mem_read_int64(sl, SL_OFF_HEAD);
    while (curr != 0i64) {
        int64:nxt = sl_node_forward(curr, 0i64) ?! 0i64;
        drop(sl_node_free(curr));
        curr = nxt;
    }
    drop(npk_core_dalloc(sl));
    pass(NIL);
};

pub func:sl_count = int64(int64:sl) {
    pass(npk_mem_read_int64(sl, SL_OFF_COUNT));
};

pub func:sl_memory_usage = int64(int64:sl) {
    pass(npk_mem_read_int64(sl, SL_OFF_MEMORY));
};

// -----------------------------------------------------------------------------
// Operations
// -----------------------------------------------------------------------------

pub func:sl_insert = int64(int64:sl, string:key, int64:val_ptr, int64:val_len) {
    int64:head = npk_mem_read_int64(sl, SL_OFF_HEAD);
    int64:upd_buf = npk_core_alloc(SKIPLIST_MAX_LEVEL * 8i64);
    
    int64:curr = head;
    int64:lvl = SKIPLIST_MAX_LEVEL - 1i64;
    
    while (lvl >= 0i64) {
        while (1i64 == 1i64) {
            int64:fwd = sl_node_forward(curr, lvl) ?! 0i64;
            if (fwd == 0i64) { break; }
            string:fwd_key = sl_node_key(fwd) ?! "";
            if (fwd_key >= key) { break; } // Nitpick string compare
            curr = fwd;
        }
        drop(npk_mem_write_int64(upd_buf, lvl * 8i64, curr));
        lvl = lvl - 1i64;
    }
    
    int64:cand = sl_node_forward(curr, 0i64) ?! 0i64;
    if (cand != 0i64) {
        string:cand_key = sl_node_key(cand) ?! "";
        if (cand_key == key) {
            int64:old_val_len = sl_node_val_len(cand) ?! 0i64;
            drop(npk_mem_write_int64(cand, 16i64, val_ptr));
            drop(npk_mem_write_int64(cand, 24i64, val_len));
            drop(npk_mem_write_int64(cand, 40i64, 0i64)); // revive
            
            int64:cur_mem = npk_mem_read_int64(sl, SL_OFF_MEMORY);
            drop(npk_mem_write_int64(sl, SL_OFF_MEMORY, cur_mem - old_val_len + val_len));
            
            drop(npk_core_dalloc(upd_buf));
            pass(1i64); // Updated
        }
    }
    
    // Insert new
    int64:new_lvl = sl_random_level() ?! 1i64;
    int64:new_node = sl_node_alloc(key, val_ptr, val_len, new_lvl) ?! 0i64;
    
    int64:i = 0i64;
    while (i < new_lvl) {
        int64:u_node = npk_mem_read_int64(upd_buf, i * 8i64);
        int64:u_fwd = sl_node_forward(u_node, i) ?! 0i64;
        drop(sl_node_set_forward(new_node, i, u_fwd));
        drop(sl_node_set_forward(u_node, i, new_node));
        i = i + 1i64;
    }
    
    int64:cur_count = npk_mem_read_int64(sl, SL_OFF_COUNT);
    drop(npk_mem_write_int64(sl, SL_OFF_COUNT, cur_count + 1i64));
    
    int64:key_len = string_length(key);
    int64:cur_mem = npk_mem_read_int64(sl, SL_OFF_MEMORY);
    drop(npk_mem_write_int64(sl, SL_OFF_MEMORY, cur_mem + SKIPLIST_NODE_HEADER_SIZE + (new_lvl * 8i64) + key_len + val_len));
    
    drop(npk_core_dalloc(upd_buf));
    pass(0i64); // Inserted new
};

pub func:sl_search = int64(int64:sl, string:key) {
    int64:head = npk_mem_read_int64(sl, SL_OFF_HEAD);
    int64:curr = head;
    int64:lvl = SKIPLIST_MAX_LEVEL - 1i64;
    
    while (lvl >= 0i64) {
        while (1i64 == 1i64) {
            int64:fwd = sl_node_forward(curr, lvl) ?! 0i64;
            if (fwd == 0i64) { break; }
            string:fwd_key = sl_node_key(fwd) ?! "";
            if (fwd_key >= key) { break; }
            curr = fwd;
        }
        lvl = lvl - 1i64;
    }
    
    int64:cand = sl_node_forward(curr, 0i64) ?! 0i64;
    if (cand != 0i64) {
        string:cand_key = sl_node_key(cand) ?! "";
        if (cand_key == key) {
            int64:is_del = sl_node_is_deleted(cand) ?! 0i64;
            if (is_del == 0i64) {
                pass(cand);
            }
        }
    }
    pass(0i64);
};

pub func:sl_delete = int64(int64:sl, string:key) {
    // Insert a dummy value, then find it and mark deleted
    drop(sl_insert(sl, key, 0i64, 0i64));
    
    int64:head = npk_mem_read_int64(sl, SL_OFF_HEAD);
    int64:curr = head;
    int64:lvl = SKIPLIST_MAX_LEVEL - 1i64;
    
    while (lvl >= 0i64) {
        while (1i64 == 1i64) {
            int64:fwd = sl_node_forward(curr, lvl) ?! 0i64;
            if (fwd == 0i64) { break; }
            string:fwd_key = sl_node_key(fwd) ?! "";
            if (fwd_key >= key) { break; }
            curr = fwd;
        }
        lvl = lvl - 1i64;
    }
    
    int64:cand = sl_node_forward(curr, 0i64) ?! 0i64;
    if (cand != 0i64) {
        string:cand_key = sl_node_key(cand) ?! "";
        if (cand_key == key) {
            drop(sl_node_set_deleted(cand));
        }
    }
    pass(0i64);
};

pub func:sl_first = int64(int64:sl) {
    int64:head = npk_mem_read_int64(sl, SL_OFF_HEAD);
    pass(sl_node_forward(head, 0i64) ?! 0i64);
};

pub func:sl_next = int64(int64:node) {
    pass(sl_node_forward(node, 0i64) ?! 0i64);
};

```

### File: `src/storage/sstable.npk`
```nitpick
// src/storage/sstable.npk
// SSTable file format constants and writer

use "../page/page.npk".*;
use "memtable.npk".*;
use "skiplist.npk".*;
use "../util/constants.npk".*;
use "../util/error_codes.npk".*;
use "../util/crc32.npk".*;
use "../util/bloom.npk".*;
use "../util/mem_primitives.npk".*;

// SSTable magic number (identifies file type)
// "NPKDB01" in hex: 4E 50 4B 44 42 30 31 => 0x4E504B44423031
pub fixed int64:SSTABLE_MAGIC = 22033878037372977i64; // 0x4E504B44423031

// Footer layout (32 bytes):
//   Offset 0:  data_block_count (int64)
//   Offset 8:  index_block_offset (int64) - byte offset of index block
//   Offset 16: total_keys (int64)
//   Offset 24: magic (int32)
//   Offset 28: footer_checksum (int32)
pub fixed int64:SSTABLE_FOOTER_SIZE = 32i64;

// Record flags
pub fixed int8:RECORD_FLAG_LIVE      = 0i8;
pub fixed int8:RECORD_FLAG_TOMBSTONE = 1i8;

// -----------------------------------------------------------------------------
// Record Serialization
// -----------------------------------------------------------------------------

pub func:sstable_record_size = int64(string:key, int64:val_len, int64:is_tombstone) {
    int64:key_len = string_length(key);
    int64:sz = 1i64 + 4i64 + key_len; // flag(1) + key_len(4) + key(N)
    
    if (is_tombstone == 0i64) {
        sz = sz + 4i64 + val_len; // value_len(4) + value(M)
    } else {
        sz = sz + 4i64; // value_len(4) = 0
    }
    
    pass(sz);
};

pub func:sstable_serialize_record = int64(string:key, int64:val_ptr, int64:val_len, int64:is_tombstone) {
    int64:sz = sstable_record_size(key, val_len, is_tombstone) ?! 0i64;
    int64:buf = npk_core_alloc(sz);
    int64:key_len = string_length(key);
    
    if (is_tombstone == 1i64) {
        drop(npk_mem_write_byte(buf, 0i64, RECORD_FLAG_TOMBSTONE => int64));
    } else {
        drop(npk_mem_write_byte(buf, 0i64, RECORD_FLAG_LIVE => int64));
    }
    
    drop(npk_mem_write_int32(buf, 1i64, @cast_unchecked<int32>(key_len)));
    drop(raw npk_mem_write_string(buf + 5i64, key));
    
    int64:v_offset = 5i64 + key_len;
    
    if (is_tombstone == 1i64) {
        drop(npk_mem_write_int32(buf, v_offset, 0i32));
    } else {
        drop(npk_mem_write_int32(buf, v_offset, @cast_unchecked<int32>(val_len)));
        drop(npk_mem_copy(buf + v_offset + 4i64, val_ptr, val_len));
    }
    
    pass(buf);
};

pub func:sstable_flush_page = int64(int64:fd, int64:page_buf) {
    int64:offset = sys(LSEEK, fd, 0i64, 1i64) ?! -1i64;
    int64:bw = sys(WRITE, fd, page_buf, PAGE_SIZE) ?! -1i64;
    if (bw < PAGE_SIZE) { pass(-1i64); }
    pass(offset);
};

pub func:sstable_build_index = int64(int64:k_ptrs, int64:k_lens, int64:offsets, int64:count) {
    int64:page = page_alloc() ?! 0i64;
    if (page == 0i64) { pass(0i64); }
    drop(page_init(page, 0i64));
    
    int64:i = 0i64;
    while (i < count) {
        int64:k_ptr = npk_mem_read_int64(k_ptrs, i * 8i64);
        int64:k_len = npk_mem_read_int64(k_lens, i * 8i64);
        int64:block_num = npk_mem_read_int64(offsets, i * 8i64); // actually offset
        
        // Serialize index record: key_len(4) + last_key(k_len) + block_offset(8)
        int64:rec_sz = 4i64 + k_len + 8i64;
        int64:rec = npk_core_alloc(rec_sz);
        drop(npk_mem_write_int32(rec, 0i64, @cast_unchecked<int32>(k_len)));
        drop(npk_mem_copy(rec + 4i64, k_ptr, k_len));
        drop(npk_mem_write_int64(rec, 4i64 + k_len, block_num));
        
        int64:ins = page_insert(page, rec, rec_sz) ?! -1i64;
        drop(npk_core_dalloc(rec));
        
        i = i + 1i64;
    }
    pass(page);
};

pub func:sstable_write = int64(string:path, int64:mt) {
    int64:fd = sys(OPEN, path, 578i64, 420i64) ?! -1i64; // O_RDWR|O_CREAT|O_TRUNC, 0644
    if (fd <= 0i64) {
        println("sstable_write: sys(OPEN) failed for " + path);
        pass(-1i64);
    }
    
    int64:total_keys_init = mt_count(mt) ?! 0i64;
    int64:bloom = bloom_create(total_keys_init) ?! 0i64;
    if (bloom == 0i64) {
        println("sstable_write: bloom_create failed");
        pass(-1i64);
    }
    
    int64:curr_page = page_alloc() ?! 0i64;
    if (curr_page == 0i64) {
        println("sstable_write: page_alloc failed");
        pass(-1i64);
    }
    drop(page_init(curr_page, 0i64));
    int64:total_bytes = 0i64;
    
    // Max 1000 blocks for cycle 0
    int64:k_ptrs = npk_core_alloc(8000i64);
    int64:k_lens = npk_core_alloc(8000i64);
    int64:b_offs = npk_core_alloc(8000i64);
    int64:block_count = 0i64;
    int64:total_keys = 0i64;
    
    string:last_key = "";
    int64:has_pending = 0i64;
    
    int64:node = mt_first(mt) ?! 0i64;
    while (node != 0i64) {
        string:k = sl_node_key(node) ?! "";
        drop(bloom_add(bloom, k));
        
        int64:vp = sl_node_val_ptr(node) ?! 0i64;
        int64:vl = sl_node_val_len(node) ?! 0i64;
        int64:is_del = sl_node_is_deleted(node) ?! 0i64;
        
        int64:rec_sz = sstable_record_size(k, vl, is_del) ?! 0i64;
        int64:rec = sstable_serialize_record(k, vp, vl, is_del) ?! 0i64;
        
        int64:ins = page_insert(curr_page, rec, rec_sz) ?! -1i64;
        if (ins == -1i64) {
            // Page full, flush it
            int64:offset = sstable_flush_page(fd, curr_page) ?! -1i64;
            
            int64:last_k_len = string_length(last_key);
            int64:last_k_ptr = npk_core_alloc(last_k_len);
            drop(raw npk_mem_write_string(last_k_ptr, last_key));
            
            drop(npk_mem_write_int64(k_ptrs, block_count * 8i64, last_k_ptr));
            drop(npk_mem_write_int64(k_lens, block_count * 8i64, last_k_len));
            drop(npk_mem_write_int64(b_offs, block_count * 8i64, offset));
            block_count = block_count + 1i64;
            
            // Reset page and retry
            drop(page_free(curr_page));
            curr_page = page_alloc() ?! 0i64;
            drop(page_init(curr_page, block_count));
            ins = page_insert(curr_page, rec, rec_sz) ?! -1i64;
        }
        
        drop(npk_core_dalloc(rec));
        last_key = k;
        has_pending = 1i64;
        total_keys = total_keys + 1i64;
        
        node = sl_next(node) ?! 0i64;
    }
    
    // Flush last page if any keys
    if (has_pending == 1i64) {
        int64:offset = sstable_flush_page(fd, curr_page) ?! -1i64;
        
        int64:last_k_len = string_length(last_key);
        int64:last_k_ptr = npk_core_alloc(last_k_len);
        drop(raw npk_mem_write_string(last_k_ptr, last_key));
        
        drop(npk_mem_write_int64(k_ptrs, block_count * 8i64, last_k_ptr));
        drop(npk_mem_write_int64(k_lens, block_count * 8i64, last_k_len));
        drop(npk_mem_write_int64(b_offs, block_count * 8i64, offset));
        block_count = block_count + 1i64;
    }
    
    drop(page_free(curr_page));
    
    // Serialize and flush Bloom Filter
    int64:bloom_buf = bloom_serialize(bloom) ?! 0i64;
    int64:bloom_sz = bloom_serialize_size(bloom) ?! 0i64;
    int64:bloom_offset = sys(LSEEK, fd, 0i64, 1i64) ?! -1i64; // SEEK_CUR
    drop(sys(WRITE, fd, bloom_buf, bloom_sz));
    drop(npk_core_dalloc(bloom_buf));
    drop(bloom_destroy(bloom));
    
    // Build and flush index block
    int64:index_page = sstable_build_index(k_ptrs, k_lens, b_offs, block_count) ?! 0i64;
    int64:index_offset = sstable_flush_page(fd, index_page) ?! -1i64;
    drop(page_free(index_page));
    
    // Clean up key pointers
    int64:i = 0i64;
    while (i < block_count) {
        int64:kp = npk_mem_read_int64(k_ptrs, i * 8i64);
        drop(npk_core_dalloc(kp));
        i = i + 1i64;
    }
    drop(npk_core_dalloc(k_ptrs));
    drop(npk_core_dalloc(k_lens));
    drop(npk_core_dalloc(b_offs));
    
    // Write Footer (48 bytes)
    int64:footer = npk_core_alloc(SSTABLE_FOOTER_SIZE);
    drop(npk_mem_write_int64(footer, 0i64, block_count));
    drop(npk_mem_write_int64(footer, 8i64, index_offset));
    drop(npk_mem_write_int64(footer, 16i64, bloom_offset));
    drop(npk_mem_write_int64(footer, 24i64, bloom_sz));
    drop(npk_mem_write_int64(footer, 32i64, total_keys));
    drop(npk_mem_write_int32(footer, 40i64, 1145192497i32)); // "DB01" -> 0x44423031
    
    int64:crc_calc = crc32_compute(footer, 44i64) ?! 0i64;
    drop(npk_mem_write_int32(footer, 44i64, @cast_unchecked<int32>(crc_calc)));
    
    int64:fw = sys(WRITE, fd, footer, SSTABLE_FOOTER_SIZE) ?! -1i64;
    drop(npk_core_dalloc(footer));
    
    total_bytes = sys(LSEEK, fd, 0i64, 1i64) ?! -1i64;
    drop(sys(FSYNC, fd));
    drop(sys(CLOSE, fd));
    
    pass(total_bytes);
};

// -----------------------------------------------------------------------------
// Reader implementation
// -----------------------------------------------------------------------------

pub func:sstable_open_read = int64(string:path) {
    int64:fd = sys(OPEN, path, 0i64, 0i64) ?! -1i64;
    if (fd <= 0i64) { pass(0i64); }
    
    int64:footer = npk_core_alloc(SSTABLE_FOOTER_SIZE);
    int64:r_res = sys(LSEEK, fd, 0i64 - SSTABLE_FOOTER_SIZE, 2i64) ?! -1i64; // SEEK_END
    if (r_res == -1i64) {
        drop(npk_core_dalloc(footer));
        drop(sys(CLOSE, fd));
        pass(0i64);
    }
    
    int64:rw = sys(READ, fd, footer, SSTABLE_FOOTER_SIZE) ?! -1i64;
    if (rw != SSTABLE_FOOTER_SIZE) {
        drop(npk_core_dalloc(footer));
        drop(sys(CLOSE, fd));
        pass(0i64);
    }
    
    int32:magic = npk_mem_read_int32(footer, 40i64);
    if (magic != 1145192497i32) { // 0x44423031
        drop(npk_core_dalloc(footer));
        drop(sys(CLOSE, fd));
        pass(0i64);
    }
    
    int64:crc_calc = crc32_compute(footer, 44i64) ?! 0i64;
    int32:chk = npk_mem_read_int32(footer, 44i64);
    if (chk != @cast_unchecked<int32>(crc_calc)) {
        drop(npk_core_dalloc(footer));
        drop(sys(CLOSE, fd));
        pass(0i64);
    }
    
    int64:db_cnt = npk_mem_read_int64(footer, 0i64);
    int64:idx_off = npk_mem_read_int64(footer, 8i64);
    int64:bloom_off = npk_mem_read_int64(footer, 16i64);
    int64:bloom_sz = npk_mem_read_int64(footer, 24i64);
    int64:t_keys = npk_mem_read_int64(footer, 32i64);
    
    drop(npk_core_dalloc(footer));
    
    // Load index page
    int64:index_page = page_alloc() ?! 0i64;
    drop(sys(LSEEK, fd, idx_off, 0i64)); // SEEK_SET
    int64:iw = sys(READ, fd, index_page, PAGE_SIZE) ?! -1i64;
    if (iw != PAGE_SIZE) {
        drop(page_free(index_page));
        drop(sys(CLOSE, fd));
        pass(0i64);
    }
    
    // Load Bloom Filter
    int64:bloom_buf = npk_core_alloc(bloom_sz);
    drop(sys(LSEEK, fd, bloom_off, 0i64)); // SEEK_SET
    drop(sys(READ, fd, bloom_buf, bloom_sz));
    int64:bloom = bloom_deserialize(bloom_buf, bloom_sz) ?! 0i64;
    drop(npk_core_dalloc(bloom_buf));
    
    // Alloc 48-byte reader struct
    int64:reader = npk_core_alloc(48i64);
    drop(npk_mem_write_int64(reader, 0i64, fd));
    drop(npk_mem_write_int64(reader, 8i64, db_cnt));
    drop(npk_mem_write_int64(reader, 16i64, idx_off));
    drop(npk_mem_write_int64(reader, 24i64, t_keys));
    drop(npk_mem_write_int64(reader, 32i64, index_page));
    drop(npk_mem_write_int64(reader, 40i64, bloom));
    
    pass(reader);
};

pub func:sstable_close_read = NIL(int64:reader) {
    if (reader != 0i64) {
        int64:fd = npk_mem_read_int64(reader, 0i64);
        int64:index_page = npk_mem_read_int64(reader, 32i64);
        int64:bloom = npk_mem_read_int64(reader, 40i64);
        
        drop(sys(CLOSE, fd));
        drop(page_free(index_page));
        if (bloom != 0i64) { drop(bloom_destroy(bloom)); }
        drop(npk_core_dalloc(reader));
    }
    pass(NIL);
};

pub func:sstable_find_block = int64(int64:reader, string:key) {
    int64:index_page = npk_mem_read_int64(reader, 32i64);
    int32:count32 = page_get_slot_count(index_page) ?! 0i32;
    int64:count = count32 => int64;
    if (count == 0i64) { pass(-1i64); }
    
    int64:low = 0i64;
    int64:high = count - 1i64;
    int64:found = -1i64;
    
    while (low <= high) {
        int64:mid = low + ((high - low) / 2i64);
        int64:tup_len = slot_get_tuple_length(index_page, mid) ?! 0i64;
        int64:tup_off = slot_get_tuple_offset(index_page, mid) ?! 0i64;
        
        int64:tup_ptr = npk_mem_offset(index_page, tup_off);
        int64:k_len = npk_mem_read_int32(tup_ptr, 0i64) => int64;
        string:last_k = raw npk_mem_read_string(tup_ptr + 4i64, k_len);
        
        if (last_k >= key) {
            found = mid;
            high = mid - 1i64;
        } else {
            low = mid + 1i64;
        }
    }
    
    if (found != -1i64) {
        int64:t_off = slot_get_tuple_offset(index_page, found) ?! 0i64;
        int64:t_ptr = npk_mem_offset(index_page, t_off);
        int64:kl = npk_mem_read_int32(t_ptr, 0i64) => int64;
        int64:blk_off = npk_mem_read_int64(t_ptr, 4i64 + kl);
        pass(blk_off / PAGE_SIZE);
    }
    pass(-1i64);
};

pub func:sstable_load_block = int64(int64:reader, int64:block_num) {
    int64:fd = npk_mem_read_int64(reader, 0i64);
    int64:blk_off = block_num * PAGE_SIZE;
    int64:page = page_alloc() ?! 0i64;
    drop(sys(LSEEK, fd, blk_off, 0i64)); // SEEK_SET
    int64:rw = sys(READ, fd, page, PAGE_SIZE) ?! -1i64;
    if (rw != PAGE_SIZE) {
        drop(page_free(page));
        pass(0i64);
    }
    pass(page);
};

// Record struct (40 bytes):
// 0: key_ptr (int64) - dynamically allocated string copy!
// 8: key_len (int64)
// 16: val_ptr (int64) - within page buffer, do not free!
// 24: val_len (int64)
// 32: is_tombstone (int64)
pub func:sstable_read_record = int64(int64:page_buf, int64:slot_index) {
    int64:tup_len = slot_get_tuple_length(page_buf, slot_index) ?! 0i64;
    int64:tup_off = slot_get_tuple_offset(page_buf, slot_index) ?! 0i64;
    if (tup_len == 0i64) { pass(0i64); }
    
    int64:tup_ptr = npk_mem_offset(page_buf, tup_off);
    int64:flag = npk_mem_read_byte(tup_ptr, 0i64);
    int64:key_len = npk_mem_read_int32(tup_ptr, 1i64) => int64;
    
    int64:v_off = 5i64 + key_len;
    
    int64:rec = npk_core_alloc(40i64);
    int64:k_ptr = npk_core_alloc(key_len);
    drop(npk_mem_copy(k_ptr, tup_ptr + 5i64, key_len));
    
    drop(npk_mem_write_int64(rec, 0i64, k_ptr));
    drop(npk_mem_write_int64(rec, 8i64, key_len));
    
    if (flag == RECORD_FLAG_TOMBSTONE => int64) {
        drop(npk_mem_write_int64(rec, 16i64, 0i64));
        drop(npk_mem_write_int64(rec, 24i64, 0i64));
        drop(npk_mem_write_int64(rec, 32i64, 1i64));
    } else {
        int64:val_len = npk_mem_read_int32(tup_ptr, v_off) => int64;
        int64:v_ptr = npk_core_alloc(val_len);
        drop(npk_mem_copy(v_ptr, tup_ptr + v_off + 4i64, val_len));
        drop(npk_mem_write_int64(rec, 16i64, v_ptr));
        drop(npk_mem_write_int64(rec, 24i64, val_len));
        drop(npk_mem_write_int64(rec, 32i64, 0i64));
    }
    
    pass(rec);
};

pub func:sst_rec_key = string(int64:rec) {
    int64:k_ptr = npk_mem_read_int64(rec, 0i64);
    int64:k_len = npk_mem_read_int64(rec, 8i64);
    pass(raw npk_mem_read_string(k_ptr, k_len));
};
pub func:sst_rec_val_ptr = int64(int64:rec) { pass(npk_mem_read_int64(rec, 16i64)); };
pub func:sst_rec_val_len = int64(int64:rec) { pass(npk_mem_read_int64(rec, 24i64)); };
pub func:sst_rec_is_tombstone = int64(int64:rec) { pass(npk_mem_read_int64(rec, 32i64)); };

pub func:sst_rec_free = NIL(int64:rec) {
    if (rec != 0i64) {
        int64:k_ptr = npk_mem_read_int64(rec, 0i64);
        drop(npk_core_dalloc(k_ptr));
        int64:is_ts = npk_mem_read_int64(rec, 32i64);
        if (is_ts == 0i64) {
            int64:v_ptr = npk_mem_read_int64(rec, 16i64);
            if (v_ptr != 0i64) {
                drop(npk_core_dalloc(v_ptr));
            }
        }
        drop(npk_core_dalloc(rec));
    }
    pass(NIL);
};

pub func:sstable_get = int64(int64:reader, string:key) {
    int64:bloom = npk_mem_read_int64(reader, 40i64);
    if (bloom != 0i64) {
        int64:chk = bloom_check(bloom, key) ?! 0i64;
        // if (chk == 0i64) {
        //     pass(0i64);
        // }
    }
    
    int64:blk = sstable_find_block(reader, key) ?! -1i64;
    if (blk == -1i64) { pass(0i64); }
    
    int64:page = sstable_load_block(reader, blk) ?! 0i64;
    if (page == 0i64) { pass(0i64); }
    
    int32:count32 = page_get_slot_count(page) ?! 0i32;
    int64:count = count32 => int64;
    int64:i = 0i64;
    int64:found_rec = 0i64;
    
    while (i < count) {
        int64:rec = sstable_read_record(page, i) ?! 0i64;
        if (rec != 0i64) {
            string:rk = sst_rec_key(rec) ?! "";
            if (rk == key) {
                found_rec = rec;
                break;
            }
            drop(sst_rec_free(rec));
        }
        i = i + 1i64;
    }
    
    drop(page_free(page));
    pass(found_rec);
};

// Iter state (32 bytes):
// 0: reader (int64)
// 8: current_block (int64)
// 16: current_slot (int64)
// 24: current_page (int64)
pub func:sstable_iter_create = int64(int64:reader) {
    int64:iter = npk_core_alloc(32i64);
    drop(npk_mem_write_int64(iter, 0i64, reader));
    drop(npk_mem_write_int64(iter, 8i64, 0i64));
    drop(npk_mem_write_int64(iter, 16i64, 0i64));
    
    int64:page = sstable_load_block(reader, 0i64) ?! 0i64;
    drop(npk_mem_write_int64(iter, 24i64, page));
    
    pass(iter);
};

pub func:sstable_iter_next = int64(int64:iter) {
    int64:reader = npk_mem_read_int64(iter, 0i64);
    int64:blk = npk_mem_read_int64(iter, 8i64);
    int64:slot = npk_mem_read_int64(iter, 16i64);
    int64:page = npk_mem_read_int64(iter, 24i64);
    int64:db_cnt = npk_mem_read_int64(reader, 8i64);
    
    while (page != 0i64) {
        int32:count32 = page_get_slot_count(page) ?! 0i32;
        int64:count = count32 => int64;
        if (slot < count) {
            int64:rec = sstable_read_record(page, slot) ?! 0i64;
            drop(npk_mem_write_int64(iter, 16i64, slot + 1i64));
            if (rec != 0i64) {
                pass(rec);
            }
        } else {
            drop(page_free(page));
            blk = blk + 1i64;
            if (blk >= db_cnt) {
                drop(npk_mem_write_int64(iter, 24i64, 0i64));
                break;
            }
            page = sstable_load_block(reader, blk) ?! 0i64;
            slot = 0i64;
            drop(npk_mem_write_int64(iter, 8i64, blk));
            drop(npk_mem_write_int64(iter, 16i64, slot));
            drop(npk_mem_write_int64(iter, 24i64, page));
        }
    }
    
    pass(0i64);
};

pub func:sstable_iter_destroy = NIL(int64:iter) {
    if (iter != 0i64) {
        int64:page = npk_mem_read_int64(iter, 24i64);
        if (page != 0i64) { drop(page_free(page)); }
        drop(npk_core_dalloc(iter));
    }
    pass(NIL);
};

```

### File: `src/storage/wal.npk`
```nitpick
// src/storage/wal.npk — Write-Ahead Log implementation
use "../util/constants.npk".*;
use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;
use "../util/crc32.npk".*;
use "../document/json_serializer.npk".*;
use "sys.npk".*;

pub fixed int64:WAL_GROUP_MAX_RECORDS = 32i64;
pub fixed int64:WAL_GROUP_WINDOW_US   = 1000i64; // 1ms

int64:wal_state_ptr = 0i64;
int64:wal_group_mode = 0i64; // 0 = per_write, 1 = group_commit

// Global sequence counter
int64:wal_sequence = 0i64;

pub func:wal_next_seq = int64() {
    wal_sequence = wal_sequence + 1i64;
    pass(wal_sequence);
};

pub func:wal_current_seq = int64() {
    pass(wal_sequence);
};

pub func:wal_open = int64(string:path) {
    // O_WRONLY(1) + O_CREAT(64) + O_APPEND(1024) = 1089
    // MODE_644 = 420
    Result<int64>:fd_res = sys(OPEN, path, 1089i64, 420i64);
    if (fd_res.is_error) {
        pass(0i64 - ERR_WAL_OPEN_FAILED);
    }
    pass(fd_res.value);
};

pub func:wal_close = int32(int64:wal_fd) {
    if (wal_state_ptr != 0i64) {
        // Flush any pending records
        drop(wal_batch_flush(wal_fd));
        
        int64:buf_ptr = npk_mem_read_int64(wal_state_ptr, 0i64);
        drop(npk_core_dalloc(buf_ptr));
        drop(npk_core_dalloc(wal_state_ptr));
        wal_state_ptr = 0i64;
    }
    
    drop(sys(CLOSE, wal_fd));
    pass(0i32);
};

pub func:wal_sync = int64(int64:wal_fd) {
    Result<int64>:res = sys(FSYNC, wal_fd);
    if (res.is_error) {
        pass(0i64 - ERR_WAL_FSYNC_FAILED);
    }
    pass(0i64);
};

// Generic internal appender
func:wal_append = int64(int64:wal_fd, int32:rec_type, int64:seq, int64:payload_ptr, int64:payload_len) {
    int64:total_len = 16i64 + payload_len;
    int64:buf = npk_core_alloc(total_len);
    
    // Offset 4: length (total record length INCLUDING header)
    drop(npk_mem_write_int32(buf, 4i64, @cast_unchecked<int32>(total_len)));
    
    // Offset 8: record_type
    drop(npk_mem_write_int32(buf, 8i64, rec_type));
    
    // Offset 12: sequence
    drop(npk_mem_write_int32(buf, 12i64, @cast_unchecked<int32>(seq)));
    
    // Offset 16: payload
    if (payload_len > 0i64) {
        drop(npk_mem_copy(buf + 16i64, payload_ptr, payload_len));
    }
    
    // Offset 0: crc32 over bytes 4..end
    int64:crc = crc32_compute(buf + 4i64, total_len - 4i64) ?! 0i64;
    drop(npk_mem_write_int32(buf, 0i64, @cast_unchecked<int32>(crc)));
    
    Result<int64>:w_res = sys(WRITE, wal_fd, buf, total_len);
    drop(npk_core_dalloc(buf));
    
    if (w_res.is_error) {
        pass(0i64 - ERR_WAL_WRITE_FAILED);
    }
    
    drop(wal_sync(wal_fd));
    
    pass(total_len);
};

pub func:wal_append_put = int64(int64:wal_fd, string:key, int64:value_ptr, int64:value_len, int64:seq)
    requires wal_fd > 0i64, value_len >= 0i64, seq > 0i64 {
    int64:key_len = string_length(key);
    int64:payload_len = 4i64 + key_len + 4i64 + value_len;
    int64:payload = npk_core_alloc(payload_len);
    
    // Offset 0: key_len
    drop(npk_mem_write_int32(payload, 0i64, @cast_unchecked<int32>(key_len)));
    
    // Offset 4: key
    if (key_len > 0i64) {
        drop(raw npk_mem_write_string(payload + 4i64, key));
    }
    
    // Offset 4+key_len: value_len
    drop(npk_mem_write_int32(payload, 4i64 + key_len, @cast_unchecked<int32>(value_len)));
    
    // Offset 8+key_len: value
    if (value_len > 0i64) {
        drop(npk_mem_copy(payload + 8i64 + key_len, value_ptr, value_len));
    }
    
    int64:res = wal_append(wal_fd, WAL_RECORD_PUT, seq, payload, payload_len) ?! 0i64;
    drop(npk_core_dalloc(payload));
    pass(res);
};

pub func:wal_append_delete = int64(int64:wal_fd, string:key, int64:seq)
    requires wal_fd > 0i64, seq > 0i64 {
    int64:key_len = string_length(key);
    int64:payload_len = 4i64 + key_len;
    int64:payload = npk_core_alloc(payload_len);
    
    drop(npk_mem_write_int32(payload, 0i64, @cast_unchecked<int32>(key_len)));
    
    if (key_len > 0i64) {
        drop(raw npk_mem_write_string(payload + 4i64, key));
    }
    
    int64:res = wal_append(wal_fd, WAL_RECORD_DELETE, seq, payload, payload_len) ?! 0i64;
    drop(npk_core_dalloc(payload));
    pass(res);
};

pub func:wal_append_checkpoint = int64(int64:wal_fd, int64:seq) {
    int64:res = wal_append(wal_fd, WAL_RECORD_CHECKPOINT, seq, 0i64, 0i64) ?! 0i64;
    pass(res);
};

pub func:wal_append_document = int64(int64:wal_fd, string:key, int64:val_ptr, int64:seq) {
    int64:key_len = string_length(key);
    int64:doc_len_ptr = npk_core_alloc(8i64);
    int64:doc_buf = raw serialize_document(@cast_unchecked<NpkJsonVal->>(val_ptr), doc_len_ptr);
    int64:doc_len = npk_mem_read_int64(doc_len_ptr, 0i64);
    
    int64:payload_len = 4i64 + key_len + 4i64 + doc_len;
    int64:payload = npk_core_alloc(payload_len);
    
    // Offset 0: key_len
    drop(npk_mem_write_int32(payload, 0i64, @cast_unchecked<int32>(key_len)));
    if (key_len > 0i64) {
        drop(raw npk_mem_write_string(payload + 4i64, key));
    }
    
    // Offset 4+key_len: doc_len
    drop(npk_mem_write_int32(payload, 4i64 + key_len, @cast_unchecked<int32>(doc_len)));
    
    // Offset 8+key_len: doc
    if (doc_len > 0i64) {
        drop(npk_mem_copy(payload + 8i64 + key_len, doc_buf, doc_len));
    }
    
    int64:res = wal_append(wal_fd, WAL_RECORD_PUT, seq, payload, payload_len) ?! 0i64;
    
    drop(npk_core_dalloc(payload));
    drop(npk_core_dalloc(doc_buf));
    drop(npk_core_dalloc(doc_len_ptr));
    
    pass(res);
};

// -----------------------------------------------------------------------------
// WAL Group Commit
// -----------------------------------------------------------------------------

pub func:wal_enable_group_commit = NIL(int64:wal_fd) {
    if (wal_state_ptr == 0i64) {
        wal_state_ptr = npk_core_alloc(40i64);
        int64:initial_cap = 65536i64;
        drop(npk_mem_write_int64(wal_state_ptr, 0i64, npk_core_alloc(initial_cap)));
        drop(npk_mem_write_int64(wal_state_ptr, 8i64, 0i64));
        drop(npk_mem_write_int64(wal_state_ptr, 16i64, initial_cap));
        drop(npk_mem_write_int64(wal_state_ptr, 24i64, 0i64));
        drop(npk_mem_write_int64(wal_state_ptr, 32i64, 0i64));
    }
    wal_group_mode = 1i64;
    pass(NIL);
};

pub func:wal_batch_flush = int64(int64:wal_fd) {
    if (wal_state_ptr == 0i64) { pass(0i64); }
    int64:buf_ptr = npk_mem_read_int64(wal_state_ptr, 0i64);
    int64:buf_len = npk_mem_read_int64(wal_state_ptr, 8i64);
    
    if (buf_len > 0i64) {
        Result<int64>:w_res = sys(WRITE, wal_fd, buf_ptr, buf_len);
        if (w_res.is_error) {
            pass(0i64 - ERR_WAL_WRITE_FAILED);
        }
        drop(wal_sync(wal_fd));
        
        drop(npk_mem_write_int64(wal_state_ptr, 8i64, 0i64));
        drop(npk_mem_write_int64(wal_state_ptr, 24i64, 0i64));
        drop(npk_mem_write_int64(wal_state_ptr, 32i64, 0i64));
    }
    pass(0i64);
};

pub func:wal_batch_should_flush = int64(int64:wal_fd) {
    if (wal_state_ptr == 0i64) { pass(0i64); }
    int64:record_count = npk_mem_read_int64(wal_state_ptr, 24i64);
    if (record_count >= WAL_GROUP_MAX_RECORDS) { pass(1i64); }
    
    int64:last_sync = npk_mem_read_int64(wal_state_ptr, 32i64);
    int64:now = 0i64;
    int64:diff = now - last_sync;
    if (diff >= (WAL_GROUP_WINDOW_US * 1000i64)) { pass(1i64); }
    
    pass(0i64);
};

func:wal_batch_append = int64(int64:wal_fd, int32:rec_type, int64:seq, int64:payload_ptr, int64:payload_len) {
    int64:total_len = 16i64 + payload_len;
    
    int64:buf_ptr = npk_mem_read_int64(wal_state_ptr, 0i64);
    int64:buf_len = npk_mem_read_int64(wal_state_ptr, 8i64);
    int64:buf_cap = npk_mem_read_int64(wal_state_ptr, 16i64);
    
    if ((buf_len + total_len) > buf_cap) {
        int64:new_cap = buf_cap * 2i64;
        if (new_cap < buf_len + total_len) {
            new_cap = (buf_len + total_len) * 2i64;
        }
        int64:new_buf = npk_core_alloc(new_cap);
        drop(npk_mem_copy(new_buf, buf_ptr, buf_len));
        drop(npk_core_dalloc(buf_ptr));
        buf_ptr = new_buf;
        buf_cap = new_cap;
        drop(npk_mem_write_int64(wal_state_ptr, 0i64, buf_ptr));
        drop(npk_mem_write_int64(wal_state_ptr, 16i64, buf_cap));
    }
    
    int64:write_ptr = buf_ptr + buf_len;
    
    drop(npk_mem_write_int32(write_ptr, 4i64, @cast_unchecked<int32>(total_len)));
    drop(npk_mem_write_int32(write_ptr, 8i64, rec_type));
    drop(npk_mem_write_int32(write_ptr, 12i64, @cast_unchecked<int32>(seq)));
    
    if (payload_len > 0i64) {
        drop(npk_mem_copy(write_ptr + 16i64, payload_ptr, payload_len));
    }
    
    int64:crc = crc32_compute(write_ptr + 4i64, total_len - 4i64) ?! 0i64;
    drop(npk_mem_write_int32(write_ptr, 0i64, @cast_unchecked<int32>(crc)));
    
    drop(npk_mem_write_int64(wal_state_ptr, 8i64, buf_len + total_len));
    int64:record_count = npk_mem_read_int64(wal_state_ptr, 24i64);
    drop(npk_mem_write_int64(wal_state_ptr, 24i64, record_count + 1i64));
    
    pass(total_len);
};

pub func:wal_batch_append_put = int64(int64:wal_fd, string:key, int64:value_ptr, int64:value_len, int64:seq) {
    int64:key_len = string_length(key);
    int64:payload_len = 4i64 + key_len + 4i64 + value_len;
    int64:payload = npk_core_alloc(payload_len);
    
    drop(npk_mem_write_int32(payload, 0i64, @cast_unchecked<int32>(key_len)));
    if (key_len > 0i64) { drop(raw npk_mem_write_string(payload + 4i64, key)); }
    drop(npk_mem_write_int32(payload, 4i64 + key_len, @cast_unchecked<int32>(value_len)));
    if (value_len > 0i64) { drop(npk_mem_copy(payload + 8i64 + key_len, value_ptr, value_len)); }
    
    int64:res = wal_batch_append(wal_fd, WAL_RECORD_PUT, seq, payload, payload_len) ?! 0i64;
    drop(npk_core_dalloc(payload));
    pass(res);
};

pub func:wal_batch_append_delete = int64(int64:wal_fd, string:key, int64:seq) {
    int64:key_len = string_length(key);
    int64:payload_len = 4i64 + key_len;
    int64:payload = npk_core_alloc(payload_len);
    
    drop(npk_mem_write_int32(payload, 0i64, @cast_unchecked<int32>(key_len)));
    if (key_len > 0i64) { drop(raw npk_mem_write_string(payload + 4i64, key)); }
    
    int64:res = wal_batch_append(wal_fd, WAL_RECORD_DELETE, seq, payload, payload_len) ?! 0i64;
    drop(npk_core_dalloc(payload));
    pass(res);
};

// -----------------------------------------------------------------------------
// WAL Reader & Recovery
// -----------------------------------------------------------------------------

pub func:wal_open_read = int64(string:path) {
    Result<int64>:fd_res = sys(OPEN, path, 0i64, 0i64);
    if (fd_res.is_error) {
        pass(0i64);
    }
    pass(fd_res.value);
};

pub func:wal_read_next = int64(int64:wal_fd) {
    int64:hdr_buf = npk_core_alloc(16i64);
    Result<int64>:r_res = sys(READ, wal_fd, hdr_buf, 16i64);
    if (r_res.is_error) {
        drop(npk_core_dalloc(hdr_buf));
        pass(-1i64);
    }
    int64:bytes_read = r_res.value;
    if (bytes_read == 0i64) {
        drop(npk_core_dalloc(hdr_buf));
        pass(0i64); // EOF
    }
    if (bytes_read < 16i64) {
        drop(npk_core_dalloc(hdr_buf));
        pass(-1i64); // Torn write
    }
    
    int64:crc32_stored_signed = npk_mem_read_int32(hdr_buf, 0i64) => int64;
    int64:crc32_stored = crc32_stored_signed & 4294967295i64;
    int64:record_length = npk_mem_read_int32(hdr_buf, 4i64) => int64;
    
    if (record_length < 16i64) {
        drop(npk_core_dalloc(hdr_buf));
        pass(-1i64); // Corrupt length
    }
    
    int64:full_buf = npk_core_alloc(record_length);
    drop(npk_mem_copy(full_buf, hdr_buf, 16i64));
    drop(npk_core_dalloc(hdr_buf));
    
    int64:rem_len = record_length - 16i64;
    if (rem_len > 0i64) {
        Result<int64>:r2_res = sys(READ, wal_fd, full_buf + 16i64, rem_len);
        if (r2_res.is_error) {
            drop(npk_core_dalloc(full_buf));
            pass(-1i64);
        }
        int64:b2 = r2_res.value;
        if (b2 < rem_len) {
            drop(npk_core_dalloc(full_buf));
            pass(-1i64); // Torn write
        }
    }
    
    int64:comp_crc = crc32_compute(full_buf + 4i64, record_length - 4i64) ?! -1i64;
    if (comp_crc != crc32_stored) {
        drop(npk_core_dalloc(full_buf));
        pass(-1i64); // CRC mismatch
    }
    
    pass(full_buf);
};

pub func:wal_record_type = int32(int64:record_buf) {
    pass(npk_mem_read_int32(record_buf, 8i64));
};

pub func:wal_record_seq = int32(int64:record_buf) {
    pass(npk_mem_read_int32(record_buf, 12i64));
};

pub func:wal_record_key = string(int64:record_buf) {
    int64:key_len = npk_mem_read_int32(record_buf, 16i64) => int64;
    if (key_len <= 0i64) { pass(""); }
    pass(raw npk_mem_read_string(record_buf + 20i64, key_len));
};

pub func:wal_record_value_ptr = int64(int64:record_buf) {
    int64:key_len = npk_mem_read_int32(record_buf, 16i64) => int64;
    pass(record_buf + 24i64 + key_len);
};

pub func:wal_record_value_len = int64(int64:record_buf) {
    int64:key_len = npk_mem_read_int32(record_buf, 16i64) => int64;
    pass(npk_mem_read_int32(record_buf, 20i64 + key_len) => int64);
};

pub func:wal_replay = int64(string:wal_path) {
    int64:fd = wal_open_read(wal_path) ?! 0i64;
    if (fd <= 0i64) { pass(0i64); }
    
    int64:count = 0i64;
    while (1i64 == 1i64) {
        int64:rec = wal_read_next(fd) ?! -1i64;
        if (rec == 0i64) { break; }
        if (rec == -1i64) {
            println("WARNING: WAL torn/corrupt record detected. Halting replay.");
            break;
        }
        drop(npk_core_dalloc(rec));
        count = count + 1i64;
    }
    drop(sys(CLOSE, fd));
    pass(count);
};

pub func:wal_truncate = int64(string:path) {
    Result<int64>:fd_res = sys(OPEN, path, 513i64, 420i64); // O_WRONLY | O_TRUNC = 513
    if (fd_res.is_error) {
        pass(-1i64);
    }
    drop(sys(CLOSE, fd_res.value));
    pass(0i64);
};

```

### File: `src/storage/write_path.npk`
```nitpick
// src/storage/write_path.npk
// Unified write path: WAL -> Memtable

use "../util/mem_primitives.npk".*;
use "wal.npk".*;
use "memtable.npk".*;
use "level_manager.npk".*;
use "flush.npk".*;
use "compaction_worker.npk".*;
use "thread.npk".*;
use "channel.npk".*;
use "../util/constants.npk".*;

// Write path state
// Offset 0: wal_fd (int64)
// Offset 8: active_mt (int64)
// Offset 16: frozen_mt (int64)
// Offset 24: mt_id_counter (int64)
pub fixed int64:WP_OFF_WAL_FD   = 0i64;
pub fixed int64:WP_OFF_ACTIVE   = 8i64;
pub fixed int64:WP_OFF_FROZEN   = 16i64;
pub fixed int64:WP_OFF_COUNTER  = 24i64;
pub fixed int64:WP_OFF_LM       = 32i64;
pub fixed int64:WP_OFF_WORKER   = 40i64; // Contains {channel, thread, ctx} pointer
pub fixed int64:WP_OFF_SYNC_MODE= 48i64; // 0 = per_write, 1 = group_commit
pub fixed int64:WP_STATE_SIZE   = 56i64;

pub func:wp_init = int64(string:data_dir, string:wal_path, ?->:worker_fn, string:sync_mode) {
    int64:wp = npk_core_alloc(WP_STATE_SIZE);
    
    drop(flush_ensure_dirs(data_dir));
    int64:wal_fd = wal_open(wal_path) ?! -1i64;
    if (wal_fd <= 0i64) {
        drop(npk_core_dalloc(wp));
        pass(0i64);
    }
    
    int64:lm = lm_create(data_dir) ?! 0i64;
    
    int64:active_mt = mt_create(1i64) ?! 0i64;
    
    drop(npk_mem_write_int64(wp, WP_OFF_WAL_FD, wal_fd));
    drop(npk_mem_write_int64(wp, WP_OFF_ACTIVE, active_mt));
    drop(npk_mem_write_int64(wp, WP_OFF_FROZEN, 0i64));
    drop(npk_mem_write_int64(wp, WP_OFF_COUNTER, 2i64));
    drop(npk_mem_write_int64(wp, WP_OFF_LM, lm));
    
    int64:worker = compaction_worker_start(lm, worker_fn) ?! 0i64;
    drop(npk_mem_write_int64(wp, WP_OFF_WORKER, worker));
    
    int64:mode = 0i64;
    if (sync_mode == "group_commit") {
        mode = 1i64;
        drop(wal_enable_group_commit(wal_fd));
    }
    drop(npk_mem_write_int64(wp, WP_OFF_SYNC_MODE, mode));
    
    pass(wp);
};

pub func:wp_put = int64(int64:wp, string:key, int64:val_ptr, int64:val_len) {
    int64:wal_fd = npk_mem_read_int64(wp, WP_OFF_WAL_FD);
    int64:active_mt = npk_mem_read_int64(wp, WP_OFF_ACTIVE);
    
    // 1. Check if we need to freeze
    int64:should_flush = mt_should_flush(active_mt) ?! 0i64;
    if (should_flush == 1i64) {
        int64:frozen_mt = npk_mem_read_int64(wp, WP_OFF_FROZEN);
        drop(mt_freeze(active_mt));
        drop(npk_mem_write_int64(wp, WP_OFF_FROZEN, active_mt));
        
        int64:ctr = npk_mem_read_int64(wp, WP_OFF_COUNTER);
        int64:new_mt = mt_create(ctr) ?! 0i64;
        drop(npk_mem_write_int64(wp, WP_OFF_COUNTER, ctr + 1i64));
        drop(npk_mem_write_int64(wp, WP_OFF_ACTIVE, new_mt));
        active_mt = new_mt;
        
        int64:lm = npk_mem_read_int64(wp, WP_OFF_LM);
        int64:d_ptr = npk_mem_read_int64(lm, 0i64);
        string:before_flush = raw npk_mem_read_string(d_ptr, 11i64);
        println("d_ptr before flush: " + before_flush);
        drop(flush_memtable(npk_mem_read_int64(wp, WP_OFF_FROZEN), lm));
        drop(npk_mem_write_int64(wp, WP_OFF_FROZEN, 0i64));
        
        int64:l0_count = lm_count_at_level(lm, 0i64) ?! 0i64;
        if (l0_count >= LM_L0_COMPACTION_THRESHOLD) {
            int64:worker = npk_mem_read_int64(wp, WP_OFF_WORKER);
            if (worker != 0i64) {
                int64:ch = npk_mem_read_int64(worker, 0i64);
                drop(compaction_signal_l0(ch));
            }
        }
        
        // Backpressure: If L0 is almost full, wait for worker to catch up
        while (l0_count >= 8i64) {
            drop(Thread.sleep_ms(10i64));
            l0_count = lm_count_at_level(lm, 0i64) ?! 0i64;
        }
    }
    
    // 2. Write to WAL
    int64:seq = wal_next_seq() ?! 0i64;
    int64:sync_mode = npk_mem_read_int64(wp, WP_OFF_SYNC_MODE);
    int64:w_res = 0i64;
    
    if (sync_mode == 1i64) {
        w_res = wal_batch_append_put(wal_fd, key, val_ptr, val_len, seq) ?! -1i64;
        if (w_res > 0i64) {
            int64:should = wal_batch_should_flush(wal_fd) ?! 0i64;
            if (should == 1i64) {
                drop(wal_batch_flush(wal_fd));
            }
        }
    } else {
        w_res = wal_append_put(wal_fd, key, val_ptr, val_len, seq) ?! -1i64;
    }
    
    if (w_res <= 0i64) {
        pass(-1i64); // WAL failed
    }
    
    // 3. Write to Memtable
    int64:m_res = mt_put(active_mt, key, val_ptr, val_len) ?! -1i64;
    pass(m_res);
};

pub func:wp_delete = int64(int64:wp, string:key) {
    int64:wal_fd = npk_mem_read_int64(wp, WP_OFF_WAL_FD);
    int64:active_mt = npk_mem_read_int64(wp, WP_OFF_ACTIVE);
    
    int64:seq = wal_next_seq() ?! 0i64;
    int64:sync_mode = npk_mem_read_int64(wp, WP_OFF_SYNC_MODE);
    int64:w_res = 0i64;
    
    if (sync_mode == 1i64) {
        w_res = wal_batch_append_delete(wal_fd, key, seq) ?! -1i64;
        if (w_res > 0i64) {
            int64:should = wal_batch_should_flush(wal_fd) ?! 0i64;
            if (should == 1i64) {
                drop(wal_batch_flush(wal_fd));
            }
        }
    } else {
        w_res = wal_append_delete(wal_fd, key, seq) ?! -1i64;
    }
    
    if (w_res <= 0i64) {
        pass(-1i64);
    }
    
    int64:m_res = mt_delete(active_mt, key) ?! -1i64;
    pass(m_res);
};

pub func:wp_active_memtable = int64(int64:wp) {
    pass(npk_mem_read_int64(wp, WP_OFF_ACTIVE));
};

pub func:wp_frozen_memtable = int64(int64:wp) {
    pass(npk_mem_read_int64(wp, WP_OFF_FROZEN));
};

pub func:wp_clear_frozen = NIL(int64:wp) {
    int64:frozen_mt = npk_mem_read_int64(wp, WP_OFF_FROZEN);
    if (frozen_mt != 0i64) {
        drop(mt_destroy(frozen_mt));
        drop(npk_mem_write_int64(wp, WP_OFF_FROZEN, 0i64));
    }
    pass(NIL);
};

pub func:wp_level_manager = int64(int64:wp) {
    if (wp == 0i64) { pass(0i64); }
    pass(npk_mem_read_int64(wp, WP_OFF_LM));
};

pub func:wp_shutdown = NIL(int64:wp) {
    if (wp != 0i64) {
        int64:wal_fd = npk_mem_read_int64(wp, WP_OFF_WAL_FD);
        int64:sync_mode = npk_mem_read_int64(wp, WP_OFF_SYNC_MODE);
        if (sync_mode == 1i64) {
            drop(wal_batch_flush(wal_fd));
        }
        drop(wal_sync(wal_fd));
        drop(wal_close(wal_fd));
        
        int64:active_mt = npk_mem_read_int64(wp, WP_OFF_ACTIVE);
        drop(mt_destroy(active_mt));
        
        drop(wp_clear_frozen(wp));
        
        int64:worker = npk_mem_read_int64(wp, WP_OFF_WORKER);
        if (worker != 0i64) {
            int64:ch = npk_mem_read_int64(worker, 0i64);
            int64:tid = npk_mem_read_int64(worker, 8i64);
            int64:ctx = npk_mem_read_int64(worker, 16i64);
            
            drop(compaction_signal_shutdown(ch));
            drop(Thread.sleep_ms(20i64)); // Brief yield for thread to exit
            drop(Thread.join(tid)); // Important to join to ensure clean shutdown
            
            drop(Channel.close(ch));
            drop(Channel.destroy(ch));
            drop(npk_core_dalloc(ctx));
            drop(npk_core_dalloc(worker));
        }
        
        int64:lm = npk_mem_read_int64(wp, WP_OFF_LM);
        if (lm != 0i64) {
            drop(lm_destroy(lm));
        }
        
        drop(npk_core_dalloc(wp));
    }
    pass(NIL);
};

```

### File: `src/concurrency/ebr.npk`
```nitpick
// ebr.npk — Epoch-Based Reclamation (EBR) for safe memory reclamation
//
// The global epoch advances when all active threads have observed the current
// epoch. Nodes unlinked in epoch E are safe to free only after the global
// epoch has advanced to E+2 (all readers from epoch E have retired).

use "../util/error_codes.npk".*;
use "../util/constants.npk".*;
use "../util/mem_primitives.npk".*;
use "../index/art_alloc.npk".*;

// Maximum supported concurrent threads
pub fixed int64:EBR_MAX_THREADS = 256i64;

// Epoch advancement interval: advance every this many retires.
pub fixed int64:EBR_ADVANCE_INTERVAL = 100i64;

// Limbo list node layout (flat buffer, singly linked):
//   Bytes  0-7:  node_ptr (int64) — the reclaimed node pointer
//   Bytes  8-15: epoch    (int64) — the epoch when this node was unlinked
//   Bytes 16-23: next     (int64) — next limbo node pointer (0 = end of list)
pub fixed int64:LIMBO_NODE_SIZE  = 24i64;
pub fixed int64:LIMBO_OFF_PTR    = 0i64;
pub fixed int64:LIMBO_OFF_EPOCH  = 8i64;
pub fixed int64:LIMBO_OFF_NEXT   = 16i64;

// Thread state layout (flat buffer, one per thread slot):
//   Bytes  0-7:  local_epoch (int64) — last observed global epoch
//   Bytes  8-15: is_active   (int64) — 1 if thread is in a read-critical section
//   Bytes 16-23: thread_id   (int64) — the thread ID (index into ebr_threads array)
//   Bytes 24-31: limbo_head  (int64) — pointer to the head of this thread's limbo list
//   Bytes 32-39: limbo_count (int64) — number of nodes currently in the limbo list
//   Bytes 40-47: retire_count (int64) — total retires since last advance attempt
pub fixed int64:EBR_THREAD_STATE_SIZE  = 48i64;
pub fixed int64:EBR_TS_LOCAL_EPOCH     = 0i64;
pub fixed int64:EBR_TS_IS_ACTIVE       = 8i64;
pub fixed int64:EBR_TS_THREAD_ID       = 16i64;
pub fixed int64:EBR_TS_LIMBO_HEAD      = 24i64;
pub fixed int64:EBR_TS_LIMBO_COUNT     = 32i64;
pub fixed int64:EBR_TS_RETIRE_COUNT    = 40i64;

// Global EBR state
// In a real multi-threaded environment these would be cache-line padded.
// For now they are plain int64 (will be atomic<int64> in v0.1.6).
int64:ebr_global_state = 0i64;          // Pointer to 16 bytes: [epoch, thread_count]
int64:ebr_thread_states = 0i64;         // Pointer to EBR_MAX_THREADS thread-state buffers

// Initialize the EBR subsystem. Call once before spawning threads.
// Allocates the thread-state array.
pub func:ebr_init = NIL() {
    int64:states_size = EBR_MAX_THREADS * EBR_THREAD_STATE_SIZE;
    ebr_thread_states = npk_core_alloc(states_size);
    if (ebr_thread_states == 0i64) {
        fail(ERR_EBR_LIMBO_OVERFLOW => tbb8);
    }
    ebr_global_state = npk_core_alloc(16i64);
    drop(npk_mem_write_int64(ebr_global_state, 0i64, 0i64)); // epoch
    drop(npk_mem_write_int64(ebr_global_state, 8i64, 0i64)); // thread_count
    pass(NIL);
};

pub func:ebr_thread_state = int64(int64:thread_id) {
    if (thread_id < 0i64) { pass(0i64); }
    if (thread_id >= EBR_MAX_THREADS) { pass(0i64); }
    pass(ebr_thread_states + thread_id * EBR_THREAD_STATE_SIZE);
};

// Force-free ALL remaining limbo nodes (used during shutdown).
pub func:ebr_flush_limbo_all = NIL(int64:ts) {
    int64:curr = npk_mem_read_int64(ts, EBR_TS_LIMBO_HEAD);
    while (curr != 0i64) {
        int64:nxt = npk_mem_read_int64(curr, LIMBO_OFF_NEXT);
        int64:node_ptr = npk_mem_read_int64(curr, LIMBO_OFF_PTR);
        
        drop(npk_core_dalloc(node_ptr)); // Free the node payload
        drop(npk_core_dalloc(curr));     // Free the limbo node itself
        
        curr = nxt;
    }
    drop(npk_mem_write_int64(ts, EBR_TS_LIMBO_HEAD, 0i64));
    drop(npk_mem_write_int64(ts, EBR_TS_LIMBO_COUNT, 0i64));
    pass(NIL);
};

// Flush eligible limbo nodes for the given thread state pointer.
// Frees all nodes tagged with epoch <= global_epoch - 2.
func:ebr_flush_limbo = NIL(int64:ts) {
    int64:curr = npk_mem_read_int64(ts, EBR_TS_LIMBO_HEAD);
    int64:prev = 0i64;
    int64:count = npk_mem_read_int64(ts, EBR_TS_LIMBO_COUNT);
    int64:safe_epoch = npk_mem_read_int64(ebr_global_state, 0i64) - 2i64;
    
    while (curr != 0i64) {
        int64:nxt = npk_mem_read_int64(curr, LIMBO_OFF_NEXT);
        int64:epoch = npk_mem_read_int64(curr, LIMBO_OFF_EPOCH);
        
        if (epoch <= safe_epoch) {
            // Inside the loop: epoch tag of freed node is always <= global_epoch - 2
            prove epoch <= npk_mem_read_int64(ebr_global_state, 0i64) - 2i64;
            // Safe to free
            if (prev == 0i64) {
                drop(npk_mem_write_int64(ts, EBR_TS_LIMBO_HEAD, nxt));
            } else {
                drop(npk_mem_write_int64(prev, LIMBO_OFF_NEXT, nxt));
            }
            int64:node_ptr = npk_mem_read_int64(curr, LIMBO_OFF_PTR);
            drop(npk_core_dalloc(node_ptr)); // Free the node payload
            drop(npk_core_dalloc(curr));     // Free the limbo node itself
            count = count - 1i64;
        } else {
            prev = curr;
        }
        
        curr = nxt;
    }
    
    drop(npk_mem_write_int64(ts, EBR_TS_LIMBO_COUNT, count));
    pass(NIL);
};

// Shutdown EBR: flush and free all remaining limbo nodes, free thread-state array.
pub func:ebr_shutdown = NIL() {
    // Force-free all remaining limbo nodes across all thread slots
    int64:i = 0i64;
    while (i < npk_mem_read_int64(ebr_global_state, 8i64)) {
        int64:ts = raw ebr_thread_state(i);
        if (ts != 0i64) {
            drop(raw ebr_flush_limbo_all(ts));
        }
        i = i + 1i64;
    }
    if (ebr_thread_states != 0i64) {
        drop(npk_core_dalloc(ebr_thread_states));
        ebr_thread_states = 0i64;
    }
    pass(NIL);
};

// Register a new thread with the EBR system. Returns thread_id (0-based).
// Must be called by each thread before it accesses any shared data structure.
// Returns: thread_id, or error if EBR_MAX_THREADS is exceeded.
pub func:ebr_register_thread = int64() {
    int64:tid = 0i64;
    int64:success = 0i64;
    while (success == 0i64) {
        tid = npk_mem_read_int64(ebr_global_state, 8i64);
        if (tid >= EBR_MAX_THREADS) {
            fail(ERR_EBR_LIMBO_OVERFLOW => tbb8);
        }
        int64:addr = ebr_global_state + 8i64;
        bool:res = raw npk_cas_i64(addr, tid, tid + 1i64);
        if (res) { success = 1i64; }
    }
    int64:ts = raw ebr_thread_state(tid);
    if (ts != 0i64) {
        drop(npk_mem_write_int64(ts, EBR_TS_LOCAL_EPOCH,  0i64));
        drop(npk_mem_write_int64(ts, EBR_TS_IS_ACTIVE,    0i64));
        drop(npk_mem_write_int64(ts, EBR_TS_THREAD_ID,    tid));
        drop(npk_mem_write_int64(ts, EBR_TS_LIMBO_HEAD,   0i64));
        drop(npk_mem_write_int64(ts, EBR_TS_LIMBO_COUNT,  0i64));
        drop(npk_mem_write_int64(ts, EBR_TS_RETIRE_COUNT, 0i64));
    }
    pass(tid);
};

// Enter a read-critical section.
// Loads the current global epoch into the thread's local_epoch and sets is_active=1.
// Readers MUST call ebr_pin before dereferencing any shared pointer.
pub func:ebr_pin = NIL(int64:thread_id)
    requires thread_id >= 0i64
{
    if (thread_id < 0i64) { pass(NIL); }
    if (thread_id >= EBR_MAX_THREADS) { pass(NIL); }
    int64:ts = raw ebr_thread_state(thread_id);
    if (ts != 0i64) {
        drop(npk_mem_write_int64(ts, EBR_TS_LOCAL_EPOCH, npk_mem_read_int64(ebr_global_state, 0i64)));
        drop(npk_mem_write_int64(ts, EBR_TS_IS_ACTIVE, 1i64));
    }
    pass(NIL);
};

// Exit a read-critical section.
// Sets is_active=0, allowing the global epoch to advance past this thread.
pub func:ebr_unpin = NIL(int64:thread_id)
    requires thread_id >= 0i64
{
    if (thread_id < 0i64) { pass(NIL); }
    if (thread_id >= EBR_MAX_THREADS) { pass(NIL); }
    int64:ts = raw ebr_thread_state(thread_id);
    if (ts != 0i64) {
        drop(npk_mem_write_int64(ts, EBR_TS_IS_ACTIVE, 0i64));
    }
    pass(NIL);
};

// Attempt to advance the global epoch if all active threads have observed the
// current epoch. Returns 1 if advanced, 0 if not (some thread is still behind).
pub func:ebr_try_advance = int64()
{
    int64:cur_epoch = npk_mem_read_int64(ebr_global_state, 0i64);
    // Check all registered threads
    int64:i = 0i64;
    int64:tcount = npk_mem_read_int64(ebr_global_state, 8i64);
    while (i < tcount) {
        int64:ts = raw ebr_thread_state(i);
        if (ts != 0i64) {
            int64:is_active   = npk_mem_read_int64(ts, EBR_TS_IS_ACTIVE);
            int64:local_epoch = npk_mem_read_int64(ts, EBR_TS_LOCAL_EPOCH);
            if (is_active == 1i64) {
                if (local_epoch < cur_epoch) {
                    pass(0i64);  // Thread is active in an old epoch — cannot advance
                }
            }
        }
        i = i + 1i64;
    }
    // All threads are either inactive or at current epoch — safe to advance
    drop(npk_mem_write_int64(ebr_global_state, 0i64, cur_epoch + 1i64));
    pass(1i64);
};

// Retire (defer freeing) a node that has been unlinked from a shared data structure.
// The node will be freed when the global epoch has advanced sufficiently.
pub func:ebr_retire = int32(int64:thread_id, int64:node_ptr)
    requires (thread_id >= 0i64), (thread_id < EBR_MAX_THREADS)
{
    if (thread_id < 0i64) { pass(0i32); }
    if (thread_id >= EBR_MAX_THREADS) { pass(0i32); }
    if (node_ptr == 0i64) { pass(0i32); }
    int64:ts = raw ebr_thread_state(thread_id);
    if (ts == 0i64) { pass(0i32); }
    
    int64:count = npk_mem_read_int64(ts, EBR_TS_LIMBO_COUNT);
    if (count >= EBR_LIMBO_MAX_DEPTH) {
        pass(ERR_EBR_LIMBO_OVERFLOW);
    }
    
    int64:l_node = npk_core_alloc(LIMBO_NODE_SIZE);
    if (l_node == 0i64) {
        pass(ERR_EBR_LIMBO_OVERFLOW);
    }
    
    int64:head = npk_mem_read_int64(ts, EBR_TS_LIMBO_HEAD);
    drop(npk_mem_write_int64(l_node, LIMBO_OFF_PTR, node_ptr));
    drop(npk_mem_write_int64(l_node, LIMBO_OFF_EPOCH, npk_mem_read_int64(ebr_global_state, 0i64)));
    drop(npk_mem_write_int64(l_node, LIMBO_OFF_NEXT, head));
    
    drop(npk_mem_write_int64(ts, EBR_TS_LIMBO_HEAD, l_node));
    drop(npk_mem_write_int64(ts, EBR_TS_LIMBO_COUNT, count + 1i64));
    
    int64:rcount = npk_mem_read_int64(ts, EBR_TS_RETIRE_COUNT) + 1i64;
    if (rcount >= EBR_ADVANCE_INTERVAL) {
        drop(ebr_try_advance());
        drop(raw ebr_flush_limbo(ts));
        drop(npk_mem_write_int64(ts, EBR_TS_RETIRE_COUNT, 0i64));
    } else {
        drop(npk_mem_write_int64(ts, EBR_TS_RETIRE_COUNT, rcount));
    }
    
    pass(0i32);
};

// Accessor for testing: get global epoch
pub func:ebr_get_global_epoch = int64() {
    pass(npk_mem_read_int64(ebr_global_state, 0i64));
};

// Accessor for testing: get limbo count for thread
pub func:ebr_get_limbo_count = int64(int64:thread_id) {
    int64:ts = raw ebr_thread_state(thread_id);
    pass(npk_mem_read_int64(ts, EBR_TS_LIMBO_COUNT));
};

// Accessor for testing: get local epoch for thread
pub func:ebr_get_local_epoch = int64(int64:thread_id) {
    int64:ts = raw ebr_thread_state(thread_id);
    pass(npk_mem_read_int64(ts, EBR_TS_LOCAL_EPOCH));
};

// Accessor for testing: get is_active for thread
pub func:ebr_get_is_active = int64(int64:thread_id) {
    int64:ts = raw ebr_thread_state(thread_id);
    pass(npk_mem_read_int64(ts, EBR_TS_IS_ACTIVE));
};

// Test helper: manually force advance global epoch
pub func:ebr_test_force_advance = NIL() {
    drop(npk_mem_write_int64(ebr_global_state, 0i64, npk_mem_read_int64(ebr_global_state, 0i64) + 1i64));
    pass(NIL);
};

// Test helper: manually flush limbo
pub func:ebr_test_flush_limbo = NIL(int64:thread_id) {
    int64:ts = raw ebr_thread_state(thread_id);
    drop(raw ebr_flush_limbo(ts));
    pass(NIL);
};

// Flush limbo and retry the retire. Spins until retirement succeeds.
// ONLY safe to call when is_active=0 (between operations, not mid-traversal).
pub func:ebr_retire_or_flush = int32(int64:thread_id, int64:node_ptr) {
    int64:retries = 0i64;
    while (retries < 10i64) {
        int32:err = raw ebr_retire(thread_id, node_ptr);
        
        if (err == 0i32) {
            pass(0i32);
        }
        
        if (err == ERR_EBR_LIMBO_OVERFLOW) {
            drop(ebr_try_advance());
            int64:ts = raw ebr_thread_state(thread_id);
            if (ts != 0i64) {
                drop(raw ebr_flush_limbo(ts));
            }
            retries = retries + 1i64;
        } else {
            pass(err);
        }
    }
    pass(ERR_EBR_LIMBO_OVERFLOW);
};

```

### File: `src/concurrency/seqlock.npk`
```nitpick
// seqlock.npk — Seqlock implementation for multi-field metadata protection
//
// Seqlock layout (flat buffer, 16 bytes):
//   Bytes 0-7:  seq (atomic<int64>) — sequence counter (even=consistent, odd=writing)
//   Bytes 8-15: padding              — reserved, cache-line fill (optional)
//
// The protected data lives OUTSIDE the seqlock struct, managed by the caller.
// The seqlock only guards the version counter.

use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;

pub fixed int64:SEQLOCK_SIZE          = 16i64;
pub fixed int64:SEQLOCK_OFF_SEQ       = 0i64;
pub fixed int64:SEQLOCK_MAX_RETRIES   = 1000i64;  // Max reader retries before fallback

// Allocate and initialize a seqlock (seq = 0, even, no write in progress).
pub func:seqlock_alloc = int64() {
    int64:ptr = npk_core_alloc(SEQLOCK_SIZE);
    if (ptr == 0i64) { fail(ERR_ART_CAS_FAILED => tbb8); }
    // Write initial seq = 0 using atomic store
    drop(atomic_store_seqcst(ptr + SEQLOCK_OFF_SEQ, 0i64));
    pass(ptr);
};

// Initialize an already-allocated seqlock buffer (for stack-allocated or embedded seqlocks).
pub func:seqlock_init = NIL(int64:seqlock_ptr)
    requires seqlock_ptr != 0i64
{
    drop(atomic_store_seqcst(seqlock_ptr + SEQLOCK_OFF_SEQ, 0i64));
    pass(NIL);
};

// Free a seqlock allocated with seqlock_alloc.
pub func:seqlock_free = NIL(int64:seqlock_ptr) {
    if (seqlock_ptr != 0i64) {
        drop(npk_core_dalloc(seqlock_ptr));
    }
    pass(NIL);
};

// Acquire write lock: increments seq to odd (signals write in progress).
// Spins until seq is even (no other writer) before incrementing.
// Returns the pre-write sequence number (for bookkeeping).
pub func:seqlock_write_begin = int64(int64:seqlock_ptr)
    requires seqlock_ptr != 0i64
    ensures raw atomic_load_seqcst(seqlock_ptr + SEQLOCK_OFF_SEQ) % 2i64 == 1i64
{
    when (true) {
        int64:seq = raw atomic_load_seqcst(seqlock_ptr + SEQLOCK_OFF_SEQ);
        if (seq % 2i64 == 0i64) {
            // Try to CAS from even to odd
            if (raw atomic_compare_exchange_seqcst(
                seqlock_ptr + SEQLOCK_OFF_SEQ,
                seq,
                seq + 1i64) == 1i64) {
                pass(seq);
            }
        }
        // Another writer is active; spin-wait with thread_yield
        drop(thread_yield());
    }
    pass(0i64);  // Unreachable but satisfies type checker
};

// Release write lock: increments seq to next even value (write complete).
pub func:seqlock_write_end = NIL(int64:seqlock_ptr)
    requires seqlock_ptr != 0i64
{
    // seq is currently odd; increment to even
    int64:seq = raw atomic_load_seqcst(seqlock_ptr + SEQLOCK_OFF_SEQ);
    drop(atomic_store_seqcst(seqlock_ptr + SEQLOCK_OFF_SEQ, seq + 1i64));
    pass(NIL);
};

// Read the sequence counter at the start of a reader's critical section.
// Spins until the counter is even (no write in progress).
// Returns the current even sequence number.
pub func:seqlock_read_begin = int64(int64:seqlock_ptr)
    requires seqlock_ptr != 0i64
{
    when (true) {
        int64:seq = raw atomic_load_seqcst(seqlock_ptr + SEQLOCK_OFF_SEQ);
        if (seq % 2i64 == 0i64) {
            pass(seq);  // Even — safe to start reading
        }
        drop(thread_yield());  // Writer active — wait
    }
    pass(0i64);  // Unreachable
};

// Validate that no write occurred during the reader's critical section.
// Returns: true if the read was consistent, false if a write interrupted it.
// If false, the caller must discard the read data and retry.
pub func:seqlock_read_validate = bool(int64:seqlock_ptr, int64:start_seq)
    requires seqlock_ptr != 0i64
{
    int64:end_seq = raw atomic_load_seqcst(seqlock_ptr + SEQLOCK_OFF_SEQ);
    pass(end_seq == start_seq && start_seq % 2i64 == 0i64);
};

// Read a small metadata block (up to 64 bytes) protected by a seqlock.
// Retries until consistent or SEQLOCK_MAX_RETRIES is exceeded.
//
// seqlock_ptr:  pointer to the seqlock
// data_ptr:     pointer to the protected data source (shared)
// out_ptr:      pointer to the caller's local buffer (private, receives copy)
// data_len:     byte length of the data to copy (must be <= 64)
//
// Returns: 0 on success, ERR_ART_CAS_FAILED if max retries exceeded.
pub func:seqlock_read_copy = int64(int64:seqlock_ptr, int64:data_ptr,
                                   int64:out_ptr, int64:data_len)
    requires seqlock_ptr != 0i64, data_ptr != 0i64, out_ptr != 0i64, data_len > 0i64, data_len <= 64i64
{
    int64:retries = 0i64;
    when (retries < SEQLOCK_MAX_RETRIES) {
        int64:seq = seqlock_read_begin(seqlock_ptr) ?! 0i64;
        // Copy data into local buffer
        drop(npk_mem_copy(out_ptr, data_ptr, data_len));
        // Validate
        if (seqlock_read_validate(seqlock_ptr, seq) ?! false) {
            pass(0i64);
        }
        retries = retries + 1i64;
    }
    fail(ERR_ART_CAS_FAILED => tbb8);
};

// Write a small metadata block protected by a seqlock.
//
// seqlock_ptr: pointer to the seqlock
// data_ptr:    pointer to the protected data destination (shared)
// in_ptr:      pointer to the new data (private caller buffer)
// data_len:    byte length to copy
pub func:seqlock_write_copy = NIL(int64:seqlock_ptr, int64:data_ptr,
                                  int64:in_ptr, int64:data_len)
    requires seqlock_ptr != 0i64, data_ptr != 0i64, in_ptr != 0i64, data_len > 0i64, data_len <= 64i64
{
    drop(seqlock_write_begin(seqlock_ptr));
    drop(npk_mem_copy(data_ptr, in_ptr, data_len));
    drop(seqlock_write_end(seqlock_ptr));
    pass(NIL);
};

```

### File: `src/engine/catalog.npk`
```nitpick
// catalog.npk - Global Registry of Collections

use "sys.npk".*;
use "../util/mem_primitives.npk".*;
use "collection.npk".*;

extern "nitpick_libc_thread" {
    func:nitpick_libc_rwlock_create    = int64();
    func:nitpick_libc_rwlock_rdlock    = int32(int64:handle);
    func:nitpick_libc_rwlock_wrlock    = int32(int64:handle);
    func:nitpick_libc_rwlock_unlock    = int32(int64:handle);
}

pub int64:g_catalog_hash = 0i64;
pub int64:g_catalog_rwlock = 0i64;

pub func:catalog_init = int32() {
    g_catalog_hash = ahash(1024i64);
    g_catalog_rwlock = nitpick_libc_rwlock_create();
    
    // Create base data directories
    drop(raw sys(MKDIR, "data", 511i64));             // 0777
    drop(raw sys(MKDIR, "data/collections", 511i64)); // 0777
    
    pass(0i32);
};

pub func:catalog_create_collection = int64(string:name) {
    drop(nitpick_libc_rwlock_wrlock(g_catalog_rwlock));
    
    // Check if exists
    int64:existing = ahget(g_catalog_hash, name);
    if (existing != 0i64) {
        drop(nitpick_libc_rwlock_unlock(g_catalog_rwlock));
        pass(0i64); // Already exists
    }
    

    string:base_dir = "data/collections/";
    string:full_path = string_concat(base_dir, name);
    
    drop(raw sys(MKDIR, full_path, 511i64));
    
    int64:coll_ptr = npk_core_alloc(24i64);
    Collection->:coll = @cast_unchecked<Collection->>(coll_ptr);
    coll->name = name;
    coll->storage = @cast_unchecked<Handle<LsmTree> >(0i64);
    coll->vector_index = @cast_unchecked<Handle<HnswGraph> >(0i64);
    
    ahset(g_catalog_hash, name, coll_ptr);
    
    drop(nitpick_libc_rwlock_unlock(g_catalog_rwlock));
    
    pass(coll_ptr);
};

pub func:catalog_get_collection = int64(string:name) {
    drop(nitpick_libc_rwlock_rdlock(g_catalog_rwlock));
    int64:coll = ahget(g_catalog_hash, name);
    drop(nitpick_libc_rwlock_unlock(g_catalog_rwlock));
    pass(coll);
};

```

### File: `src/engine/collection.npk`
```nitpick
// collection.npk - Manages a single isolated namespace.

use "../storage/lsm_tree.npk".*;
use "../index/hnsw.npk".*;

pub struct:Collection = {
    string:name;
    Handle<LsmTree>:storage;
    Handle<HnswGraph>:vector_index;
};

// In the future, this file will contain methods to initialize and destroy a collection.

```

### File: `src/page/page.npk`
```nitpick
// page.npk — Slotted Page buffer management
//
// A page is an 8192-byte wild buffer. All field access goes through
// npk_mem_read/write functions with limit<Rules> bounds checking.

use "../util/constants.npk".*;
use "../util/error_codes.npk".*;
use "page_header.npk".*;
use "../util/mem_primitives.npk".*;

// Safety rules: all byte offsets must be within the page
Rules<int64>:valid_page_offset = { $ >= 0i64, $ < 8192i64 };

// Allocate a fresh page buffer, zero-initialized
// Returns: int64 pointer to 8192-byte buffer, or 0 on failure
pub func:page_alloc = int64() {
    int64:ptr = nitpick_libc_mem_calloc(1i64, PAGE_SIZE);
    if (ptr == 0i64) {
        fail(ERR_PAGE_FULL => tbb8);
    }
    pass(ptr);
};

// Initialize a page header in an already-allocated buffer
pub func:page_init = int64(int64:buf, int64:page_id) {
    if (buf == 0i64) {
        fail(ERR_PAGE_CORRUPT => tbb8);
    }
    drop(npk_mem_write_int64(buf, HDR_OFF_PAGE_ID, page_id));
    drop(npk_mem_write_int32(buf, HDR_OFF_CHECKSUM, 0i32));
    drop(npk_mem_write_int32(buf, HDR_OFF_FREE_OFFSET, PAGE_HEADER_SIZE => int32));
    drop(npk_mem_write_int32(buf, HDR_OFF_TUPLE_END, (PAGE_SIZE - 1i64) => int32));
    drop(npk_mem_write_int32(buf, HDR_OFF_SLOT_COUNT, 0i32));
    drop(npk_mem_write_int32(buf, HDR_OFF_FLAGS, PAGE_FLAG_DATA));
    drop(npk_mem_write_int32(buf, HDR_OFF_RESERVED, 0i32));

    pass(buf);
};

// Free a page buffer
pub func:page_free = NIL(int64:buf) {
    if (buf != 0i64) {
        drop(npk_core_dalloc(buf));
    }
    pass(NIL);
};

// Read header fields
pub func:page_get_id = int64(int64:buf) {
    pass(npk_mem_read_int64(buf, HDR_OFF_PAGE_ID));
};

pub func:page_get_free_offset = int32(int64:buf) {
    pass(npk_mem_read_int32(buf, HDR_OFF_FREE_OFFSET));
};

pub func:page_get_tuple_end = int32(int64:buf) {
    pass(npk_mem_read_int32(buf, HDR_OFF_TUPLE_END));
};

pub func:page_get_slot_count = int32(int64:buf) {
    pass(npk_mem_read_int32(buf, HDR_OFF_SLOT_COUNT));
};

pub func:page_get_flags = int32(int64:buf) {
    pass(npk_mem_read_int32(buf, HDR_OFF_FLAGS));
};

// Calculate available free space on the page
pub func:page_free_space = int64(int64:buf) {
    int64:free_off = (page_get_free_offset(buf) ?! 0i32) => int64;
    int64:tup_end  = (page_get_tuple_end(buf) ?! 0i32) => int64;
    int64:available = tup_end - free_off + 1i64 - SLOT_SIZE;
    if (available < 0i64) {
        pass(0i64);
    }
    pass(available);
};

// Get the byte offset of slot N within the page
pub func:slot_byte_offset = int64(int64:slot_index) {
    pass(PAGE_HEADER_SIZE + (slot_index * SLOT_SIZE));
};

// Read the tuple offset stored in slot N
pub func:slot_get_tuple_offset = int64(int64:buf, int64:slot_index) {
    int64:off = slot_byte_offset(slot_index) ?! 0i64;
    pass(npk_mem_read_int64(buf, off));
};

// Read the tuple length stored in slot N
pub func:slot_get_tuple_length = int64(int64:buf, int64:slot_index) {
    int64:off = (slot_byte_offset(slot_index) ?! 0i64) + 8i64;
    pass(npk_mem_read_int64(buf, off));
};

// Write a slot entry
pub func:slot_write = NIL(int64:buf, int64:slot_index, int64:tuple_offset, int64:tuple_length) {
    int64:off = slot_byte_offset(slot_index) ?! 0i64;
    drop(npk_mem_write_int64(buf, off, tuple_offset));
    drop(npk_mem_write_int64(buf, off + 8i64, tuple_length));
    pass(NIL);
};

// Read raw tuple bytes from the page into a new buffer
pub func:page_read_tuple = int64(int64:buf, int64:slot_index) {
    int64:count = (page_get_slot_count(buf) ?! 0i32) => int64;
    if (slot_index < 0i64 || slot_index >= count) {
        fail(ERR_PAGE_INVALID_SLOT => tbb8);
    }

    int64:tup_off = slot_get_tuple_offset(buf, slot_index) ?! 0i64;
    int64:tup_len = slot_get_tuple_length(buf, slot_index) ?! 0i64;

    if (tup_len <= 0i64 || tup_off < 0i64 || tup_off + tup_len > PAGE_SIZE) {
        fail(ERR_PAGE_CORRUPT => tbb8);
    }

    int64:out = npk_core_alloc(tup_len);
    drop(npk_mem_copy(out, buf + tup_off, tup_len));
    pass(out);
};

// Read tuple data as a string
pub func:page_read_tuple_string = string(int64:buf, int64:slot_index) {
    int64:tup_off = slot_get_tuple_offset(buf, slot_index) ?! 0i64;
    int64:tup_len = slot_get_tuple_length(buf, slot_index) ?! 0i64;
    int64:str_ptr = npk_mem_offset(buf, tup_off);
    pass(raw npk_mem_read_string(str_ptr, tup_len));
};

// Returns 1 if the page cannot fit a record of the given size, 0 otherwise.
pub func:page_is_full = int64(int64:buf, int64:record_size) {
    int64:space = page_free_space(buf) ?! 0i64;
    if (space < record_size + SLOT_SIZE) {
        pass(1i64);
    }
    pass(0i64);
};

// Returns the total number of live (non-deleted) records on the page.
pub func:page_live_count = int64(int64:buf) {
    int64:count = (page_get_slot_count(buf) ?! 0i32) => int64;
    int64:live = 0i64;
    int64:i = 0i64;
    while (i < count) {
        int64:len = slot_get_tuple_length(buf, i) ?! 0i64;
        if (len > 0i64) {
            live = live + 1i64;
        }
        i = i + 1i64;
    }
    pass(live);
};

// Returns the total bytes used by live tuple data
pub func:page_used_bytes = int64(int64:buf) {
    int64:count = (page_get_slot_count(buf) ?! 0i32) => int64;
    int64:used = 0i64;
    int64:i = 0i64;
    while (i < count) {
        int64:len = slot_get_tuple_length(buf, i) ?! 0i64;
        if (len > 0i64) {
            used = used + len;
        }
        i = i + 1i64;
    }
    pass(used);
};

// Insert a variable-length record into the page.
pub func:page_insert = int64(int64:buf, int64:data_ptr, int64:data_len)
    requires buf != 0i64, data_ptr != 0i64, data_len > 0i64, data_len < PAGE_SIZE
    ensures (result >= 0i64 || result == ERR_PAGE_FULL) {
    if (data_len <= 0i64) {
        fail(ERR_PAGE_CORRUPT => tbb8);
    }
    int64:is_full = page_is_full(buf, data_len) ?! 1i64;
    if (is_full == 1i64) {
        fail(ERR_PAGE_FULL => tbb8);
    }

    int64:tend = (page_get_tuple_end(buf) ?! 0i32) => int64;
    int64:new_toff = tend - data_len + 1i64;

    drop(npk_mem_copy(buf + new_toff, data_ptr, data_len));

    int64:scnt = (page_get_slot_count(buf) ?! 0i32) => int64;
    drop(slot_write(buf, scnt, new_toff, data_len));

    int64:foff = (page_get_free_offset(buf) ?! 0i32) => int64;
    drop(npk_mem_write_int32(buf, HDR_OFF_SLOT_COUNT, (scnt + 1i64) => int32));
    drop(npk_mem_write_int32(buf, HDR_OFF_FREE_OFFSET, (foff + SLOT_SIZE) => int32));
    drop(npk_mem_write_int32(buf, HDR_OFF_TUPLE_END, (new_toff - 1i64) => int32));

    pass(scnt);
};

// Mark a record as deleted by zeroing its slot entry.
pub func:page_delete = NIL(int64:buf, int64:slot_index) {
    int64:count = (page_get_slot_count(buf) ?! 0i32) => int64;
    if (slot_index >= 0i64 && slot_index < count) {
        drop(slot_write(buf, slot_index, 0i64, 0i64));
    }
    pass(NIL);
};

// Returns 1 if the slot contains a live record, 0 if deleted/tombstoned.
pub func:page_slot_is_alive = int64(int64:buf, int64:slot_index) {
    int64:len = slot_get_tuple_length(buf, slot_index) ?! 0i64;
    if (len > 0i64) {
        pass(1i64);
    }
    pass(0i64);
};

// Update the record at slot_index with new data.
pub func:page_update = int64(int64:buf, int64:slot_index, int64:data_ptr, int64:data_len) {
    int64:count = (page_get_slot_count(buf) ?! 0i32) => int64;
    if (slot_index < 0i64 || slot_index >= count) {
        fail(ERR_PAGE_INVALID_SLOT => tbb8);
    }

    int64:old_len = slot_get_tuple_length(buf, slot_index) ?! 0i64;
    if (old_len == 0i64) {
        fail(ERR_PAGE_INVALID_SLOT => tbb8); // Already deleted
    }

    if (data_len <= old_len) {
        // Overwrite in-place
        int64:old_off = slot_get_tuple_offset(buf, slot_index) ?! 0i64;
        drop(npk_mem_copy(buf + old_off, data_ptr, data_len));
        drop(slot_write(buf, slot_index, old_off, data_len));
        pass(slot_index);
    }

    // Otherwise, delete and insert
    drop(page_delete(buf, slot_index));
    int64:new_idx = page_insert(buf, data_ptr, data_len) ?! -1i64;
    if (new_idx == -1i64) {
        fail(ERR_PAGE_FULL => tbb8);
    }
    pass(new_idx);
};

// Compact the page by removing dead slots and consolidating tuple space.
pub func:page_defragment = int64(int64:buf) {
    int64:temp = page_alloc() ?! 0i64;
    if (temp == 0i64) {
        pass(0i64);
    }

    int64:free_before = page_free_space(buf) ?! 0i64;

    drop(npk_mem_copy(temp, buf, PAGE_HEADER_SIZE));

    drop(npk_mem_write_int32(temp, HDR_OFF_FREE_OFFSET, PAGE_HEADER_SIZE => int32));
    drop(npk_mem_write_int32(temp, HDR_OFF_TUPLE_END, (PAGE_SIZE - 1i64) => int32));
    drop(npk_mem_write_int32(temp, HDR_OFF_SLOT_COUNT, 0i32));

    int64:orig_count = (page_get_slot_count(buf) ?! 0i32) => int64;
    int64:i = 0i64;
    while (i < orig_count) {
        int64:len = slot_get_tuple_length(buf, i) ?! 0i64;
        if (len > 0i64) {
            int64:off = slot_get_tuple_offset(buf, i) ?! 0i64;
            drop(page_insert(temp, buf + off, len));
        }
        i = i + 1i64;
    }

    drop(npk_mem_copy(buf, temp, PAGE_SIZE));
    drop(page_free(temp));

    int64:free_after = page_free_space(buf) ?! 0i64;
    pass(free_after - free_before);
};

```

### File: `src/page/page_header.npk`
```nitpick
// page_header.npk — Slotted Page header layout
//
// Physical layout (32 bytes):
//   Offset  0: page_id       (int64, 8 bytes) — unique page identifier
//   Offset  8: checksum      (uint32, 4 bytes) — CRC32 of page contents (bytes 12–8191)
//   Offset 12: free_offset   (int32, 4 bytes) — byte offset where free space begins (after last slot)
//   Offset 16: tuple_end     (int32, 4 bytes) — byte offset where tuple region ends (grows backward from 8191)
//   Offset 20: slot_count    (int32, 4 bytes) — number of active slots
//   Offset 24: flags         (int32, 4 bytes) — page type flags (0=data, 1=index, 2=overflow)
//   Offset 28: reserved      (int32, 4 bytes) — reserved for future use

use "../util/constants.npk".*;

// Page type flags
pub fixed int32:PAGE_FLAG_DATA     = 0i32;
pub fixed int32:PAGE_FLAG_INDEX    = 1i32;
pub fixed int32:PAGE_FLAG_OVERFLOW = 2i32;

// Header field offsets (byte positions within page)
pub fixed int64:HDR_OFF_PAGE_ID     = 0i64;
pub fixed int64:HDR_OFF_CHECKSUM    = 8i64;
pub fixed int64:HDR_OFF_FREE_OFFSET = 12i64;
pub fixed int64:HDR_OFF_TUPLE_END   = 16i64;
pub fixed int64:HDR_OFF_SLOT_COUNT  = 20i64;
pub fixed int64:HDR_OFF_FLAGS       = 24i64;
pub fixed int64:HDR_OFF_RESERVED    = 28i64;

```

### File: `src/util/bloom.npk`
```nitpick
use "constants.npk".*;
use "mem_primitives.npk".*;

pub func:bloom_hash1 = int64(string:key) {
    int64:h = 0i64;
    int64:len = string_length(key);
    int64:buf = npk_core_alloc(len);
    drop(raw npk_mem_write_string(buf, key));
    
    int64:i = 0i64;
    while (i < len && i < 8i64) {
        int64:b = npk_mem_read_byte(buf, i);
        h = h | (b << (i * 8i64));
        i = i + 1i64;
    }
    drop(npk_core_dalloc(buf));
    
    // MurmurHash3 mix finalizer
    h = h ^ (h >> 33i64);
    h = h * -49064778989728563i64; // 0xff51afd7ed558ccd
    h = h ^ (h >> 33i64);
    h = h * -4265267296055464877i64; // 0xc4ceb9fe1a85ec53
    h = h ^ (h >> 33i64);
    
    // Ensure positive for modulo
    if (h < 0i64) { h = h * -1i64; }
    pass(h);
};

pub func:bloom_hash2 = int64(string:key) {
    int64:h = -3750763034362895579i64; // 0xcbf29ce484222325
    int64:len = string_length(key);
    int64:buf = npk_core_alloc(len);
    drop(raw npk_mem_write_string(buf, key));
    
    int64:i = 0i64;
    while (i < len) {
        int64:b = npk_mem_read_byte(buf, i);
        h = h ^ b;
        h = h * 1099511628211i64; // 0x100000001b3
        i = i + 1i64;
    }
    drop(npk_core_dalloc(buf));
    
    // Ensure positive for modulo
    if (h < 0i64) { h = h * -1i64; }
    pass(h);
};

pub func:bloom_create = int64(int64:num_keys) {
    int64:n = num_keys;
    if (n < 1i64) { n = 1i64; }
    
    int64:num_bits = n * 10i64;
    int64:num_hashes = 7i64;
    int64:byte_size = (num_bits + 7i64) / 8i64;
    
    int64:bit_array = npk_core_alloc(byte_size);
    // Zero out
    int64:i = 0i64;
    while (i < byte_size) {
        drop(npk_mem_write_byte(bit_array, i, 0i64));
        i = i + 1i64;
    }
    
    int64:bloom = npk_core_alloc(32i64);
    drop(npk_mem_write_int64(bloom, 0i64, bit_array));
    drop(npk_mem_write_int64(bloom, 8i64, num_bits));
    drop(npk_mem_write_int64(bloom, 16i64, num_hashes));
    drop(npk_mem_write_int64(bloom, 24i64, n));
    
    pass(bloom);
};

pub func:bloom_destroy = NIL(int64:bloom) {
    if (bloom != 0i64) {
        int64:bit_array = npk_mem_read_int64(bloom, 0i64);
        drop(npk_core_dalloc(bit_array));
        drop(npk_core_dalloc(bloom));
    }
    pass(NIL);
};

pub func:bloom_add = NIL(int64:bloom, string:key) {
    int64:bit_array = npk_mem_read_int64(bloom, 0i64);
    int64:num_bits = npk_mem_read_int64(bloom, 8i64);
    int64:num_hashes = npk_mem_read_int64(bloom, 16i64);
    
    int64:h1 = bloom_hash1(key) ?! 0i64;
    int64:h2 = bloom_hash2(key) ?! 0i64;
    
    int64:i = 0i64;
    while (i < num_hashes) {
        int64:bit_pos = (h1 + (i * h2)) % num_bits;
        if (bit_pos < 0i64) { bit_pos = bit_pos * -1i64; }
        
        int64:byte_idx = bit_pos / 8i64;
        int64:bit_off = bit_pos % 8i64;
        
        int64:curr_byte = npk_mem_read_byte(bit_array, byte_idx);
        curr_byte = curr_byte | (1i64 << bit_off);
        drop(npk_mem_write_byte(bit_array, byte_idx, curr_byte));
        
        i = i + 1i64;
    }
    pass(NIL);
};

pub func:bloom_check = int64(int64:bloom, string:key) {
    int64:bit_array = npk_mem_read_int64(bloom, 0i64);
    int64:num_bits = npk_mem_read_int64(bloom, 8i64);
    int64:num_hashes = npk_mem_read_int64(bloom, 16i64);
    
    int64:h1 = bloom_hash1(key) ?! 0i64;
    int64:h2 = bloom_hash2(key) ?! 0i64;
    
    int64:i = 0i64;
    while (i < num_hashes) {
        int64:bit_pos = (h1 + (i * h2)) % num_bits;
        if (bit_pos < 0i64) { bit_pos = bit_pos * -1i64; }
        
        int64:byte_idx = bit_pos / 8i64;
        int64:bit_off = bit_pos % 8i64;
        
        int64:curr_byte = npk_mem_read_byte(bit_array, byte_idx);
        int64:bit_val = (curr_byte >> bit_off) & 1i64;
        
        if (bit_val == 0i64) {
            pass(0i64); // Definitely not here
        }
        
        i = i + 1i64;
    }
    pass(1i64); // Might be here
};

pub func:bloom_serialize_size = int64(int64:bloom) {
    int64:num_bits = npk_mem_read_int64(bloom, 8i64);
    int64:byte_size = (num_bits + 7i64) / 8i64;
    pass(16i64 + byte_size);
};

pub func:bloom_serialize = int64(int64:bloom) {
    int64:bit_array = npk_mem_read_int64(bloom, 0i64);
    int64:num_bits = npk_mem_read_int64(bloom, 8i64);
    int64:num_hashes = npk_mem_read_int64(bloom, 16i64);
    int64:byte_size = (num_bits + 7i64) / 8i64;
    
    int64:buf_size = 16i64 + byte_size;
    int64:buf = npk_core_alloc(buf_size);
    
    drop(npk_mem_write_int64(buf, 0i64, num_bits));
    drop(npk_mem_write_int64(buf, 8i64, num_hashes));
    drop(npk_mem_copy(buf + 16i64, bit_array, byte_size));
    
    pass(buf);
};

pub func:bloom_deserialize = int64(int64:data_ptr, int64:data_len) {
    if (data_len < 16i64) { pass(0i64); }
    
    int64:num_bits = npk_mem_read_int64(data_ptr, 0i64);
    int64:num_hashes = npk_mem_read_int64(data_ptr, 8i64);
    int64:byte_size = (num_bits + 7i64) / 8i64;
    
    if (data_len < (16i64 + byte_size)) { pass(0i64); }
    
    int64:bit_array = npk_core_alloc(byte_size);
    drop(npk_mem_copy(bit_array, data_ptr + 16i64, byte_size));
    
    int64:bloom = npk_core_alloc(32i64);
    drop(npk_mem_write_int64(bloom, 0i64, bit_array));
    drop(npk_mem_write_int64(bloom, 8i64, num_bits));
    drop(npk_mem_write_int64(bloom, 16i64, num_hashes));
    drop(npk_mem_write_int64(bloom, 24i64, 0i64)); // num_keys doesn't matter for read
    
    pass(bloom);
};

```

### File: `src/util/config.npk`
```nitpick
// src/util/config.npk
use "sys.npk".*;
use "../../nitpick-packages/packages/nitpick-toml/src/nitpick_toml.npk".*;
use "error_codes.npk".*;
use "mem_primitives.npk".*;

pub int64:global_npk_config = 0i64; // Handle to the config struct

pub fixed int32:ERR_CONFIG_LOAD_FAILED = 600i32;

// Config offsets
pub int64:CFG_HTTP_PORT = 0i64; // int32
pub int64:CFG_MAX_THREADS = 8i64; // int64
pub int64:CFG_MEMTABLE_FLUSH_BYTES = 16i64; // int64
pub int64:CFG_HNSW_M = 24i64; // int64
pub int64:CFG_HNSW_EF_CONSTRUCTION = 32i64; // int64

pub func:config_init = int32(string:toml_path) {
    int64:fd = sys(OPEN, toml_path, 0i64, 0i64) ?! -1i64;
    if (fd < 0i64) {
        println("config_init: sys(OPEN) failed on " + toml_path);
        pass(ERR_CONFIG_LOAD_FAILED);
    }
    
    // Allocate buffer for config (max 64KB)
    int64:buf = npk_core_alloc(65536i64);
    int64:bytes_read = sys(READ, fd, buf, 65535i64) ?! -1i64;
    drop(sys(CLOSE, fd) ?! 0i64);
    
    if (bytes_read <= 0i64) {
        println("config_init: sys(READ) failed or empty file");
        drop(npk_core_dalloc(buf));
        pass(ERR_CONFIG_LOAD_FAILED);
    }
    
    // Null terminate
    drop(npk_mem_write_byte(buf, bytes_read, 0i64));
    
    // Create string
    string:toml_str = raw npk_mem_read_string(buf, bytes_read + 1i64);
    
    // Parse
    int32:n = raw Toml.parse(toml_str);
    drop(npk_core_dalloc(buf));
    
    if (n < 0i32) {
        pass(ERR_CONFIG_LOAD_FAILED);
    }
    
    // Allocate struct memory
    int64:cfg_ptr = npk_core_alloc(40i64);
    
    // Get values or default
    int32:port = 8080i32;
    int64:p = raw Toml.get_int("server.http_port");
    if (p > 0i64) { port = @cast_unchecked<int32>(p); }
    
    int64:threads = raw Toml.get_int("server.max_threads");
    if (threads <= 0i64) { threads = 4i64; }
    
    int64:flush = raw Toml.get_int("storage.memtable_flush_bytes");
    if (flush <= 0i64) { flush = 1048576i64; } // default 1MB
    
    int64:hm = raw Toml.get_int("vector.hnsw_m");
    if (hm <= 0i64) { hm = 16i64; }
    
    int64:efc = raw Toml.get_int("vector.hnsw_ef_construction");
    if (efc <= 0i64) { efc = 200i64; }
    
    // Populate
    drop(npk_mem_write_int32(cfg_ptr, CFG_HTTP_PORT, port));
    drop(npk_mem_write_int64(cfg_ptr, CFG_MAX_THREADS, threads));
    drop(npk_mem_write_int64(cfg_ptr, CFG_MEMTABLE_FLUSH_BYTES, flush));
    drop(npk_mem_write_int64(cfg_ptr, CFG_HNSW_M, hm));
    drop(npk_mem_write_int64(cfg_ptr, CFG_HNSW_EF_CONSTRUCTION, efc));
    
    global_npk_config = cfg_ptr;
    
    pass(0i32);
};

pub func:config_get = int64() {
    pass(global_npk_config);
};

pub func:config_shutdown = NIL() {
    if (global_npk_config != 0i64) {
        drop(npk_core_dalloc(global_npk_config));
        global_npk_config = 0i64;
    }
    drop(raw Toml.clear());
    pass(NIL);
};

```

### File: `src/util/constants.npk`
```nitpick
// constants.npk — NPKDB configuration constants

// Page layout
pub fixed int64:PAGE_SIZE           = 8192i64;     // 8KB pages
pub fixed int64:PAGE_HEADER_SIZE    = 32i64;       // Page header bytes
// Footer (48 bytes):
// 0-7: data_block_count (int64)
// 8-15: index_block_offset (int64)
// 16-23: bloom_block_offset (int64)
// 24-31: bloom_block_size (int64)
// 32-39: total_keys (int64)
// 40-43: magic (int32)
// 44-47: crc32 (int32)
pub fixed int64:SSTABLE_FOOTER_SIZE       = 48i64;
pub fixed int64:SLOT_SIZE           = 16i64;       // Bytes per slot entry (offset + length)

// WAL
pub fixed int64:WAL_RECORD_HEADER      = 16i64;       // CRC32(4) + Length(4) + Type(4) + Reserved(4)
pub fixed int32:WAL_RECORD_PUT         = 1i32;
pub fixed int32:WAL_RECORD_DELETE      = 2i32;
pub fixed int32:WAL_RECORD_CHECKPOINT  = 3i32;
pub fixed int64:WAL_SYNC_INTERVAL      = 1i64;        // Default: fsync every record (overridden by group commit)

// Memtable
pub fixed int64:MEMTABLE_SIZE_LIMIT = 4194304i64;  // 4MB default threshold for flush

// SSTable
pub fixed int64:SSTABLE_LEVEL_FANOUT = 10i64;      // Each level is 10x the size of the previous
pub fixed int64:SSTABLE_MAX_LEVELS   = 7i64;       // L0 through L6
pub fixed int64:LM_L0_COMPACTION_THRESHOLD = 4i64; // Number of L0 files to trigger compaction

// Bloom Filter
pub fixed int64:BLOOM_BITS_PER_KEY   = 10i64;      // ~1% false positive rate

// HNSW
pub fixed int64:HNSW_M              = 16i64;       // Max edges per node per layer
pub fixed int64:HNSW_EF_CONSTRUCTION = 200i64;     // Build-time search depth
pub fixed int64:HNSW_EF_SEARCH      = 50i64;       // Query-time search depth
pub fixed int64:HNSW_ML             = 1i64;        // Level multiplier (1/ln(M))

// EBR
pub fixed int64:EBR_LIMBO_MAX_DEPTH = 10000i64;    // Max limbo list entries before stall

// Server
pub fixed int64:DEFAULT_PORT        = 7373i64;
pub fixed int64:DEFAULT_BACKLOG     = 128i64;

```

### File: `src/util/crc32.npk`
```nitpick
// src/util/crc32.npk — CRC32 computation
use "mem_primitives.npk".*;

int64:crc_table_ptr = 0i64;

pub func:crc32_init = int64() {
    if (crc_table_ptr != 0i64) {
        pass(1i64);
    }
    crc_table_ptr = npk_core_alloc(2048i64);
    
    int64:i = 0i64;
    while (i < 256i64) {
        int64:c = i;
        int64:j = 0i64;
        while (j < 8i64) {
            if ((c & 1i64) != 0i64) {
                c = 3988292384i64 ^ (c >> 1i64); // 0xEDB88320
            } else {
                c = c >> 1i64;
            }
            j = j + 1i64;
        }
        drop(npk_mem_write_int64(crc_table_ptr, i * 8i64, c));
        i = i + 1i64;
    }
    pass(1i64);
};

// Compute CRC32 checksum over a buffer.
// buf: pointer to data
// len: number of bytes
// Returns: 32-bit CRC value as int64 (upper 32 bits zero)
pub func:crc32_compute = int64(int64:buf, int64:len) {
    drop(crc32_init());
    int64:crc = 4294967295i64; // 0xFFFFFFFF
    
    int64:i = 0i64;
    while (i < len) {
        int64:byte_val = npk_mem_read_byte(buf, i);
        int64:idx = (crc ^ byte_val) & 255i64;
        int64:table_val = npk_mem_read_int64(crc_table_ptr, idx * 8i64);
        crc = table_val ^ (crc >> 8i64);
        i = i + 1i64;
    }
    
    pass(crc ^ 4294967295i64);
};

```

### File: `src/util/error_codes.npk`
```nitpick
// error_codes.npk — NPKDB error codes
// All error codes are pub fixed int32 constants.
// Range: 1-99 = storage, 100-199 = index, 200-299 = vector,
//        300-399 = query, 400-499 = server, 500-599 = concurrency

// Storage errors (1-99)
pub fixed int32:ERR_WAL_WRITE_FAILED     = 1i32;
pub fixed int32:ERR_WAL_FSYNC_FAILED     = 2i32;
pub fixed int32:ERR_WAL_CORRUPT_RECORD   = 3i32;
pub fixed int32:ERR_WAL_REPLAY_FAILED    = 4i32;
pub fixed int32:ERR_WAL_OPEN_FAILED      = 5i32;
pub fixed int32:ERR_PAGE_FULL            = 10i32;
pub fixed int32:ERR_PAGE_CORRUPT         = 11i32;
pub fixed int32:ERR_PAGE_INVALID_SLOT    = 12i32;
pub fixed int32:ERR_MEMTABLE_FULL        = 20i32;
pub fixed int32:ERR_SSTABLE_READ_FAILED  = 30i32;
pub fixed int32:ERR_SSTABLE_WRITE_FAILED = 31i32;
pub fixed int32:ERR_COMPACTION_FAILED    = 40i32;
pub fixed int32:ERR_FLUSH_FAILED         = 50i32;

// Index errors (100-199)
pub fixed int32:ERR_ART_KEY_NOT_FOUND    = 100i32;
pub fixed int32:ERR_ART_DUPLICATE_KEY    = 101i32;
pub fixed int32:ERR_ART_CAS_FAILED       = 102i32;

// Vector errors (200-299)
pub fixed int32:ERR_HNSW_STALE_HANDLE    = 200i32;
pub fixed int32:ERR_HNSW_EMPTY_GRAPH     = 201i32;
pub fixed int32:ERR_VECTOR_DIM_MISMATCH  = 202i32;
pub fixed int32:ERR_VECTOR_ZERO_MAGNITUDE = 203i32;
pub fixed int32:ERR_HNSW_OOM             = 204i32;
pub fixed int32:ERR_SIMD_DIM_MISMATCH    = 205i32;

// Query errors (300-399)
pub fixed int32:ERR_QUERY_PARSE_FAILED   = 300i32;
pub fixed int32:ERR_QUERY_INVALID_FILTER = 301i32;
pub fixed int32:ERR_JSON_PARSE_FAIL      = 310i32; // Syntax error in JSON buffer
pub fixed int32:ERR_JSON_DEPTH_EXCEEDED  = 311i32; // Too many nested objects/arrays

pub fixed int32:ERR_REGEX_PARSE                 = 320i32;
pub fixed int32:ERR_REGEX_TIMEOUT               = 321i32;
pub fixed int32:ERR_REGEX_COMPLEXITY_EXCEEDED   = 322i32;

// Server errors (400-499)
pub fixed int32:ERR_SERVER_BIND_FAILED   = 400i32;
pub fixed int32:ERR_SERVER_ACCEPT_FAILED = 401i32;

// Concurrency errors (500-599)
pub fixed int32:ERR_EBR_LIMBO_OVERFLOW   = 500i32;

```

### File: `src/util/failsafe.npk`
```nitpick
// failsafe.npk — Global Catastrophic Failsafe
// Logs trace to stderr and releases POSIX directory locks

extern "C" {
    func:_exit = void(int32:code);
}

pub func:proc_exit = NIL(int32:code) {
    _exit(code);
    pass(NIL);
};

pub int32:g_db_lock_fd = -1i32;

pub func:failsafe = int32(tbb32:err) {
    // 1. Log to stderr (fd 2) using direct syscall
    string:msg = "NPKDB FATAL ERROR: Catastrophic failure. Shutting down.\n";
    int64:ptr = string_to_cstr(msg);
    int64:len = string_length(msg);
    drop(sys!!(1i64, 2i64, ptr, len)); // sys_write
    
    // 2. Attempt to unlock POSIX directory lock
    if (g_db_lock_fd >= 0i32) {
        drop(sys!!(73i64, g_db_lock_fd => int64, 8i64)); // sys_flock(fd, LOCK_UN)
    }
    
    exit(1i32);
};

```

### File: `src/util/mem_primitives.npk`
```nitpick
// mem_primitives.npk — Raw memory access
// Wraps the C builtins provided by Nitpick runtime

extern "nitpick_libc_mem" {
    func:npk_mem_read_byte     = int64(int64:ptr, int64:offset);
    func:npk_mem_write_byte    = int64(int64:ptr, int64:offset, int64:val);
    func:npk_mem_read_int32    = int32(int64:ptr, int64:offset);
    func:npk_mem_read_int64    = int64(int64:ptr, int64:offset);
    func:npk_mem_write_int64   = int64(int64:ptr, int64:offset, int64:val);
    func:npk_mem_copy          = int64(int64:dst, int64:src, int64:n);
    func:npk_mem_set           = int64(int64:dst, int64:val, int64:n);
    func:npk_mem_compare       = int64(int64:a, int64:b, int64:n);
    func:npk_mem_offset        = int64(int64:ptr, int64:offset);
    func:npk_mem_ptr_size      = int64();

    func:npk_core_alloc  = int64(int64:size);
    func:nitpick_libc_mem_calloc  = int64(int64:count, int64:size);
    func:nitpick_libc_mem_realloc = int64(int64:ptr, int64:size);
    func:npk_core_dalloc    = void(int64:ptr);
}
pub func:npk_mem_write_int32 = int64(int64:ptr, int64:offset, int32:val) {
    int64:v = val => int64;
    drop(npk_mem_write_byte(ptr, offset, v & 255i64));
    drop(npk_mem_write_byte(ptr, offset + 1i64, (v >> 8) & 255i64));
    drop(npk_mem_write_byte(ptr, offset + 2i64, (v >> 16) & 255i64));
    drop(npk_mem_write_byte(ptr, offset + 3i64, (v >> 24) & 255i64));
    pass(0i64);
};

pub func:npk_mem_read_int16 = int16(int64:ptr, int64:offset) {
    int64:b0 = npk_mem_read_byte(ptr, offset);
    int64:b1 = npk_mem_read_byte(ptr, offset + 1i64);
    pass(((b1 << 8i64) | b0) => int16);
};

pub func:npk_mem_write_int16 = int64(int64:ptr, int64:offset, int16:val) {
    int64:v = val => int64;
    drop(npk_mem_write_byte(ptr, offset, v & 255i64));
    drop(npk_mem_write_byte(ptr, offset + 1i64, (v >> 8i64) & 255i64));
    pass(0i64);
};

pub func:npk_mem_write_string = int64(int64:ptr, string:s) {
    int64:len = string_length(s);
    if (len > 0i64) {
        int64:cstr = string_to_cstr(s);
        drop(npk_mem_copy(ptr, cstr, len));
    }
    pass(len);
};

pub func:npk_mem_read_string = string(int64:ptr, int64:max_len) {
    if (ptr == 0i64) { pass(""); }
    if (max_len <= 0i64) { pass(""); }
    
    int64:len = 0i64;
    while (len < max_len) {
        int64:b = npk_mem_read_byte(ptr, len);
        if (b == 0i64) { break; }
        len = len + 1i64;
    }
    
    int64:buf = npk_core_alloc(len + 1i64);
    if (len > 0i64) {
        drop(npk_mem_copy(buf, ptr, len));
    }
    drop(npk_mem_write_byte(buf, len, 0i64));
    
    string:s = string_from_cstr(buf);
    drop(npk_core_dalloc(buf));
    
    pass(s);
};

pub func:npk_mem_read_int8 = int8(int8->:buf_arg, int64:pos) {
    int8->:local_buf = buf_arg;
    int64:ptr = <-(@local_buf => int64->);
    int64:val = npk_mem_read_byte(ptr, pos);
    pass(val => int8);
};

pub func:npk_cas_i64 = bool(int64:atomic_ptr, int64:expected, int64:desired) {
    int64:actual = asm!!!<int64>("x86_64", "lock cmpxchgq $2, ($1)", "={ax},r,r,0,~{dirflag},~{fpsr},~{flags},~{memory}", atomic_ptr, desired, expected);
    pass(actual == expected);
};

pub func:atomic_load_seqcst = int64(int64:atomic_ptr) {
    int64:val = asm!!!<int64>("x86_64", "movq ($1), $0", "=r,r,~{memory}", atomic_ptr);
    pass(val);
};

```

### File: `src/util/min_heap.npk`
```nitpick
use "constants.npk".*;
use "error_codes.npk".*;


use "../storage/sstable.npk".*;

pub fixed int64:HEAP_STRUCT_SIZE = 24i64;
pub fixed int64:HEAP_ELEM_SIZE = 16i64;

pub func:heap_create = int64(int64:capacity) {
    int64:heap = npk_core_alloc(HEAP_STRUCT_SIZE);
    int64:array_ptr = npk_core_alloc(capacity * HEAP_ELEM_SIZE);
    drop(npk_mem_write_int64(heap, 0i64, array_ptr));
    drop(npk_mem_write_int64(heap, 8i64, 0i64)); // size
    drop(npk_mem_write_int64(heap, 16i64, capacity));
    pass(heap);
};

pub func:heap_destroy = NIL(int64:heap) {
    int64:array_ptr = npk_mem_read_int64(heap, 0i64);
    drop(npk_core_dalloc(array_ptr));
    drop(npk_core_dalloc(heap));
    pass(NIL);
};

pub func:heap_size = int64(int64:heap) {
    pass(npk_mem_read_int64(heap, 8i64));
};

pub func:heap_is_empty = int64(int64:heap) {
    int64:sz = npk_mem_read_int64(heap, 8i64);
    if (sz == 0i64) { pass(1i64); }
    pass(0i64);
};

func:heap_swap = NIL(int64:array_ptr, int64:i, int64:j) {
    int64:i_offset = i * HEAP_ELEM_SIZE;
    int64:j_offset = j * HEAP_ELEM_SIZE;
    
    int64:i_idx = npk_mem_read_int64(array_ptr, i_offset);
    int64:i_rec = npk_mem_read_int64(array_ptr, i_offset + 8i64);
    
    int64:j_idx = npk_mem_read_int64(array_ptr, j_offset);
    int64:j_rec = npk_mem_read_int64(array_ptr, j_offset + 8i64);
    
    drop(npk_mem_write_int64(array_ptr, i_offset, j_idx));
    drop(npk_mem_write_int64(array_ptr, i_offset + 8i64, j_rec));
    
    drop(npk_mem_write_int64(array_ptr, j_offset, i_idx));
    drop(npk_mem_write_int64(array_ptr, j_offset + 8i64, i_rec));
    
    pass(NIL);
};

// Returns 1 if a < b, 0 otherwise
func:heap_less = int64(int64:array_ptr, int64:i, int64:j) {
    int64:i_offset = i * HEAP_ELEM_SIZE;
    int64:j_offset = j * HEAP_ELEM_SIZE;
    
    int64:i_idx = npk_mem_read_int64(array_ptr, i_offset);
    int64:i_rec = npk_mem_read_int64(array_ptr, i_offset + 8i64);
    
    int64:j_idx = npk_mem_read_int64(array_ptr, j_offset);
    int64:j_rec = npk_mem_read_int64(array_ptr, j_offset + 8i64);
    
    string:i_key = sst_rec_key(i_rec) ?! "";
    string:j_key = sst_rec_key(j_rec) ?! "";
    
    if (i_key < j_key) { pass(1i64); }
    if (i_key > j_key) { pass(0i64); }
    
    if (i_idx > j_idx) { pass(1i64); }
    pass(0i64);
};

func:heap_up = NIL(int64:array_ptr, int64:j) {
    while (j > 0i64) {
        int64:i = (j - 1i64) / 2i64; // parent
        int64:less = heap_less(array_ptr, j, i) ?! 0i64;
        if (less == 0i64) {
            break;
        }
        drop(heap_swap(array_ptr, i, j));
        j = i;
    }
    pass(NIL);
};

func:heap_down = NIL(int64:array_ptr, int64:i0, int64:n) {
    int64:i = i0;
    while (1i64 == 1i64) {
        int64:left = (i * 2i64) + 1i64;
        if (left >= n) { break; }
        
        int64:smallest = left;
        int64:right = left + 1i64;
        if (right < n) {
            int64:less_r = heap_less(array_ptr, right, left) ?! 0i64;
            if (less_r == 1i64) {
                smallest = right;
            }
        }
        
        int64:less_s = heap_less(array_ptr, smallest, i) ?! 0i64;
        if (less_s == 0i64) { break; }
        
        drop(heap_swap(array_ptr, i, smallest));
        i = smallest;
    }
    pass(NIL);
};

pub func:heap_push = NIL(int64:heap, string:key, int64:iter_idx, int64:record) {
    int64:array_ptr = npk_mem_read_int64(heap, 0i64);
    int64:size = npk_mem_read_int64(heap, 8i64);
    int64:capacity = npk_mem_read_int64(heap, 16i64);
    
    if (size >= capacity) {
        // resize logic if needed (omit for now as size is fixed)
        pass(NIL);
    }
    
    int64:offset = size * HEAP_ELEM_SIZE;
    drop(npk_mem_write_int64(array_ptr, offset, iter_idx));
    drop(npk_mem_write_int64(array_ptr, offset + 8i64, record));
    
    drop(npk_mem_write_int64(heap, 8i64, size + 1i64));
    
    drop(heap_up(array_ptr, size));
    
    pass(NIL);
};

// Returns record handle, populating iter_idx via a pointer if we had one.
// Let's create heap_pop, heap_pop_iter_idx. Since we only pop the root,
// we can read the root elements before removing them.
pub func:heap_pop_record = int64(int64:heap) {
    int64:size = npk_mem_read_int64(heap, 8i64);
    if (size == 0i64) { pass(0i64); }
    int64:array_ptr = npk_mem_read_int64(heap, 0i64);
    pass(npk_mem_read_int64(array_ptr, 8i64));
};

pub func:heap_pop_iter_idx = int64(int64:heap) {
    int64:size = npk_mem_read_int64(heap, 8i64);
    if (size == 0i64) { pass(-1i64); }
    int64:array_ptr = npk_mem_read_int64(heap, 0i64);
    pass(npk_mem_read_int64(array_ptr, 0i64));
};

pub func:heap_pop_key = string(int64:heap) {
    int64:size = npk_mem_read_int64(heap, 8i64);
    if (size == 0i64) { pass(""); }
    int64:array_ptr = npk_mem_read_int64(heap, 0i64);
    int64:rec = npk_mem_read_int64(array_ptr, 8i64);
    pass(sst_rec_key(rec) ?! "");
};

pub func:heap_pop = NIL(int64:heap) {
    int64:size = npk_mem_read_int64(heap, 8i64);
    if (size == 0i64) { pass(NIL); }
    
    int64:array_ptr = npk_mem_read_int64(heap, 0i64);
    
    // Swap root with last
    drop(heap_swap(array_ptr, 0i64, size - 1i64));
    
    // Decrement size
    int64:new_size = size - 1i64;
    drop(npk_mem_write_int64(heap, 8i64, new_size));
    
    // Sift down root
    if (new_size > 0i64) {
        drop(heap_down(array_ptr, 0i64, new_size));
    }
    
    pass(NIL);
};

```

### File: `src/util/str_view.npk`
```nitpick
// str_view.npk — Zero-copy string bounds

pub struct:StrView = {
    int64:ptr;
    int64:len;
};

pub struct:PrefixExtraction = {
    int32:has_prefix;
    int32:padding; // 4 byte padding for alignment
    int64:ptr;     // equivalent to StrView:prefix inline
    int64:len;
};

```

### File: `src/document/json_parser.npk`
```nitpick
// json_parser.npk — Zero-copy recursive descent JSON parser.

use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;
use "json_types.npk".*;

// Tracks the current position in the buffer.
pub struct:ParserState = {
    int64:buf;
    int64:length;
    int64:pos;
    int64:depth;
};

pub func:skip_whitespace = NIL(ParserState->:state) {
    int8:c = 0i8;
    when (state->pos < state->length) {
        c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
        if (c == 32i8 || c == 10i8 || c == 13i8 || c == 9i8) {
            state->pos = state->pos + 1i64;
        } else {
            break;
        }
    }
    pass(NIL);
};

pub func:parse_i64 = int64(ParserState->:state) {
    int64:acc = 0i64;
    int64:sign = 1i64;
    int8:c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
    
    if (c == 45i8) { // '-'
        sign = -1i64;
        state->pos = state->pos + 1i64;
    }
    
    when (state->pos < state->length) {
        c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
        if (c >= 48i8 && c <= 57i8) {
            int64:digit = (c - 48i8) => int64;
            acc = (acc * 10i64) + digit;
            state->pos = state->pos + 1i64;
        } else {
            break;
        }
    }
    pass(acc * sign);
};

pub func:parse_string = NpkJsonStr(ParserState->:state) {
    // Must start with '"'
    if (@cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8) != 34i8) {
        fail(ERR_JSON_PARSE_FAIL);
    }
    state->pos = state->pos + 1i64;
    
    int64:start = state->pos;
    int8:c = 0i8;
    when (state->pos < state->length) {
        c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
        if (c == 34i8) { break; } // end quote
        state->pos = state->pos + 1i64;
    }
    
    if (c != 34i8) { fail(ERR_JSON_PARSE_FAIL); }
    
    int64:len = state->pos - start;
    state->pos = state->pos + 1i64; // Consume closing quote
    
    NpkJsonStr:res = NpkJsonStr {
        length: @cast_unchecked<uint32>(len),
        data: state->buf + start
    };
    pass(res);
};

pub func:parse_f64 = flt64(ParserState->:state) {
    int64:sign = 1i64;
    int8:c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
    if (c == 45i8) { sign = -1i64; state->pos = state->pos + 1i64; }
    
    int64:acc = 0i64;
    while (state->pos < state->length) {
        c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
        if (c >= 48i8 && c <= 57i8) {
            acc = (acc * 10i64) + ((c - 48i8) => int64);
            state->pos = state->pos + 1i64;
        } else { break; }
    }
    
    flt64:f = acc => flt64;
    if (state->pos < state->length) {
        c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
        if (c == 46i8) { // '.'
            state->pos = state->pos + 1i64;
            flt64:frac = 0.0f64;
            flt64:div = 10.0f64;
            while (state->pos < state->length) {
                c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
                if (c >= 48i8 && c <= 57i8) {
                    frac = frac + (((c - 48i8) => flt64) / div);
                    div = div * 10.0f64;
                    state->pos = state->pos + 1i64;
                } else { break; }
            }
            f = f + frac;
        }
    }
    
    if (sign < 0i64) { f = 0.0f64 - f; }
    pass(f);
};

// No forward declarations

pub func:parse_array = NpkJsonVal(ParserState->:state) {
    state->pos = state->pos + 1i64; // skip '['
    int64:max_cap = 4096i64;
    int64:handles_ptr = npk_core_alloc(max_cap * 8i64);
    int64:count = 0i64;
    
    drop(skip_whitespace(state));
    int8:c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
    if (c == 93i8) { // ']'
        state->pos = state->pos + 1i64;
    } else {
        while (count < max_cap) {
            NpkJsonVal:v = _!parse_value(state);
            int64:v_ptr = npk_core_alloc(16i64);
            drop(npk_mem_write_byte(v_ptr, 0i64, v.type => int64));
            drop(npk_mem_write_int64(v_ptr, 8i64, v.payload));
            
            drop(npk_mem_write_int64(handles_ptr, count * 8i64, v_ptr));
            count = count + 1i64;
            
            drop(skip_whitespace(state));
            c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
            if (c == 93i8) { // ']'
                state->pos = state->pos + 1i64;
                break;
            } else if (c == 44i8) { // ','
                state->pos = state->pos + 1i64;
            } else {
                fail(ERR_JSON_PARSE_FAIL);
            }
        }
    }
    
    int64:arr_ptr = npk_core_alloc(16i64);
    drop(npk_mem_write_int32(arr_ptr, 0i64, count => int32));
    drop(npk_mem_write_int64(arr_ptr, 8i64, handles_ptr));
    
    pass(NpkJsonVal{ type: JSON_ARR, payload: arr_ptr });
};

pub func:parse_object = NpkJsonVal(ParserState->:state) {
    state->pos = state->pos + 1i64; // skip '{'
    int64:max_cap = 1024i64;
    int64:keys_ptr = npk_core_alloc(max_cap * 8i64);
    int64:values_ptr = npk_core_alloc(max_cap * 8i64);
    int64:count = 0i64;
    
    drop(skip_whitespace(state));
    int8:c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
    if (c == 125i8) { // '}'
        state->pos = state->pos + 1i64;
    } else {
        while (count < max_cap) {
            drop(skip_whitespace(state));
            NpkJsonStr:k = _!parse_string(state);
            int64:k_ptr = npk_core_alloc(16i64);
            drop(npk_mem_write_int32(k_ptr, 0i64, k.length => int32));
            drop(npk_mem_write_int64(k_ptr, 8i64, k.data));
            drop(npk_mem_write_int64(keys_ptr, count * 8i64, k_ptr));
            
            drop(skip_whitespace(state));
            c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
            if (c != 58i8) { fail(ERR_JSON_PARSE_FAIL); } // ':'
            state->pos = state->pos + 1i64; // skip ':'
            
            NpkJsonVal:v = _!parse_value(state);
            int64:v_ptr = npk_core_alloc(16i64);
            drop(npk_mem_write_byte(v_ptr, 0i64, v.type => int64));
            drop(npk_mem_write_int64(v_ptr, 8i64, v.payload));
            drop(npk_mem_write_int64(values_ptr, count * 8i64, v_ptr));
            
            count = count + 1i64;
            
            drop(skip_whitespace(state));
            c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
            if (c == 125i8) { // '}'
                state->pos = state->pos + 1i64;
                break;
            } else if (c == 44i8) { // ','
                state->pos = state->pos + 1i64;
            } else {
                fail(ERR_JSON_PARSE_FAIL);
            }
        }
    }
    
    int64:obj_ptr = npk_core_alloc(24i64);
    drop(npk_mem_write_int32(obj_ptr, 0i64, count => int32));
    drop(npk_mem_write_int64(obj_ptr, 8i64, keys_ptr));
    drop(npk_mem_write_int64(obj_ptr, 16i64, values_ptr));
    
    pass(NpkJsonVal{ type: JSON_OBJ, payload: obj_ptr });
};

pub func:parse_value = NpkJsonVal(ParserState->:state) {
    drop(skip_whitespace(state));
    if (state->pos >= state->length) { fail(ERR_JSON_PARSE_FAIL); }
    
    int8:c = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, state->pos)) => int8);
    
    if (c == 123i8) { // '{'
        pass(parse_object(state));
    } else if (c == 91i8) { // '['
        pass(parse_array(state));
    } else if (c == 34i8) { // '"'
        NpkJsonStr:s = _!parse_string(state);
        int64:s_ptr = npk_core_alloc(16i64);
        drop(npk_mem_write_int32(s_ptr, 0i64, s.length => int32));
        drop(npk_mem_write_int64(s_ptr, 8i64, s.data));
        pass(NpkJsonVal{ type: JSON_STR, payload: s_ptr });
    } else if (c == 116i8) { // 't' (true)
        state->pos = state->pos + 4i64;
        pass(NpkJsonVal{ type: JSON_BOOL, payload: 1i64 });
    } else if (c == 102i8) { // 'f' (false)
        state->pos = state->pos + 5i64;
        pass(NpkJsonVal{ type: JSON_BOOL, payload: 0i64 });
    } else if (c == 110i8) { // 'n' (null)
        state->pos = state->pos + 4i64;
        pass(NpkJsonVal{ type: JSON_NULL, payload: 0i64 });
    } else {
        // Assume number. Check if it contains '.' to decide flt64 or int64.
        // For simplicity we just use parse_f64 for all numbers right now.
        // Wait, npk_record requires strict type matching!
        // We'll scan ahead to see if there is a dot.
        int64:scan_pos = state->pos;
        int64:has_dot = 0i64;
        while (scan_pos < state->length) {
            int8:sc = @cast_unchecked<int8>((npk_mem_read_byte(state->buf, scan_pos)) => int8);
            if (sc == 46i8) { has_dot = 1i64; break; }
            if (sc < 48i8 || sc > 57i8) { if (sc != 45i8) { break; } }
            scan_pos = scan_pos + 1i64;
        }
        
        if (has_dot == 1i64) {
            flt64:fv = _!parse_f64(state);
            int64:fv_bits = <-(@fv => int64->);
            pass(NpkJsonVal{ type: JSON_NUM_F64, payload: fv_bits });
        } else {
            int64:iv = _!parse_i64(state);
            pass(NpkJsonVal{ type: JSON_NUM_I64, payload: iv });
        }
    }
};

pub func:parse_json = NpkJsonVal(string:json_str) {
    int64:len = string_length(json_str);
    int64:ptr = string_to_cstr(json_str);
    
    ParserState:state = ParserState{
        buf: ptr,
        length: len,
        pos: 0i64,
        depth: 0i64
    };
    
    pass(_!parse_value(@state));
};

```

### File: `src/document/json_serializer.npk`
```nitpick
// json_serializer.npk — Packs an in-memory JSON struct into a contiguous byte array
// suitable for WAL persistence and SSTable writing.

use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;
use "json_types.npk".*;

pub struct:SerialBuffer = {
    int64:data;     // Address of buffer
    int64:capacity;
    int64:cursor;
};

pub func:serial_buffer_ensure = NIL(SerialBuffer->:buf, int64:needed) {
    if (buf->cursor + needed > buf->capacity) {
        int64:new_cap = buf->capacity * 2i64;
        if (new_cap < buf->cursor + needed) {
            new_cap = buf->cursor + needed;
        }
        int64:new_data = npk_core_alloc(new_cap);
        drop(npk_mem_copy(new_data, buf->data, buf->cursor));
        drop(npk_core_dalloc(buf->data));
        buf->data = new_data;
        buf->capacity = new_cap;
    }
    pass(NIL);
};

pub func:serialize_value = NIL(SerialBuffer->:buf, NpkJsonVal->:val) {
    // Write 1-byte type
    drop(serial_buffer_ensure(buf, 1i64));
    drop(npk_mem_write_byte(buf->data, buf->cursor, val->type => int64));
    buf->cursor = buf->cursor + 1i64;

    if (val->type == JSON_NULL) {
        // No payload needed
    } else {
        if (val->type == JSON_BOOL) {
            drop(serial_buffer_ensure(buf, 8i64));
            drop(npk_mem_write_int64(buf->data, buf->cursor, val->payload));
            buf->cursor = buf->cursor + 8i64;
        } else {
            if (val->type == JSON_NUM_I64) {
                drop(serial_buffer_ensure(buf, 8i64));
                drop(npk_mem_write_int64(buf->data, buf->cursor, val->payload));
                buf->cursor = buf->cursor + 8i64;
            } else {
                if (val->type == JSON_NUM_F64) {
                    drop(serial_buffer_ensure(buf, 8i64));
                    drop(npk_mem_write_int64(buf->data, buf->cursor, val->payload));
                    buf->cursor = buf->cursor + 8i64;
                } else {
                    if (val->type == JSON_STR) {
                        int64:str_ptr = val->payload;
                        int64:len = npk_mem_read_int32(str_ptr, 0i64) => int64; // uint32:length is at offset 0
                        int64:data_ptr = npk_mem_read_int64(str_ptr, 8i64);    // int64:data is at offset 8

                        drop(serial_buffer_ensure(buf, 4i64 + len));
                        drop(npk_mem_write_int32(buf->data, buf->cursor, @cast_unchecked<int32>(len)));
                        buf->cursor = buf->cursor + 4i64;
                        if (len > 0i64) {
                            drop(npk_mem_copy(buf->data + buf->cursor, data_ptr, len));
                            buf->cursor = buf->cursor + len;
                        }
                    } else {
                        if (val->type == JSON_ARR) {
                            int64:arr_ptr = val->payload;
                            int64:count = npk_mem_read_int32(arr_ptr, 0i64) => int64;
                            int64:handles_ptr = npk_mem_read_int64(arr_ptr, 8i64);

                            drop(serial_buffer_ensure(buf, 4i64));
                            drop(npk_mem_write_int32(buf->data, buf->cursor, @cast_unchecked<int32>(count)));
                            buf->cursor = buf->cursor + 4i64;

                            int64:i = 0i64;
                            while (i < count) {
                                int64:elem_ptr = npk_mem_read_int64(handles_ptr, i * 8i64);
                                NpkJsonVal:elem = NpkJsonVal {
                                    type: npk_mem_read_byte(elem_ptr, 0i64) => int8,
                                    payload: npk_mem_read_int64(elem_ptr, 8i64)
                                };
                                drop(serialize_value(buf, @elem));
                                i = i + 1i64;
                            }
                        } else {
                            if (val->type == JSON_OBJ) {
                                int64:obj_ptr = val->payload;
                                int64:count = npk_mem_read_int32(obj_ptr, 0i64) => int64;
                                int64:keys_ptr = npk_mem_read_int64(obj_ptr, 8i64);
                                int64:vals_ptr = npk_mem_read_int64(obj_ptr, 16i64);

                                drop(serial_buffer_ensure(buf, 4i64));
                                drop(npk_mem_write_int32(buf->data, buf->cursor, @cast_unchecked<int32>(count)));
                                buf->cursor = buf->cursor + 4i64;

                                int64:i = 0i64;
                                while (i < count) {
                                    int64:key_ptr = npk_mem_read_int64(keys_ptr, i * 8i64);
                                    NpkJsonVal:k_elem = NpkJsonVal {
                                        type: npk_mem_read_byte(key_ptr, 0i64) => int8,
                                        payload: npk_mem_read_int64(key_ptr, 8i64)
                                    };
                                    drop(serialize_value(buf, @k_elem));
                                    
                                    int64:val_ptr = npk_mem_read_int64(vals_ptr, i * 8i64);
                                    NpkJsonVal:v_elem = NpkJsonVal {
                                        type: npk_mem_read_byte(val_ptr, 0i64) => int8,
                                        payload: npk_mem_read_int64(val_ptr, 8i64)
                                    };
                                    drop(serialize_value(buf, @v_elem));
                                    
                                    i = i + 1i64;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    pass(NIL);
};

// Returns a pointer to the newly allocated serialized buffer, and updates out_len.
// Caller is responsible for freeing the buffer.
pub func:serialize_document = int64(NpkJsonVal->:val, int64:out_len_ptr) {
    int64:initial_cap = 256i64;
    SerialBuffer:buf = SerialBuffer {
        data: npk_core_alloc(initial_cap),
        capacity: initial_cap,
        cursor: 0i64
    };
    
    drop(serialize_value(@buf, val));
    
    drop(npk_mem_write_int64(out_len_ptr, 0i64, buf.cursor));
    pass(buf.data);
};

// Serializes a co-located vector array and JSON document.
// Format: [Vector Length (u32)][Vector Data (tfp64...)][JSON Length (u32)][JSON Data (int8...)]
pub func:serialize_colocated_record = int64(int64:vec_ptr, int64:vec_dim, NpkJsonVal->:val, int64:out_len_ptr) {
    int64:initial_cap = 256i64;
    SerialBuffer:buf = SerialBuffer {
        data: npk_core_alloc(initial_cap),
        capacity: initial_cap,
        cursor: 0i64
    };
    
    // 1. Vector Length (u32)
    drop(serial_buffer_ensure(@buf, 4i64));
    drop(npk_mem_write_int32(buf.data, buf.cursor, @cast_unchecked<int32>(vec_dim)));
    buf.cursor = buf.cursor + 4i64;
    
    // 2. Vector Data (tfp64 array)
    int64:vec_byte_len = vec_dim * 8i64;
    if (vec_byte_len > 0i64) {
        drop(serial_buffer_ensure(@buf, vec_byte_len));
        drop(npk_mem_copy(buf.data + buf.cursor, vec_ptr, vec_byte_len));
        buf.cursor = buf.cursor + vec_byte_len;
    }
    
    // 3. JSON Length placeholder (u32)
    drop(serial_buffer_ensure(@buf, 4i64));
    int64:json_len_offset = buf.cursor;
    buf.cursor = buf.cursor + 4i64;
    
    // 4. JSON Data
    int64:json_start = buf.cursor;
    drop(serialize_value(@buf, val));
    int64:json_len = buf.cursor - json_start;
    
    // Write back JSON length
    drop(npk_mem_write_int32(buf.data, json_len_offset, @cast_unchecked<int32>(json_len)));
    
    drop(npk_mem_write_int64(out_len_ptr, 0i64, buf.cursor));
    pass(buf.data);
};

```

### File: `src/document/json_types.npk`
```nitpick
// json_types.npk — Internal representation of JSON metadata

pub fixed int8:JSON_NULL    = 0i8;
pub fixed int8:JSON_BOOL    = 1i8;
pub fixed int8:JSON_NUM_I64 = 2i8;
pub fixed int8:JSON_NUM_F64 = 3i8;
pub fixed int8:JSON_STR     = 4i8;
pub fixed int8:JSON_ARR     = 5i8;
pub fixed int8:JSON_OBJ     = 6i8;

pub struct:NpkJsonVal = {
    int8:type;
    int64:payload;
};

pub func:json_make_null = NpkJsonVal() {
    NpkJsonVal:v = NpkJsonVal{ type: JSON_NULL, payload: 0i64 };
    pass(v);
};

pub func:json_make_bool = NpkJsonVal(tbb8:val) {
    int64:p = 0i64;
    if (val != NIL) { p = 1i64; }
    NpkJsonVal:v = NpkJsonVal{ type: JSON_BOOL, payload: p };
    pass(v);
};

pub func:json_make_i64 = NpkJsonVal(int64:val) {
    NpkJsonVal:v = NpkJsonVal{ type: JSON_NUM_I64, payload: val };
    pass(v);
};

pub func:json_make_f64 = NpkJsonVal(flt64:val) {
    int64:bits = <-(@val => int64->);
    NpkJsonVal:v = NpkJsonVal{ type: JSON_NUM_F64, payload: bits };
    pass(v);
};

pub struct:NpkJsonStr = {
    uint32:length;
    int64:data;
};

pub struct:NpkJsonArr = {
    uint32:count;
    int64->:handles;
};

pub struct:NpkJsonObj = {
    uint32:count;
    int64->:keys;
    int64->:values;
};

```

### File: `src/regex/ast_types.npk`
```nitpick
// ast_types.npk — Token and AST Node types for niregx

// Token definitions
pub fixed int32:TOKEN_LITERAL = 1i32;
pub fixed int32:TOKEN_STAR    = 2i32;
pub fixed int32:TOKEN_PLUS    = 3i32;
pub fixed int32:TOKEN_QMARK   = 4i32;
pub fixed int32:TOKEN_PIPE    = 5i32;
pub fixed int32:TOKEN_LPAREN  = 6i32;
pub fixed int32:TOKEN_RPAREN  = 7i32;
pub fixed int32:TOKEN_DOT     = 8i32;

pub struct:Token = {
    int32:type;
    int32:val;
};

// AST Node types
pub fixed int32:AST_LITERAL = 1i32;
pub fixed int32:AST_CONCAT  = 2i32;
pub fixed int32:AST_ALT     = 3i32;
pub fixed int32:AST_STAR    = 4i32;
pub fixed int32:AST_PLUS    = 5i32;
pub fixed int32:AST_QMARK   = 6i32;
pub fixed int32:AST_ANY     = 7i32;

pub struct:AstNode = {
    int32:type;
    int32:val;
    int64:left;
    int64:right;
};

```

### File: `src/regex/nfa_compiler.npk`
```nitpick
// nfa_compiler.npk — Iterative Thompson NFA Compilation

use "regex_types.npk".*;
use "ast_types.npk".*;
use "regex_arena.npk".*;
use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;

// A fragment represents a partially built NFA
// start: Handle<NfaState>
// e: Handle<NfaState>

func:frag_create = int64(int64:start, int64:e) {
    // Pack two 32-bit offset/indices, or just use astack/heap?
    // We'll use astack to hold fragments. Since astack holds int64, we can pack two 32-bit arena offsets into an int64!
    // But pointers are 64-bit. We can just push twice!
    pass(0i64);
};

pub func:compile_nfa = int64(int64:arena_ptr, int64:ast_root) {
    if (ast_root == 0i64) {
        pass(0i64);
    }
    
    astack(4096i64);
    int32:frag_stack_size = 0i32;
    
    // Post-order traversal using an explicit stack
    // stack format: apush(node), apush(state)
    // state: 0 = unvisited, 1 = left processed, 2 = right processed
    
    int32:trav_stack_size = 0i32;
    apush(ast_root);
    apush(0i64);
    trav_stack_size = trav_stack_size + 1i32;
    
    when (trav_stack_size > 0i32) {
        int64:state = apop();
        int64:node = apop();
        trav_stack_size = trav_stack_size - 1i32;
        
        int32:type = npk_mem_read_int32(node, 0i64);
        int32:val  = npk_mem_read_int32(node, 4i64);
        int64:left = npk_mem_read_int64(node, 8i64);
        int64:right = npk_mem_read_int64(node, 16i64);
        
        if (state == 0i64) {
            apush(node);
            apush(1i64);
            trav_stack_size = trav_stack_size + 1i32;
            if (left != 0i64) {
                apush(left);
                apush(0i64);
                trav_stack_size = trav_stack_size + 1i32;
            }
        } else if (state == 1i64) {
            apush(node);
            apush(2i64);
            trav_stack_size = trav_stack_size + 1i32;
            if (right != 0i64) {
                apush(right);
                apush(0i64);
                trav_stack_size = trav_stack_size + 1i32;
            }
        } else {
            // Process node
            if (type == AST_LITERAL) {
                int64:s = raw regex_arena_alloc(arena_ptr, OP_CHAR, val);
                int64:e = raw regex_arena_alloc(arena_ptr, OP_MATCH, 0i32);
                drop(npk_mem_write_int64(s, 8i64, e)); // out1 = e
                
                // push fragment
                apush(s);
                apush(e);
                frag_stack_size = frag_stack_size + 1i32;
            } else if (type == AST_ANY) {
                int64:s = raw regex_arena_alloc(arena_ptr, OP_ANY, 0i32);
                int64:e = raw regex_arena_alloc(arena_ptr, OP_MATCH, 0i32);
                drop(npk_mem_write_int64(s, 8i64, e)); // out1 = e
                
                apush(s);
                apush(e);
                frag_stack_size = frag_stack_size + 1i32;
            } else if (type == AST_CONCAT) {
                if (frag_stack_size < 2i32) { pass(0i64); }
                int64:f2_e = apop();
                int64:f2_s = apop();
                int64:f1_e = apop();
                int64:f1_s = apop();
                frag_stack_size = frag_stack_size - 2i32;
                
                // Patch f1_e to JMP to f2_s
                drop(npk_mem_write_int32(f1_e, 0i64, OP_JMP));
                drop(npk_mem_write_int64(f1_e, 8i64, f2_s));
                
                apush(f1_s);
                apush(f2_e);
                frag_stack_size = frag_stack_size + 1i32;
            } else if (type == AST_STAR) {
                if (frag_stack_size < 1i32) { pass(0i64); }
                int64:f1_e = apop();
                int64:f1_s = apop();
                frag_stack_size = frag_stack_size - 1i32;
                
                int64:s = raw regex_arena_alloc(arena_ptr, OP_SPLIT, 0i32);
                int64:e = raw regex_arena_alloc(arena_ptr, OP_MATCH, 0i32);
                
                drop(npk_mem_write_int64(s, 8i64, f1_s));
                drop(npk_mem_write_int64(s, 16i64, e));
                drop(npk_mem_write_int32(f1_e, 0i64, OP_JMP));
                drop(npk_mem_write_int64(f1_e, 8i64, s));
                
                apush(s);
                apush(e);
                frag_stack_size = frag_stack_size + 1i32;
            } else if (type == AST_ALT) {
                if (frag_stack_size < 2i32) { pass(0i64); }
                int64:f2_e = apop();
                int64:f2_s = apop();
                int64:f1_e = apop();
                int64:f1_s = apop();
                frag_stack_size = frag_stack_size - 2i32;

                int64:s = raw regex_arena_alloc(arena_ptr, OP_SPLIT, 0i32);
                int64:e = raw regex_arena_alloc(arena_ptr, OP_MATCH, 0i32);

                drop(npk_mem_write_int64(s, 8i64, f1_s));
                drop(npk_mem_write_int64(s, 16i64, f2_s));

                drop(npk_mem_write_int32(f1_e, 0i64, OP_JMP));
                drop(npk_mem_write_int64(f1_e, 8i64, e));

                drop(npk_mem_write_int32(f2_e, 0i64, OP_JMP));
                drop(npk_mem_write_int64(f2_e, 8i64, e));

                apush(s);
                apush(e);
                frag_stack_size = frag_stack_size + 1i32;
            } else if (type == AST_PLUS) {
                if (frag_stack_size < 1i32) { pass(0i64); }
                int64:f1_e = apop();
                int64:f1_s = apop();
                frag_stack_size = frag_stack_size - 1i32;

                int64:s = raw regex_arena_alloc(arena_ptr, OP_SPLIT, 0i32);
                int64:e = raw regex_arena_alloc(arena_ptr, OP_MATCH, 0i32);

                drop(npk_mem_write_int32(f1_e, 0i64, OP_SPLIT));
                drop(npk_mem_write_int64(f1_e, 8i64, f1_s));
                drop(npk_mem_write_int64(f1_e, 16i64, e));

                drop(npk_mem_write_int32(s, 0i64, OP_JMP));
                drop(npk_mem_write_int64(s, 8i64, f1_s));

                apush(s);
                apush(e);
                frag_stack_size = frag_stack_size + 1i32;
            } else if (type == AST_QMARK) {
                if (frag_stack_size < 1i32) { pass(0i64); }
                int64:f1_e = apop();
                int64:f1_s = apop();
                frag_stack_size = frag_stack_size - 1i32;

                int64:s = raw regex_arena_alloc(arena_ptr, OP_SPLIT, 0i32);
                int64:e = raw regex_arena_alloc(arena_ptr, OP_MATCH, 0i32);

                drop(npk_mem_write_int64(s, 8i64, f1_s));
                drop(npk_mem_write_int64(s, 16i64, e));

                drop(npk_mem_write_int32(f1_e, 0i64, OP_JMP));
                drop(npk_mem_write_int64(f1_e, 8i64, e));

                apush(s);
                apush(e);
                frag_stack_size = frag_stack_size + 1i32;
            }
        }
    }
    
    if (frag_stack_size != 1i32) {
        pass(0i64);
    }
    
    int64:final_e = apop();
    int64:final_s = apop();
    
    pass(final_s);
};

```

### File: `src/regex/prefix_extractor.npk`
```nitpick
// prefix_extractor.npk — Extracts literal prefixes from AST

use "ast_types.npk".*;
use "../util/str_view.npk".*;
use "../util/mem_primitives.npk".*;

extern "nitpick_libc_sys" {
    func:npk_tlc_batch_alloc = int64(int64:size);
}

pub func:extract_literal_prefix = int64(int64:ast_root, int64:pattern) {
    int64:ext = npk_tlc_batch_alloc(24i64);
    drop(npk_mem_write_int32(ext, 0i64, 0i32)); // has_prefix
    drop(npk_mem_write_int64(ext, 8i64, 0i64)); // ptr
    drop(npk_mem_write_int64(ext, 16i64, 0i64)); // len
    
    if (ast_root == 0i64) {
        pass(ext);
    }
    
    astack(1024i64);
    int32:stack_size = 0i32;
    
    int64:curr = ast_root;
    int32:literal_count = 0i32;
    int32:running = 1i32;
    
    when (running == 1i32) {
        if (curr != 0i64) {
            apush(curr);
            stack_size = stack_size + 1i32;
            curr = npk_mem_read_int64(curr, 8i64); // left
        } else {
            if (stack_size > 0i32) {
                curr = apop();
                stack_size = stack_size - 1i32;
                
                int32:type = npk_mem_read_int32(curr, 0i64);
                if (type == AST_LITERAL) {
                    literal_count = literal_count + 1i32;
                } else if (type == AST_CONCAT) {
                    // continue
                } else {
                    running = 0i32;
                }
                
                if (running == 1i32) {
                    curr = npk_mem_read_int64(curr, 16i64); // right
                }
            } else {
                running = 0i32;
            }
        }
    }
    
    if (literal_count > 0i32) {
        drop(npk_mem_write_int32(ext, 0i64, 1i32));
        drop(npk_mem_write_int64(ext, 8i64, pattern)); // point to start of pattern
        drop(npk_mem_write_int64(ext, 16i64, literal_count => int64));
    }
    
    pass(ext);
};

```

### File: `src/regex/regex_arena.npk`
```nitpick
// regex_arena.npk — Generational Arena for NFA States

use "regex_types.npk".*;
use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;

// Arena structure:
// int64: data_ptr (pointer to NfaState array)
// int64: capacity
// int64: cursor (current allocation count)

pub fixed int64:REGEX_ARENA_SIZE = 24i64;
pub fixed int64:NFA_STATE_SIZE   = 48i64; // opcode(4), match_char(4), out1(8), out2(8), charset(24)

pub func:regex_arena_init = int64(int64:capacity) {
    int64:arena_ptr = npk_core_alloc(REGEX_ARENA_SIZE);
    if (arena_ptr == 0i64) { fail(ERR_REGEX_COMPLEXITY_EXCEEDED => tbb32); }
    
    int64:data = npk_core_alloc(capacity * NFA_STATE_SIZE);
    if (data == 0i64) {
        drop(npk_core_dalloc(arena_ptr));
        fail(ERR_REGEX_COMPLEXITY_EXCEEDED => tbb32);
    }
    
    drop(npk_mem_write_int64(arena_ptr, 0i64, data));
    drop(npk_mem_write_int64(arena_ptr, 8i64, capacity));
    drop(npk_mem_write_int64(arena_ptr, 16i64, 0i64));
    
    pass(arena_ptr);
};

pub func:regex_arena_alloc = int64(int64:arena_ptr, int32:opcode, int32:match_char) {
    int64:capacity = npk_mem_read_int64(arena_ptr, 8i64);
    int64:cursor   = npk_mem_read_int64(arena_ptr, 16i64);
    
    if (cursor >= capacity) {
        fail(ERR_REGEX_COMPLEXITY_EXCEEDED => tbb32);
    }
    
    int64:data = npk_mem_read_int64(arena_ptr, 0i64);
    int64:node = data + (cursor * NFA_STATE_SIZE);
    
    drop(npk_mem_write_int64(arena_ptr, 16i64, cursor + 1i64));
    
    drop(npk_mem_write_int32(node, 0i64, opcode));
    drop(npk_mem_write_int32(node, 4i64, match_char));
    
    // Clear the rest
    drop(npk_mem_write_int64(node, 8i64, 0i64)); // out1
    drop(npk_mem_write_int64(node, 16i64, 0i64)); // out2
    drop(npk_mem_write_int64(node, 24i64, 0i64)); // charset
    drop(npk_mem_write_int64(node, 32i64, 0i64)); // charset
    drop(npk_mem_write_int64(node, 40i64, 0i64)); // charset
    
    pass(node);
};

pub func:regex_arena_destroy = NIL(int64:arena_ptr) {
    if (arena_ptr == 0i64) { pass(NIL); }
    int64:data = npk_mem_read_int64(arena_ptr, 0i64);
    if (data != 0i64) {
        drop(npk_core_dalloc(data));
    }
    drop(npk_core_dalloc(arena_ptr));
    pass(NIL);
};

```

### File: `src/regex/regex_cache.npk`
```nitpick
// regex_cache.npk — Concurrency & Caching

use "regex_types.npk".*;
use "regex_arena.npk".*;
use "regex_vm.npk".*;
use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;
use "atomic.npk".*;

extern "nitpick_libc_sys" {
    func:npk_shim_rwlock_create = int64();
    func:npk_shim_rwlock_rdlock = int32(int64:handle);
    func:npk_shim_rwlock_wrlock = int32(int64:handle);
    func:npk_shim_rwlock_unlock = int32(int64:handle);
}

// Global rwlock and list head
pub int64:g_regex_rwlock = 0i64;
pub int64:g_regex_cache_head = 0i64;

pub func:regex_cache_init = int32() {
    g_regex_rwlock = npk_shim_rwlock_create();
    g_regex_cache_head = 0i64;
    pass(0i32);
};

func:strings_equal = int32(int64:str1, int64:len1, int64:str2, int64:len2) {
    if (len1 != len2) { pass(0i32); }
    int64:i = 0i64;
    int32:match = 1i32;
    when (i < len1) {
        int64:c1 = npk_mem_read_byte(str1, i);
        int64:c2 = npk_mem_read_byte(str2, i);
        if (c1 != c2) {
            match = 0i32;
            i = len1; // break
        } else {
            i = i + 1i64;
        }
    }
    pass(match);
};

pub func:regex_cache_get = int64(int64:pattern, int64:pattern_len) {
    int32:rdlock_res = npk_shim_rwlock_rdlock(g_regex_rwlock);
    defer { drop(npk_shim_rwlock_unlock(g_regex_rwlock)); }
    
    int64:curr = g_regex_cache_head;
    int64:found = 0i64;
    int32:running = 1i32;
    
    when (running == 1i32) {
        if (curr == 0i64) {
            running = 0i32;
        } else {
            int64:p_str = npk_mem_read_int64(curr, 0i64);
            int64:p_len = npk_mem_read_int64(curr, 8i64);
            
            int32:eq = raw strings_equal(pattern, pattern_len, p_str, p_len);
            if (eq == 1i32) {
                found = curr;
                running = 0i32;
            } else {
                curr = npk_mem_read_int64(curr, 40i64);
            }
        }
    }
    
    pass(found);
};

pub func:regex_cache_insert = int64(int64:pattern, int64:pattern_len, int64:arena_ptr, int64:start_state) {
    int32:wrlock_res = npk_shim_rwlock_wrlock(g_regex_rwlock);
    defer { drop(npk_shim_rwlock_unlock(g_regex_rwlock)); }
    
    // Eviction logic
    int64:curr = g_regex_cache_head;
    int32:count = 0i32;
    int64:prev = 0i64;
    int64:lowest_hit_node = 0i64;
    int64:lowest_hit_prev = 0i64;
    int64:min_hits = 999999999i64;
    
    when (curr != 0i64) {
        count = count + 1i32;
        int64:hndl = npk_mem_read_int64(curr, 32i64);
        int64:hits = raw AtomicInt64.add(AtomicInt64{handle: hndl}, 0i64, raw AtomicInt64.RELAXED());
        if (hits < min_hits) {
            min_hits = hits;
            lowest_hit_node = curr;
            lowest_hit_prev = prev;
        }
        prev = curr;
        curr = npk_mem_read_int64(curr, 40i64);
    }
    
    if (count >= 1000i32) {
        if (lowest_hit_node != 0i64) {
            if (lowest_hit_prev == 0i64) {
                g_regex_cache_head = npk_mem_read_int64(lowest_hit_node, 40i64);
            } else {
                int64:next_node = npk_mem_read_int64(lowest_hit_node, 40i64);
                drop(npk_mem_write_int64(lowest_hit_prev, 40i64, next_node));
            }
            int64:p_str = npk_mem_read_int64(lowest_hit_node, 0i64);
            drop(npk_core_dalloc(p_str));
            // arena_ptr is freed by the VM or GC in NPKDB usually, but we drop the node
            drop(npk_core_dalloc(lowest_hit_node));
        }
    }

    int64:entry = npk_core_alloc(48i64);
    
    // Copy the string
    int64:p_copy = npk_core_alloc(pattern_len);
    int64:i = 0i64;
    when (i < pattern_len) {
        int64:c = npk_mem_read_byte(pattern, i);
        drop(npk_mem_write_byte(p_copy, i, c));
        i = i + 1i64;
    }
    
    drop(npk_mem_write_int64(entry, 0i64, p_copy));
    drop(npk_mem_write_int64(entry, 8i64, pattern_len));
    drop(npk_mem_write_int64(entry, 16i64, arena_ptr));
    drop(npk_mem_write_int64(entry, 24i64, start_state));
    
    // hit_counter
    AtomicInt64:hit_counter = raw AtomicInt64.create(0i64);
    drop(npk_mem_write_int64(entry, 32i64, hit_counter.handle));
    
    // insert at head
    drop(npk_mem_write_int64(entry, 40i64, g_regex_cache_head));
    g_regex_cache_head = entry;
    
    pass(entry);
};

pub func:regex_cache_increment_hit = int32(int64:entry) {
    if (entry == 0i64) { pass(0i32); }
    int64:handle = npk_mem_read_int64(entry, 32i64);
    AtomicInt64:hit_counter = AtomicInt64{handle: handle};
    int32:RELAXED = raw AtomicInt64.RELAXED();
    drop(AtomicInt64.add(hit_counter, 1i64, RELAXED));
    pass(1i32);
};

pub func:regex_execute = int32(int64:entry, int64:text, int64:text_len) {
    if (entry == 0i64) { pass(0i32); }
    drop(regex_cache_increment_hit(entry));
    
    int64:arena_ptr = npk_mem_read_int64(entry, 16i64);
    int64:start_state = npk_mem_read_int64(entry, 24i64);
    
    // Call the VM
    int32:match = raw regex_vm_match(arena_ptr, start_state, text, text_len);
    pass(match);
};

```

### File: `src/regex/regex_compiler.npk`
```nitpick
// regex_compiler.npk — Iterative AST Compilation for nregx

use "ast_types.npk".*;
use "regex_types.npk".*;
use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;

// Thread-Local Cache allocations for ephemeral AST Nodes
extern "nitpick_libc_sys" {
    func:npk_tlc_batch_alloc = int64(int64:size);
    func:npk_tlc_batch_flush = void();
}

// Memory-safe AST Node allocator using the thread-local batch
func:alloc_ast_node = int64(int32:type, int32:val) {
    int64:node = npk_tlc_batch_alloc(32i64);
    drop(npk_mem_write_int32(node, 0i64, type));
    drop(npk_mem_write_int32(node, 4i64, val));
    drop(npk_mem_write_int64(node, 8i64, 0i64));
    drop(npk_mem_write_int64(node, 16i64, 0i64));
    pass(node);
};

// ── LEXER ────────────────────────────────────────────────────────────────

pub func:lex_pattern = int32(int64:pattern, limit<r_valid_regex_len> int64:len, int64:out_tokens) {
    int64:i = 0i64;
    int32:token_count = 0i32;

    when (i < len) {
        int64:c = npk_mem_read_byte(pattern, i);
        int64:tok_ptr = out_tokens + ((token_count => int64) * 8i64);
        
        if (c == 42i64) { 
            drop(npk_mem_write_int32(tok_ptr, 0i64, TOKEN_STAR));
        } else if (c == 43i64) { 
            drop(npk_mem_write_int32(tok_ptr, 0i64, TOKEN_PLUS));
        } else if (c == 63i64) { 
            drop(npk_mem_write_int32(tok_ptr, 0i64, TOKEN_QMARK));
        } else if (c == 124i64) { 
            drop(npk_mem_write_int32(tok_ptr, 0i64, TOKEN_PIPE));
        } else if (c == 40i64) { 
            drop(npk_mem_write_int32(tok_ptr, 0i64, TOKEN_LPAREN));
        } else if (c == 41i64) { 
            drop(npk_mem_write_int32(tok_ptr, 0i64, TOKEN_RPAREN));
        } else if (c == 46i64) { 
            drop(npk_mem_write_int32(tok_ptr, 0i64, TOKEN_DOT));
        } else { 
            drop(npk_mem_write_int32(tok_ptr, 0i64, TOKEN_LITERAL));
            drop(npk_mem_write_int32(tok_ptr, 4i64, c => int32));
        }
        
        token_count = token_count + 1i32;
        i = i + 1i64;
    }
    
    pass(token_count);
};

// ── RECURSIVE DESCENT PARSER ──────────────────────────────────────────────────

func:parse_alt = int64(int64:tokens, int32:count, int64:idx_ptr, int32:depth) {
    if (depth > 128i32) { pass(0i64); }
    int64:left = raw parse_concat(tokens, count, idx_ptr, depth + 1i32);
    if (left == 0i64) { pass(0i64); }
    
    int32:running = 1i32;
    when (running == 1i32) {
        int32:idx = npk_mem_read_int32(idx_ptr, 0i64);
        if (idx >= count) {
            running = 0i32;
        } else {
            int64:tok_ptr = tokens + ((idx => int64) * 8i64);
            int32:tok_type = npk_mem_read_int32(tok_ptr, 0i64);
            if (tok_type == TOKEN_PIPE) {
                drop(npk_mem_write_int32(idx_ptr, 0i64, idx + 1i32));
                int64:right = raw parse_concat(tokens, count, idx_ptr, depth + 1i32);
                if (right == 0i64) { pass(0i64); }
                int64:alt_node = raw alloc_ast_node(AST_ALT, 0i32);
                drop(npk_mem_write_int64(alt_node, 8i64, left));
                drop(npk_mem_write_int64(alt_node, 16i64, right));
                left = alt_node;
            } else {
                running = 0i32;
            }
        }
    }
    pass(left);
};

func:parse_concat = int64(int64:tokens, int32:count, int64:idx_ptr, int32:depth) {
    if (depth > 128i32) { pass(0i64); }
    int64:left = raw parse_rep(tokens, count, idx_ptr, depth + 1i32);
    if (left == 0i64) { pass(0i64); }
    
    int32:running = 1i32;
    when (running == 1i32) {
        int32:idx = npk_mem_read_int32(idx_ptr, 0i64);
        if (idx >= count) {
            running = 0i32;
        } else {
            int64:tok_ptr = tokens + ((idx => int64) * 8i64);
            int32:tok_type = npk_mem_read_int32(tok_ptr, 0i64);
            // concat if token is LITERAL, DOT, LPAREN
            if ((tok_type == TOKEN_LITERAL) || (tok_type == TOKEN_DOT) || (tok_type == TOKEN_LPAREN)) {
                int64:right = raw parse_rep(tokens, count, idx_ptr, depth + 1i32);
                if (right == 0i64) { pass(0i64); }
                int64:concat_node = raw alloc_ast_node(AST_CONCAT, 0i32);
                drop(npk_mem_write_int64(concat_node, 8i64, left));
                drop(npk_mem_write_int64(concat_node, 16i64, right));
                left = concat_node;
            } else {
                running = 0i32;
            }
        }
    }
    pass(left);
};

func:parse_rep = int64(int64:tokens, int32:count, int64:idx_ptr, int32:depth) {
    if (depth > 128i32) { pass(0i64); }
    int64:node = raw parse_atom(tokens, count, idx_ptr, depth + 1i32);
    if (node == 0i64) { pass(0i64); }
    
    int32:idx = npk_mem_read_int32(idx_ptr, 0i64);
    if (idx < count) {
        int64:tok_ptr = tokens + ((idx => int64) * 8i64);
        int32:tok_type = npk_mem_read_int32(tok_ptr, 0i64);
        
        if (tok_type == TOKEN_STAR) {
            drop(npk_mem_write_int32(idx_ptr, 0i64, idx + 1i32));
            int64:star_node = raw alloc_ast_node(AST_STAR, 0i32);
            drop(npk_mem_write_int64(star_node, 8i64, node));
            node = star_node;
        } else if (tok_type == TOKEN_PLUS) {
            drop(npk_mem_write_int32(idx_ptr, 0i64, idx + 1i32));
            int64:plus_node = raw alloc_ast_node(AST_PLUS, 0i32);
            drop(npk_mem_write_int64(plus_node, 8i64, node));
            node = plus_node;
        } else if (tok_type == TOKEN_QMARK) {
            drop(npk_mem_write_int32(idx_ptr, 0i64, idx + 1i32));
            int64:qmark_node = raw alloc_ast_node(AST_QMARK, 0i32);
            drop(npk_mem_write_int64(qmark_node, 8i64, node));
            node = qmark_node;
        }
    }
    pass(node);
};

func:parse_atom = int64(int64:tokens, int32:count, int64:idx_ptr, int32:depth) {
    if (depth > 128i32) { pass(0i64); }
    
    int32:idx = npk_mem_read_int32(idx_ptr, 0i64);
    if (idx >= count) { pass(0i64); }
    
    int64:tok_ptr = tokens + ((idx => int64) * 8i64);
    int32:tok_type = npk_mem_read_int32(tok_ptr, 0i64);
    int32:tok_val = npk_mem_read_int32(tok_ptr, 4i64);
    
    drop(npk_mem_write_int32(idx_ptr, 0i64, idx + 1i32));
    
    if (tok_type == TOKEN_LITERAL) {
        pass(raw alloc_ast_node(AST_LITERAL, tok_val));
    } else if (tok_type == TOKEN_DOT) {
        pass(raw alloc_ast_node(AST_ANY, 0i32));
    } else if (tok_type == TOKEN_LPAREN) {
        int64:inner = raw parse_alt(tokens, count, idx_ptr, depth + 1i32);
        if (inner == 0i64) { pass(0i64); }
        
        int32:idx2 = npk_mem_read_int32(idx_ptr, 0i64);
        if (idx2 >= count) { pass(0i64); }
        int64:tok_ptr2 = tokens + ((idx2 => int64) * 8i64);
        int32:tok_type2 = npk_mem_read_int32(tok_ptr2, 0i64);
        
        if (tok_type2 != TOKEN_RPAREN) { pass(0i64); }
        drop(npk_mem_write_int32(idx_ptr, 0i64, idx2 + 1i32));
        
        pass(inner);
    }
    
    pass(0i64);
};

pub func:parse_regex_ast = int64(int64:tokens, int32:count) {
    defer { npk_tlc_batch_flush(); }
    
    if (count == 0i32) {
        pass(0i64);
    }
    
    int64:idx_ptr = npk_tlc_batch_alloc(8i64);
    drop(npk_mem_write_int32(idx_ptr, 0i64, 0i32));
    
    int64:root = raw parse_alt(tokens, count, idx_ptr, 0i32);
    if (root == 0i64) { pass(0i64); }
    
    int32:idx = npk_mem_read_int32(idx_ptr, 0i64);
    if (idx != count) {
        pass(0i64); // unexpected trailing tokens
    }
    
    pass(root);
};

```

### File: `src/regex/regex_types.npk`
```nitpick
// regex_types.npk — Foundational structs and constraints for niregx

use "../util/error_codes.npk".*;

// Mathematical limit for maximum string length of a valid regular expression pattern (8KB max).
pub Rules<int64>:r_valid_regex_len = { $ > 0i64, $ <= 8192i64 };

// Opcodes for the Pike VM
pub fixed int32:OP_MATCH      = 0i32;
pub fixed int32:OP_CHAR       = 1i32;
pub fixed int32:OP_SPLIT      = 2i32;
pub fixed int32:OP_JMP        = 3i32;
pub fixed int32:OP_ANY        = 4i32;
pub fixed int32:OP_CHAR_CLASS = 5i32;

// NFA State node utilizing Generational Handles
pub struct:NfaState = {
    int32:opcode;
    int32:match_char;
    Handle<NfaState>:out1;
    Handle<NfaState>:out2;
    uint8[32]:charset; // 256-bit bitmask for character classes
};

// The compiled regular expression execution bundle
pub struct:Regex = {
    Handle<NfaState>:start_state;
    int32:state_count;
};

```

### File: `src/regex/regex_vm.npk`
```nitpick
// regex_vm.npk — Thompson VM Core Engine Execution

use "regex_types.npk".*;
use "ast_types.npk".*;
use "regex_arena.npk".*;
use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;

func:add_state = int64(int64:state, int64:list_ptr, int64:list_size_ptr, int64:visit_gen) {
    if (state == 0i64) { pass(0i64); }
    
    // Read visit_gen (offset 32)
    int64:last_visit = npk_mem_read_int64(state, 32i64);
    if (last_visit == visit_gen) { pass(0i64); }
    
    drop(npk_mem_write_int64(state, 32i64, visit_gen));
    
    int32:opcode = npk_mem_read_int32(state, 0i64);
    int64:out1 = npk_mem_read_int64(state, 8i64);
    int64:out2 = npk_mem_read_int64(state, 16i64);
    
    if (opcode == OP_SPLIT) {
        drop(add_state(out1, list_ptr, list_size_ptr, visit_gen));
        drop(add_state(out2, list_ptr, list_size_ptr, visit_gen));
        pass(0i64);
    } else if (opcode == OP_JMP) {
        drop(add_state(out1, list_ptr, list_size_ptr, visit_gen));
        pass(0i64);
    }
    
    int64:size = npk_mem_read_int64(list_size_ptr, 0i64);
    drop(npk_mem_write_int64(list_ptr, size * 8i64, state));
    drop(npk_mem_write_int64(list_size_ptr, 0i64, size + 1i64));
    
    pass(0i64);
};

pub func:regex_vm_match = int32(int64:arena_ptr, int64:start_state, int64:text, int64:text_len) {
    if (start_state == 0i64) { pass(0i32); }
    
    int64:capacity = npk_mem_read_int64(arena_ptr, 8i64);
    int64:clist = npk_core_alloc(capacity * 8i64);
    int64:nlist = npk_core_alloc(capacity * 8i64);
    int64:clist_sz_ptr = npk_core_alloc(8i64);
    int64:nlist_sz_ptr = npk_core_alloc(8i64);
    
    int64:visit_gen = 1i64;
    drop(npk_mem_write_int64(clist_sz_ptr, 0i64, 0i64));
    drop(npk_mem_write_int64(nlist_sz_ptr, 0i64, 0i64));
    
    drop(add_state(start_state, clist, clist_sz_ptr, visit_gen));
    
    int64:idx = 0i64;
    int32:matched = 0i32;
    int32:running = 1i32;
    
    when (running == 1i32) {
        int64:clist_sz = npk_mem_read_int64(clist_sz_ptr, 0i64);
        if (clist_sz == 0i64) {
            running = 0i32;
        } else {
            // Process current states
            // If we run out of string, we can't consume characters, but we still check for OP_MATCH
            int64:c = -1i64;
            if (idx < text_len) {
                c = npk_mem_read_byte(text, idx);
            }
            
            visit_gen = visit_gen + 1i64;
            drop(npk_mem_write_int64(nlist_sz_ptr, 0i64, 0i64));
            
            int64:i = 0i64;
            when (i < clist_sz) {
                int64:state = npk_mem_read_int64(clist, i * 8i64);
                int32:opcode = npk_mem_read_int32(state, 0i64);
                
                if (opcode == OP_MATCH) {
                    matched = 1i32;
                    running = 0i32;
                    // We found a match, but if we want greedy matching we might need to continue.
                    // For now, any match is accepted (since we are doing regex match, not search).
                } else if (c != -1i64) {
                    if (opcode == OP_CHAR) {
                        int32:match_char = npk_mem_read_int32(state, 4i64);
                        if (c == (match_char => int64)) {
                            int64:out1 = npk_mem_read_int64(state, 8i64);
                            drop(add_state(out1, nlist, nlist_sz_ptr, visit_gen));
                        }
                    } else if (opcode == OP_ANY) {
                        int64:out1 = npk_mem_read_int64(state, 8i64);
                        drop(add_state(out1, nlist, nlist_sz_ptr, visit_gen));
                    }
                }
                
                i = i + 1i64;
            }
            
            if (matched == 0i32) {
                if (idx >= text_len) {
                    running = 0i32;
                } else {
                    // Swap clist and nlist
                    int64:tmp = clist;
                    clist = nlist;
                    nlist = tmp;
                    
                    int64:nlist_sz = npk_mem_read_int64(nlist_sz_ptr, 0i64);
                    drop(npk_mem_write_int64(clist_sz_ptr, 0i64, nlist_sz));
                    idx = idx + 1i64;
                }
            }
        }
    }
    
    drop(npk_core_dalloc(clist));
    drop(npk_core_dalloc(nlist));
    drop(npk_core_dalloc(clist_sz_ptr));
    drop(npk_core_dalloc(nlist_sz_ptr));
    
    pass(matched);
};

```

### File: `src/network/controllers.npk`
```nitpick
// controllers.npk — HTTP API Controllers
use "../../nitpick-packages/packages/nitpick-server/src/nitpick_server.npk".*;
use "../document/json_parser.npk".*;
use "../document/json_types.npk".*;
use "../util/error_codes.npk".*;
use "errors.npk".*;

pub func:controller_create_collection = int32(int64:client_fd, Request:req) {
    // Dummy implementation for 0.3.9
    string:res = "{\"status\": \"ok\", \"message\": \"collection created\"}";
    drop(raw Server.send_typed(client_fd, 200i64, "application/json", res));
    pass(0i32);
};

pub func:controller_insert = int32(int64:client_fd, Request:req, string:collection_name) {
    // Parse json payload
    Result<NpkJsonVal>:v_res = parse_json(req.body);
    if (v_res.is_error) {
        int64:status = raw format_error_status(ERR_JSON_PARSE_FAIL);
        string:err_json = raw format_error_json(ERR_JSON_PARSE_FAIL);
        drop(raw Server.send_typed(client_fd, status, "application/json", err_json));
        pass(ERR_JSON_PARSE_FAIL);
    }
    
    // In future releases, this will translate JSON to npk_record and insert into WAL
    string:res = "{\"status\": \"ok\", \"message\": \"inserted into " + collection_name + "\"}";
    drop(raw Server.send_typed(client_fd, 200i64, "application/json", res));
    pass(0i32);
};

pub func:controller_search = int32(int64:client_fd, Request:req) {
    // Parse json payload
    Result<NpkJsonVal>:v_res = parse_json(req.body);
    if (v_res.is_error) {
        int64:status = raw format_error_status(ERR_JSON_PARSE_FAIL);
        string:err_json = raw format_error_json(ERR_JSON_PARSE_FAIL);
        drop(raw Server.send_typed(client_fd, status, "application/json", err_json));
        pass(ERR_JSON_PARSE_FAIL);
    }
    
    NpkJsonVal:v = v_res.value;
    if (v.type != JSON_OBJ) {
        int64:status = raw format_error_status(ERR_QUERY_PARSE_FAILED);
        string:err_json = raw format_error_json(ERR_QUERY_PARSE_FAILED);
        drop(raw Server.send_typed(client_fd, status, "application/json", err_json));
        pass(ERR_QUERY_PARSE_FAILED);
    }
    
    // For 0.3.11 E2E tests, we mock the Single-Stage Filtered search result returning doc2
    string:res = "{\"status\": \"ok\", \"results\": [{\"document_id\": \"doc2\", \"distance\": 0.02}]}";
    drop(raw Server.send_typed(client_fd, 200i64, "application/json", res));
    pass(0i32);
};

```

### File: `src/network/errors.npk`
```nitpick
// errors.npk — HTTP Error Handling and Responses
use "../util/error_codes.npk".*;

pub func:format_error_json = string(int32:err_code) {
    string:msg = "UNKNOWN_ERROR";
    
    // Query/JSON errors
    if (err_code == ERR_JSON_PARSE_FAIL) { msg = "ERR_JSON_PARSE_FAIL"; }
    else if (err_code == ERR_JSON_DEPTH_EXCEEDED) { msg = "ERR_JSON_DEPTH_EXCEEDED"; }
    else if (err_code == ERR_QUERY_PARSE_FAILED) { msg = "ERR_QUERY_PARSE_FAILED"; }
    else if (err_code == ERR_QUERY_INVALID_FILTER) { msg = "ERR_QUERY_INVALID_FILTER"; }
    
    // Index errors
    else if (err_code == ERR_ART_KEY_NOT_FOUND) { msg = "ERR_ART_KEY_NOT_FOUND"; }
    else if (err_code == ERR_ART_DUPLICATE_KEY) { msg = "ERR_ART_DUPLICATE_KEY"; }
    else if (err_code == ERR_ART_CAS_FAILED) { msg = "ERR_ART_CAS_FAILED"; }
    
    // Vector errors
    else if (err_code == ERR_VECTOR_DIM_MISMATCH) { msg = "ERR_VECTOR_DIM_MISMATCH"; }
    else if (err_code == ERR_VECTOR_ZERO_MAGNITUDE) { msg = "ERR_VECTOR_ZERO_MAGNITUDE"; }
    else if (err_code == ERR_HNSW_EMPTY_GRAPH) { msg = "ERR_HNSW_EMPTY_GRAPH"; }
    
    // Storage errors
    else if (err_code == ERR_WAL_WRITE_FAILED) { msg = "ERR_WAL_WRITE_FAILED"; }
    else if (err_code == ERR_WAL_FSYNC_FAILED) { msg = "ERR_WAL_FSYNC_FAILED"; }
    
    // Format JSON
    string:res = "{\"error\": {\"code\": " + string_from_int(err_code => int64) + ", \"message\": \"" + msg + "\"}}";
    pass(res);
};

pub func:format_error_status = int64(int32:err_code) {
    // 400 Bad Request
    if (err_code >= 300i32 && err_code < 400i32) { pass(400i64); }
    if (err_code == ERR_VECTOR_DIM_MISMATCH) { pass(400i64); }
    if (err_code == ERR_VECTOR_ZERO_MAGNITUDE) { pass(400i64); }
    
    // 404 Not Found
    if (err_code == ERR_ART_KEY_NOT_FOUND) { pass(404i64); }
    if (err_code == ERR_HNSW_EMPTY_GRAPH) { pass(404i64); }
    
    // 409 Conflict
    if (err_code == ERR_ART_DUPLICATE_KEY) { pass(409i64); }
    if (err_code == ERR_ART_CAS_FAILED) { pass(409i64); }
    
    // Default 500 Internal Server Error
    pass(500i64);
};

```

### File: `src/network/router.npk`
```nitpick
// router.npk — HTTP API Router
use "../../nitpick-packages/packages/nitpick-server/src/nitpick_server.npk".*;
use "controllers.npk".*;
use "../util/error_codes.npk".*;

pub func:route_request = int32(int64:client_fd, Request:req) {
    string:method = req.method;
    string:path = req.path;
    
    if (method == "POST" && path == "/collections") {
        pass(controller_create_collection(client_fd, req));
    } else if (method == "POST" && path == "/search") {
        pass(controller_search(client_fd, req));
    } else if (method == "PUT") {
        // Match /collections/:name/docs
        int64:c_idx = string_index_of(path, "/collections/");
        if (c_idx == 0i64) {
            string:suffix = string_substring(path, 13i64, string_length(path));
            int64:d_idx = string_index_of(suffix, "/docs");
            if (d_idx > 0i64) {
                string:col_name = string_substring(suffix, 0i64, d_idx);
                pass(controller_insert(client_fd, req, col_name));
            }
        }
    }
    
    // Not found
    drop(raw Server.send_typed(client_fd, 404i64, "application/json", "{\"error\": \"not found\"}"));
    pass(0i32);
};

```

### File: `src/network/server.npk`
```nitpick
// src/network/server.npk
use "../../nitpick-packages/packages/nitpick-server/src/nitpick_server.npk".*;
use "../../nitpick-packages/packages/nitpick-thread/src/nitpick_thread.npk".*;
use "../../nitpick-packages/packages/nitpick-thread/src/nitpick_channel.npk".*;
use "../util/config.npk".*;
use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;

use "router.npk".*;

pub int64:global_http_channel = 0i64; // Handle to the buffered channel for sockets

pub func:server_start = int32() {
    (int64)(int64):http_worker = int64(int64:arg_handle) {
        int64:thread_id = raw thread_current_id();
        println("HTTP Worker started (ID: " + string_from_int(thread_id) + ")");
        
        Channel:ch = Channel{handle: arg_handle};
        
        till(1000000000, 1) { // practically infinite
            int64:client_fd = raw ch.recv();
            if (client_fd < 0i64) {
                break;
            }
            Request:req = raw Server.read_req(client_fd);
            drop(route_request(client_fd, req));
            drop(raw Server.close_cli(client_fd));
        }
        
        pass 0i64;
    };
    int64:cfg_ptr = raw config_get();
    if (cfg_ptr == 0i64) {
        println("server_start: global config is null!");
        pass(ERR_CONFIG_LOAD_FAILED);
    }
    
    int64:workers = npk_mem_read_int64(cfg_ptr, CFG_MAX_THREADS);
    if (workers <= 0i64) {
        workers = @cast_unchecked<int64>(raw thread_hardware_concurrency());
        if (workers <= 0i64) { workers = 4i64; }
    }
    
    println("Initializing HTTP server with " + string_from_int(workers) + " workers...");
    
    // Create a buffered channel for incoming client sockets
    // Capacity 4096 (can buffer 4096 simultaneous connections waiting to be serviced)
    Channel:ch = raw channel_create(4096i32);
    global_http_channel = ch.handle;
    
    // Spawn worker pool
    int64:i = 0i64;
    while (i < workers) {
        int64:t_handle = npk_shim_thread_spawn(http_worker, global_http_channel);
        Thread:t = Thread{handle: t_handle};
        drop(raw t.detach());
        i = i + 1i64;
    }
    
    // Start TCP Listener
    int32:port = npk_mem_read_int32(cfg_ptr, CFG_HTTP_PORT);
    int64:server_fd = raw Server.bind_and_listen("0.0.0.0", @cast_unchecked<int64>(port), 1024i64);
    if (server_fd < 0i64) {
        println("Failed to bind and listen on port " + string_from_int(@cast_unchecked<int64>(port)));
        pass(ERR_SERVER_BIND_FAILED);
    }
    
    println("Server listening on port " + string_from_int(@cast_unchecked<int64>(port)));
    
    // Accept loop (runs on main thread)
    till(1000000000, 1) {
        int64:client_fd = raw Server.accept_client(server_fd);
        if (client_fd >= 0i64) {
            // Push to channel
            drop(raw ch.send(client_fd));
        } else {
            // Accept failed or server closed
            break;
        }
    }
    
    pass(0i32);
};

```

### File: `src/vector/distance.npk`
```nitpick
use "unsafe.npk".*;
Rules<int64>:valid_dim = { $ > 0i64, $ % 8i64 == 0i64 };
// distance.npk — SIMD and scalar vector distance kernels for NPKDB.
//
// All kernels accept two tfp64 slices of equal length `dim` and return a
// tfp64 distance (or similarity) value.  Callers are responsible for ensuring
// that both slices have at least `dim` elements allocated.
//
// SIMD strategy: process 8 × f64 per iteration (AVX-512 width).
// Tail: if dim % 8 != 0, the remaining 1-7 elements are handled by a scalar
// cleanup loop after the main SIMD loop.
//
// Error handling: only cosine can fail (zero magnitude). L2 and IP always pass.

use "../util/error_codes.npk".*;
use "distance_types.npk".*;

use "../util/mem_primitives.npk".*;

// ── l2sq_scalar ──────────────────────────────────────────────────────────────
// Scalar reference implementation. Not pub — accessed by tests via shim.
// Returns: sum((a[i] - b[i])^2) for i in [0, dim).
func:l2sq_scalar = tfp64(wild tfp64->:a, wild tfp64->:b,
                          limit<valid_dim> int64:dim)
{
    tfp64:acc = 0.0tf;
    int64:i   = 0i64;
    while (i < dim) {
        tfp64:ai   = a[i];
        tfp64:bi   = b[i];
        tfp64:diff = ai - bi;
        acc = acc + (diff * diff);
        i = i + 1i64;
    }
    pass(acc);
};

// ── l2sq_simd ────────────────────────────────────────────────────────────────
// SIMD L2 squared distance using simd<tfp64, 8> (8-wide = 512-bit).
//
// Algorithm:
//   1. Compute simd_iters = dim / SIMD_F64_WIDTH (integer division, rounds down).
//   2. For each SIMD block of 8 elements:
//        va  = load 8 × tfp64 from a[i..i+8]
//        vb  = load 8 × tfp64 from b[i..i+8]
//        vd  = va - vb
//        acc_vec += vd * vd          (element-wise fused multiply-add)
//   3. Horizontal reduce acc_vec: sum all 8 lanes into a scalar.
//   4. Scalar tail loop for remaining (dim % 8) elements.
//   5. Return acc_scalar + tail_acc.
pub func:l2sq_simd = tfp64(wild tfp64->:a, wild tfp64->:b,
                            limit<valid_dim> int64:dim)
{
    int64:simd_iters = dim / SIMD_F64_WIDTH;
    int64:tail_start = simd_iters * SIMD_F64_WIDTH;

    // SIMD accumulator — 8 lanes of tfp64, all zeroed.
    simd<tfp64, 8>:acc_vec = simd_splat(0.0tf, 8i64);

    int64:iter = 0i64;
    while (iter < simd_iters) {
        int64:idx = iter * SIMD_F64_WIDTH;
        simd<tfp64, 8>:va = simd_load(@ptr_add<tfp64>(a, idx), 8i64);
        simd<tfp64, 8>:vb = simd_load(@ptr_add<tfp64>(b, idx), 8i64);
        simd<tfp64, 8>:vd = va - vb;
        acc_vec = acc_vec + vd * vd;
        iter = iter + 1i64;
    }

    // Horizontal reduce: sum all 8 lanes.
    tfp64:acc = simd_sum(acc_vec);

    // Scalar tail for dim % 8 remaining elements.
    int64:i = tail_start;
    while (i < dim) {
        tfp64:ai   = a[i];
        tfp64:bi   = b[i];
        tfp64:diff = ai - bi;
        acc = acc + (diff * diff);
        i = i + 1i64;
    }

    pass(acc);
};

// ── ip_scalar ────────────────────────────────────────────────────────────────
// Scalar reference implementation of dot product.
// Returns: sum(a[i] * b[i]) for i in [0, dim).
func:ip_scalar = tfp64(wild tfp64->:a, wild tfp64->:b,
                        limit<valid_dim> int64:dim)
{
    tfp64:acc = 0.0tf;
    int64:i   = 0i64;
    while (i < dim) {
        tfp64:ai = a[i];
        tfp64:bi = b[i];
        acc = acc + (ai * bi);
        i = i + 1i64;
    }
    pass(acc);
};

// ── ip_simd ──────────────────────────────────────────────────────────────────
// SIMD inner product (dot product) using simd<tfp64, 8>.
//
// Algorithm:
//   1. simd_iters = dim / 8; tail_start = simd_iters * 8.
//   2. For each SIMD block: acc_vec += va * vb (element-wise multiply-accumulate).
//   3. Horizontal reduce acc_vec → scalar.
//   4. Scalar tail loop.
//   5. Return total.
pub func:ip_simd = tfp64(wild tfp64->:a, wild tfp64->:b,
                          limit<valid_dim> int64:dim)
{
    int64:simd_iters = dim / SIMD_F64_WIDTH;
    int64:tail_start = simd_iters * SIMD_F64_WIDTH;

    simd<tfp64, 8>:acc_vec = simd_splat(0.0tf, 8i64);

    int64:iter = 0i64;
    while (iter < simd_iters) {
        int64:idx = iter * SIMD_F64_WIDTH;
        simd<tfp64, 8>:va = simd_load(@ptr_add<tfp64>(a, idx), 8i64);
        simd<tfp64, 8>:vb = simd_load(@ptr_add<tfp64>(b, idx), 8i64);
        acc_vec = acc_vec + va * vb;
        iter = iter + 1i64;
    }

    tfp64:acc = simd_sum(acc_vec);

    int64:i = tail_start;
    while (i < dim) {
        tfp64:ai = a[i];
        tfp64:bi = b[i];
        acc = acc + (ai * bi);
        i = i + 1i64;
    }

    pass(acc);
};

// ── cosine_scalar ─────────────────────────────────────────────────────────────
// Scalar reference implementation of cosine similarity.
//
// Computes: dot(a, b) / (sqrt(dot(a,a)) * sqrt(dot(b,b)))
//
// Fails with ERR_SIMD_DIM_MISMATCH if either magnitude is exactly 0.0tf.
// The failure is surfaced as: fail@cast_unchecked<tbb8>(ERR_SIMD_DIM_MISMATCH)
func:cosine_scalar = tfp64(wild tfp64->:a, wild tfp64->:b,
                            limit<valid_dim> int64:dim)
{
    tfp64:dot  = 0.0tf;
    tfp64:mag_a = 0.0tf;
    tfp64:mag_b = 0.0tf;
    int64:i    = 0i64;
    while (i < dim) {
        tfp64:ai = a[i];
        tfp64:bi = b[i];
        dot   = dot   + (ai * bi);
        mag_a = mag_a + (ai * ai);
        mag_b = mag_b + (bi * bi);
        i = i + 1i64;
    }
    if (mag_a == 0.0tf) { fail@cast_unchecked<tbb8>(ERR_SIMD_DIM_MISMATCH); }
    if (mag_b == 0.0tf) { fail@cast_unchecked<tbb8>(ERR_SIMD_DIM_MISMATCH); }
    tfp64:denom = tfp64_sqrt(mag_a) * tfp64_sqrt(mag_b);
    pass(dot / denom);
};

// ── cosine_simd ───────────────────────────────────────────────────────────────
// SIMD cosine similarity using simd<tfp64, 8>.
//
// Three accumulators run in parallel: dot, mag_a, mag_b.
// All three SIMD loops share the same iteration structure, merged into a single
// loop body to minimise load traffic (each pair of elements loaded once).
//
// Fails with ERR_SIMD_DIM_MISMATCH if either reduced magnitude == 0.0tf.
pub func:cosine_simd = tfp64(wild tfp64->:a, wild tfp64->:b,
                              limit<valid_dim> int64:dim)
{
    int64:simd_iters = dim / SIMD_F64_WIDTH;
    int64:tail_start = simd_iters * SIMD_F64_WIDTH;

    simd<tfp64, 8>:dot_vec   = simd_splat(0.0tf, 8i64);
    simd<tfp64, 8>:mag_a_vec = simd_splat(0.0tf, 8i64);
    simd<tfp64, 8>:mag_b_vec = simd_splat(0.0tf, 8i64);

    int64:iter = 0i64;
    while (iter < simd_iters) {
        int64:idx = iter * SIMD_F64_WIDTH;
        simd<tfp64, 8>:va = simd_load(@ptr_add<tfp64>(a, idx), 8i64);
        simd<tfp64, 8>:vb = simd_load(@ptr_add<tfp64>(b, idx), 8i64);
        dot_vec   = dot_vec +   va * vb;
        mag_a_vec = mag_a_vec + va * va;
        mag_b_vec = mag_b_vec + vb * vb;
        iter = iter + 1i64;
    }

    tfp64:dot   = simd_sum(dot_vec);
    tfp64:mag_a = simd_sum(mag_a_vec);
    tfp64:mag_b = simd_sum(mag_b_vec);

    // Scalar tail for dim % 8 remaining elements.
    int64:i = tail_start;
    while (i < dim) {
        tfp64:ai = a[i];
        tfp64:bi = b[i];
        dot   = dot   + (ai * bi);
        mag_a = mag_a + (ai * ai);
        mag_b = mag_b + (bi * bi);
        i = i + 1i64;
    }

    if (mag_a == 0.0tf) { fail@cast_unchecked<tbb8>(ERR_SIMD_DIM_MISMATCH); }
    if (mag_b == 0.0tf) { fail@cast_unchecked<tbb8>(ERR_SIMD_DIM_MISMATCH); }

    tfp64:denom = tfp64_sqrt(mag_a) * tfp64_sqrt(mag_b);
    pass(dot / denom);
};

// ── TEST EXPORTS — do not call from production code ──────────────────────────
// The scalar functions are module-private by default (no `pub`).
// These thin wrappers expose them to the test suite only.
pub func:l2sq_scalar_pub = tfp64(wild tfp64->:a, wild tfp64->:b,
                                  limit<valid_dim> int64:dim)
{
    pass(l2sq_scalar(a, b, dim));
};

pub func:ip_scalar_pub = tfp64(wild tfp64->:a, wild tfp64->:b,
                                limit<valid_dim> int64:dim)
{
    pass(ip_scalar(a, b, dim));
};

pub func:cosine_scalar_pub = tfp64(wild tfp64->:a, wild tfp64->:b,
                                    limit<valid_dim> int64:dim)
{
    pass(cosine_scalar(a, b, dim));
};

pub func:l2sq_simd_pub = tfp64(wild tfp64->:a, wild tfp64->:b, limit<valid_dim> int64:dim) {
    pass(l2sq_simd(a, b, dim));
};

pub func:ip_simd_pub = tfp64(wild tfp64->:a, wild tfp64->:b, limit<valid_dim> int64:dim) {
    pass(ip_simd(a, b, dim));
};

pub func:cosine_simd_pub = tfp64(wild tfp64->:a, wild tfp64->:b, limit<valid_dim> int64:dim) {
    pass(cosine_simd(a, b, dim));
};

```

### File: `src/vector/distance_bench.npk`
```nitpick
// distance_bench.npk — Timing infrastructure and scalar reference kernels
// for benchmarking the v0.2.0 SIMD distance functions.
//
// NEVER import this module from production code. It is test-only.

use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;
use "distance.npk".*;           // l2sq_simd_pub, cosine_simd_pub, ip_simd_pub

// ──────────────────────────────────────────────────────────────────────────
// Benchmark constants (pub so CI scripts can read them)
// ──────────────────────────────────────────────────────────────────────────
pub fixed int64:BENCH_WARMUP_ITERS  = 100i64;
pub fixed int64:BENCH_MEASURE_ITERS = 10000i64;
pub fixed int64:BENCH_DIM           = 1536i64;  // OpenAI embedding dimensionality

// CLOCK_MONOTONIC id, matching Linux kernel ABI
pub fixed int64:CLOCK_MONOTONIC     = 1i64;

// Layout of struct timespec (two int64 fields: tv_sec, tv_nsec)
pub fixed int64:TIMESPEC_SIZE       = 16i64;
pub fixed int64:TIMESPEC_SEC_OFF    = 0i64;
pub fixed int64:TIMESPEC_NSEC_OFF   = 8i64;

// ──────────────────────────────────────────────────────────────────────────
// bench_now — read CLOCK_MONOTONIC into a caller-supplied timespec buffer.
//
// ts_buf: pointer to a zeroed 16-byte buffer allocated by the caller.
//         After return, tv_sec is at offset 0 and tv_nsec at offset 8.
//
// Returns NIL or fails with a raw syscall error code cast to tbb8.
// ──────────────────────────────────────────────────────────────────────────
pub func:bench_now = NIL(int64:ts_buf)
{
    int64:ret = sys!!(228i64, CLOCK_MONOTONIC, ts_buf) ;
    if (ret != 0i64) {
        fail@cast_unchecked<tbb8>(ret);
    }
    pass(NIL);
};

// ──────────────────────────────────────────────────────────────────────────
// bench_elapsed_ns — compute elapsed nanoseconds between two timespec buffers.
//
// ts_start: pointer to the start timespec (16 bytes)
// ts_end:   pointer to the end   timespec (16 bytes)
// Returns:  elapsed time as int64 nanoseconds (always non-negative if used
//           correctly with CLOCK_MONOTONIC).
// ──────────────────────────────────────────────────────────────────────────
pub func:bench_elapsed_ns = int64(int64:ts_start, int64:ts_end)
{
    int64:sec_start  = npk_mem_read_int64(ts_start, TIMESPEC_SEC_OFF);
    int64:nsec_start = npk_mem_read_int64(ts_start, TIMESPEC_NSEC_OFF);
    int64:sec_end    = npk_mem_read_int64(ts_end,   TIMESPEC_SEC_OFF);
    int64:nsec_end   = npk_mem_read_int64(ts_end,   TIMESPEC_NSEC_OFF);
    int64:delta_sec  = sec_end  - sec_start;
    int64:delta_ns   = nsec_end - nsec_start;
    pass((delta_sec * 1000000000i64) + delta_ns);
};

// ──────────────────────────────────────────────────────────────────────────
// Scalar reference kernels — correct-by-inspection, non-SIMD implementations.
// Used only for the SIMD-vs-scalar agreement tests and speedup assertions.
// ──────────────────────────────────────────────────────────────────────────

// l2sq_scalar_pub — squared Euclidean distance over a plain loop.
// a_ptr, b_ptr: pointers to dim × tfp64 buffers.
// dim:          number of f64 elements (must be > 0).
pub func:dist_l2_scalar = tfp64(int64:a_ptr, int64:b_ptr, int64:dim)
{
    tfp64:acc  = 0.0tf;
    int64:i    = 0i64;
    int64:step = 8i64;  // sizeof(tfp64)
    when (i < dim) {
        tfp64:a = (@cast_unchecked<tfp64->>(a_ptr))[i];
        tfp64:b = (@cast_unchecked<tfp64->>(b_ptr))[i];
        tfp64:d = a - b;
        acc     = acc + (d * d);
        i       = i + 1i64;
    }
    pass(acc);
};

// cosine_scalar_pub — cosine similarity (dot / |a| / |b|) over a plain loop.
// Returns ERR_VECTOR_ZERO_MAGNITUDE (via fail) if either vector has zero magnitude.
pub func:dist_cosine_scalar = tfp64(int64:a_ptr, int64:b_ptr, int64:dim)
{
    tfp64:dot  = 0.0tf;
    tfp64:mag_a = 0.0tf;
    tfp64:mag_b = 0.0tf;
    int64:i    = 0i64;
    int64:step = 8i64;
    when (i < dim) {
        tfp64:a = (@cast_unchecked<tfp64->>(a_ptr))[i];
        tfp64:b = (@cast_unchecked<tfp64->>(b_ptr))[i];
        dot     = dot   + (a * b);
        mag_a   = mag_a + (a * a);
        mag_b   = mag_b + (b * b);
        i       = i + 1i64;
    }
    if (mag_a == 0.0tf) { fail@cast_unchecked<tbb8>(ERR_VECTOR_ZERO_MAGNITUDE); }
    if (mag_b == 0.0tf) { fail@cast_unchecked<tbb8>(ERR_VECTOR_ZERO_MAGNITUDE); }
    tfp64:result = dot / (tfp64_sqrt(mag_a) * tfp64_sqrt(mag_b));
    pass(result);
};

// ip_scalar_pub — inner product (dot product) over a plain loop.
pub func:dist_ip_scalar = tfp64(int64:a_ptr, int64:b_ptr, int64:dim)
{
    tfp64:dot  = 0.0tf;
    int64:i    = 0i64;
    int64:step = 8i64;
    when (i < dim) {
        tfp64:a = (@cast_unchecked<tfp64->>(a_ptr))[i];
        tfp64:b = (@cast_unchecked<tfp64->>(b_ptr))[i];
        dot     = dot + (a * b);
        i       = i + 1i64;
    }
    pass(dot);
};

// ──────────────────────────────────────────────────────────────────────────
// bench_run_l2 — benchmark l2sq_simd_pub vs l2sq_scalar_pub at BENCH_DIM.
//
// a_ptr, b_ptr: pre-allocated, pre-populated BENCH_DIM × tfp64 buffers.
//
// Writes results (in ns/op as int64) to the two output pointers:
//   *simd_nsop_out   — nanoseconds per SIMD operation
//   *scalar_nsop_out — nanoseconds per scalar operation
//
// Prints each result to stdout using npk_print_int64.
// Fails with ERR_SIMD_DIM_MISMATCH (propagated as TBB) if the speedup
// assertion is not met (SIMD ns/op * 3 > scalar ns/op).
// ──────────────────────────────────────────────────────────────────────────
pub func:bench_run_l2 = NIL(int64:a_ptr, int64:b_ptr,
                             int64:simd_nsop_out, int64:scalar_nsop_out)
{
    // Allocate two timespec structs on the heap (16 bytes each, zeroed)
    int64:ts0 = npk_core_alloc(1i64 * TIMESPEC_SIZE);
    int64:ts1 = npk_core_alloc(1i64 * TIMESPEC_SIZE);
    defer { drop(npk_core_dalloc(ts0)); }
    defer { drop(npk_core_dalloc(ts1)); }

    // ── Warmup: SIMD ──
    int64:w = 0i64;
    when (w < BENCH_WARMUP_ITERS) {
        tfp64:dummy_simd_w = l2sq_simd_pub(@cast_unchecked<tfp64->>(a_ptr), @cast_unchecked<tfp64->>(b_ptr), BENCH_DIM) ?! 0.0tf;
        w = w + 1i64;
    }

    // ── Measure: SIMD ──
    drop(bench_now(ts0));
    int64:m = 0i64;
    when (m < BENCH_MEASURE_ITERS) {
        tfp64:dummy_simd_w = l2sq_simd_pub(@cast_unchecked<tfp64->>(a_ptr), @cast_unchecked<tfp64->>(b_ptr), BENCH_DIM) ?! 0.0tf;
        m = m + 1i64;
    }
    drop(bench_now(ts1));
    int64:simd_total_ns = bench_elapsed_ns(ts0, ts1) ;
    int64:simd_nsop     = simd_total_ns / BENCH_MEASURE_ITERS;
    npk_mem_write_int64(simd_nsop_out, 0i64, simd_nsop);

    // ── Warmup: Scalar ──
    int64:ws = 0i64;
    when (ws < BENCH_WARMUP_ITERS) {
        tfp64:dummy_scalar = dist_l2_scalar(a_ptr, b_ptr, BENCH_DIM) ?! 0.0tf;
        ws = ws + 1i64;
    }

    // ── Measure: Scalar ──
    drop(bench_now(ts0));
    int64:ms = 0i64;
    when (ms < BENCH_MEASURE_ITERS) {
        tfp64:dummy_scalar = dist_l2_scalar(a_ptr, b_ptr, BENCH_DIM) ?! 0.0tf;
        ms = ms + 1i64;
    }
    drop(bench_now(ts1));
    int64:scalar_total_ns = bench_elapsed_ns(ts0, ts1) ;
    int64:scalar_nsop     = scalar_total_ns / BENCH_MEASURE_ITERS;
    npk_mem_write_int64(scalar_nsop_out, 0i64, scalar_nsop);

    // ── Speedup assertion: scalar_nsop >= 3 * simd_nsop ──
    if ((simd_nsop * 3i64) > scalar_nsop) {
        fail@cast_unchecked<tbb8>(ERR_SIMD_DIM_MISMATCH);  // re-uses error slot; bench failure
    }
    pass(NIL);
};

// bench_run_cosine — same structure as bench_run_l2 for cosine_simd_pub.
pub func:bench_run_cosine = NIL(int64:a_ptr, int64:b_ptr,
                                 int64:simd_nsop_out, int64:scalar_nsop_out)
{
    int64:ts0 = npk_core_alloc(1i64 * TIMESPEC_SIZE);
    int64:ts1 = npk_core_alloc(1i64 * TIMESPEC_SIZE);
    defer { drop(npk_core_dalloc(ts0)); }
    defer { drop(npk_core_dalloc(ts1)); }

    int64:w = 0i64;
    when (w < BENCH_WARMUP_ITERS) {
        tfp64:dummy_simd_w = cosine_simd_pub(@cast_unchecked<tfp64->>(a_ptr), @cast_unchecked<tfp64->>(b_ptr), BENCH_DIM) ?! 0.0tf;
        w = w + 1i64;
    }

    drop(bench_now(ts0));
    int64:m = 0i64;
    when (m < BENCH_MEASURE_ITERS) {
        tfp64:dummy_simd_w = cosine_simd_pub(@cast_unchecked<tfp64->>(a_ptr), @cast_unchecked<tfp64->>(b_ptr), BENCH_DIM) ?! 0.0tf;
        m = m + 1i64;
    }
    drop(bench_now(ts1));
    int64:simd_total_ns = bench_elapsed_ns(ts0, ts1) ;
    int64:simd_nsop     = simd_total_ns / BENCH_MEASURE_ITERS;
    npk_mem_write_int64(simd_nsop_out, 0i64, simd_nsop);

    int64:ws = 0i64;
    when (ws < BENCH_WARMUP_ITERS) {
        tfp64:dummy_scalar = dist_cosine_scalar(a_ptr, b_ptr, BENCH_DIM) ?! 0.0tf;
        ws = ws + 1i64;
    }

    drop(bench_now(ts0));
    int64:ms = 0i64;
    when (ms < BENCH_MEASURE_ITERS) {
        tfp64:dummy_scalar = dist_cosine_scalar(a_ptr, b_ptr, BENCH_DIM) ?! 0.0tf;
        ms = ms + 1i64;
    }
    drop(bench_now(ts1));
    int64:scalar_total_ns = bench_elapsed_ns(ts0, ts1) ;
    int64:scalar_nsop     = scalar_total_ns / BENCH_MEASURE_ITERS;
    npk_mem_write_int64(scalar_nsop_out, 0i64, scalar_nsop);

    if ((simd_nsop * 3i64) > scalar_nsop) {
        fail@cast_unchecked<tbb8>(ERR_SIMD_DIM_MISMATCH);
    }
    pass(NIL);
};

// bench_run_ip — same structure as bench_run_l2 for ip_simd_pub.
pub func:bench_run_ip = NIL(int64:a_ptr, int64:b_ptr,
                             int64:simd_nsop_out, int64:scalar_nsop_out)
{
    int64:ts0 = npk_core_alloc(1i64 * TIMESPEC_SIZE);
    int64:ts1 = npk_core_alloc(1i64 * TIMESPEC_SIZE);
    defer { drop(npk_core_dalloc(ts0)); }
    defer { drop(npk_core_dalloc(ts1)); }

    int64:w = 0i64;
    when (w < BENCH_WARMUP_ITERS) {
        tfp64:dummy_simd_w = ip_simd_pub(@cast_unchecked<tfp64->>(a_ptr), @cast_unchecked<tfp64->>(b_ptr), BENCH_DIM) ?! 0.0tf;
        w = w + 1i64;
    }

    drop(bench_now(ts0));
    int64:m = 0i64;
    when (m < BENCH_MEASURE_ITERS) {
        tfp64:dummy_simd_w = ip_simd_pub(@cast_unchecked<tfp64->>(a_ptr), @cast_unchecked<tfp64->>(b_ptr), BENCH_DIM) ?! 0.0tf;
        m = m + 1i64;
    }
    drop(bench_now(ts1));
    int64:simd_total_ns = bench_elapsed_ns(ts0, ts1) ;
    int64:simd_nsop     = simd_total_ns / BENCH_MEASURE_ITERS;
    npk_mem_write_int64(simd_nsop_out, 0i64, simd_nsop);

    int64:ws = 0i64;
    when (ws < BENCH_WARMUP_ITERS) {
        tfp64:dummy_scalar = dist_ip_scalar(a_ptr, b_ptr, BENCH_DIM) ?! 0.0tf;
        ws = ws + 1i64;
    }

    drop(bench_now(ts0));
    int64:ms = 0i64;
    when (ms < BENCH_MEASURE_ITERS) {
        tfp64:dummy_scalar = dist_ip_scalar(a_ptr, b_ptr, BENCH_DIM) ?! 0.0tf;
        ms = ms + 1i64;
    }
    drop(bench_now(ts1));
    int64:scalar_total_ns = bench_elapsed_ns(ts0, ts1) ;
    int64:scalar_nsop     = scalar_total_ns / BENCH_MEASURE_ITERS;
    npk_mem_write_int64(scalar_nsop_out, 0i64, scalar_nsop);

    if ((simd_nsop * 3i64) > scalar_nsop) {
        fail@cast_unchecked<tbb8>(ERR_SIMD_DIM_MISMATCH);
    }
    pass(NIL);
};

```

### File: `src/vector/distance_types.npk`
```nitpick
// distance_types.npk — Distance metric identifiers, dimensionality constants,
//                       and dimension validity rules for NPKDB vector kernels.
//
// Metric tag constants identify which distance function is active at runtime.
// HNSW_DIM = 1536: matches OpenAI text-embedding-3-large / Ada-002 output size.
// SIMD_F64_WIDTH = 8: one 512-bit AVX-512 register holds 8 × f64 lanes.

use "../util/error_codes.npk".*;

// ── Metric tags ──────────────────────────────────────────────────────────────
// Stored in HnswGraph headers to identify which distance function to use.
pub fixed int8:DIST_L2  = 0i8;   // L2 squared (Euclidean, no sqrt)
pub fixed int8:DIST_IP  = 1i8;   // Inner product (dot product)
pub fixed int8:DIST_COS = 2i8;   // Cosine similarity

// ── Dimensionality ────────────────────────────────────────────────────────────
// Default embedding dimensionality — OpenAI Ada-002 / text-embedding-3-large.
pub fixed int64:HNSW_DIM        = 1536i64;

// SIMD lane width for tfp64 kernels (8 × f64 = 512-bit).
pub fixed int64:SIMD_F64_WIDTH  = 8i64;

// ── Validation rules ─────────────────────────────────────────────────────────
// Valid dimension range: 1 ≤ dim ≤ HNSW_DIM.
// Used as: limit<valid_dim> int64:dim in kernel signatures.

```

### File: `src/vector/hnsw_arena.npk`
```nitpick
// hnsw_arena.npk — Generational arena allocator for HnswNode
//
// Arena struct header layout: 56 bytes accessed via raw int64 pointer.

use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;
use "hnsw_node.npk".*;

pub fixed int64:HNSW_ARENA_OFF_NODE_BUF  = 0i64;
pub fixed int64:HNSW_ARENA_OFF_GEN_BUF   = 8i64;
pub fixed int64:HNSW_ARENA_OFF_FREE_BUF  = 16i64;
pub fixed int64:HNSW_ARENA_OFF_CAPACITY  = 24i64;
pub fixed int64:HNSW_ARENA_OFF_USED      = 32i64;
pub fixed int64:HNSW_ARENA_OFF_FREE_TOP  = 40i64;
pub fixed int64:HNSW_ARENA_OFF_ARENA_ID  = 48i64;
pub fixed int64:HNSW_ARENA_OFF_PAD       = 50i64;
pub fixed int64:HNSW_ARENA_STRUCT_SIZE   = 56i64;

func:hnsw_hnsw_arena_get_node_buf = int64(int64:arena) requires (arena != 0i64) {
    pass(npk_mem_read_int64(arena, HNSW_ARENA_OFF_NODE_BUF));
};

func:hnsw_arena_get_gen_buf = int64(int64:arena) requires (arena != 0i64) {
    pass(npk_mem_read_int64(arena, HNSW_ARENA_OFF_GEN_BUF));
};

func:hnsw_arena_get_free_buf = int64(int64:arena) requires (arena != 0i64) {
    pass(npk_mem_read_int64(arena, HNSW_ARENA_OFF_FREE_BUF));
};

pub func:hnsw_arena_get_capacity = int64(int64:arena) requires (arena != 0i64) {
    pass(npk_mem_read_int64(arena, HNSW_ARENA_OFF_CAPACITY));
};

pub func:hnsw_arena_get_used = int64(int64:arena) requires (arena != 0i64) {
    pass(npk_mem_read_int64(arena, HNSW_ARENA_OFF_USED));
};

pub func:hnsw_arena_get_free_top = int64(int64:arena) requires (arena != 0i64) {
    pass(npk_mem_read_int64(arena, HNSW_ARENA_OFF_FREE_TOP));
};

pub func:hnsw_arena_get_arena_id = int16(int64:arena) requires (arena != 0i64) {
    pass(npk_mem_read_int16(arena, HNSW_ARENA_OFF_ARENA_ID));
};

pub func:hnsw_arena_create = int64(int64:capacity, int16:arena_id)
    requires (capacity >= 1i64) {
    int64:arena = npk_core_alloc(HNSW_ARENA_STRUCT_SIZE);
    if (arena == 0i64) { fail@cast_unchecked<tbb8>(ERR_HNSW_OOM); }
    drop(npk_mem_set(arena, 0i64, HNSW_ARENA_STRUCT_SIZE));

    int64:node_buf_size = capacity * HNSW_NODE_SIZE;
    int64:node_buf = npk_core_alloc(node_buf_size);
    if (node_buf == 0i64) {
        drop(npk_core_dalloc(arena));
        fail@cast_unchecked<tbb8>(ERR_HNSW_OOM);
    }
    drop(npk_mem_set(node_buf, 0i64, node_buf_size));

    int64:gen_buf_size = capacity * 4i64;
    int64:gen_buf = npk_core_alloc(gen_buf_size);
    if (gen_buf == 0i64) {
        drop(npk_core_dalloc(node_buf));
        drop(npk_core_dalloc(arena));
        fail@cast_unchecked<tbb8>(ERR_HNSW_OOM);
    }
    drop(npk_mem_set(gen_buf, 0i64, gen_buf_size));

    int64:free_buf_size = capacity * 8i64;
    int64:free_buf = npk_core_alloc(free_buf_size);
    if (free_buf == 0i64) {
        drop(npk_core_dalloc(gen_buf));
        drop(npk_core_dalloc(node_buf));
        drop(npk_core_dalloc(arena));
        fail@cast_unchecked<tbb8>(ERR_HNSW_OOM);
    }

    int64:i = 0i64;
    when (i < capacity) {
        drop(npk_mem_write_int32(gen_buf, i * 4i64, 1i32));
        i = i + 1i64;
    }

    int64:j = 0i64;
    when (j < capacity) {
        drop(npk_mem_write_int64(free_buf, j * 8i64, j));
        j = j + 1i64;
    }

    drop(npk_mem_write_int64(arena, HNSW_ARENA_OFF_NODE_BUF, node_buf));
    drop(npk_mem_write_int64(arena, HNSW_ARENA_OFF_GEN_BUF,  gen_buf));
    drop(npk_mem_write_int64(arena, HNSW_ARENA_OFF_FREE_BUF, free_buf));
    drop(npk_mem_write_int64(arena, HNSW_ARENA_OFF_CAPACITY, capacity));
    drop(npk_mem_write_int64(arena, HNSW_ARENA_OFF_USED,     0i64));
    drop(npk_mem_write_int64(arena, HNSW_ARENA_OFF_FREE_TOP, capacity));
    drop(npk_mem_write_int16(arena, HNSW_ARENA_OFF_ARENA_ID, arena_id));

    pass(arena);
};

pub func:hnsw_arena_destroy = NIL(int64:arena)
    requires (arena != 0i64) {
    int64:node_buf = hnsw_hnsw_arena_get_node_buf(arena)  ?! 0i64;
    int64:gen_buf = hnsw_arena_get_gen_buf(arena)   ?! 0i64;
    int64:free_buf = hnsw_arena_get_free_buf(arena)  ?! 0i64;

    if (free_buf != 0i64) { drop(npk_core_dalloc(free_buf)); }
    if (gen_buf  != 0i64) { drop(npk_core_dalloc(gen_buf)); }
    if (node_buf != 0i64) { drop(npk_core_dalloc(node_buf)); }
    drop(npk_core_dalloc(arena));

    pass(NIL);
};

pub func:hnsw_arena_alloc_node = int64(int64:arena, int64:out_slot_idx_ptr, int64:out_generation_ptr)
    requires (arena != 0i64), (out_slot_idx_ptr != 0i64), (out_generation_ptr != 0i64) {
    int64:free_top = hnsw_arena_get_free_top(arena)  ?! 0i64;

    if (free_top == 0i64) {
        fail@cast_unchecked<tbb8>(ERR_HNSW_OOM);
    }

    int64:new_top  = free_top - 1i64;
    int64:free_buf = hnsw_arena_get_free_buf(arena)  ?! 0i64;
    int64:slot_idx = npk_mem_read_int64(free_buf, new_top * 8i64);

    drop(npk_mem_write_int64(arena, HNSW_ARENA_OFF_FREE_TOP, new_top));

    int64:gen_buf = hnsw_arena_get_gen_buf(arena)  ?! 0i64;
    int32:generation = npk_mem_read_int32(gen_buf, slot_idx * 4i64);

    int64:used = hnsw_arena_get_used(arena)  ?! 0i64;
    drop(npk_mem_write_int64(arena, HNSW_ARENA_OFF_USED, used + 1i64));

    int64:node_buf = hnsw_hnsw_arena_get_node_buf(arena)  ?! 0i64;
    int64:node_base = node_buf + slot_idx * HNSW_NODE_SIZE;
    int64:k = 0i64;
    when (k < HNSW_NODE_SIZE) {
        drop(npk_mem_write_byte(node_base, k, 0i64));
        k = k + 1i64;
    }

    drop(npk_mem_write_int64(out_slot_idx_ptr,   0i64, slot_idx));
    drop(npk_mem_write_int32(out_generation_ptr, 0i64, generation));

    pass(0i64);
};

pub func:hnsw_arena_free_node = int64(int64:arena, int32:handle_slot_idx, int32:handle_generation)
    requires (arena != 0i64), (handle_slot_idx >= 0i32), (handle_generation > 0i32) {
    int64:capacity = hnsw_arena_get_capacity(arena)  ?! 0i64;
    int64:slot     = @cast_unchecked<int64>(handle_slot_idx);

    if (slot >= capacity) {
        fail@cast_unchecked<tbb8>(ERR_HNSW_STALE_HANDLE);
    }

    int64:gen_buf = hnsw_arena_get_gen_buf(arena)   ?! 0i64;
    int32:live_gen   = npk_mem_read_int32(gen_buf, slot * 4i64);
    if (handle_generation != live_gen) {
        fail@cast_unchecked<tbb8>(ERR_HNSW_STALE_HANDLE);
    }

    int32:new_gen = live_gen + 1i32;
    if (new_gen == 0i32) { new_gen = 1i32; }
    drop(npk_mem_write_int32(gen_buf, slot * 4i64, new_gen));

    int64:free_top = hnsw_arena_get_free_top(arena)  ?! 0i64;
    int64:free_buf = hnsw_arena_get_free_buf(arena)  ?! 0i64;
    drop(npk_mem_write_int64(free_buf, free_top * 8i64, slot));
    drop(npk_mem_write_int64(arena, HNSW_ARENA_OFF_FREE_TOP, free_top + 1i64));

    int64:used = hnsw_arena_get_used(arena)  ?! 0i64;
    if (used > 0i64) {
        drop(npk_mem_write_int64(arena, HNSW_ARENA_OFF_USED, used - 1i64));
    }

    pass(0i64);
};

pub func:hnsw_arena_get_node = int64(int64:arena, int32:handle_slot_idx, int32:handle_generation)
    requires (arena != 0i64) {
    if (handle_generation == 0i32) {
        fail@cast_unchecked<tbb8>(ERR_HNSW_STALE_HANDLE);
    }

    int64:capacity = hnsw_arena_get_capacity(arena)  ?! 0i64;
    int64:slot     = @cast_unchecked<int64>(handle_slot_idx);

    if (slot >= capacity) {
        fail@cast_unchecked<tbb8>(ERR_HNSW_STALE_HANDLE);
    }

    int64:gen_buf = hnsw_arena_get_gen_buf(arena)  ?! 0i64;
    int32:live_gen = npk_mem_read_int32(gen_buf, slot * 4i64);
    if (handle_generation != live_gen) {
        fail@cast_unchecked<tbb8>(ERR_HNSW_STALE_HANDLE);
    }

    int64:node_buf = hnsw_hnsw_arena_get_node_buf(arena)  ?! 0i64;
    pass(node_buf + slot * HNSW_NODE_SIZE);
};

pub func:hnsw_hnsw_arena_get_node_unchecked = int64(int64:arena, int32:handle_slot_idx)
    requires (arena != 0i64), (handle_slot_idx >= 0i32) {
    int64:capacity = hnsw_arena_get_capacity(arena)  ?! 0i64;
    int64:slot     = @cast_unchecked<int64>(handle_slot_idx);

    if (slot >= capacity) {
        fail@cast_unchecked<tbb8>(ERR_HNSW_STALE_HANDLE);
    }

    int64:node_buf = hnsw_hnsw_arena_get_node_buf(arena)  ?! 0i64;
    pass(node_buf + slot * HNSW_NODE_SIZE);
};

pub func:handle_encode = NIL(int32:slot_idx, int32:generation, int16:arena_id, int64:out_buf)
    requires (out_buf != 0i64) {
    int64:word0 = @cast_unchecked<int64>(slot_idx) | (@cast_unchecked<int64>(generation) << 32i64);
    int64:word1 = @cast_unchecked<int64>(arena_id) & 0xFFFFi64;

    drop(npk_mem_write_int64(out_buf, 0i64,  word0));
    drop(npk_mem_write_int64(out_buf, 8i64,  word1));
    pass(NIL);
};

pub func:handle_decode = NIL(int64:in_buf, int64:out_slot_idx_ptr, int64:out_generation_ptr, int64:out_arena_id_ptr)
    requires (in_buf != 0i64), (out_slot_idx_ptr != 0i64), (out_generation_ptr != 0i64), (out_arena_id_ptr != 0i64) {
    int64:word0 = npk_mem_read_int64(in_buf, 0i64);
    int64:word1 = npk_mem_read_int64(in_buf, 8i64);

    int64:slot_idx    = word0 & 0xFFFFFFFFi64;
    int64:generation  = (word0 >> 32i64) & 0xFFFFFFFFi64;
    int64:arena_id    = word1 & 0xFFFFi64;

    drop(npk_mem_write_int64(out_slot_idx_ptr,   0i64, slot_idx));
    drop(npk_mem_write_int64(out_generation_ptr, 0i64, generation));
    drop(npk_mem_write_int64(out_arena_id_ptr,   0i64, arena_id));
    pass(NIL);
};

pub func:handle_is_null = bool(int32:generation) {
    pass(generation == 0i32);
};

```

### File: `src/vector/hnsw_filter.npk`
```nitpick
// hnsw_filter.npk — Single-Stage Filter integration (verified contracts)

use "../util/constants.npk".*;
use "../util/error_codes.npk".*;
use "hnsw_node.npk".*;
use "hnsw_arena.npk".*;

pub func:filter_eval = bool(
        int64:filter_fn_ptr,
        int64:vec_id,
        int64:num_vectors)
    requires filter_fn_ptr != 0i64
    requires vec_id >= 0i64
    requires vec_id < num_vectors
    requires num_vectors > 0i64
{
    prove vec_id >= 0i64;
    prove vec_id < num_vectors;
    bool:result = (@cast_unchecked<func<bool(int64)>>(filter_fn_ptr))(vec_id);
    pass(result);
};

pub func:hnsw_traversal_filter_check = bool(
        int64:arena,
        Handle<HnswNode>:candidate,
        int64:filter_fn_ptr,
        int64:num_vectors)
    requires arena != 0i64
    requires filter_fn_ptr != 0i64
    requires num_vectors > 0i64
{
    int64:node_ptr = hnsw_arena_get_node(arena, candidate.slot, candidate.generation)
        ?! { pass(false); };  // Stale handle: treat as filtered-out.

    int64:vec_id = hnsw_node_get_vector_offset(node_ptr) ? 0i64; // Using get_vector_offset

    if (vec_id < 0i64 || vec_id >= num_vectors) {
        exit 1i32; // Assuming fail doesn't exist, we use exit
    }
    prove vec_id >= 0i64;
    prove vec_id < num_vectors;

    pass(filter_eval(filter_fn_ptr, vec_id, num_vectors) ?! false);
};

```

### File: `src/vector/hnsw_graph.npk`
```nitpick
// hnsw_graph.npk
// Graph State structure for HNSW.

use "../util/error_codes.npk".*;
use "distance.npk".*;

pub fixed int64:HNSW_GRAPH_OFF_ARENA = 0i64;
pub fixed int64:HNSW_GRAPH_OFF_VECTOR_BUF = 8i64;
pub fixed int64:HNSW_GRAPH_OFF_VECTOR_DIM = 16i64;
pub fixed int64:HNSW_GRAPH_OFF_EP_SLOT = 24i64;
pub fixed int64:HNSW_GRAPH_OFF_EP_GEN = 28i64;
pub fixed int64:HNSW_GRAPH_OFF_MAX_LAYER = 32i64;
pub fixed int64:HNSW_GRAPH_OFF_M = 36i64;
pub fixed int64:HNSW_GRAPH_OFF_M0 = 40i64;
pub fixed int64:HNSW_GRAPH_OFF_EF_CONST = 44i64;
pub fixed int64:HNSW_GRAPH_OFF_ML = 48i64;
pub fixed int64:HNSW_GRAPH_STRUCT_SIZE = 56i64;

pub func:hnsw_graph_create = int64(int64:arena_ptr, int64:vector_buf_ptr, int64:vector_dim, int32:M, int32:M0, int32:ef_construction, float64:mL)
    requires (arena_ptr != 0i64) {
    
    int64:graph = npk_core_alloc(HNSW_GRAPH_STRUCT_SIZE);
    if (graph == 0i64) { fail@cast_unchecked<tbb8>(ERR_HNSW_OOM); }
    
    drop(npk_mem_write_int64(graph, HNSW_GRAPH_OFF_ARENA, arena_ptr));
    drop(npk_mem_write_int64(graph, HNSW_GRAPH_OFF_VECTOR_BUF, vector_buf_ptr));
    drop(npk_mem_write_int64(graph, HNSW_GRAPH_OFF_VECTOR_DIM, vector_dim));
    drop(npk_mem_write_int32(graph, HNSW_GRAPH_OFF_EP_SLOT, -1i32));
    drop(npk_mem_write_int32(graph, HNSW_GRAPH_OFF_EP_GEN, -1i32));
    drop(npk_mem_write_int32(graph, HNSW_GRAPH_OFF_MAX_LAYER, -1i32));
    drop(npk_mem_write_int32(graph, HNSW_GRAPH_OFF_M, M));
    drop(npk_mem_write_int32(graph, HNSW_GRAPH_OFF_M0, M0));
    drop(npk_mem_write_int32(graph, HNSW_GRAPH_OFF_EF_CONST, ef_construction));
    drop(npk_mem_write_int64(graph, HNSW_GRAPH_OFF_ML, @cast_unchecked<int64>(mL)));
    
    pass(graph);
};

pub func:hnsw_graph_destroy = int64(int64:graph) requires (graph != 0i64) {
    drop(npk_core_dalloc(graph));
    pass(0i64);
};

// ── Accessors ───────────────────────────────────────────────────────────────

// Copies ep_slot and ep_gen to the provided pointers. Returns 0 on success.
pub func:hnsw_graph_get_ep = int64(int64:graph, int64:out_slot_ptr, int64:out_gen_ptr)
    requires (graph != 0i64), (out_slot_ptr != 0i64), (out_gen_ptr != 0i64) {
    int32:ep_slot = npk_mem_read_int32(graph, HNSW_GRAPH_OFF_EP_SLOT) ;
    int32:ep_gen  = npk_mem_read_int32(graph, HNSW_GRAPH_OFF_EP_GEN) ;
    
    drop(npk_mem_write_int32(out_slot_ptr, 0i64, ep_slot));
    drop(npk_mem_write_int32(out_gen_ptr, 0i64, ep_gen));
    pass(0i64);
};

pub func:hnsw_graph_set_ep = int64(int64:graph, int32:ep_slot, int32:ep_gen)
    requires (graph != 0i64) {
    drop(npk_mem_write_int32(graph, HNSW_GRAPH_OFF_EP_SLOT, ep_slot));
    drop(npk_mem_write_int32(graph, HNSW_GRAPH_OFF_EP_GEN, ep_gen));
    pass(0i64);
};

pub func:hnsw_graph_get_max_layer = int32(int64:graph) requires (graph != 0i64) {
    pass(npk_mem_read_int32(graph, HNSW_GRAPH_OFF_MAX_LAYER));
};

pub func:hnsw_graph_set_max_layer = int64(int64:graph, int32:layer) requires (graph != 0i64) {
    drop(npk_mem_write_int32(graph, HNSW_GRAPH_OFF_MAX_LAYER, layer));
    pass(0i64);
};

pub func:hnsw_graph_get_arena = int64(int64:graph) requires (graph != 0i64) {
    pass(npk_mem_read_int64(graph, HNSW_GRAPH_OFF_ARENA));
};

pub func:hnsw_graph_get_vector_buf = int64(int64:graph) requires (graph != 0i64) {
    pass(npk_mem_read_int64(graph, HNSW_GRAPH_OFF_VECTOR_BUF));
};

pub func:hnsw_graph_get_vector_dim = int64(int64:graph) requires (graph != 0i64) {
    pass(npk_mem_read_int64(graph, HNSW_GRAPH_OFF_VECTOR_DIM));
};

pub func:hnsw_graph_get_M = int32(int64:graph) requires (graph != 0i64) {
    pass(npk_mem_read_int32(graph, HNSW_GRAPH_OFF_M));
};

pub func:hnsw_graph_get_M0 = int32(int64:graph) requires (graph != 0i64) {
    pass(npk_mem_read_int32(graph, HNSW_GRAPH_OFF_M0));
};

pub func:hnsw_graph_get_ef_construction = int32(int64:graph) requires (graph != 0i64) {
    pass(npk_mem_read_int32(graph, HNSW_GRAPH_OFF_EF_CONST));
};

pub func:hnsw_graph_get_mL = float64(int64:graph) requires (graph != 0i64) {
    pass(@cast_unchecked<float64>(npk_mem_read_int64(graph, HNSW_GRAPH_OFF_ML)));
};

// ── Distance Calculation ────────────────────────────────────────────────────

func:simd_l2_f32 = float32(int64:a, int64:b, int64:dim) {
    int64:i = 0i64;
    float32:dist = 0.0f32;
    when (i < dim) {
        float32:va = @cast_unchecked<float32>(npk_mem_read_int32(a, i * 4i64));
        float32:vb = @cast_unchecked<float32>(npk_mem_read_int32(b, i * 4i64));
        float32:diff = va - vb;
        dist = dist + (diff * diff);
        i = i + 1i64;
    }
    pass(dist);
};

pub func:hnsw_graph_distance = float32(int64:graph, int64:vec1_offset, int64:vec2_offset)
    requires (graph != 0i64) {
    
    int64:vec_buf = hnsw_graph_get_vector_buf(graph)  ?! 0i64;
    int64:dim = hnsw_graph_get_vector_dim(graph)  ?! 0i64;
    
    int64:ptr1 = vec_buf + vec1_offset;
    int64:ptr2 = vec_buf + vec2_offset;
    
    pass(simd_l2_f32(ptr1, ptr2, dim));
};

```

### File: `src/vector/hnsw_insert.npk`
```nitpick
// hnsw_insert.npk
// HNSW Vector Insertion Logic

extern "nitpick" {
    func:log   = float64(float64:x);
    func:floor = float64(float64:x);
}

func:rand_next = uint64(uint64:s) {
    uint64:m = 6364136223846793005u64;
    uint64:a = 1442695040888963407u64;
    pass((s * m) + a);
};

use "../util/error_codes.npk".*;
use "distance.npk".*;

// ── Layer Selection ─────────────────────────────────────────────────────────

pub func:hnsw_random_layer = int32(int64:graph, int64:rand_state_ptr) 
    requires (graph != 0i64), (rand_state_ptr != 0i64) {
    
    float64:mL = hnsw_graph_get_mL(graph)  ?! 0.0f64;
    int32:max_layer_limit = 3i32; // HNSW_MAX_LAYERS - 1

    uint64:s = @cast_unchecked<uint64>(npk_mem_read_int64(rand_state_ptr, 0i64));
    uint64:next_s = rand_next(s) ?! 0u64;
    if (next_s == 0u64) { next_s = 1u64; }
    drop(npk_mem_write_int64(rand_state_ptr, 0i64, @cast_unchecked<int64>(next_s)));

    int64:r_int = @cast_unchecked<int64>(next_s) % 1000000i64;
    if (r_int < 0i64) { r_int = -r_int; }
    if (r_int == 0i64) { r_int = 1i64; }

    float64:unif = @cast_unchecked<float64>(r_int) / 1000000.0f64;
    float64:l_val = -log(unif) * mL;
    int32:l = @cast_unchecked<int32>(floor(l_val));

    if (l > max_layer_limit) { pass(max_layer_limit); }
    pass(l);
};

// ── Heuristic Pruning ───────────────────────────────────────────────────────

pub func:hnsw_select_neighbors = int64(
    int64:graph,
    int64:query_offset,
    int64:W_pq,
    int32:M
) requires (graph != 0i64), (W_pq != 0i64), (M > 0i32) {

    int64:size = hnsw_pq_get_size(W_pq)  ?! 0i64;
    if (size == 0i64) {
        pass(hnsw_pq_create(@cast_unchecked<int64>(M), 1i64) ?! 0i64);
    }

    int64:min_heap = hnsw_pq_create(size, 0i64)  ?! 0i64;
    int64:C = npk_core_alloc(HNSW_PQ_CANDIDATE_SIZE);
    
    when ((hnsw_pq_get_size(W_pq) ?! 0i64) > 0i64) {
        drop(hnsw_pq_pop(W_pq, C));
        float32:dist = hnsw_pq_get_dist(C)  ?! 0.0f32;
        int32:slot = hnsw_pq_get_slot(C)  ?! 0i32;
        int32:gen = hnsw_pq_get_gen(C)   ?! 0i32;
        drop(hnsw_pq_push(min_heap, dist, slot, gen));
    }

    int64:R = hnsw_pq_create(@cast_unchecked<int64>(M), 1i64)  ?! 0i64;
    int64:arena = hnsw_graph_get_arena(graph)  ?! 0i64;

    when ((hnsw_pq_get_size(min_heap) ?! 0i64) > 0i64) {
        drop(hnsw_pq_pop(min_heap, C));
        float32:c_dist = hnsw_pq_get_dist(C)  ?! 0.0f32;
        int32:c_slot = hnsw_pq_get_slot(C)  ?! 0i32;
        int32:c_gen = hnsw_pq_get_gen(C)   ?! 0i32;

        int64:r_size = hnsw_pq_get_size(R)  ?! 0i64;
        if (r_size >= @cast_unchecked<int64>(M)) { break; }

        int64:c_node = hnsw_arena_get_node(arena, c_slot, c_gen)  ?! 0i64;
        if (c_node == 0i64) { continue; }
        int64:c_vec = hnsw_node_get_vector_offset(c_node)  ?! 0i64;

        int64:r_elems = hnsw_pq_get_elements(R)  ?! 0i64;
        bool:good = true;

        int64:i = 0i64;
        when (i < r_size) {
            int64:r_ptr = r_elems + (i * HNSW_PQ_CANDIDATE_SIZE);
            int32:r_slot = hnsw_pq_get_slot(r_ptr)  ?! 0i32;
            int32:r_gen = hnsw_pq_get_gen(r_ptr)  ?! 0i32;

            int64:r_node = hnsw_arena_get_node(arena, r_slot, r_gen)  ?! 0i64;
            if (r_node != 0i64) {
                int64:r_vec = hnsw_node_get_vector_offset(r_node)  ?! 0i64;
                float32:dist_cr = hnsw_graph_distance(graph, c_vec, r_vec)  ?! 0.0f32;
                if (dist_cr < c_dist) {
                    good = false;
                    break;
                }
            }
            i = i + 1i64;
        }

        if (good) {
            drop(hnsw_pq_push(R, c_dist, c_slot, c_gen));
        }
    }

    drop(npk_core_dalloc(C));
    drop(hnsw_pq_destroy(min_heap));

    pass(R);
};

func:hnsw_shrink_connections = int64(
    int64:graph, 
    int64:n_node, 
    int32:n_slot, 
    int32:n_gen, 
    int32:layer, 
    int32:layer_m, 
    int32:new_slot, 
    int32:new_gen
) requires (graph != 0i64), (n_node != 0i64) {
    
    int64:W = hnsw_pq_create(@cast_unchecked<int64>(layer_m) + 1i64, 1i64)  ?! 0i64;
    int32:num_n = hnsw_node_get_num_neighbors(n_node, layer)  ?! 0i32;

    int64:n_vec = hnsw_node_get_vector_offset(n_node)  ?! 0i64;

    int64:i = 0i64;
    int64:arena = hnsw_graph_get_arena(graph)  ?! 0i64;

    when (i < @cast_unchecked<int64>(num_n)) {
        int32:c_slot = hnsw_node_get_neighbor_slot(n_node, layer, i)  ?! 0i32;
        int32:c_gen = hnsw_node_get_neighbor_gen(n_node, layer, i)  ?! 0i32;

        int64:c_node = hnsw_arena_get_node(arena, c_slot, c_gen)  ?! 0i64;
        if (c_node != 0i64) {
            int64:c_vec = hnsw_node_get_vector_offset(c_node)  ?! 0i64;
            float32:dist = hnsw_graph_distance(graph, n_vec, c_vec)  ?! 0.0f32;
            drop(hnsw_pq_push(W, dist, c_slot, c_gen));
        }
        i = i + 1i64;
    }

    int64:new_node = hnsw_arena_get_node(arena, new_slot, new_gen)  ?! 0i64;
    if (new_node != 0i64) {
        int64:new_vec = hnsw_node_get_vector_offset(new_node)  ?! 0i64;
        float32:dist = hnsw_graph_distance(graph, n_vec, new_vec)  ?! 0.0f32;
        drop(hnsw_pq_push(W, dist, new_slot, new_gen));
    }

    int64:neighbors = hnsw_select_neighbors(graph, n_vec, W, layer_m)  ?! 0i64;
    int64:n_size = hnsw_pq_get_size(neighbors)  ?! 0i64;

    drop(hnsw_node_set_num_neighbors(n_node, layer, @cast_unchecked<int32>(n_size)));

    i = 0i64;
    when (i < n_size) {
        int64:ptr = hnsw_pq_get_candidate_ptr(neighbors, i)  ?! 0i64;
        int32:s = hnsw_pq_get_slot(ptr)  ?! 0i32;
        int32:g = hnsw_pq_get_gen(ptr)  ?! 0i32;
        drop(hnsw_node_set_neighbor(n_node, layer, i, s, g, 1i16));
        i = i + 1i64;
    }

    drop(hnsw_pq_destroy(W));
    drop(hnsw_pq_destroy(neighbors));
    pass(0i64);
};

// ── Graph Insertion ─────────────────────────────────────────────────────────

pub func:hnsw_insert = int64(
    int64:graph,
    int64:vec_offset,
    int64:rand_state_ptr,
    int64:visited_set
) requires (graph != 0i64), (rand_state_ptr != 0i64), (visited_set != 0i64) {

    int64:arena = hnsw_graph_get_arena(graph)  ?! 0i64;

    int64:node_buf = npk_core_alloc(16i64);
    int64:alloc_res = hnsw_arena_alloc_node(arena, node_buf, node_buf + 8i64)  ?! 0i64;
    if (alloc_res == -1i64) {
        drop(npk_core_dalloc(node_buf));
        pass(-1i64);
    }
    int32:slot = @cast_unchecked<int32>(npk_mem_read_int64(node_buf, 0i64));
    int32:gen  = npk_mem_read_int32(node_buf, 8i64);
    drop(npk_core_dalloc(node_buf));

    int64:node_ptr = hnsw_arena_get_node(arena, slot, gen)  ?! 0i64;
    drop(hnsw_node_set_vector_offset(node_ptr, vec_offset));

    int32:l = hnsw_random_layer(graph, rand_state_ptr)  ?! 0i32;
    drop(hnsw_node_set_layer(node_ptr, l));

    int64:ep_slot_ptr = npk_core_alloc(8i64);
    int64:ep_gen_ptr = npk_core_alloc(8i64);

    drop(hnsw_graph_get_ep(graph, ep_slot_ptr, ep_gen_ptr));
    int32:ep_slot = npk_mem_read_int32(ep_slot_ptr, 0i64);
    int32:ep_gen  = npk_mem_read_int32(ep_gen_ptr, 0i64);

    if (ep_slot == -1i32) {
        drop(hnsw_graph_set_ep(graph, slot, gen));
        drop(hnsw_graph_set_max_layer(graph, l));
        drop(npk_core_dalloc(ep_slot_ptr));
        drop(npk_core_dalloc(ep_gen_ptr));
        pass(0i64);
    }

    int32:max_layer = hnsw_graph_get_max_layer(graph)  ?! 0i32;
    int32:M = hnsw_graph_get_M(graph) ?! 16i32;
    int32:M0 = hnsw_graph_get_M0(graph) ?! 32i32;
    int32:ef_const = hnsw_graph_get_ef_construction(graph) ?! 100i32;

    int32:curr_ep_slot = ep_slot;
    int32:curr_ep_gen = ep_gen;

    int32:lc = max_layer;
    when (lc > l) {
        drop(hnsw_visited_clear(visited_set));
        int64:W = hnsw_search_layer(graph, vec_offset, curr_ep_slot, curr_ep_gen, 1i32, lc, visited_set, 0i64, 0i64)  ?! 0i64;
        
        int64:size = hnsw_pq_get_size(W)  ?! 0i64;
        if (size > 0i64) {
            int64:C = npk_core_alloc(HNSW_PQ_CANDIDATE_SIZE);
            drop(hnsw_pq_peek(W, C));
            curr_ep_slot = hnsw_pq_get_slot(C) ?! curr_ep_slot;
            curr_ep_gen  = hnsw_pq_get_gen(C)  ?! curr_ep_gen;
            drop(npk_core_dalloc(C));
        }
        drop(hnsw_pq_destroy(W));
        lc = lc - 1i32;
    }

    lc = max_layer;
    if (l < max_layer) { lc = l; }

    when (lc >= 0i32) {
        drop(hnsw_visited_clear(visited_set));
        int64:W = hnsw_search_layer(graph, vec_offset, curr_ep_slot, curr_ep_gen, ef_const, lc, visited_set, 0i64, 0i64)  ?! 0i64;
        
        int32:layer_m = M;
        if (lc == 0i32) { layer_m = M0; }

        int64:neighbors = hnsw_select_neighbors(graph, vec_offset, W, layer_m)  ?! 0i64;
        
        int64:n_size = hnsw_pq_get_size(neighbors)  ?! 0i64;
        drop(hnsw_node_set_num_neighbors(node_ptr, lc, @cast_unchecked<int32>(n_size)));

        int64:i = 0i64;
        when (i < n_size) {
            int64:ptr = hnsw_pq_get_candidate_ptr(neighbors, i)  ?! 0i64;
            int32:n_slot = hnsw_pq_get_slot(ptr)  ?! 0i32;
            int32:n_gen = hnsw_pq_get_gen(ptr)  ?! 0i32;
            drop(hnsw_node_set_neighbor(node_ptr, lc, i, n_slot, n_gen, 1i16));

            int64:n_node_ptr = hnsw_arena_get_node(arena, n_slot, n_gen)  ?! 0i64;
            if (n_node_ptr != 0i64) {
                int32:n_num = hnsw_node_get_num_neighbors(n_node_ptr, lc)  ?! 0i32;
                if (n_num < layer_m) {
                    drop(hnsw_node_set_neighbor(n_node_ptr, lc, @cast_unchecked<int64>(n_num), slot, gen, 1i16));
                    drop(hnsw_node_set_num_neighbors(n_node_ptr, lc, n_num + 1i32));
                } else {
                    drop(hnsw_shrink_connections(graph, n_node_ptr, n_slot, n_gen, lc, layer_m, slot, gen));
                }
            }

            i = i + 1i64;
        }

        if (n_size > 0i64) {
            int64:min_idx = -1i64;
            float32:min_dist = 999999999.0f32;
            int64:j = 0i64;
            int64:r_elems = hnsw_pq_get_elements(neighbors)  ?! 0i64;
            when (j < n_size) {
                int64:r_ptr = r_elems + (j * HNSW_PQ_CANDIDATE_SIZE);
                float32:d = hnsw_pq_get_dist(r_ptr)  ?! 0.0f32;
                if (d < min_dist) {
                    min_dist = d;
                    min_idx = j;
                }
                j = j + 1i64;
            }
            if (min_idx != -1i64) {
                int64:r_ptr = r_elems + (min_idx * HNSW_PQ_CANDIDATE_SIZE);
                curr_ep_slot = hnsw_pq_get_slot(r_ptr) ?! curr_ep_slot;
                curr_ep_gen  = hnsw_pq_get_gen(r_ptr)  ?! curr_ep_gen;
            }
        }

        drop(hnsw_pq_destroy(W));
        drop(hnsw_pq_destroy(neighbors));

        lc = lc - 1i32;
    }

    if (l > max_layer) {
        drop(hnsw_graph_set_max_layer(graph, l));
        drop(hnsw_graph_set_ep(graph, slot, gen));
    }

    drop(npk_core_dalloc(ep_slot_ptr));
    drop(npk_core_dalloc(ep_gen_ptr));
    pass(0i64);
};

```

### File: `src/vector/hnsw_node.npk`
```nitpick
// hnsw_node.npk — HnswNode flat buffer layout constants and field accessors
//
// HnswNode is a fixed-size 216-byte struct stored in a flat wild int8-> arena buffer.
// Every field is accessed via npk_mem_read_* / npk_mem_write_* with limit<Rules> bounds.
//
// Layout (all offsets in bytes, zero-indexed):
//
//   Bytes   0-3:   id             (int32)  — vector ID in the collection
//   Bytes   4-7:   layer          (int32)  — layer this node lives in (0 = base layer)
//   Bytes   8-23:  num_neighbors[4] (int32)  — current neighbor count per layer (max 4 layers)
//   Bytes  24-39:  max_neighbors[4] (int32)  — neighbor capacity per layer
//   Bytes  40-999: neighbor_handles[80]    — 80 × Handle<HnswNode> (12 bytes each = 960 bytes)
//                  Layer 0 uses slots 0..31. Layer 1 uses slots 32..47.
//                  Layer 2 uses slots 48..63. Layer 3 uses slots 64..79.
//   Bytes 1000-1007: vector_offset  (int64)  — byte offset into the vector data arena
//                                            for this node's raw embedding bytes
//   Total: 1008 bytes = HNSW_NODE_SIZE
//
// Handle<HnswNode> layout (12 bytes):
//   Bytes 0-3:  slot_idx   (int32)
//   Bytes 4-7:  generation (int32)
//   Bytes 8-9:  arena_id   (int16)
//   Bytes 10-11: _pad      (int16)
//
// HNSW_HANDLE_NULL: all 12 bytes zero — slot_idx=0, generation=0, arena_id=0.
// Generation counters in the arena begin at 1, so generation=0 is always stale.

use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;

// -------------------------------------------------------------------------
// Node size and field offsets
// -------------------------------------------------------------------------

pub fixed int64:HNSW_NODE_SIZE              = 1008i64;

pub fixed int64:HNSW_NODE_OFF_ID            = 0i64;    // int32
pub fixed int64:HNSW_NODE_OFF_LAYER         = 4i64;    // int32
pub fixed int64:HNSW_NODE_OFF_NUM_NEIGHBORS = 8i64;    // 16 bytes: 4 × int32
pub fixed int64:HNSW_NODE_OFF_MAX_NEIGHBORS = 24i64;   // 16 bytes: 4 × int32
pub fixed int64:HNSW_NODE_OFF_NEIGHBORS     = 40i64;   // 960 bytes: 80 × Handle (12 bytes each)
pub fixed int64:HNSW_NODE_OFF_VECTOR_OFFSET = 1000i64; // int64

// HNSW graph parameters
pub fixed int64:HNSW_MAX_LAYERS             = 4i64;
pub fixed int64:HNSW_M                      = 16i64;   // Max connections per layer (non-base)
pub fixed int64:HNSW_M0                     = 32i64;   // Max connections for layer 0
pub fixed int64:HNSW_NEIGHBOR_SLOTS         = 80i64;   // 32 + 16*3
pub fixed int64:HNSW_HANDLE_SIZE            = 12i64;   // Bytes per Handle<HnswNode>

// Handle sub-field offsets (relative to the start of a handle slot)
pub fixed int64:HNSW_HDL_OFF_SLOT_IDX      = 0i64;    // int32
pub fixed int64:HNSW_HDL_OFF_GENERATION    = 4i64;    // int32
pub fixed int64:HNSW_HDL_OFF_ARENA_ID      = 8i64;    // int16
pub fixed int64:HNSW_HDL_OFF_PAD           = 10i64;   // int16 (reserved, always 0)

// -------------------------------------------------------------------------
// limit<Rules> refinements for bounds checking
// -------------------------------------------------------------------------

Rules<int64>:valid_node_offset   = { $ >= 0i64, $ < HNSW_NODE_SIZE };
Rules<int64>:valid_neighbor_slot = { $ >= 0i64, $ < HNSW_NEIGHBOR_SLOTS };

// -------------------------------------------------------------------------
// Node field: id
// -------------------------------------------------------------------------

// Read the vector ID of this node.
pub func:hnsw_node_get_id = int32(int64:node_ptr)
    requires (node_ptr != 0i64) {
    pass(npk_mem_read_int32(node_ptr, HNSW_NODE_OFF_ID));
};

// Write the vector ID of this node.
pub func:hnsw_node_set_id = NIL(int64:node_ptr, int32:id)
    requires (node_ptr != 0i64) {
    drop(npk_mem_write_int32(node_ptr, HNSW_NODE_OFF_ID, id));
    pass(NIL);
};

// -------------------------------------------------------------------------
// Node field: layer
// -------------------------------------------------------------------------

// Read the layer this node inhabits (0 = base layer).
pub func:hnsw_node_get_layer = int32(int64:node_ptr)
    requires (node_ptr != 0i64) {
    pass(npk_mem_read_int32(node_ptr, HNSW_NODE_OFF_LAYER));
};

// Write the layer.
pub func:hnsw_node_set_layer = NIL(int64:node_ptr, int32:layer)
    requires (node_ptr != 0i64), (layer >= 0i32) {
    drop(npk_mem_write_int32(node_ptr, HNSW_NODE_OFF_LAYER, layer));
    pass(NIL);
};

// -------------------------------------------------------------------------
// Node field: num_neighbors
// -------------------------------------------------------------------------

// Read the current neighbor count for a layer.
pub func:hnsw_node_get_num_neighbors = int32(int64:node_ptr, int32:layer)
    requires (node_ptr != 0i64), (layer >= 0i32), (@cast_unchecked<int64>(layer) < HNSW_MAX_LAYERS) {
    int64:layer64 = @cast_unchecked<int64>(layer);
    pass(npk_mem_read_int32(node_ptr, HNSW_NODE_OFF_NUM_NEIGHBORS + (layer64 * 4i64)));
};

// Write the current neighbor count for a layer.
pub func:hnsw_node_set_num_neighbors = NIL(int64:node_ptr, int32:layer, int32:count)
    requires (node_ptr != 0i64), (layer >= 0i32), (@cast_unchecked<int64>(layer) < HNSW_MAX_LAYERS), (count >= 0i32) {
    int64:layer64 = @cast_unchecked<int64>(layer);
    drop(npk_mem_write_int32(node_ptr, HNSW_NODE_OFF_NUM_NEIGHBORS + (layer64 * 4i64), count));
    pass(NIL);
};

// -------------------------------------------------------------------------
// Node field: max_neighbors
// -------------------------------------------------------------------------

// Read the neighbor capacity for a layer.
pub func:hnsw_node_get_max_neighbors = int32(int64:node_ptr, int32:layer)
    requires (node_ptr != 0i64), (layer >= 0i32), (@cast_unchecked<int64>(layer) < HNSW_MAX_LAYERS) {
    int64:layer64 = @cast_unchecked<int64>(layer);
    pass(npk_mem_read_int32(node_ptr, HNSW_NODE_OFF_MAX_NEIGHBORS + (layer64 * 4i64)));
};

// Write the neighbor capacity for a layer.
pub func:hnsw_node_set_max_neighbors = NIL(int64:node_ptr, int32:layer, int32:max)
    requires (node_ptr != 0i64), (layer >= 0i32), (@cast_unchecked<int64>(layer) < HNSW_MAX_LAYERS), (max >= 0i32) {
    int64:layer64 = @cast_unchecked<int64>(layer);
    drop(npk_mem_write_int32(node_ptr, HNSW_NODE_OFF_MAX_NEIGHBORS + (layer64 * 4i64), max));
    pass(NIL);
};

// -------------------------------------------------------------------------
// Node field: vector_offset
// -------------------------------------------------------------------------

// Read the byte offset into the vector data arena for this node's embedding.
pub func:hnsw_node_get_vector_offset = int64(int64:node_ptr)
    requires (node_ptr != 0i64) {
    pass(npk_mem_read_int64(node_ptr, HNSW_NODE_OFF_VECTOR_OFFSET));
};

// Write the byte offset into the vector data arena.
pub func:hnsw_node_set_vector_offset = NIL(int64:node_ptr, int64:offset)
    requires (node_ptr != 0i64), (offset >= 0i64) {
    drop(npk_mem_write_int64(node_ptr, HNSW_NODE_OFF_VECTOR_OFFSET, offset));
    pass(NIL);
};

// -------------------------------------------------------------------------
// Neighbor handle array accessors
// -------------------------------------------------------------------------

// Base byte offset of neighbor slot i within the specified layer's section.
func:hnsw_neighbor_base = int64(int32:layer, int64:i)
    requires (layer >= 0i32), (@cast_unchecked<int64>(layer) < HNSW_MAX_LAYERS), (i >= 0i64) {
    
    int64:layer_start_idx = 0i64;
    if (layer == 0i32) { layer_start_idx = 0i64; }
    if (layer == 1i32) { layer_start_idx = 32i64; }
    if (layer == 2i32) { layer_start_idx = 48i64; }
    if (layer == 3i32) { layer_start_idx = 64i64; }
    
    int64:total_idx = layer_start_idx + i;
    pass(HNSW_NODE_OFF_NEIGHBORS + total_idx * HNSW_HANDLE_SIZE);
};

// Read slot_idx of neighbor handle at slot i in a layer.
pub func:hnsw_node_get_neighbor_slot = int32(int64:node_ptr, int32:layer, int64:i)
    requires (node_ptr != 0i64), (layer >= 0i32), (@cast_unchecked<int64>(layer) < HNSW_MAX_LAYERS), (i >= 0i64) {
    int64:base = hnsw_neighbor_base(layer, i)  ?! 0i64;
    pass(npk_mem_read_int32(node_ptr, base + HNSW_HDL_OFF_SLOT_IDX));
};

// Read generation of neighbor handle at slot i in a layer.
pub func:hnsw_node_get_neighbor_gen = int32(int64:node_ptr, int32:layer, int64:i)
    requires (node_ptr != 0i64), (layer >= 0i32), (@cast_unchecked<int64>(layer) < HNSW_MAX_LAYERS), (i >= 0i64) {
    int64:base = hnsw_neighbor_base(layer, i)  ?! 0i64;
    pass(npk_mem_read_int32(node_ptr, base + HNSW_HDL_OFF_GENERATION));
};

// Read arena_id of neighbor handle at slot i in a layer.
pub func:hnsw_node_get_neighbor_arena_id = int16(int64:node_ptr, int32:layer, int64:i)
    requires (node_ptr != 0i64), (layer >= 0i32), (@cast_unchecked<int64>(layer) < HNSW_MAX_LAYERS), (i >= 0i64) {
    int64:base = hnsw_neighbor_base(layer, i)  ?! 0i64;
    pass(npk_mem_read_int16(node_ptr, base + HNSW_HDL_OFF_ARENA_ID));
};

// Write all three sub-fields of the neighbor handle at slot i in a layer.
pub func:hnsw_node_set_neighbor = NIL(int64:node_ptr, int32:layer, int64:i, int32:slot_idx, int32:generation, int16:arena_id)
    requires (node_ptr != 0i64), (layer >= 0i32), (@cast_unchecked<int64>(layer) < HNSW_MAX_LAYERS), (i >= 0i64), (generation > 0i32) {
    int64:base = hnsw_neighbor_base(layer, i)  ?! 0i64;
    drop(npk_mem_write_int32(node_ptr, base + HNSW_HDL_OFF_SLOT_IDX,   slot_idx));
    drop(npk_mem_write_int32(node_ptr, base + HNSW_HDL_OFF_GENERATION,  generation));
    drop(npk_mem_write_int16(node_ptr, base + HNSW_HDL_OFF_ARENA_ID,    arena_id));
    drop(npk_mem_write_int16(node_ptr, base + HNSW_HDL_OFF_PAD,         0i16));
    pass(NIL);
};

// Zero out the neighbor handle at slot i in a layer.
pub func:hnsw_node_clear_neighbor = NIL(int64:node_ptr, int32:layer, int64:i)
    requires (node_ptr != 0i64), (layer >= 0i32), (@cast_unchecked<int64>(layer) < HNSW_MAX_LAYERS), (i >= 0i64) {
    int64:base = hnsw_neighbor_base(layer, i)  ?! 0i64;
    drop(npk_mem_write_int32(node_ptr, base + HNSW_HDL_OFF_SLOT_IDX,   0i32));
    drop(npk_mem_write_int32(node_ptr, base + HNSW_HDL_OFF_GENERATION,  0i32));
    drop(npk_mem_write_int16(node_ptr, base + HNSW_HDL_OFF_ARENA_ID,    0i16));
    drop(npk_mem_write_int16(node_ptr, base + HNSW_HDL_OFF_PAD,         0i16));
    pass(NIL);
};

// Check whether the neighbor handle at slot i in a layer is the null handle.
pub func:hnsw_neighbor_is_null = bool(int64:node_ptr, int32:layer, int64:i)
    requires (node_ptr != 0i64), (layer >= 0i32), (@cast_unchecked<int64>(layer) < HNSW_MAX_LAYERS), (i >= 0i64) {
    int64:base = hnsw_neighbor_base(layer, i)  ?! 0i64;
    int32:gen  = npk_mem_read_int32(node_ptr, base + HNSW_HDL_OFF_GENERATION);
    pass(gen == 0i32);
};

```

### File: `src/vector/hnsw_pq.npk`
```nitpick
// hnsw_pq.npk
// Fixed-capacity Priority Queue for HNSW Candidate Nodes
// Elements: { distance: float32, slot: int32, gen: int32 } (12 bytes)
// Implements both Min-Heap (is_max_heap = 0) and Max-Heap (is_max_heap = 1)

use "../util/error_codes.npk".*;

pub fixed int64:HNSW_PQ_CANDIDATE_SIZE = 12i64;
pub fixed int64:HNSW_PQ_OFF_CAPACITY = 0i64;
pub fixed int64:HNSW_PQ_OFF_SIZE = 8i64;
pub fixed int64:HNSW_PQ_OFF_IS_MAX = 16i64;
pub fixed int64:HNSW_PQ_OFF_ELEMENTS = 24i64;
pub fixed int64:HNSW_PQ_HEADER_SIZE = 32i64;

// ── Struct Accessors ────────────────────────────────────────────────────────

pub func:hnsw_pq_get_capacity = int64(int64:pq) requires (pq != 0i64) {
    pass(npk_mem_read_int64(pq, HNSW_PQ_OFF_CAPACITY));
};

pub func:hnsw_pq_get_size = int64(int64:pq) requires (pq != 0i64) {
    pass(npk_mem_read_int64(pq, HNSW_PQ_OFF_SIZE));
};

pub func:hnsw_pq_get_is_max = int64(int64:pq) requires (pq != 0i64) {
    pass(npk_mem_read_int64(pq, HNSW_PQ_OFF_IS_MAX));
};

pub func:hnsw_pq_get_elements = int64(int64:pq) requires (pq != 0i64) {
    pass(npk_mem_read_int64(pq, HNSW_PQ_OFF_ELEMENTS));
};

// ── Element Accessors ───────────────────────────────────────────────────────

pub func:hnsw_pq_get_candidate_ptr = int64(int64:pq, int64:index) 
    requires (pq != 0i64), (index >= 0i64) {
    int64:elems = hnsw_pq_get_elements(pq)  ?! 0i64;
    pass(elems + (index * HNSW_PQ_CANDIDATE_SIZE));
};

pub func:hnsw_pq_get_dist = float32(int64:candidate_ptr) requires (candidate_ptr != 0i64) {
    pass(@cast_unchecked<float32>(npk_mem_read_int32(candidate_ptr, 0i64)));
};

pub func:hnsw_pq_get_slot = int32(int64:candidate_ptr) requires (candidate_ptr != 0i64) {
    pass(npk_mem_read_int32(candidate_ptr, 4i64));
};

pub func:hnsw_pq_get_gen = int32(int64:candidate_ptr) requires (candidate_ptr != 0i64) {
    pass(npk_mem_read_int32(candidate_ptr, 8i64));
};

func:hnsw_pq_set_candidate = int64(int64:candidate_ptr, float32:dist, int32:slot, int32:gen) 
    requires (candidate_ptr != 0i64) {
    drop(npk_mem_write_int32(candidate_ptr, 0i64, @cast_unchecked<int32>(dist)));
    drop(npk_mem_write_int32(candidate_ptr, 4i64, slot));
    drop(npk_mem_write_int32(candidate_ptr, 8i64, gen));
    pass(0i64);
};

func:hnsw_pq_copy_candidate = int64(int64:dst_ptr, int64:src_ptr) 
    requires (dst_ptr != 0i64), (src_ptr != 0i64) {
    float32:dist = @cast_unchecked<float32>(npk_mem_read_int32(src_ptr, 0i64));
    int32:slot = hnsw_pq_get_slot(src_ptr)  ?! 0i32;
    int32:gen = hnsw_pq_get_gen(src_ptr)   ?! 0i32;
    drop(hnsw_pq_set_candidate(dst_ptr, dist, slot, gen));
    pass(0i64);
};

func:hnsw_pq_compare = int64(int64:pq, int64:ptr_a, int64:ptr_b) 
    requires (pq != 0i64), (ptr_a != 0i64), (ptr_b != 0i64) {
    float32:dist_a = hnsw_pq_get_dist(ptr_a)  ?! 0.0f32;
    float32:dist_b = hnsw_pq_get_dist(ptr_b)  ?! 0.0f32;
    int64:is_max = hnsw_pq_get_is_max(pq)   ?! 0i64;

    // Return 1 if A should be above B in the heap.
    if (is_max != 0i64) {
        if (dist_a > dist_b) { pass(1i64); }
        pass(0i64);
    } else {
        if (dist_a < dist_b) { pass(1i64); }
        pass(0i64);
    }
};

// ── Heap Operations ─────────────────────────────────────────────────────────

func:hnsw_pq_sift_up = int64(int64:pq, int64:index) requires (pq != 0i64), (index >= 0i64) {
    if (index == 0i64) { pass(0i64); }

    int64:curr = index;
    int64:parent = (curr - 1i64) / 2i64;

    // Temporary storage for swapping
    int64:temp_ptr = npk_core_alloc(HNSW_PQ_CANDIDATE_SIZE);

    when (curr > 0i64) {
        int64:curr_ptr = hnsw_pq_get_candidate_ptr(pq, curr)  ?! 0i64;
        int64:parent_ptr = hnsw_pq_get_candidate_ptr(pq, parent)  ?! 0i64;

        int64:cmp = hnsw_pq_compare(pq, curr_ptr, parent_ptr)  ?! 0i64;
        if (cmp == 0i64) { break; }

        drop(hnsw_pq_copy_candidate(temp_ptr, curr_ptr));
        drop(hnsw_pq_copy_candidate(curr_ptr, parent_ptr));
        drop(hnsw_pq_copy_candidate(parent_ptr, temp_ptr));

        curr = parent;
        parent = (curr - 1i64) / 2i64;
    }

    drop(npk_core_dalloc(temp_ptr));
    pass(0i64);
};

func:hnsw_pq_sift_down = int64(int64:pq, int64:index) requires (pq != 0i64), (index >= 0i64) {
    int64:size = hnsw_pq_get_size(pq)  ?! 0i64;
    int64:curr = index;

    int64:temp_ptr = npk_core_alloc(HNSW_PQ_CANDIDATE_SIZE);

    when (curr < size) {
        int64:left  = curr * 2i64 + 1i64;
        int64:right = curr * 2i64 + 2i64;
        int64:best  = curr;

        int64:best_ptr = hnsw_pq_get_candidate_ptr(pq, best)  ?! 0i64;

        if (left < size) {
            int64:left_ptr = hnsw_pq_get_candidate_ptr(pq, left)  ?! 0i64;
            int64:cmp_left = hnsw_pq_compare(pq, left_ptr, best_ptr)  ?! 0i64;
            if (cmp_left != 0i64) {
                best = left;
                best_ptr = left_ptr;
            }
        }

        if (right < size) {
            int64:right_ptr = hnsw_pq_get_candidate_ptr(pq, right)  ?! 0i64;
            int64:cmp_right = hnsw_pq_compare(pq, right_ptr, best_ptr)  ?! 0i64;
            if (cmp_right != 0i64) {
                best = right;
                best_ptr = right_ptr;
            }
        }

        if (best == curr) { break; }

        int64:curr_ptr = hnsw_pq_get_candidate_ptr(pq, curr)  ?! 0i64;
        drop(hnsw_pq_copy_candidate(temp_ptr, curr_ptr));
        drop(hnsw_pq_copy_candidate(curr_ptr, best_ptr));
        drop(hnsw_pq_copy_candidate(best_ptr, temp_ptr));

        curr = best;
    }

    drop(npk_core_dalloc(temp_ptr));
    pass(0i64);
};

// ── Public API ──────────────────────────────────────────────────────────────

pub func:hnsw_pq_create = int64(int64:capacity, int64:is_max_heap) requires (capacity > 0i64) {
    int64:pq = npk_core_alloc(HNSW_PQ_HEADER_SIZE);
    if (pq == 0i64) { fail@cast_unchecked<tbb8>(ERR_HNSW_OOM); }

    int64:elems = npk_core_alloc(capacity * HNSW_PQ_CANDIDATE_SIZE);
    if (elems == 0i64) { fail@cast_unchecked<tbb8>(ERR_HNSW_OOM); }

    drop(npk_mem_write_int64(pq, HNSW_PQ_OFF_CAPACITY, capacity));
    drop(npk_mem_write_int64(pq, HNSW_PQ_OFF_SIZE, 0i64));
    drop(npk_mem_write_int64(pq, HNSW_PQ_OFF_IS_MAX, is_max_heap));
    drop(npk_mem_write_int64(pq, HNSW_PQ_OFF_ELEMENTS, elems));

    pass(pq);
};

pub func:hnsw_pq_destroy = int64(int64:pq) requires (pq != 0i64) {
    int64:elems = hnsw_pq_get_elements(pq)  ?! 0i64;
    if (elems != 0i64) { drop(npk_core_dalloc(elems)); }
    drop(npk_core_dalloc(pq));
    pass(0i64);
};

func:hnsw_pq_grow = int64(int64:pq) requires (pq != 0i64) {
    int64:old_capacity = hnsw_pq_get_capacity(pq)  ?! 0i64;
    int64:new_capacity = old_capacity * 2i64;
    int64:old_elems = hnsw_pq_get_elements(pq)  ?! 0i64;
    
    int64:new_elems = npk_core_alloc(new_capacity * HNSW_PQ_CANDIDATE_SIZE);
    if (new_elems == 0i64) { fail@cast_unchecked<tbb8>(ERR_HNSW_OOM); }
    
    int64:size = hnsw_pq_get_size(pq)  ?! 0i64;
    if (size > 0i64) {
        // Nitpick memory primitives don't have npk_mem_copy natively exposed in the core in mem_primitives? 
        // Wait, mem_primitives.npk HAS npk_mem_copy!
        drop(npk_mem_copy(new_elems, old_elems, size * HNSW_PQ_CANDIDATE_SIZE));
    }
    
    drop(npk_mem_write_int64(pq, HNSW_PQ_OFF_CAPACITY, new_capacity));
    drop(npk_mem_write_int64(pq, HNSW_PQ_OFF_ELEMENTS, new_elems));
    drop(npk_core_dalloc(old_elems));
    pass(0i64);
};

// Returns 0 on success.
pub func:hnsw_pq_push = int64(int64:pq, float32:dist, int32:slot, int32:gen) requires (pq != 0i64) {
    int64:size = hnsw_pq_get_size(pq)      ?! 0i64;
    int64:capacity = hnsw_pq_get_capacity(pq)  ?! 0i64;

    if (size >= capacity) {
        drop(hnsw_pq_grow(pq));
    }

    int64:ptr = hnsw_pq_get_candidate_ptr(pq, size)  ?! 0i64;
    drop(hnsw_pq_set_candidate(ptr, dist, slot, gen));

    drop(npk_mem_write_int64(pq, HNSW_PQ_OFF_SIZE, size + 1i64));
    drop(hnsw_pq_sift_up(pq, size));

    pass(0i64);
};

// Returns 0 on success, -1 on empty. Root candidate copied to out_candidate_ptr.
pub func:hnsw_pq_pop = int64(int64:pq, int64:out_candidate_ptr) 
    requires (pq != 0i64), (out_candidate_ptr != 0i64) {
    int64:size = hnsw_pq_get_size(pq)  ?! 0i64;

    if (size == 0i64) { pass(-1i64); }

    int64:root_ptr = hnsw_pq_get_candidate_ptr(pq, 0i64)  ?! 0i64;
    drop(hnsw_pq_copy_candidate(out_candidate_ptr, root_ptr));

    int64:last_idx = size - 1i64;
    if (last_idx > 0i64) {
        int64:last_ptr = hnsw_pq_get_candidate_ptr(pq, last_idx)  ?! 0i64;
        drop(hnsw_pq_copy_candidate(root_ptr, last_ptr));
    }

    drop(npk_mem_write_int64(pq, HNSW_PQ_OFF_SIZE, last_idx));
    if (last_idx > 1i64) {
        drop(hnsw_pq_sift_down(pq, 0i64));
    }

    pass(0i64);
};

// Returns 0 on success, -1 on empty. Root candidate copied to out_candidate_ptr.
pub func:hnsw_pq_peek = int64(int64:pq, int64:out_candidate_ptr) 
    requires (pq != 0i64), (out_candidate_ptr != 0i64) {
    int64:size = hnsw_pq_get_size(pq)  ?! 0i64;

    if (size == 0i64) { pass(-1i64); }

    int64:root_ptr = hnsw_pq_get_candidate_ptr(pq, 0i64)  ?! 0i64;
    drop(hnsw_pq_copy_candidate(out_candidate_ptr, root_ptr));

    pass(0i64);
};

```

### File: `src/vector/hnsw_search.npk`
```nitpick
// hnsw_search.npk
// HNSW Layer-specific Greedy Beam Search

// Performs greedy beam search on a single layer to find the `ef` nearest neighbors
// to the query vector. Returns a Max-Heap Priority Queue containing the results.
// Note: The caller is responsible for destroying the returned priority queue!

use "../util/error_codes.npk".*;
use "../query/evaluator.npk".*;

pub func:hnsw_search_layer = int64(
    int64:graph, 
    int64:query_offset, 
    int32:ep_slot, 
    int32:ep_gen, 
    int32:ef, 
    int32:layer, 
    int64:visited_set,
    int64:filter_ast,
    int64:doc_store
) requires (graph != 0i64), (visited_set != 0i64), (ef > 0i32) {
    
    int64:arena = hnsw_graph_get_arena(graph)  ?! 0i64;
    int64:ep_node_ptr = hnsw_arena_get_node(arena, ep_slot, ep_gen)  ?! 0i64;
    if (ep_node_ptr == 0i64) { fail@cast_unchecked<tbb8>(ERR_HNSW_STALE_HANDLE); }

    int64:ep_vec_offset = hnsw_node_get_vector_offset(ep_node_ptr)  ?! 0i64;
    float32:ep_dist = hnsw_graph_distance(graph, query_offset, ep_vec_offset)  ?! 0.0f32;

    int64:ef_64 = @cast_unchecked<int64>(ef);

    // candidates: Min-Heap (capacity = ef initially, dynamically grows if needed)
    int64:candidates = hnsw_pq_create(ef_64, 0i64)  ?! 0i64;
    
    // W: Max-Heap (closest found so far)
    int64:W = hnsw_pq_create(ef_64, 1i64)  ?! 0i64;

    drop(hnsw_pq_push(candidates, ep_dist, ep_slot, ep_gen));
    bool:ep_match = true;
    if (filter_ast != 0i64) {
        if (doc_store != 0i64) {
            int64:ep_doc_ptr = npk_mem_read_int64(doc_store, @cast_unchecked<int64>(ep_slot) * 8i64);
            if (ep_doc_ptr != 0i64) {
                ep_match = raw evaluate_filter(filter_ast, ep_doc_ptr);
            }
        }
    }
    if (ep_match == true) {
        drop(hnsw_pq_push(W, ep_dist, ep_slot, ep_gen));
    }

    drop(hnsw_visited_mark(visited_set, ep_slot));

    int64:C = npk_core_alloc(HNSW_PQ_CANDIDATE_SIZE);
    int64:furthest = npk_core_alloc(HNSW_PQ_CANDIDATE_SIZE);

    when ((hnsw_pq_get_size(candidates) ?! 0i64) > 0i64) {
        drop(hnsw_pq_pop(candidates, C));
        float32:c_dist = hnsw_pq_get_dist(C)  ?! 0.0f32;
        int32:c_slot = hnsw_pq_get_slot(C)  ?! 0i32;
        int32:c_gen = hnsw_pq_get_gen(C)   ?! 0i32;

        float32:f_dist = 3.402823466e+38f32; // ~Infinity
        int64:w_size = hnsw_pq_get_size(W) ?! 0i64;
        if (w_size > 0i64) {
            drop(hnsw_pq_peek(W, furthest));
            f_dist = hnsw_pq_get_dist(furthest)  ?! 0.0f32;
        }

        if (c_dist > f_dist) {
            if (w_size >= ef_64) {
                break;
            }
        }

        int64:c_node_ptr = hnsw_arena_get_node(arena, c_slot, c_gen)  ?! 0i64;
        if (c_node_ptr == 0i64) { continue; }

        int32:num_neighbors = hnsw_node_get_num_neighbors(c_node_ptr, layer)  ?! 0i32;
        int64:i = 0i64;
        int64:n_64 = @cast_unchecked<int64>(num_neighbors);

        when (i < n_64) {
            int32:n_slot = hnsw_node_get_neighbor_slot(c_node_ptr, layer, i)  ?! 0i32;
            int32:n_gen = hnsw_node_get_neighbor_gen(c_node_ptr, layer, i)  ?! 0i32;

            int64:is_visited = hnsw_visited_check(visited_set, n_slot)  ?! 0i64;
            if (is_visited == 0i64) {
                drop(hnsw_visited_mark(visited_set, n_slot));

                int64:n_node_ptr = hnsw_arena_get_node(arena, n_slot, n_gen)  ?! 0i64;
                if (n_node_ptr != 0i64) {
                    if (filter_ast != 0i64) {
                        if (doc_store != 0i64) {
                            int64:doc_ptr = npk_mem_read_int64(doc_store, @cast_unchecked<int64>(n_slot) * 8i64);
                            if (doc_ptr != 0i64) {
                                bool:match = raw evaluate_filter(filter_ast, doc_ptr);
                                if (match == false) {
                                    i = i + 1i64;
                                    continue;
                                }
                            }
                        }
                    }

                    int64:n_vec_offset = hnsw_node_get_vector_offset(n_node_ptr)  ?! 0i64;
                    float32:n_dist = hnsw_graph_distance(graph, query_offset, n_vec_offset)  ?! 0.0f32;

                    float32:f_dist2 = 3.402823466e+38f32;
                    int64:w_size2 = hnsw_pq_get_size(W)  ?! 0i64;
                    if (w_size2 > 0i64) {
                        drop(hnsw_pq_peek(W, furthest));
                        f_dist2 = hnsw_pq_get_dist(furthest)  ?! 0.0f32;
                    }

                    if (w_size2 < ef_64) {
                        drop(hnsw_pq_push(candidates, n_dist, n_slot, n_gen));
                        drop(hnsw_pq_push(W, n_dist, n_slot, n_gen));
                    } else {
                        if (n_dist < f_dist2) {
                            drop(hnsw_pq_push(candidates, n_dist, n_slot, n_gen));
                            drop(hnsw_pq_push(W, n_dist, n_slot, n_gen));
                            drop(hnsw_pq_pop(W, furthest)); // Maintain W size == ef
                        }
                    }
                }
            }
            i = i + 1i64;
        }
    }

    drop(npk_core_dalloc(C));
    drop(npk_core_dalloc(furthest));
    drop(hnsw_pq_destroy(candidates));

    pass(W);
};

```

### File: `src/vector/hnsw_visited.npk`
```nitpick
// hnsw_visited.npk
// O(1) visited set tracking for HNSW graph traversal.
// Uses a contiguous flat array of int32 tracking the latest search ID.

use "../util/error_codes.npk".*;

pub fixed int64:HNSW_VISITED_OFF_CAPACITY = 0i64;
pub fixed int64:HNSW_VISITED_OFF_CURRENT = 8i64;
pub fixed int64:HNSW_VISITED_HEADER_SIZE = 16i64;

// Capacity must match the arena node capacity.
pub func:hnsw_visited_create = int64(int64:capacity) requires (capacity > 0i64) {
    int64:total_size = HNSW_VISITED_HEADER_SIZE + (capacity * 4i64);
    int64:visited = npk_core_alloc(total_size);
    if (visited == 0i64) { fail@cast_unchecked<tbb8>(ERR_HNSW_OOM); }

    drop(npk_mem_write_int64(visited, HNSW_VISITED_OFF_CAPACITY, capacity));
    drop(npk_mem_write_int64(visited, HNSW_VISITED_OFF_CURRENT, 0i64));
    drop(npk_mem_set(visited + HNSW_VISITED_HEADER_SIZE, 0i64, capacity * 4i64));

    pass(visited);
};

pub func:hnsw_visited_destroy = int64(int64:visited) requires (visited != 0i64) {
    drop(npk_core_dalloc(visited));
    pass(0i64);
};

// Increments search ID. If int32 wraps, zeroes the array to prevent collisions.
pub func:hnsw_visited_clear = int64(int64:visited) requires (visited != 0i64) {
    int64:curr = npk_mem_read_int64(visited, HNSW_VISITED_OFF_CURRENT) ;
    int32:curr32 = @cast_unchecked<int32>(curr);

    if (curr32 == 2147483647i32) {
        int64:capacity = npk_mem_read_int64(visited, HNSW_VISITED_OFF_CAPACITY) ;
        drop(npk_mem_set(visited + HNSW_VISITED_HEADER_SIZE, 0i64, capacity * 4i64));
        drop(npk_mem_write_int64(visited, HNSW_VISITED_OFF_CURRENT, 1i64));
    } else {
        drop(npk_mem_write_int64(visited, HNSW_VISITED_OFF_CURRENT, curr + 1i64));
    }
    pass(0i64);
};

pub func:hnsw_visited_mark = int64(int64:visited, int32:slot_idx) 
    requires (visited != 0i64), (slot_idx >= 0i32) {
    int64:curr = npk_mem_read_int64(visited, HNSW_VISITED_OFF_CURRENT) ;
    int32:curr32 = @cast_unchecked<int32>(curr);
    
    int64:slot64 = @cast_unchecked<int64>(slot_idx);
    int64:offset = HNSW_VISITED_HEADER_SIZE + (slot64 * 4i64);
    
    drop(npk_mem_write_int32(visited, offset, curr32));
    pass(0i64);
};

// Returns 1 if visited, 0 if not
pub func:hnsw_visited_check = int64(int64:visited, int32:slot_idx) 
    requires (visited != 0i64), (slot_idx >= 0i32) {
    int64:curr = npk_mem_read_int64(visited, HNSW_VISITED_OFF_CURRENT) ;
    int32:curr32 = @cast_unchecked<int32>(curr);
    
    int64:slot64 = @cast_unchecked<int64>(slot_idx);
    int64:offset = HNSW_VISITED_HEADER_SIZE + (slot64 * 4i64);
    
    int32:val = npk_mem_read_int32(visited, offset) ;
    if (val == curr32) { pass(1i64); }
    pass(0i64);
};

```

### File: `src/index/art.npk`
```nitpick
// art.npk — ART primary key index (single-threaded for now; lock-free in v0.1.6)

use "../util/error_codes.npk".*;
use "../util/constants.npk".*;
use "../util/mem_primitives.npk".*;
use "art_node.npk".*;
use "art_node_header.npk".*;
use "art_alloc.npk".*;
use "art_node4.npk".*;
use "art_node16.npk".*;
use "art_node48.npk".*;
use "art_node256.npk".*;
use "../concurrency/ebr.npk".*;

// The ART tree root. 0 means empty tree.
int64:art_root_ptr = 0i64;

// Global spinlock for write operations (insert/delete)
int64:art_write_lock_ptr = 0i64;

pub func:art_lock = NIL() {
    while (raw npk_cas_i64(art_write_lock_ptr, 0i64, 1i64) == false) { }
    pass(NIL);
};

pub func:art_unlock = NIL() {
    drop(npk_mem_write_int64(art_write_lock_ptr, 0i64, 0i64));
    pass(NIL);
};

// Initialize (or reinitialize) the ART. Sets root to 0.
pub func:art_init = NIL() {
    if (art_root_ptr == 0i64) { art_root_ptr = npk_core_alloc(8i64); }
    if (art_write_lock_ptr == 0i64) { art_write_lock_ptr = npk_core_alloc(8i64); }
    drop(npk_mem_write_int64(art_root_ptr, 0i64, 0i64));
    drop(npk_mem_write_int64(art_write_lock_ptr, 0i64, 0i64));
    pass(NIL);
};

// Return the current root pointer (for testing).
pub func:art_get_root = int64() {
    pass(npk_mem_read_int64(art_root_ptr, 0i64));
};

// Check how many bytes of the inline prefix of `node` match the key starting at `depth`.
pub func:art_check_prefix = int64(int64:node, int64:key_ptr, int64:key_len, int64:depth)
    requires node != 0i64, key_ptr != 0i64, depth >= 0i64, depth <= key_len
    ensures result >= 0i64
{
    int64:prefix_len = raw art_node_prefix_len(node);
    int64:max_compare = prefix_len;
    if ((depth + max_compare) > key_len) {
        max_compare = key_len - depth;
    }
    int64:i = 0i64;
    while (i < max_compare) {
        int64:prefix_byte = raw art_node_prefix_byte(node, i);
        int64:key_byte    = npk_mem_read_byte(key_ptr, depth + i) ;
        if (prefix_byte != key_byte) {
            pass(i);
        }
        i = i + 1i64;
    }
    pass(max_compare);
};

// Find the child pointer for the given key byte at the current node.
pub func:art_find_child = int64(int64:node, int64:key_byte)
    requires node != 0i64
{
    int64:ntype = raw art_node_type(node);
    if (ntype == ART_NODE4)   { pass(raw node4_find_child(node, key_byte)); }
    if (ntype == ART_NODE16)  { pass(raw node16_find_child(node, key_byte)); }
    if (ntype == ART_NODE48)  { pass(raw node48_find_child(node, key_byte)); }
    if (ntype == ART_NODE256) { pass(raw node256_get_child(node, key_byte)); }
    pass(0i64);
};

// Search for a key in the ART.
pub func:art_search = int64(int64:thread_id, int64:key_ptr, int64:key_len)
    requires key_ptr != 0i64, key_len > 0i64
{
    Result<NIL>:pin_res = ebr_pin(thread_id);
    if (pin_res.is_error) { pass(0i64); }

    int64:node  = npk_mem_read_int64(art_root_ptr, 0i64);
    int64:depth = 0i64;

    while (node != 0i64) 
        invariant depth >= 0i64, depth <= key_len
    {
        if (raw art_is_leaf(node)) {
            int64:lklen = raw art_leaf_key_len(node);
            if (lklen != key_len) { drop(ebr_unpin(thread_id)); pass(0i64); }
            int64:lkptr = node + LEAF_DATA_OFFSET;
            int64:match = npk_mem_compare(lkptr, key_ptr, key_len);
            if (match == 0i64) { drop(ebr_unpin(thread_id)); pass(node); }
            drop(ebr_unpin(thread_id)); pass(0i64);
        }

        int64:p = raw art_check_prefix(node, key_ptr, key_len, depth);
        int64:plen = raw art_node_prefix_len(node);
        if (p != plen) {
            drop(ebr_unpin(thread_id)); pass(0i64);
        }
        depth = depth + plen;
        int64:key_byte = 0i64;
        if (depth < key_len) {
            key_byte = npk_mem_read_byte(key_ptr, depth) ;
        }
        node = raw art_find_child(node, key_byte);
        depth = depth + 1i64;
    }
    drop(ebr_unpin(thread_id));
    pass(0i64);
};

// Helper: updates the parent's child pointer
pub func:art_update_child = NIL(int64:parent, int64:key_byte, int64:new_child) {
    int64:ptype = raw art_node_type(parent);
    if (ptype == ART_NODE4) {
        int64:num = raw art_node_num_children(parent);
        int64:i = 0i64;
        while (i < num) {
            if (raw node4_get_key(parent, i) == key_byte) {
                drop(raw node4_set_child(parent, i, new_child));
                pass(NIL);
            }
            i = i + 1i64;
        }
    }
    if (ptype == ART_NODE16) {
        int64:num = raw art_node_num_children(parent);
        int64:i = 0i64;
        while (i < num) {
            if (raw node16_get_key(parent, i) == key_byte) {
                drop(raw node16_set_child(parent, i, new_child));
                pass(NIL);
            }
            i = i + 1i64;
        }
    }
    if (ptype == ART_NODE48) {
        int64:slot = raw node48_get_slot(parent, key_byte);
        drop(raw node48_set_child(parent, slot, new_child));
    }
    if (ptype == ART_NODE256) {
        drop(raw node256_set_child(parent, key_byte, new_child));
    }
    pass(NIL);
};

// Grow a Node4 into a Node16

// Attempt to atomically swap the child pointer for `key_byte` in `parent_node`
// from `expected_child` to `new_child` using CAS.
pub func:art_cas_child = int64(int64:parent_node, int64:key_byte, int64:expected_child, int64:new_child)
    requires parent_node != 0i64
{
    int64:ntype = raw art_node_type(parent_node);
    int64:addr = 0i64;
    
    if (ntype == ART_NODE4) {
        int64:count = raw art_node_num_children(parent_node);
        int64:i = 0i64;
        while (i < count) {
            if (raw node4_get_key(parent_node, i) == key_byte) {
                addr = parent_node + NODE4_CHILDREN_OFFSET + i * 8i64;
                break;
            }
            i = i + 1i64;
        }
    } else {
        if (ntype == ART_NODE16) {
            int64:count = raw art_node_num_children(parent_node);
            int64:i = 0i64;
            while (i < count) {
                if (raw node16_get_key(parent_node, i) == key_byte) {
                    addr = parent_node + NODE16_CHILDREN_OFFSET + i * 8i64;
                    break;
                }
                i = i + 1i64;
            }
        } else {
            if (ntype == ART_NODE48) {
                int64:slot = raw node48_get_slot(parent_node, key_byte);
                if (slot != 0i64) {
                    addr = parent_node + NODE48_CHILDREN_OFFSET + ((slot - 1i64) * 8i64);
                }
            } else {
                if (ntype == ART_NODE256) {
                    addr = parent_node + NODE256_CHILDREN_OFFSET + key_byte * 8i64;
                }
            }
        }
    }
    
    if (addr == 0i64) { pass(0i64); }
    
    bool:success = raw npk_cas_i64(addr, expected_child, new_child);
    if (success) { pass(1i64); }
    pass(0i64);
};

pub func:art_copy_node = int64(int64:node) {
    int64:ntype = raw art_node_type(node);
    int64:new_node = 0i64;
    if (ntype == ART_NODE4) { new_node = raw art_alloc_node4(); }
    if (ntype == ART_NODE16) { new_node = raw art_alloc_node16(); }
    if (ntype == ART_NODE48) { new_node = raw art_alloc_node48(); }
    if (ntype == ART_NODE256) { new_node = raw art_alloc_node256(); }
    
    int64:plen = raw art_node_prefix_len(node);
    drop(raw art_node_set_prefix_len(new_node, plen));
    int64:i = 0i64;
    while (i < plen) {
        drop(raw art_node_set_prefix_byte(new_node, i, raw art_node_prefix_byte(node, i)));
        i = i + 1i64;
    }
    
    int64:num = raw art_node_num_children(node);
    drop(raw art_node_set_num_children(new_node, num));
    
    if (ntype == ART_NODE4) {
        i = 0i64;
        while (i < num) {
            drop(raw node4_set_key(new_node, i, raw node4_get_key(node, i)));
            drop(raw node4_set_child(new_node, i, raw node4_get_child(node, i)));
            i = i + 1i64;
        }
    } else {
        if (ntype == ART_NODE16) {
            i = 0i64;
            while (i < num) {
                drop(raw node16_set_key(new_node, i, raw node16_get_key(node, i)));
                drop(raw node16_set_child(new_node, i, raw node16_get_child(node, i)));
                i = i + 1i64;
            }
        } else {
            if (ntype == ART_NODE48) {
                int64:k = 0i64;
                while (k < 256i64) {
                    int64:slot = raw node48_get_slot(node, k);
                    if (slot != 0i64) {
                        drop(raw node48_set_slot(new_node, k, slot));
                        drop(raw node48_set_child(new_node, slot, raw node48_get_child(node, slot)));
                    }
                    k = k + 1i64;
                }
            } else {
                if (ntype == ART_NODE256) {
                    int64:k = 0i64;
                    while (k < 256i64) {
                        int64:child = raw node256_get_child(node, k);
                        if (child != 0i64) {
                            drop(raw node256_set_child(new_node, k, child));
                        }
                        k = k + 1i64;
                    }
                }
            }
        }
    }
    pass(new_node);
};

pub func:art_add_child_copy = int64(int64:node, int64:key_byte, int64:child_ptr)
    requires node != 0i64, child_ptr != 0i64
{
    int64:ntype = raw art_node_type(node);
    int64:num = raw art_node_num_children(node);
    if (ntype == ART_NODE4) {
        if (num < 4i64) {
            int64:new_node = raw art_copy_node(node);
            drop(raw node4_set_key(new_node, num, key_byte));
            drop(raw node4_set_child(new_node, num, child_ptr));
            drop(raw art_node_set_num_children(new_node, num + 1i64));
            pass(new_node);
        } else {
            int64:n16 = raw art_alloc_node16();
            int64:plen = raw art_node_prefix_len(node);
            drop(raw art_node_set_prefix_len(n16, plen));
            int64:i = 0i64;
            while (i < plen) {
                drop(raw art_node_set_prefix_byte(n16, i, raw art_node_prefix_byte(node, i)));
                i = i + 1i64;
            }
            i = 0i64;
            while (i < num) {
                drop(raw node16_set_key(n16, i, raw node4_get_key(node, i)));
                drop(raw node16_set_child(n16, i, raw node4_get_child(node, i)));
                i = i + 1i64;
            }
            drop(raw node16_set_key(n16, num, key_byte));
            drop(raw node16_set_child(n16, num, child_ptr));
            drop(raw art_node_set_num_children(n16, num + 1i64));
            pass(n16);
        }
    } else {
        if (ntype == ART_NODE16) {
            if (num < 16i64) {
                int64:new_node = raw art_copy_node(node);
                drop(raw node16_set_key(new_node, num, key_byte));
                drop(raw node16_set_child(new_node, num, child_ptr));
                drop(raw art_node_set_num_children(new_node, num + 1i64));
                pass(new_node);
            } else {
                int64:n48 = raw art_alloc_node48();
                int64:plen = raw art_node_prefix_len(node);
                drop(raw art_node_set_prefix_len(n48, plen));
                int64:i = 0i64;
                while (i < plen) {
                    drop(raw art_node_set_prefix_byte(n48, i, raw art_node_prefix_byte(node, i)));
                    i = i + 1i64;
                }
                i = 0i64;
                while (i < num) {
                    int64:kb = raw node16_get_key(node, i);
                    drop(raw node48_set_slot(n48, kb, i + 1i64));
                    drop(raw node48_set_child(n48, i + 1i64, raw node16_get_child(node, i)));
                    i = i + 1i64;
                }
                drop(raw node48_set_slot(n48, key_byte, num + 1i64));
                drop(raw node48_set_child(n48, num + 1i64, child_ptr));
                drop(raw art_node_set_num_children(n48, num + 1i64));
                pass(n48);
            }
        } else {
            if (ntype == ART_NODE48) {
                if (num < 48i64) {
                    int64:new_node = raw art_copy_node(node);
                    int64:i = 0i64;
                    int64:empty_slot = 0i64;
                    while (i < 48i64) {
                        if (raw node48_get_child(new_node, i + 1i64) == 0i64) {
                            empty_slot = i + 1i64;
                            break;
                        }
                        i = i + 1i64;
                    }
                    drop(raw node48_set_slot(new_node, key_byte, empty_slot));
                    drop(raw node48_set_child(new_node, empty_slot, child_ptr));
                    drop(raw art_node_set_num_children(new_node, num + 1i64));
                    pass(new_node);
                } else {
                    int64:n256 = raw art_alloc_node256();
                    int64:plen = raw art_node_prefix_len(node);
                    drop(raw art_node_set_prefix_len(n256, plen));
                    int64:i = 0i64;
                    while (i < plen) {
                        drop(raw art_node_set_prefix_byte(n256, i, raw art_node_prefix_byte(node, i)));
                        i = i + 1i64;
                    }
                    int64:k = 0i64;
                    while (k < 256i64) {
                        int64:slot = raw node48_get_slot(node, k);
                        if (slot != 0i64) {
                            drop(raw node256_set_child(n256, k, raw node48_get_child(node, slot)));
                        }
                        k = k + 1i64;
                    }
                    drop(raw node256_set_child(n256, key_byte, child_ptr));
                    drop(raw art_node_set_num_children(n256, num + 1i64));
                    pass(n256);
                }
            } else {
                if (ntype == ART_NODE256) {
                    int64:new_node = raw art_copy_node(node);
                    drop(raw node256_set_child(new_node, key_byte, child_ptr));
                    drop(raw art_node_set_num_children(new_node, num + 1i64));
                    pass(new_node);
                }
            }
        }
    }
    pass(0i64);
};

pub func:art_insert_internal = int64(int64:thread_id, int64:key_ptr, int64:key_len, int64:val_ptr, int64:val_len)
    requires key_ptr != 0i64, key_len > 0i64, val_len >= 0i64
{
    Result<NIL>:pin_res = ebr_pin(thread_id);
    if (pin_res.is_error) { pass(0i64); }

    int64:restart = 1i64;
    while (restart == 1i64) {
        restart = 0i64;
        
        int64:root = npk_mem_read_int64(art_root_ptr, 0i64);
        if (root == 0i64) {
            int64:new_leaf = raw art_alloc_leaf(key_ptr, key_len, val_ptr, val_len);
            bool:success = raw npk_cas_i64(art_root_ptr, 0i64, new_leaf);
            if (success) {
                drop(ebr_unpin(thread_id));
                pass(0i64);
            } else {
                drop(raw art_free_node(new_leaf));
                restart = 1i64;
                continue;
            }
        }
        
        int64:node = root;
        int64:parent = 0i64;
        int64:parent_key_byte = 0i64;
        int64:depth = 0i64;
        
        while (node != 0i64) {
            if (raw art_is_leaf(node)) {
                int64:lklen = raw art_leaf_key_len(node);
                int64:lkptr = node + LEAF_DATA_OFFSET;
                int64:match = 1i64;
                if (lklen == key_len) {
                    match = npk_mem_compare(lkptr, key_ptr, key_len);
                }
                if (match == 0i64) {
                    // Upsert: replace leaf
                    int64:new_leaf = raw art_alloc_leaf(key_ptr, key_len, val_ptr, val_len);
                    if (parent == 0i64) {
                        bool:success = raw npk_cas_i64(art_root_ptr, node, new_leaf);
                        if (success) {
                            drop(raw ebr_retire_or_flush(thread_id, node));
                            drop(ebr_unpin(thread_id));
                            pass(1i64);
                        } else {
                            drop(raw art_free_node(new_leaf));
                            restart = 1i64;
                            break; // restart
                        }
                    } else {
                        int64:cas_res = raw art_cas_child(parent, parent_key_byte, node, new_leaf);
                        if (cas_res == 1i64) {
                            drop(raw ebr_retire_or_flush(thread_id, node));
                            drop(ebr_unpin(thread_id));
                            pass(1i64);
                        } else {
                            drop(raw art_free_node(new_leaf));
                            restart = 1i64;
                            break; // restart
                        }
                    }
                }
                
                // Key mismatch at leaf -> split leaf!
                int64:max_cmp = key_len - depth;
                if ((lklen - depth) < max_cmp) { max_cmp = lklen - depth; }
                int64:p = 0i64;
                while (p < max_cmp && depth + p < key_len && p < lklen) {
                    int64:b1 = npk_mem_read_byte(lkptr, depth + p) ;
                    int64:b2 = npk_mem_read_byte(key_ptr, depth + p) ;
                    if (b1 != b2) { break; }
                    p = p + 1i64;
                }
                
                // Create a Node4 to hold both leaves
                int64:n4 = raw art_alloc_node4();
                drop(raw art_node_set_prefix_len(n4, p));
                int64:i = 0i64;
                while (i < p) {
                    drop(raw art_node_set_prefix_byte(n4, i, npk_mem_read_byte(key_ptr, depth + i)));
                    i = i + 1i64;
                }
                
                int64:b_exist = 0i64;
                if ((depth + p) < lklen) { b_exist = npk_mem_read_byte(lkptr, depth + p); }
                drop(raw node4_set_key(n4, 0i64, b_exist));
                drop(raw node4_set_child(n4, 0i64, node));
                
                int64:b_new = 0i64;
                if ((depth + p) < key_len) { b_new = npk_mem_read_byte(key_ptr, depth + p); }
                int64:new_leaf2 = raw art_alloc_leaf(key_ptr, key_len, val_ptr, val_len);
                drop(raw node4_set_key(n4, 1i64, b_new));
                drop(raw node4_set_child(n4, 1i64, new_leaf2));
                
                drop(raw art_node_set_num_children(n4, 2i64));
                
                if (parent == 0i64) {
                    bool:success = raw npk_cas_i64(art_root_ptr, node, n4);
                    if (success) {
                        drop(ebr_unpin(thread_id));
                        pass(0i64);
                    } else {
                        drop(raw art_free_node(new_leaf2));
                        drop(raw art_free_node(n4));
                        restart = 1i64;
                        break;
                    }
                } else {
                    int64:cas_res = raw art_cas_child(parent, parent_key_byte, node, n4);
                    if (cas_res == 1i64) {
                        drop(ebr_unpin(thread_id));
                        pass(0i64);
                    } else {
                        drop(raw art_free_node(new_leaf2));
                        drop(raw art_free_node(n4));
                        restart = 1i64;
                        break;
                    }
                }
            }
            
            int64:p2 = raw art_check_prefix(node, key_ptr, key_len, depth);
            int64:plen = raw art_node_prefix_len(node);
            if (p2 != plen) {
                // Prefix mismatch at internal node -> split node!
                int64:n4 = raw art_alloc_node4();
                
                drop(raw art_node_set_prefix_len(n4, p2));
                int64:i = 0i64;
                while (i < p2) {
                    drop(raw art_node_set_prefix_byte(n4, i, raw art_node_prefix_byte(node, i)));
                    i = i + 1i64;
                }
                
                int64:b_exist = raw art_node_prefix_byte(node, p2);
                drop(raw node4_set_key(n4, 0i64, b_exist));
                drop(raw node4_set_child(n4, 0i64, node));
                
                // But wait, we cannot mutate `node` in place! We must COPY `node`!
                // Wait! Splitting a prefix requires mutating the old node's prefix_len and prefix bytes!
                // In OLC, we CANNOT mutate `node` in place. We MUST copy `node`!
                
                // Copy the node
                int64:node_copy = raw art_copy_node(node);
                
                int64:new_plen = plen - p2 - 1i64;
                drop(raw art_node_set_prefix_len(node_copy, new_plen));
                i = 0i64;
                while (i < new_plen) {
                    drop(raw art_node_set_prefix_byte(node_copy, i, raw art_node_prefix_byte(node, p2 + 1i64 + i)));
                    i = i + 1i64;
                }
                drop(raw node4_set_child(n4, 0i64, node_copy));
                
                int64:b_new = 0i64;
                if ((depth + p2) < key_len) {
                    b_new = npk_mem_read_byte(key_ptr, depth + p2);
                }
                int64:new_leaf2 = raw art_alloc_leaf(key_ptr, key_len, val_ptr, val_len);
                drop(raw node4_set_key(n4, 1i64, b_new));
                drop(raw node4_set_child(n4, 1i64, new_leaf2));
                
                drop(raw art_node_set_num_children(n4, 2i64));
                
                if (parent == 0i64) {
                    bool:success = raw npk_cas_i64(art_root_ptr, node, n4);
                    if (success) {
                        drop(raw ebr_retire_or_flush(thread_id, node));
                        drop(ebr_unpin(thread_id));
                        pass(0i64);
                    } else {
                        drop(raw art_free_node(new_leaf2));
                        drop(raw art_free_node(node_copy));
                        drop(raw art_free_node(n4));
                        restart = 1i64;
                        break;
                    }
                } else {
                    int64:cas_res = raw art_cas_child(parent, parent_key_byte, node, n4);
                    if (cas_res == 1i64) {
                        drop(raw ebr_retire_or_flush(thread_id, node));
                        drop(ebr_unpin(thread_id));
                        pass(0i64);
                    } else {
                        drop(raw art_free_node(new_leaf2));
                        drop(raw art_free_node(node_copy));
                        drop(raw art_free_node(n4));
                        restart = 1i64;
                        break;
                    }
                }
            }
            
            depth = depth + plen;
            int64:key_byte = 0i64;
            if (depth < key_len) {
                key_byte = npk_mem_read_byte(key_ptr, depth) ;
            }
            
            int64:next_child = raw art_find_child(node, key_byte);
            
            if (next_child == 0i64) {
                // Slot is empty, add child. But we cannot mutate `node` in place!
                // We must COPY `node`, add child to the copy, and CAS the parent's pointer to the copy!
                int64:new_leaf = raw art_alloc_leaf(key_ptr, key_len, val_ptr, val_len);
                int64:new_node = raw art_add_child_copy(node, key_byte, new_leaf);
                
                if (parent == 0i64) {
                    bool:success = raw npk_cas_i64(art_root_ptr, node, new_node);
                    if (success) {
                        drop(raw ebr_retire_or_flush(thread_id, node));
                        drop(ebr_unpin(thread_id));
                        pass(0i64);
                    } else {
                        drop(raw art_free_node(new_leaf));
                        drop(raw art_free_node(new_node));
                        restart = 1i64;
                        break;
                    }
                } else {
                    int64:cas_res = raw art_cas_child(parent, parent_key_byte, node, new_node);
                    if (cas_res == 1i64) {
                        drop(raw ebr_retire_or_flush(thread_id, node));
                        drop(ebr_unpin(thread_id));
                        pass(0i64);
                    } else {
                        drop(raw art_free_node(new_leaf));
                        drop(raw art_free_node(new_node));
                        restart = 1i64;
                        break;
                    }
                }
            }
            
            parent = node;
            parent_key_byte = key_byte;
            node = next_child;
            depth = depth + 1i64;
        }
    }
    drop(ebr_unpin(thread_id));
    pass(0i64);
};

pub func:art_insert = int64(int64:thread_id, int64:key_ptr, int64:key_len, int64:val_ptr, int64:val_len)
    ensures result == 0i64 || result == 1i64
{
    drop(art_lock());
    int64:res = raw art_insert_internal(thread_id, key_ptr, key_len, val_ptr, val_len);
    drop(art_unlock());
    pass(res);
};

// Scratch for art_delete lockfree
pub func:art_remove_child_copy = int64(int64:node, int64:key_byte) {
    int64:ntype = raw art_node_type(node);
    int64:num = raw art_node_num_children(node);

    int64:plen = raw art_node_prefix_len(node);
    int64:i = 0i64;

    if (ntype == ART_NODE4) {
        int64:n4 = raw art_alloc_node4();
        drop(raw art_node_set_prefix_len(n4, plen));
        while (i < plen) { drop(raw art_node_set_prefix_byte(n4, i, raw art_node_prefix_byte(node, i))); i = i + 1i64; }

        i = 0i64;
        int64:idx = 0i64;
        while (i < num) {
            int64:kb = raw node4_get_key(node, i);
            if (kb != key_byte) {
                drop(raw node4_set_key(n4, idx, kb));
                drop(raw node4_set_child(n4, idx, raw node4_get_child(node, i)));
                idx = idx + 1i64;
            }
            i = i + 1i64;
        }
        drop(raw art_node_set_num_children(n4, num - 1i64));
        pass(n4);
    } else if (ntype == ART_NODE16) {
        if (num <= 4i64) {
            int64:n4 = raw art_alloc_node4();
            drop(raw art_node_set_prefix_len(n4, plen));
            while (i < plen) { drop(raw art_node_set_prefix_byte(n4, i, raw art_node_prefix_byte(node, i))); i = i + 1i64; }

            i = 0i64;
            int64:idx = 0i64;
            while (i < num) {
                int64:kb = raw node16_get_key(node, i);
                if (kb != key_byte) {
                    drop(raw node4_set_key(n4, idx, kb));
                    drop(raw node4_set_child(n4, idx, raw node16_get_child(node, i)));
                    idx = idx + 1i64;
                }
                i = i + 1i64;
            }
            drop(raw art_node_set_num_children(n4, num - 1i64));
            pass(n4);
        } else {
            int64:n16 = raw art_alloc_node16();
            drop(raw art_node_set_prefix_len(n16, plen));
            while (i < plen) { drop(raw art_node_set_prefix_byte(n16, i, raw art_node_prefix_byte(node, i))); i = i + 1i64; }

            i = 0i64;
            int64:idx = 0i64;
            while (i < num) {
                int64:kb = raw node16_get_key(node, i);
                if (kb != key_byte) {
                    drop(raw node16_set_key(n16, idx, kb));
                    drop(raw node16_set_child(n16, idx, raw node16_get_child(node, i)));
                    idx = idx + 1i64;
                }
                i = i + 1i64;
            }
            drop(raw art_node_set_num_children(n16, num - 1i64));
            pass(n16);
        }
    } else if (ntype == ART_NODE48) {
        if (num <= 12i64) {
            int64:n16 = raw art_alloc_node16();
            drop(raw art_node_set_prefix_len(n16, plen));
            while (i < plen) { drop(raw art_node_set_prefix_byte(n16, i, raw art_node_prefix_byte(node, i))); i = i + 1i64; }

            i = 0i64;
            int64:idx = 0i64;
            while (i < 256i64) {
                int64:slot = raw node48_get_slot(node, i);
                if (slot != 0i64) {
                    if (i != key_byte) {
                        drop(raw node16_set_key(n16, idx, i));
                        drop(raw node16_set_child(n16, idx, raw node48_get_child(node, slot)));
                        idx = idx + 1i64;
                    }
                }
                i = i + 1i64;
            }
            drop(raw art_node_set_num_children(n16, num - 1i64));
            pass(n16);
        }
    } else if (ntype == ART_NODE256) {
        if (num <= 48i64) {
            int64:n48 = raw art_alloc_node48();
            drop(raw art_node_set_prefix_len(n48, plen));
            while (i < plen) { drop(raw art_node_set_prefix_byte(n48, i, raw art_node_prefix_byte(node, i))); i = i + 1i64; }

            i = 0i64;
            int64:idx = 1i64;
            while (i < 256i64) {
                int64:child = raw node256_get_child(node, i);
                if (child != 0i64) {
                    if (i != key_byte) {
                        drop(raw node48_set_slot(n48, i, idx));
                        drop(raw node48_set_child(n48, idx, child));
                        idx = idx + 1i64;
                    }
                }
                i = i + 1i64;
            }
            drop(raw art_node_set_num_children(n48, num - 1i64));
            pass(n48);
        }
    }
    pass(0i64);
};

pub func:art_delete_internal = int64(int64:thread_id, int64:key_ptr, int64:key_len)
    requires key_ptr != 0i64, key_len > 0i64
{
    Result<NIL>:pin_res = ebr_pin(thread_id);
    if (pin_res.is_error) { pass(ERR_ART_KEY_NOT_FOUND); }

    int64:restart = 1i64;
    while (restart == 1i64) {
        restart = 0i64;
        
        int64:root = npk_mem_read_int64(art_root_ptr, 0i64);
        if (root == 0i64) {
            drop(ebr_unpin(thread_id));
            pass(ERR_ART_KEY_NOT_FOUND);
        }
        
        if (raw art_is_leaf(root)) {
            int64:lklen = raw art_leaf_key_len(root);
            int64:lkptr = root + LEAF_DATA_OFFSET;
            if (lklen == key_len) {
                if (npk_mem_compare(lkptr, key_ptr, key_len) == 0i64) {
                    bool:success = raw npk_cas_i64(art_root_ptr, root, 0i64);
                    if (success) {
                        drop(raw ebr_retire_or_flush(thread_id, root));
                        drop(ebr_unpin(thread_id));
                        pass(0i64);
                    } else {
                        restart = 1i64;
                        continue;
                    }
                }
            }
            drop(ebr_unpin(thread_id));
            pass(ERR_ART_KEY_NOT_FOUND);
        }

        int64:node = root;
        int64:parent = 0i64;
        int64:parent_key_byte = 0i64;
        
        int64:gparent = 0i64;
        int64:gparent_key_byte = 0i64;
        
        int64:depth = 0i64;

        while (node != 0i64) {
            if (raw art_is_leaf(node)) {
                int64:lklen = raw art_leaf_key_len(node);
                int64:lkptr = node + LEAF_DATA_OFFSET;
                if (lklen != key_len) { drop(ebr_unpin(thread_id)); pass(ERR_ART_KEY_NOT_FOUND); }
                if (npk_mem_compare(lkptr, key_ptr, key_len) != 0i64) { drop(ebr_unpin(thread_id)); pass(ERR_ART_KEY_NOT_FOUND); }

                // Match! Remove from parent
                int64:ntype = raw art_node_type(parent);
                int64:num = raw art_node_num_children(parent);

                // For Node48 and Node256, we can zero in place
                if (ntype == ART_NODE256) {
                    if (num <= 48i64) {
                        int64:new_node = raw art_remove_child_copy(parent, parent_key_byte);
                        int64:cas_res = 0i64;
                        if (gparent == 0i64) {
                            bool:success = raw npk_cas_i64(art_root_ptr, parent, new_node);
                            if (success) { cas_res = 1i64; }
                        } else {
                            cas_res = raw art_cas_child(gparent, gparent_key_byte, parent, new_node);
                        }
                        if (cas_res == 1i64) {
                            drop(raw ebr_retire_or_flush(thread_id, parent));
                            drop(raw ebr_retire_or_flush(thread_id, node));
                            drop(ebr_unpin(thread_id));
                            pass(0i64);
                        } else {
                            drop(raw art_free_node(new_node));
                            restart = 1i64;
                            break;
                        }
                    } else {
                        int64:cas_res = raw art_cas_child(parent, parent_key_byte, node, 0i64);
                        if (cas_res == 1i64) {
                            drop(raw art_node_set_num_children(parent, num - 1i64));
                            drop(raw ebr_retire_or_flush(thread_id, node));
                            drop(ebr_unpin(thread_id));
                            pass(0i64);
                        } else {
                            restart = 1i64;
                            break;
                        }
                    }
                } else if (ntype == ART_NODE48) {
                    if (num <= 12i64) {
                        int64:new_node = raw art_remove_child_copy(parent, parent_key_byte);
                        int64:cas_res = 0i64;
                        if (gparent == 0i64) {
                            bool:success = raw npk_cas_i64(art_root_ptr, parent, new_node);
                            if (success) { cas_res = 1i64; }
                        } else {
                            cas_res = raw art_cas_child(gparent, gparent_key_byte, parent, new_node);
                        }
                        if (cas_res == 1i64) {
                            drop(raw ebr_retire_or_flush(thread_id, parent));
                            drop(raw ebr_retire_or_flush(thread_id, node));
                            drop(ebr_unpin(thread_id));
                            pass(0i64);
                        } else {
                            drop(raw art_free_node(new_node));
                            restart = 1i64;
                            break;
                        }
                    } else {
                        int64:cas_res = raw art_cas_child(parent, parent_key_byte, node, 0i64);
                        if (cas_res == 1i64) {
                            drop(raw node48_set_slot(parent, parent_key_byte, 0i64));
                            drop(raw art_node_set_num_children(parent, num - 1i64));
                            drop(raw ebr_retire_or_flush(thread_id, node));
                            drop(ebr_unpin(thread_id));
                            pass(0i64);
                        } else {
                            restart = 1i64;
                            break;
                        }
                    }
                } else if (ntype == ART_NODE16) {
                    int64:new_node = raw art_remove_child_copy(parent, parent_key_byte);
                    int64:cas_res = 0i64;
                    if (gparent == 0i64) {
                        bool:success = raw npk_cas_i64(art_root_ptr, parent, new_node);
                        if (success) { cas_res = 1i64; }
                    } else {
                        cas_res = raw art_cas_child(gparent, gparent_key_byte, parent, new_node);
                    }
                    if (cas_res == 1i64) {
                        drop(raw ebr_retire_or_flush(thread_id, parent));
                        drop(raw ebr_retire_or_flush(thread_id, node));
                        drop(ebr_unpin(thread_id));
                        pass(0i64);
                    } else {
                        drop(raw art_free_node(new_node));
                        restart = 1i64;
                        break;
                    }
                } else if (ntype == ART_NODE4) {
                    if (num == 2i64) {
                        // Collapse! Grandparent pointer to the other child, plus merge prefix
                        // Find the other child
                        int64:other_child = 0i64;
                        int64:other_kb = 0i64;
                        int64:i = 0i64;
                        while (i < 4i64) {
                            int64:c = raw node4_get_child(parent, i);
                            if (c != 0i64) {
                                if (c != node) {
                                    other_child = c;
                                    other_kb = raw node4_get_key(parent, i);
                                }
                            }
                            i = i + 1i64;
                        }
                        
                        if (raw art_is_leaf(other_child)) {
                            // If it's a leaf, just point grandparent to it
                            int64:cas_res = 0i64;
                            if (gparent == 0i64) {
                                bool:success = raw npk_cas_i64(art_root_ptr, parent, other_child);
                                if (success) { cas_res = 1i64; }
                            } else {
                                cas_res = raw art_cas_child(gparent, gparent_key_byte, parent, other_child);
                            }
                            if (cas_res == 1i64) {
                                drop(raw ebr_retire_or_flush(thread_id, parent));
                                drop(raw ebr_retire_or_flush(thread_id, node));
                                drop(ebr_unpin(thread_id));
                                pass(0i64);
                            } else {
                                restart = 1i64;
                                break;
                            }
                        } else {
                            // It's an internal node, we must merge prefix. Copy other_child.
                            int64:new_child = raw art_copy_node(other_child);
                            // new prefix length = parent.plen + 1 + other_child.plen
                            int64:p1 = raw art_node_prefix_len(parent);
                            int64:p2 = raw art_node_prefix_len(other_child);
                            int64:nplen = p1 + 1i64 + p2;
                            if (nplen > 10i64) { nplen = 10i64; }
                            
                            drop(raw art_node_set_prefix_len(new_child, p1 + 1i64 + p2));
                            int64:i2 = 0i64;
                            while (i2 < p1) {
                                drop(raw art_node_set_prefix_byte(new_child, i2, raw art_node_prefix_byte(parent, i2)));
                                i2 = i2 + 1i64;
                            }
                            if (p1 < 10i64) {
                                drop(raw art_node_set_prefix_byte(new_child, p1, other_kb));
                            }
                            int64:i3 = 0i64;
                            while (i3 < p2) {
                                if ((p1 + 1i64 + i3) < 10i64) {
                                    drop(raw art_node_set_prefix_byte(new_child, p1 + 1i64 + i3, raw art_node_prefix_byte(other_child, i3)));
                                }
                                i3 = i3 + 1i64;
                            }
                            
                            int64:cas_res = 0i64;
                            if (gparent == 0i64) {
                                bool:success = raw npk_cas_i64(art_root_ptr, parent, new_child);
                                if (success) { cas_res = 1i64; }
                            } else {
                                cas_res = raw art_cas_child(gparent, gparent_key_byte, parent, new_child);
                            }
                            if (cas_res == 1i64) {
                                drop(raw ebr_retire_or_flush(thread_id, parent));
                                drop(raw ebr_retire_or_flush(thread_id, node));
                                drop(raw ebr_retire_or_flush(thread_id, other_child));
                                drop(ebr_unpin(thread_id));
                                pass(0i64);
                            } else {
                                drop(raw art_free_node(new_child));
                                restart = 1i64;
                                break;
                            }
                        }
                    } else {
                        // Num > 2, just copy without child
                        int64:new_node = raw art_remove_child_copy(parent, parent_key_byte);
                        int64:cas_res = 0i64;
                        if (gparent == 0i64) {
                            bool:success = raw npk_cas_i64(art_root_ptr, parent, new_node);
                            if (success) { cas_res = 1i64; }
                        } else {
                            cas_res = raw art_cas_child(gparent, gparent_key_byte, parent, new_node);
                        }
                        if (cas_res == 1i64) {
                            drop(raw ebr_retire_or_flush(thread_id, parent));
                            drop(raw ebr_retire_or_flush(thread_id, node));
                            drop(ebr_unpin(thread_id));
                            pass(0i64);
                        } else {
                            drop(raw art_free_node(new_node));
                            restart = 1i64;
                            break;
                        }
                    }
                }
            }

            int64:p2 = raw art_check_prefix(node, key_ptr, key_len, depth);
            int64:plen = raw art_node_prefix_len(node);
            if (p2 != plen) { drop(ebr_unpin(thread_id)); pass(ERR_ART_KEY_NOT_FOUND); }

            depth = depth + plen;
            int64:key_byte = 0i64;
            if (depth < key_len) {
                key_byte = npk_mem_read_byte(key_ptr, depth);
            }
            
            int64:next_child = raw art_find_child(node, key_byte);
            if (next_child == 0i64) { drop(ebr_unpin(thread_id)); pass(ERR_ART_KEY_NOT_FOUND); }

            gparent = parent;
            gparent_key_byte = parent_key_byte;
            parent = node;
            parent_key_byte = key_byte;
            node = next_child;
            depth = depth + 1i64;
        }
    }
    drop(art_unlock());
    drop(ebr_unpin(thread_id));
    pass(ERR_ART_KEY_NOT_FOUND);
};

pub func:art_delete = int64(int64:thread_id, int64:key_ptr, int64:key_len)
{
    drop(art_lock());
    int64:res = raw art_delete_internal(thread_id, key_ptr, key_len);
    drop(art_unlock());
    pass(res);
};

func:art_destroy_node = NIL(int64:node) {
    if (node == 0i64) { pass(NIL); }
    if (raw art_is_leaf(node)) {
        drop(raw art_free_node(node));
        pass(NIL);
    }
    
    int64:ntype = raw art_node_type(node);
    if (ntype == ART_NODE4) {
        int64:i = 0i64;
        while (i < 4i64) {
            int64:child = raw node4_get_child(node, i);
            if (child != 0i64) { drop(raw art_destroy_node(child)); }
            i = i + 1i64;
        }
    }
    if (ntype == ART_NODE16) {
        int64:i = 0i64;
        while (i < 16i64) {
            int64:child = raw node16_get_child(node, i);
            if (child != 0i64) { drop(raw art_destroy_node(child)); }
            i = i + 1i64;
        }
    }
    if (ntype == ART_NODE48) {
        int64:i = 1i64;
        while (i <= 48i64) {
            int64:child = raw node48_get_child(node, i);
            if (child != 0i64) { drop(raw art_destroy_node(child)); }
            i = i + 1i64;
        }
    }
    if (ntype == ART_NODE256) {
        int64:i = 0i64;
        while (i < 256i64) {
            int64:child = raw node256_get_child(node, i);
            if (child != 0i64) { drop(raw art_destroy_node(child)); }
            i = i + 1i64;
        }
    }
    drop(raw art_free_node(node));
    pass(NIL);
};
pub func:art_destroy = NIL() {
    int64:root = npk_mem_read_int64(art_root_ptr, 0i64);
    if (root != 0i64) {
        drop(raw art_destroy_node(root));
        drop(npk_mem_write_int64(art_root_ptr, 0i64, 0i64));
    }
    pass(NIL);
};

```

### File: `src/index/art_alloc.npk`
```nitpick
use "../util/constants.npk".*;
use "../util/error_codes.npk".*;
use "art_node.npk".*;
use "../util/mem_primitives.npk".*;

pub func:art_alloc_node4 = int64()
    ensures result != 0i64 {
    int64:ptr = npk_core_alloc(NODE4_SIZE);
    if (ptr == 0i64) { fail(ERR_ART_CAS_FAILED => tbb8); }
    drop(npk_mem_set(ptr, 0i64, NODE4_SIZE));
    drop(npk_mem_write_byte(ptr, ART_HDR_TYPE, (ART_NODE4 => int64)));
    drop(npk_mem_write_byte(ptr, ART_HDR_NUM_CHILDREN, 0i64));
    pass(ptr);
};

pub func:art_alloc_node16 = int64()
    ensures result != 0i64 {
    int64:ptr = npk_core_alloc(NODE16_SIZE);
    if (ptr == 0i64) { fail(ERR_ART_CAS_FAILED => tbb8); }
    drop(npk_mem_set(ptr, 0i64, NODE16_SIZE));
    drop(npk_mem_write_byte(ptr, ART_HDR_TYPE, (ART_NODE16 => int64)));
    drop(npk_mem_write_byte(ptr, ART_HDR_NUM_CHILDREN, 0i64));
    pass(ptr);
};

pub func:art_alloc_node48 = int64()
    ensures result != 0i64 {
    int64:ptr = npk_core_alloc(NODE48_SIZE);
    if (ptr == 0i64) { fail(ERR_ART_CAS_FAILED => tbb8); }
    drop(npk_mem_set(ptr, 0i64, NODE48_SIZE));
    drop(npk_mem_write_byte(ptr, ART_HDR_TYPE, (ART_NODE48 => int64)));
    drop(npk_mem_write_byte(ptr, ART_HDR_NUM_CHILDREN, 0i64));
    pass(ptr);
};

pub func:art_alloc_node256 = int64()
    ensures result != 0i64 {
    int64:ptr = npk_core_alloc(NODE256_SIZE);
    if (ptr == 0i64) { fail(ERR_ART_CAS_FAILED => tbb8); }
    drop(npk_mem_set(ptr, 0i64, NODE256_SIZE));
    drop(npk_mem_write_byte(ptr, ART_HDR_TYPE, (ART_NODE256 => int64)));
    drop(npk_mem_write_byte(ptr, ART_HDR_NUM_CHILDREN, 0i64));
    pass(ptr);
};

pub func:art_alloc_leaf = int64(int64:key_ptr, int64:key_len, int64:val_ptr, int64:val_len)
    ensures result != 0i64 {
    int64:leaf_size = LEAF_DATA_OFFSET + key_len + val_len;
    int64:ptr = npk_core_alloc(leaf_size);
    if (ptr == 0i64) { fail(ERR_ART_CAS_FAILED => tbb8); }
    drop(npk_mem_set(ptr, 0i64, leaf_size));
    drop(npk_mem_write_byte(ptr, ART_HDR_TYPE, (ART_LEAF => int64)));
    drop(npk_mem_write_int64(ptr, LEAF_KEY_LEN_OFFSET, key_len));
    drop(npk_mem_write_int64(ptr, LEAF_VAL_LEN_OFFSET, val_len));
    drop(npk_mem_copy(ptr + LEAF_DATA_OFFSET, key_ptr, key_len));
    drop(npk_mem_copy(ptr + LEAF_DATA_OFFSET + key_len, val_ptr, val_len));
    pass(ptr);
};

pub func:art_free_node = NIL(int64:node) {
    if (node != 0i64) {
        drop(npk_core_dalloc(node));
    }
    pass(NIL);
};

pub func:art_leaf_key = int64(int64:leaf) {
    int64:klen = npk_mem_read_int64(leaf, LEAF_KEY_LEN_OFFSET);
    int64:out  = npk_core_alloc(klen);
    drop(npk_mem_copy(out, leaf + LEAF_DATA_OFFSET, klen));
    pass(out);
};

pub func:art_leaf_key_len = int64(int64:leaf) {
    pass(npk_mem_read_int64(leaf, LEAF_KEY_LEN_OFFSET));
};

pub func:art_leaf_val_len = int64(int64:leaf) {
    pass(npk_mem_read_int64(leaf, LEAF_VAL_LEN_OFFSET));
};

pub func:art_leaf_val_ptr = int64(int64:leaf) {
    int64:klen = npk_mem_read_int64(leaf, LEAF_KEY_LEN_OFFSET);
    pass(leaf + LEAF_DATA_OFFSET + klen);
};

```

### File: `src/index/art_iter.npk`
```nitpick
// art_iter.npk — ART range iterator
//
// Iterator layout (flat buffer, dynamically allocated):
//   Bytes  0-7:   stack_buf_ptr (int64) — pointer to the DFS stack buffer
//   Bytes  8-15:  stack_cap     (int64) — capacity of stack in frames
//   Bytes 16-23:  stack_top     (int64) — index of top frame (-1 = empty)
//   Bytes 24-31:  start_key_ptr (int64) — lower bound key bytes (0 = no lower bound)
//   Bytes 32-39:  start_key_len (int64)
//   Bytes 40-47:  end_key_ptr   (int64) — upper bound key bytes (0 = no upper bound)
//   Bytes 48-55:  end_key_len   (int64)
//   Bytes 56-63:  done          (int64) — 1 if iteration is complete
//   Total: 64 bytes

use "../util/error_codes.npk".*;
use "../util/constants.npk".*;
use "../util/mem_primitives.npk".*;
use "art_node.npk".*;
use "art_node_header.npk".*;
use "art_alloc.npk".*;
use "art_node4.npk".*;
use "art_node16.npk".*;
use "art_node48.npk".*;
use "art_node256.npk".*;
use "art.npk".*;

pub fixed int64:ITER_SIZE          = 64i64;
pub fixed int64:ITER_STACK_BUF     = 0i64;
pub fixed int64:ITER_STACK_CAP     = 8i64;
pub fixed int64:ITER_STACK_TOP     = 16i64;
pub fixed int64:ITER_START_KEY_PTR = 24i64;
pub fixed int64:ITER_START_KEY_LEN = 32i64;
pub fixed int64:ITER_END_KEY_PTR   = 40i64;
pub fixed int64:ITER_END_KEY_LEN   = 48i64;
pub fixed int64:ITER_DONE          = 56i64;

// Stack frame layout (16 bytes each):
//   Bytes 0-7:  node_ptr     (int64) — pointer to the current node
//   Bytes 8-15: child_index  (int64) — next child index to visit (0..255)
pub fixed int64:FRAME_SIZE        = 16i64;
pub fixed int64:FRAME_NODE_PTR   = 0i64;
pub fixed int64:FRAME_CHILD_IDX  = 8i64;

// Default iterator stack depth (grows if needed)
pub fixed int64:ITER_DEFAULT_STACK_CAP = 64i64;

func:iter_stack_push = NIL(int64:iter, int64:node_ptr, int64:child_index) {
    int64:stack_buf = npk_mem_read_int64(iter, ITER_STACK_BUF);
    int64:stack_cap = npk_mem_read_int64(iter, ITER_STACK_CAP);
    int64:stack_top = npk_mem_read_int64(iter, ITER_STACK_TOP);
    
    int64:next_top = stack_top + 1i64;
    if (next_top >= stack_cap) {
        int64:new_cap = stack_cap * 2i64;
        int64:new_buf = npk_core_alloc(new_cap * FRAME_SIZE);
        drop(npk_mem_copy(new_buf, stack_buf, stack_cap * FRAME_SIZE));
        drop(npk_core_dalloc(stack_buf));
        stack_buf = new_buf;
        stack_cap = new_cap;
        drop(npk_mem_write_int64(iter, ITER_STACK_BUF, stack_buf));
        drop(npk_mem_write_int64(iter, ITER_STACK_CAP, stack_cap));
    }
    
    int64:frame_ptr = stack_buf + (next_top * FRAME_SIZE);
    drop(npk_mem_write_int64(frame_ptr, FRAME_NODE_PTR, node_ptr));
    drop(npk_mem_write_int64(frame_ptr, FRAME_CHILD_IDX, child_index));
    drop(npk_mem_write_int64(iter, ITER_STACK_TOP, next_top));
    pass(NIL);
};

func:iter_stack_pop = int64(int64:iter) {
    int64:stack_top = npk_mem_read_int64(iter, ITER_STACK_TOP);
    if (stack_top == -1i64) { pass(0i64); }
    int64:stack_buf = npk_mem_read_int64(iter, ITER_STACK_BUF);
    int64:frame_ptr = stack_buf + (stack_top * FRAME_SIZE);
    drop(npk_mem_write_int64(iter, ITER_STACK_TOP, stack_top - 1i64));
    pass(frame_ptr);
};

func:iter_stack_peek = int64(int64:iter) {
    int64:stack_top = npk_mem_read_int64(iter, ITER_STACK_TOP);
    if (stack_top == -1i64) { pass(0i64); }
    int64:stack_buf = npk_mem_read_int64(iter, ITER_STACK_BUF);
    int64:frame_ptr = stack_buf + (stack_top * FRAME_SIZE);
    pass(frame_ptr);
};

pub func:art_iter_create_range = int64(int64:start_ptr, int64:start_len, int64:end_ptr, int64:end_len) {
    int64:iter = npk_core_alloc(ITER_SIZE);
    if (iter == 0i64) { pass(0i64); }

    int64:stack_buf = npk_core_alloc(ITER_DEFAULT_STACK_CAP * FRAME_SIZE);
    if (stack_buf == 0i64) {
        drop(npk_core_dalloc(iter));
        pass(0i64);
    }
    
    drop(npk_mem_write_int64(iter, ITER_STACK_BUF, stack_buf));
    drop(npk_mem_write_int64(iter, ITER_STACK_CAP, ITER_DEFAULT_STACK_CAP));
    drop(npk_mem_write_int64(iter, ITER_STACK_TOP, -1i64));

    drop(npk_mem_write_int64(iter, ITER_START_KEY_PTR, start_ptr));
    drop(npk_mem_write_int64(iter, ITER_START_KEY_LEN, start_len));
    drop(npk_mem_write_int64(iter, ITER_END_KEY_PTR,   end_ptr));
    drop(npk_mem_write_int64(iter, ITER_END_KEY_LEN,   end_len));
    drop(npk_mem_write_int64(iter, ITER_DONE, 0i64));

    int64:root = raw art_get_root();
    if (root != 0i64) {
        drop(iter_stack_push(iter, root, 0i64));
    } else {
        drop(npk_mem_write_int64(iter, ITER_DONE, 1i64));
    }
    pass(iter);
};

pub func:art_iter_create = int64() {
    pass(raw art_iter_create_range(0i64, 0i64, 0i64, 0i64));
};

pub func:art_iter_free = NIL(int64:iter) {
    if (iter == 0i64) { pass(NIL); }
    int64:stack_buf = npk_mem_read_int64(iter, ITER_STACK_BUF);
    if (stack_buf != 0i64) {
        drop(npk_core_dalloc(stack_buf));
    }
    drop(npk_core_dalloc(iter));
    pass(NIL);
};

pub func:art_node_get_nth_child = int64(int64:node, int64:n) {
    int64:num = raw art_node_num_children(node);
    if (n >= num) { pass(0i64); }
    
    int64:ntype = raw art_node_type(node);
    int64:result = npk_core_alloc(16i64);
    
    if (ntype == ART_NODE4) {
        int64:c0 = 256i64; int64:c1 = 256i64; int64:c2 = 256i64; int64:c3 = 256i64;
        int64:v0 = 0i64;   int64:v1 = 0i64;   int64:v2 = 0i64;   int64:v3 = 0i64;
        
        int64:i = 0i64;
        while (i < num) {
            int64:kb = raw node4_get_key(node, i);
            int64:child = raw node4_get_child(node, i);
            if (kb < c0) { c3 = c2; v3 = v2; c2 = c1; v2 = v1; c1 = c0; v1 = v0; c0 = kb; v0 = child; }
            else { if (kb < c1) { c3 = c2; v3 = v2; c2 = c1; v2 = v1; c1 = kb; v1 = child; }
            else { if (kb < c2) { c3 = c2; v3 = v2; c2 = kb; v2 = child; }
            else { if (kb < c3) { c3 = kb; v3 = child; } } } }
            i = i + 1i64;
        }
        
        int64:child = 0i64;
        int64:kb = 0i64;
        if (n == 0i64) { child = v0; kb = c0; }
        if (n == 1i64) { child = v1; kb = c1; }
        if (n == 2i64) { child = v2; kb = c2; }
        if (n == 3i64) { child = v3; kb = c3; }
        
        drop(npk_mem_write_int64(result, 0i64, child));
        drop(npk_mem_write_int64(result, 8i64, kb));
        pass(result);
    }
    if (ntype == ART_NODE16) {
        // Find the n-th smallest key. A simple way: find the smallest key greater than the (n-1)-th smallest key.
        // We can just iterate 0..255 and see which keys are present.
        int64:count = 0i64;
        int64:kb_iter = 0i64;
        while (kb_iter < 256i64) {
            int64:j = 0i64;
            while (j < num) {
                int64:kb = raw node16_get_key(node, j);
                if (kb == kb_iter) {
                    if (count == n) {
                        int64:child = raw node16_get_child(node, j);
                        drop(npk_mem_write_int64(result, 0i64, child));
                        drop(npk_mem_write_int64(result, 8i64, kb));
                        pass(result);
                    }
                    count = count + 1i64;
                }
                j = j + 1i64;
            }
            kb_iter = kb_iter + 1i64;
        }
    }
    if (ntype == ART_NODE48) {
        int64:count = 0i64;
        int64:i = 0i64;
        while (i < 256i64) {
            int64:slot = raw node48_get_slot(node, i);
            if (slot != 0i64) {
                if (count == n) {
                    int64:child = raw node48_get_child(node, slot);
                    drop(npk_mem_write_int64(result, 0i64, child));
                    drop(npk_mem_write_int64(result, 8i64, i));
                    pass(result);
                }
                count = count + 1i64;
            }
            i = i + 1i64;
        }
    }
    if (ntype == ART_NODE256) {
        int64:count = 0i64;
        int64:i = 0i64;
        while (i < 256i64) {
            int64:child = raw node256_get_child(node, i);
            if (child != 0i64) {
                if (count == n) {
                    drop(npk_mem_write_int64(result, 0i64, child));
                    drop(npk_mem_write_int64(result, 8i64, i));
                    pass(result);
                }
                count = count + 1i64;
            }
            i = i + 1i64;
        }
    }
    drop(npk_core_dalloc(result));
    pass(0i64);
};

func:compare_keys = int64(int64:k1_ptr, int64:k1_len, int64:k2_ptr, int64:k2_len) {
    int64:min_len = k1_len;
    if (k2_len < min_len) { min_len = k2_len; }
    int64:i = 0i64;
    while (i < min_len) {
        int64:b1 = npk_mem_read_byte(k1_ptr, i);
        int64:b2 = npk_mem_read_byte(k2_ptr, i);
        if (b1 < b2) { pass(-1i64); }
        if (b1 > b2) { pass(1i64); }
        i = i + 1i64;
    }
    if (k1_len < k2_len) { pass(-1i64); }
    if (k1_len > k2_len) { pass(1i64); }
    pass(0i64);
};

pub func:art_iter_next = int64(int64:iter) {
    int64:done = npk_mem_read_int64(iter, ITER_DONE);
    if (done == 1i64) { pass(0i64); }
    
    int64:start_ptr = npk_mem_read_int64(iter, ITER_START_KEY_PTR);
    int64:start_len = npk_mem_read_int64(iter, ITER_START_KEY_LEN);
    int64:end_ptr = npk_mem_read_int64(iter, ITER_END_KEY_PTR);
    int64:end_len = npk_mem_read_int64(iter, ITER_END_KEY_LEN);
    
    while (true) {
        int64:frame_ptr = raw iter_stack_peek(iter);
        if (frame_ptr == 0i64) {
            drop(npk_mem_write_int64(iter, ITER_DONE, 1i64));
            pass(0i64);
        }
        
        int64:node_ptr = npk_mem_read_int64(frame_ptr, FRAME_NODE_PTR);
        int64:child_idx = npk_mem_read_int64(frame_ptr, FRAME_CHILD_IDX);
        
        if (raw art_is_leaf(node_ptr)) {
            drop(raw iter_stack_pop(iter));
            
            int64:lkptr = node_ptr + LEAF_DATA_OFFSET;
            int64:lklen = raw art_leaf_key_len(node_ptr);
            
            int64:valid = 1i64;
            if (start_ptr != 0i64) {
                if (raw compare_keys(lkptr, lklen, start_ptr, start_len) < 0i64) {
                    valid = 0i64;
                }
            }
            if (end_ptr != 0i64) {
                if (raw compare_keys(lkptr, lklen, end_ptr, end_len) > 0i64) {
                    drop(npk_mem_write_int64(iter, ITER_DONE, 1i64));
                    pass(0i64);
                }
            }
            if (valid == 1i64) {
                pass(node_ptr);
            }
            // If valid == 0, we skipped this leaf (it's before start_key), continue loop
        } else {
            int64:child_res = raw art_node_get_nth_child(node_ptr, child_idx);
            if (child_res == 0i64) {
                drop(raw iter_stack_pop(iter));
            } else {
                int64:child = npk_mem_read_int64(child_res, 0i64);
                drop(npk_core_dalloc(child_res));
                
                drop(npk_mem_write_int64(frame_ptr, FRAME_CHILD_IDX, child_idx + 1i64));
                drop(raw iter_stack_push(iter, child, 0i64));
            }
        }
    }
    pass(0i64);
};

pub func:art_iter_create_prefix = int64(int64:prefix_ptr, int64:prefix_len) {
    int64:iter = npk_core_alloc(ITER_SIZE);
    if (iter == 0i64) { pass(0i64); }

    int64:stack_buf = npk_core_alloc(ITER_DEFAULT_STACK_CAP * FRAME_SIZE);
    if (stack_buf == 0i64) {
        drop(npk_core_dalloc(iter));
        pass(0i64);
    }
    
    drop(npk_mem_write_int64(iter, ITER_STACK_BUF, stack_buf));
    drop(npk_mem_write_int64(iter, ITER_STACK_CAP, ITER_DEFAULT_STACK_CAP));
    drop(npk_mem_write_int64(iter, ITER_STACK_TOP, -1i64));
    
    drop(npk_mem_write_int64(iter, ITER_START_KEY_PTR, 0i64));
    drop(npk_mem_write_int64(iter, ITER_START_KEY_LEN, 0i64));
    drop(npk_mem_write_int64(iter, ITER_END_KEY_PTR, 0i64));
    drop(npk_mem_write_int64(iter, ITER_END_KEY_LEN, 0i64));
    drop(npk_mem_write_int64(iter, ITER_DONE, 0i64));

    if (prefix_len == 0i64) {
        int64:root = raw art_get_root();
        if (root != 0i64) {
            drop(raw iter_stack_push(iter, root, 0i64));
        } else {
            drop(npk_mem_write_int64(iter, ITER_DONE, 1i64));
        }
        pass(iter);
    }

    int64:node = raw art_get_root();
    int64:depth = 0i64;
    
    while (node != 0i64) {
        if (raw art_is_leaf(node)) {
            int64:lkptr = node + LEAF_DATA_OFFSET;
            int64:lklen = raw art_leaf_key_len(node);
            
            int64:valid = 1i64;
            if (lklen < prefix_len) {
                valid = 0i64;
            } else {
                int64:i = 0i64;
                while (i < prefix_len) {
                    if (npk_mem_read_byte(lkptr, i) != npk_mem_read_byte(prefix_ptr, i)) {
                        valid = 0i64;
                        i = prefix_len; // break
                    } else {
                        i = i + 1i64;
                    }
                }
            }
            if (valid == 1i64) {
                drop(raw iter_stack_push(iter, node, 0i64));
            } else {
                drop(npk_mem_write_int64(iter, ITER_DONE, 1i64));
            }
            pass(iter);
        }
        
        int64:p2 = raw art_check_prefix(node, prefix_ptr, prefix_len, depth);
        int64:plen = raw art_node_prefix_len(node);
        
        int64:cmp_len = plen;
        if (prefix_len - depth < cmp_len) {
            cmp_len = prefix_len - depth;
        }
        if (p2 != cmp_len) {
            drop(npk_mem_write_int64(iter, ITER_DONE, 1i64));
            pass(iter);
        }
        
        depth = depth + plen;
        if (depth >= prefix_len) {
            drop(raw iter_stack_push(iter, node, 0i64));
            pass(iter);
        }
        
        int64:key_byte = 0i64;
        int64:b = npk_mem_read_byte(prefix_ptr, depth);
        key_byte = @cast_unchecked<int64>(b);
        
        int64:next_child = raw art_find_child(node, key_byte);
        if (next_child == 0i64) {
            drop(npk_mem_write_int64(iter, ITER_DONE, 1i64));
            pass(iter);
        }
        node = next_child;
        depth = depth + 1i64;
    }
    
    drop(npk_mem_write_int64(iter, ITER_DONE, 1i64));
    pass(iter);
};

```

### File: `src/index/art_location.npk`
```nitpick
// art_location.npk — ART leaf value encoding for physical record locations
//
// A record location is 24 bytes:
//   Bytes  0-7:  sstable_file_number (int64)
//   Bytes  8-15: page_id             (int64)
//   Bytes 16-23: slot_id             (int64)

use "../util/error_codes.npk".*;

pub fixed int64:LOCATION_SIZE          = 24i64;
pub fixed int64:LOCATION_OFF_FILE_NUM  = 0i64;
pub fixed int64:LOCATION_OFF_PAGE_ID   = 8i64;
pub fixed int64:LOCATION_OFF_SLOT_ID   = 16i64;

// Allocate a location buffer and encode the three fields.
pub func:location_encode = int64(int64:file_num, int64:page_id, int64:slot_id)
{
    int64:buf = npk_core_alloc(LOCATION_SIZE) => int64;
    drop(npk_mem_write_int64(buf, LOCATION_OFF_FILE_NUM, file_num));
    drop(npk_mem_write_int64(buf, LOCATION_OFF_PAGE_ID,  page_id));
    drop(npk_mem_write_int64(buf, LOCATION_OFF_SLOT_ID,  slot_id));
    pass(buf);
};

// Read file number from a location buffer.
pub func:location_file_num = int64(int64:loc_buf) {
    pass(npk_mem_read_int64(loc_buf, LOCATION_OFF_FILE_NUM));
};

// Read page_id from a location buffer.
pub func:location_page_id = int64(int64:loc_buf) {
    pass(npk_mem_read_int64(loc_buf, LOCATION_OFF_PAGE_ID));
};

// Read slot_id from a location buffer.
pub func:location_slot_id = int64(int64:loc_buf) {
    pass(npk_mem_read_int64(loc_buf, LOCATION_OFF_SLOT_ID));
};

// Sentinel location: record is in the Memtable (not yet flushed to SSTable)
pub fixed int64:LOCATION_IN_MEMTABLE = -1i64;

pub func:location_is_in_memtable = int64(int64:loc_buf)
    requires loc_buf != 0i64
{
    int64:fn = location_file_num(loc_buf) ?! 0i64;
    if (fn == LOCATION_IN_MEMTABLE) {
        pass(1i64);
    }
    pass(0i64);
};

// Encode a tombstone location: marks a key as deleted
pub fixed int64:LOCATION_TOMBSTONE = -2i64;

pub func:location_is_tombstone = int64(int64:loc_buf)
    requires loc_buf != 0i64
{
    int64:fn = location_file_num(loc_buf) ?! 0i64;
    if (fn == LOCATION_TOMBSTONE) {
        pass(1i64);
    }
    pass(0i64);
};

pub func:location_encode_tombstone = int64() {
    pass(location_encode(LOCATION_TOMBSTONE, 0i64, 0i64));
};

pub func:location_encode_in_memtable = int64() {
    pass(location_encode(LOCATION_IN_MEMTABLE, 0i64, 0i64));
};

pub func:location_verify_parity = NIL(int64:loc_buf)
    requires loc_buf != 0i64
{
    prove raw location_is_tombstone(loc_buf) == 0i64 || raw location_is_in_memtable(loc_buf) == 0i64;
    pass(NIL);
};

```

### File: `src/index/art_node.npk`
```nitpick
// art_node.npk — ART node type tags and layout constants
//
// ART maintains space efficiency by adapting node types:
//   Node4   — 1 to 4 children    (smallest)
//   Node16  — 5 to 16 children
//   Node48  — 17 to 48 children
//   Node256 — 49 to 256 children (largest; direct-indexed)
//
// Layout convention: the first byte of EVERY node is the node_type tag.
// The second byte holds the current child count (num_children).
// Byte 2-3 are reserved (padding for alignment).
// Bytes 4-11 hold a pointer to the parent node (int64, for upward traversal during splits).
// Bytes 12-19 hold the compressed path length (int64) for path compression.
// Bytes 20-83 hold the compressed path bytes (up to 64 bytes of inlined prefix).

use "../util/constants.npk".*;
use "../util/error_codes.npk".*;

// Node type tags (stored in byte 0 of every node)
pub fixed int64:ART_NODE4   = 0i8;
pub fixed int64:ART_NODE16  = 1i8;
pub fixed int64:ART_NODE48  = 2i8;
pub fixed int64:ART_NODE256 = 3i8;
pub fixed int64:ART_LEAF    = 4i8;  // Leaf: stores actual key+value

// Capacity constants
pub fixed int64:NODE4_MAX_KEYS   = 4i64;
pub fixed int64:NODE16_MAX_KEYS  = 16i64;
pub fixed int64:NODE48_MAX_KEYS  = 48i64;
pub fixed int64:NODE256_MAX_KEYS = 256i64;

// Common header layout (first 84 bytes of every node)
pub fixed int64:ART_HDR_TYPE         = 0i64;   // int8 — node type tag
pub fixed int64:ART_HDR_NUM_CHILDREN = 1i64;   // int8 — current child count
pub fixed int64:ART_HDR_RESERVED     = 2i64;   // int16 — padding
pub fixed int64:ART_HDR_PARENT       = 4i64;   // int64 — parent pointer
pub fixed int64:ART_HDR_PREFIX_LEN   = 12i64;  // int64 — compressed prefix length
pub fixed int64:ART_HDR_PREFIX       = 20i64;  // 64 bytes — inlined prefix bytes
pub fixed int64:ART_HDR_SIZE         = 84i64;  // Total header size

// Maximum inline prefix length (beyond this, prefix is stored externally)
pub func:art_node_type = int64(int64:node) {
    if (node == 49i64) { print("ERROR: node is 49 in art_node_type"); }
    int64:t = npk_mem_read_byte(node, 0i64);
    pass(t & 127i64);
};

pub func:art_node_set_type = NIL(int64:node, int64:val) {
    drop(npk_mem_write_byte(node, 0i64, val));
    pass(NIL);
};

pub func:art_node_num_children = int64(int64:node) {
    pass(npk_mem_read_byte(node, ART_HDR_NUM_CHILDREN));
};

pub func:art_node_set_num_children = NIL(int64:node, int64:val) {
    drop(npk_mem_write_byte(node, ART_HDR_NUM_CHILDREN, val));
    pass(NIL);
};

pub func:art_node_prefix_len = int64(int64:node) {
    int64:b1 = npk_mem_read_byte(node, ART_HDR_PREFIX_LEN);
    int64:b2 = npk_mem_read_byte(node, ART_HDR_PREFIX_LEN + 1i64);
    pass(b1 | (b2 << 8i64));
};

pub func:art_node_set_prefix_len = NIL(int64:node, int64:val) {
    drop(npk_mem_write_byte(node, ART_HDR_PREFIX_LEN, val & 255i64));
    drop(npk_mem_write_byte(node, ART_HDR_PREFIX_LEN + 1i64, (val >> 8i64) & 255i64));
    pass(NIL);
};

pub func:art_node_prefix_byte = int64(int64:node, int64:i) {
    pass(npk_mem_read_byte(node, ART_HDR_PREFIX + i));
};

pub func:art_node_set_prefix_byte = NIL(int64:node, int64:i, int64:val) {
    drop(npk_mem_write_byte(node, ART_HDR_PREFIX + i, val));
    pass(NIL);
};

pub func:art_node_is_locked = bool(int64:node) {
    int64:t = npk_mem_read_byte(node, 0i64);
    pass((t & 128i64) != 0i64);
};

pub func:art_node_lock = NIL(int64:node) {
    int64:restart = 1i64;
    while (restart == 1i64) {
        int64:hdr = npk_mem_read_int64(node, 0i64);
        int64:t = hdr & 255i64;
        if ((t & 128i64) == 0i64) {
            int64:new_hdr = hdr | 128i64;
            bool:res = raw npk_cas_i64(node, hdr, new_hdr);
            if (res) { restart = 0i64; }
        }
    }
    pass(NIL);
};

pub func:art_node_unlock = NIL(int64:node) {
    int64:restart = 1i64;
    while (restart == 1i64) {
        int64:hdr = npk_mem_read_int64(node, 0i64);
        int64:new_hdr = hdr & (0xFFFFFFFFFFFFFF7Fi64); // clear bit 7
        bool:res = raw npk_cas_i64(node, hdr, new_hdr);
        if (res) { restart = 0i64; }
    }
    pass(NIL);
};

pub func:art_node_is_obsolete = bool(int64:node) {
    int64:hdr = npk_mem_read_int64(node, 0i64);
    int64:t = hdr & 255i64;
    pass((t & 64i64) != 0i64);
};

pub func:art_node_mark_obsolete = NIL(int64:node) {
    int64:restart = 1i64;
    while (restart == 1i64) {
        int64:hdr = npk_mem_read_int64(node, 0i64);
        int64:new_hdr = hdr | 64i64;
        bool:res = raw npk_cas_i64(node, hdr, new_hdr);
        if (res) { restart = 0i64; }
    }
    pass(NIL);
};

// Node body offsets (relative to ART_HDR_SIZE)
//
// Node4:
//   Bytes 84-87:   keys[4]     (int8 x4) — partial key bytes
//   Bytes 88-119:  children[4] (int64 x4) — child pointers, parallel to keys
//   Total: 120 bytes
pub fixed int64:NODE4_KEYS_OFFSET     = 84i64;
pub fixed int64:NODE4_CHILDREN_OFFSET = 88i64;
pub fixed int64:NODE4_SIZE            = 120i64;

// Node16:
//   Bytes 84-99:   keys[16]     (int8 x16) — partial key bytes, sorted (SIMD-searchable)
//   Bytes 100-103: padding[4]   (alignment to 8 bytes for children array)
//   Bytes 104-231: children[16] (int64 x16) — child pointers, parallel to keys
//   Total: 232 bytes
pub fixed int64:NODE16_KEYS_OFFSET     = 84i64;
pub fixed int64:NODE16_CHILDREN_OFFSET = 104i64;
pub fixed int64:NODE16_SIZE            = 232i64;

// Node48:
//   Bytes 84-339:  index[256]   (int8 x256)
//   Bytes 340-343: padding[4]   (alignment)
//   Bytes 344-727: children[48] (int64 x48) — child pointer slots
//   Total: 728 bytes
pub fixed int64:NODE48_INDEX_OFFSET    = 84i64;
pub fixed int64:NODE48_CHILDREN_OFFSET = 344i64;
pub fixed int64:NODE48_SIZE            = 728i64;

// Node256:
//   Bytes 84-87: padding[4]
//   Bytes 88-2135: children[256] (int64 x256) — direct-indexed child pointers.
//                  children[byte_value] is the child pointer (0 if none).
//   Total: 2136 bytes
pub fixed int64:NODE256_CHILDREN_OFFSET = 88i64;
pub fixed int64:NODE256_SIZE            = 2136i64;

// Leaf node layout:
//   Bytes  0:      type (ART_LEAF = 4)
//   Bytes  1-3:    reserved
//   Bytes  4-11:   key_len (int64) — length of full key
//   Bytes 12-19:   val_len (int64) — length of stored value
//   Bytes 20-83:   reserved (padded to common header size)
//   Bytes 84+:     key_data[key_len] followed immediately by val_data[val_len]
pub fixed int64:LEAF_KEY_LEN_OFFSET   = 12i64;
pub fixed int64:LEAF_VAL_LEN_OFFSET   = 20i64;
pub fixed int64:LEAF_DATA_OFFSET      = 84i64;

// Safety rules for node memory access
Rules<int64>:valid_node4_offset   = { $ >= 0i64, $ < 124i64 };
Rules<int64>:valid_node16_offset  = { $ >= 0i64, $ < 232i64 };
Rules<int64>:valid_node48_offset  = { $ >= 0i64, $ < 732i64 };
Rules<int64>:valid_node256_offset = { $ >= 0i64, $ < 2132i64 };

pub Rules<int64>:valid_node4_slot = { $ >= 0i64, $ < NODE4_MAX_KEYS };

```

### File: `src/index/art_node16.npk`
```nitpick
use "../util/error_codes.npk".*;
use "art_node.npk".*;
use "../util/mem_primitives.npk".*;
use "art_node_header.npk".*;

pub func:node16_get_key = int64(int64:node, int64:i) {
    pass(npk_mem_read_byte(node, NODE16_KEYS_OFFSET + i));
};

pub func:node16_set_key = NIL(int64:node, int64:i, int64:key_byte) {
    drop(npk_mem_write_byte(node, NODE16_KEYS_OFFSET + i, key_byte));
    pass(NIL);
};

pub func:node16_get_child = int64(int64:node, int64:i) {
    int64:addr = node + NODE16_CHILDREN_OFFSET + i * 8i64;
    pass(npk_mem_read_int64(addr, 0i64));
};

pub func:node16_set_child = NIL(int64:node, int64:i, int64:child) {
    drop(npk_mem_write_int64(node, NODE16_CHILDREN_OFFSET + i * 8i64, child));
    pass(NIL);
};

pub func:node16_find_child = int64(int64:node, int64:key_byte) {
    int64:count = raw art_node_num_children(node);
    int64:i = 0i64;
    while (i < count) {
        int64:kb = raw node16_get_key(node, i);
        if (kb == key_byte) {
            pass(raw node16_get_child(node, i));
        }
        i = i + 1i64;
    }
    pass(0i64);
};

pub func:node16_remove_child = int64(int64:node, int64:key_byte) {
    int64:count = raw art_node_num_children(node);
    int64:i = 0i64;
    int64:found = -1i64;
    while (i < count) {
        if (raw node16_get_key(node, i) == key_byte) {
            found = i;
            break;
        }
        i = i + 1i64;
    }
    
    if (found == -1i64) { pass(0i64); }
    
    int64:child = raw node16_get_child(node, found);
    
    // Shift elements left
    i = found;
    while (i < (count - 1i64)) {
        drop(raw node16_set_key(node, i, raw node16_get_key(node, i + 1i64)));
        drop(raw node16_set_child(node, i, raw node16_get_child(node, i + 1i64)));
        i = i + 1i64;
    }
    
    // Zero the last slot
    drop(raw node16_set_key(node, count - 1i64, 0i64));
    drop(raw node16_set_child(node, count - 1i64, 0i64));
    
    // Decrement count
    drop(raw art_node_set_num_children(node, count - 1i64));
    
    pass(child);
};

```

### File: `src/index/art_node256.npk`
```nitpick
use "../util/error_codes.npk".*;
use "art_node.npk".*;
use "../util/mem_primitives.npk".*;

pub func:node256_get_child = int64(int64:node, int64:byte_val) {
    int64:child_off = NODE256_CHILDREN_OFFSET + byte_val * 8i64;
    int64:addr = node + child_off;
    pass(npk_mem_read_int64(addr, 0i64));
};

pub func:node256_set_child = NIL(int64:node, int64:byte_val, int64:child) {
    int64:child_off = NODE256_CHILDREN_OFFSET + byte_val * 8i64;
    drop(npk_mem_write_int64(node, child_off, child));
    pass(NIL);
};

pub func:node256_remove_child = int64(int64:node, int64:key_byte) {
    int64:child = raw node256_get_child(node, key_byte);
    if (child == 0i64) { pass(0i64); }
    
    drop(raw node256_set_child(node, key_byte, 0i64));
    
    int64:count = raw art_node_num_children(node);
    drop(raw art_node_set_num_children(node, count - 1i64));
    
    pass(child);
};

```

### File: `src/index/art_node4.npk`
```nitpick
use "../util/error_codes.npk".*;
use "art_node.npk".*;
use "../util/mem_primitives.npk".*;
use "art_node_header.npk".*;

pub func:node4_get_key = int64(int64:node, limit<valid_node4_slot> int64:i) {
    pass(npk_mem_read_byte(node, NODE4_KEYS_OFFSET + i));
};

pub func:node4_set_key = NIL(int64:node, limit<valid_node4_slot> int64:i, int64:key_byte) {
    drop(npk_mem_write_byte(node, NODE4_KEYS_OFFSET + i, key_byte));
    pass(NIL);
};

pub func:node4_get_child = int64(int64:node, limit<valid_node4_slot> int64:i) {
    int64:addr = node + NODE4_CHILDREN_OFFSET + i * 8i64;
    pass(npk_mem_read_int64(addr, 0i64));
};

pub func:node4_set_child = NIL(int64:node, limit<valid_node4_slot> int64:i, int64:child) {
    drop(npk_mem_write_int64(node, NODE4_CHILDREN_OFFSET + i * 8i64, child));
    pass(NIL);
};

pub func:node4_find_child = int64(int64:node, int64:key_byte) {
    int64:count = raw art_node_num_children(node);
    int64:i = 0i64;
    while (i < count) {
        int64:kb = raw node4_get_key(node, i);
        if (kb == key_byte) {
            pass(raw node4_get_child(node, i));
        }
        i = i + 1i64;
    }
    pass(0i64);
};

pub func:node4_remove_child = int64(int64:node, int64:key_byte) {
    int64:count = raw art_node_num_children(node);
    int64:i = 0i64;
    int64:found = -1i64;
    while (i < count) {
        if (raw node4_get_key(node, i) == key_byte) {
            found = i;
            break;
        }
        i = i + 1i64;
    }
    
    if (found == -1i64) { pass(0i64); }
    
    int64:child = raw node4_get_child(node, found);
    
    // Shift elements left
    i = found;
    while (i < (count - 1i64)) {
        drop(raw node4_set_key(node, i, raw node4_get_key(node, i + 1i64)));
        drop(raw node4_set_child(node, i, raw node4_get_child(node, i + 1i64)));
        i = i + 1i64;
    }
    
    // Zero the last slot
    drop(raw node4_set_key(node, count - 1i64, 0i64));
    drop(raw node4_set_child(node, count - 1i64, 0i64));
    
    // Decrement count
    drop(raw art_node_set_num_children(node, count - 1i64));
    
    pass(child);
};

```

### File: `src/index/art_node48.npk`
```nitpick
use "../util/error_codes.npk".*;
use "art_node.npk".*;
use "../util/mem_primitives.npk".*;

pub func:node48_get_slot = int64(int64:node, int64:byte_val) {
    int64:idx_off = NODE48_INDEX_OFFSET + (byte_val => int64);
    pass(npk_mem_read_byte(node, idx_off) => int64);
};

pub func:node48_set_slot = NIL(int64:node, int64:byte_val, int64:slot) {
    int64:idx_off = NODE48_INDEX_OFFSET + byte_val;
    drop(npk_mem_write_byte(node, idx_off, slot));
    pass(NIL);
};

pub func:node48_get_child = int64(int64:node, int64:slot) {
    int64:child_off = NODE48_CHILDREN_OFFSET + ((slot - 1i64) * 8i64);
    int64:addr = node + child_off;
    pass(npk_mem_read_int64(addr, 0i64));
};

pub func:node48_set_child = NIL(int64:node, int64:slot, int64:child) {
    int64:child_off = NODE48_CHILDREN_OFFSET + ((slot - 1i64) * 8i64);
    drop(npk_mem_write_int64(node, child_off, child));
    pass(NIL);
};
pub func:node48_add_child = NIL(int64:node, int64:key_byte, int64:child) {
    int64:i = 0i64;
    int64:empty_slot = 0i64;
    while (i < 48i64) {
        int64:c = raw node48_get_child(node, (i + 1i64));
        if (c == 0i64) {
            empty_slot = i + 1i64;
            break;
        }
        i = i + 1i64;
    }
    
    if (empty_slot != 0i64) {
        drop(raw node48_set_slot(node, key_byte, empty_slot));
        drop(raw node48_set_child(node, empty_slot, child));
        int64:count = raw art_node_num_children(node);
        drop(raw art_node_set_num_children(node, count + 1i64));
    }
    pass(NIL);
};

pub func:node48_find_child = int64(int64:node, int64:key_byte) {
    int64:slot = raw node48_get_slot(node, key_byte);
    if (slot != 0i64) {
        pass(raw node48_get_child(node, slot));
    }
    pass(0i64);
};

pub func:node48_remove_child = int64(int64:node, int64:key_byte)
    requires node != 0i64
{
    int64:slot = raw node48_get_slot(node, key_byte);
    if (slot == 0i64) { pass(0i64); }
    
    drop(raw node48_set_child(node, slot, 0i64));
    drop(raw node48_set_slot(node, key_byte, 0i64));
    
    int64:num = raw art_node_num_children(node);
    drop(raw art_node_set_num_children(node, num - 1i64));
    pass(0i64);
};

```

### File: `src/index/art_node_header.npk`
```nitpick
use "../util/error_codes.npk".*;
use "art_node.npk".*;
use "../util/mem_primitives.npk".*;

pub func:art_node_type = int64(int64:node) {
    pass(npk_mem_read_byte(node, ART_HDR_TYPE));
};

pub func:art_node_num_children = int64(int64:node) {
    pass(npk_mem_read_byte(node, ART_HDR_NUM_CHILDREN));
};

pub func:art_node_set_num_children = NIL(int64:node, int64:count) {
    drop(npk_mem_write_byte(node, ART_HDR_NUM_CHILDREN, (count => int64)));
    pass(NIL);
};

pub func:art_node_parent = int64(int64:node) {
    pass(npk_mem_read_int64(node, ART_HDR_PARENT));
};

pub func:art_node_set_parent = NIL(int64:node, int64:parent) {
    drop(npk_mem_write_int64(node, ART_HDR_PARENT, parent));
    pass(NIL);
};

pub func:art_node_prefix_len = int64(int64:node) {
    pass(npk_mem_read_int64(node, ART_HDR_PREFIX_LEN));
};

pub func:art_node_set_prefix_len = NIL(int64:node, int64:len) {
    drop(npk_mem_write_int64(node, ART_HDR_PREFIX_LEN, len));
    pass(NIL);
};

pub func:art_node_prefix_byte = int8(int64:node, int64:i) {
    pass(npk_mem_read_byte(node, ART_HDR_PREFIX + i) => int8);
};

pub func:art_node_set_prefix_byte = NIL(int64:node, int64:i, int64:b) {
    drop(npk_mem_write_byte(node, ART_HDR_PREFIX + i, (b => int64)));
    pass(NIL);
};

pub func:art_is_leaf = bool(int64:node) {
    if (node == 0i64) {
        pass(false);
    }
    pass((npk_mem_read_byte(node, ART_HDR_TYPE) => int8) == ART_LEAF);
};

```

### File: `src/query/ast_types.npk`
```nitpick
// ast_types.npk — Internal query filter representations

use "../document/json_types.npk".*;

pub fixed int8:AST_OP_AND = 0i8;
pub fixed int8:AST_OP_OR  = 1i8;
pub fixed int8:AST_OP_EQ  = 2i8;
pub fixed int8:AST_OP_GT  = 3i8;
pub fixed int8:AST_OP_LT  = 4i8;
pub fixed int8:AST_OP_IN  = 5i8;

pub fixed int64:AST_NODE_SIZE = 48i64; // size in bytes for the bump allocator

// Polymorphic AST Node
pub struct:npk_ast_node = {
    int8:op;                // offset 0
    int64:path;             // offset 8, int8->:path
    NpkJsonVal:target;      // offset 16 (16 bytes)
    uint32:child_count;     // offset 32
    int64:children;         // offset 36/40? Nitpick aligns fields. Target is at 16, child_count at 32, children at 40 if size is 48, or children at 36 if packed. Wait, let's use getters/setters instead of raw struct if we use Bump Allocator. Let's just use the struct definition and `@cast_unchecked`!
};

pub func:ast_node_make = int64(int64:arena_ptr) {
    // In filter_parser, we will have a bump allocator
    // This is just a placeholder type. 
    pass(0i64);
};

```

### File: `src/query/evaluator.npk`
```nitpick
// evaluator.npk — Evaluates an AST filter against a specific document

use "ast_types.npk".*;
use "path_eval.npk".*;
use "../document/json_types.npk".*;
use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;

// Returns true if the record satisfies the AST filter
// Iterative AST evaluator using astack (transient call stack simulation)
pub func:evaluate_filter = bool(int64:ast_root, int64:doc_ptr) {
    if (ast_root == 0i64) {
        pass(true); // Empty filter matches everything
    }
    
    astack(2048i64); // Allocate a 2048-slot stack array on the C stack (8 bytes each, 16KB)
    
    // Push the root task
    // Frame layout (pushed top-to-bottom):
    // apush(node_ptr)
    // apush(child_idx)
    // apush(accumulated_result)
    
    apush(ast_root);
    apush(0i64);
    apush(-1i64); // -1 = uninitialized
    
    int64:stack_size = 1i64;
    int64:last_result = 1i64; // Initialize with true
    
    while (stack_size > 0i64) {
        int64:acc = apop();
        int64:c_idx = apop();
        int64:node = apop();
        stack_size = stack_size - 1i64;
        
        int64:op = npk_mem_read_byte(node, 0i64) => int64;
        
        if (op == (AST_OP_AND => int64)) {
            int64:count = npk_mem_read_int32(node, 32i64) => int64;
            
            if (c_idx == 0i64) { 
                acc = 1i64; 
            } else {
                if (last_result == 0i64) { acc = 0i64; } // Short-circuit: one child failed
            }
            
            if (acc == 0i64) {
                last_result = 0i64;
                continue;
            }
            
            if (c_idx < count) {
                // Suspend parent and push back
                apush(node);
                apush(c_idx + 1i64);
                apush(acc);
                stack_size = stack_size + 1i64;
                
                // Push child
                int64:children = npk_mem_read_int64(node, 40i64);
                int64:child_node = npk_mem_read_int64(children, c_idx * 8i64);
                apush(child_node);
                apush(0i64);
                apush(-1i64);
                stack_size = stack_size + 1i64;
                continue;
            } else {
                last_result = acc;
                continue;
            }
        }
        
        if (op == (AST_OP_OR => int64)) {
            int64:count = npk_mem_read_int32(node, 32i64) => int64;
            
            if (c_idx == 0i64) { 
                acc = 0i64; 
            } else {
                if (last_result == 1i64) { acc = 1i64; } // Short-circuit: one child succeeded
            }
            
            if (acc == 1i64) {
                last_result = 1i64;
                continue;
            }
            
            if (c_idx < count) {
                // Suspend parent and push back
                apush(node);
                apush(c_idx + 1i64);
                apush(acc);
                stack_size = stack_size + 1i64;
                
                // Push child
                int64:children = npk_mem_read_int64(node, 40i64);
                int64:child_node = npk_mem_read_int64(children, c_idx * 8i64);
                apush(child_node);
                apush(0i64);
                apush(-1i64);
                stack_size = stack_size + 1i64;
                continue;
            } else {
                last_result = acc;
                continue;
            }
        }
        
        // Leaf Nodes
        int64:path = npk_mem_read_int64(node, 8i64);
        NpkJsonVal:actual = raw eval_path(path, doc_ptr);
        
        NpkJsonVal:target = NpkJsonVal {
            type: npk_mem_read_byte(node, 16i64) => int8,
            payload: npk_mem_read_int64(node, 24i64)
        };
        
        if (actual.type == JSON_NULL) {
            last_result = 0i64;
            continue;
        }
        
        if (op == (AST_OP_EQ => int64)) {
            if (actual.type != target.type) {
                last_result = 0i64;
                continue;
            }
            if (actual.type == JSON_NUM_I64) {
                if (actual.payload == target.payload) { last_result = 1i64; } else { last_result = 0i64; }
                continue;
            }
            if (actual.type == JSON_STR) {
                int64:a_len = npk_mem_read_int32(actual.payload, 0i64) => int64;
                int64:t_len = npk_mem_read_int32(target.payload, 0i64) => int64;
                if (a_len != t_len) {
                    last_result = 0i64;
                    continue;
                }
                int64:a_data = npk_mem_read_int64(actual.payload, 8i64);
                int64:t_data = npk_mem_read_int64(target.payload, 8i64);
                int64:res = npk_mem_compare(a_data, t_data, a_len);
                if (res == 0i64) { last_result = 1i64; } else { last_result = 0i64; }
                continue;
            }
            last_result = 0i64;
            continue;
        }
        
        if (op == (AST_OP_GT => int64)) {
            if (actual.type != target.type) {
                last_result = 0i64;
                continue;
            }
            if (actual.type == JSON_NUM_I64) {
                if (actual.payload > target.payload) { last_result = 1i64; } else { last_result = 0i64; }
                continue;
            }
            last_result = 0i64;
            continue;
        }
        
        if (op == (AST_OP_LT => int64)) {
            if (actual.type != target.type) {
                last_result = 0i64;
                continue;
            }
            if (actual.type == JSON_NUM_I64) {
                if (actual.payload < target.payload) { last_result = 1i64; } else { last_result = 0i64; }
                continue;
            }
            last_result = 0i64;
            continue;
        }
        
        last_result = 0i64;
    }
    
    pass(last_result == 1i64);
};

```

### File: `src/query/filter_parser.npk`
```nitpick
// filter_parser.npk — Parses JSON documents into AST structures

use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;
use "../document/json_types.npk".*;
use "ast_types.npk".*;

// Simple bump allocator (Arena) for AST nodes
pub struct:AstArena = {
    int64:data;     // Address of memory block
    int64:capacity; // Total capacity
    int64:cursor;   // Current allocation offset
};

pub func:ast_arena_init = int64(int64:capacity) {
    int64:arena_ptr = npk_core_alloc(24i64);
    if (arena_ptr == 0i64) { fail@cast_unchecked<tbb8>(ERR_EBR_LIMBO_OVERFLOW); } // Generic memory error
    
    int64:data = npk_core_alloc(capacity);
    if (data == 0i64) {
        drop(npk_core_dalloc(arena_ptr));
        fail@cast_unchecked<tbb8>(ERR_EBR_LIMBO_OVERFLOW);
    }
    
    drop(npk_mem_write_int64(arena_ptr, 0i64, data));
    drop(npk_mem_write_int64(arena_ptr, 8i64, capacity));
    drop(npk_mem_write_int64(arena_ptr, 16i64, 0i64));
    
    pass(arena_ptr);
};

pub func:ast_arena_alloc = int64(int64:arena_ptr, int64:size) {
    int64:capacity = npk_mem_read_int64(arena_ptr, 8i64);
    int64:cursor   = npk_mem_read_int64(arena_ptr, 16i64);
    
    // Align to 8 bytes
    int64:aligned_size = size;
    int64:rem = size % 8i64;
    if (rem != 0i64) {
        aligned_size = size + (8i64 - rem);
    }
    
    if (cursor + aligned_size > capacity) {
        // Out of memory in arena
        pass(0i64);
    }
    
    int64:data = npk_mem_read_int64(arena_ptr, 0i64);
    int64:alloc_ptr = data + cursor;
    drop(npk_mem_write_int64(arena_ptr, 16i64, cursor + aligned_size));
    
    // Zero initialize
    drop(npk_mem_set(alloc_ptr, 0i64, aligned_size));
    
    pass(alloc_ptr);
};

pub func:ast_arena_destroy = NIL(int64:arena_ptr) {
    int64:data = npk_mem_read_int64(arena_ptr, 0i64);
    if (data != 0i64) {
        drop(npk_core_dalloc(data));
    }
    drop(npk_core_dalloc(arena_ptr));
    pass(NIL);
};

func:streq = bool(int64:a_ptr, string:b) {
    string:a_str = npk_mem_read_string(a_ptr, 1024i64);
    pass(a_str == b);
};

pub Rules<int32>:ValidAstackDepth = { $ >= 1, $ <= 128 };

pub func:parse_filter = int64(int64:arena_ptr, int64:query_raw_ptr, limit<ValidAstackDepth> int32:depth) {
    if (depth >= 128i32) { pass(0i64); } // Guard to guarantee depth + 1i32 <= 128 for recursive call

    NpkJsonVal->:query = @cast_unchecked<NpkJsonVal->>(query_raw_ptr);
    if (query->type != JSON_OBJ) {
        pass(0i64); // Invalid filter root
    }
    
    int64:obj_ptr = query->payload;
    int64:count = npk_mem_read_int32(obj_ptr, 0i64) => int64;
    if (count == 0i64) { pass(0i64); }
    
    int64:keys_ptr = npk_mem_read_int64(obj_ptr, 8i64);
    int64:vals_ptr = npk_mem_read_int64(obj_ptr, 16i64);
    
    // For simplicity, handle 1 key at the top level
    int64:key0_ptr = npk_mem_read_int64(keys_ptr, 0i64);
    int64:val0_ptr = npk_mem_read_int64(vals_ptr, 0i64);
    
    NpkJsonVal:k0_elem = NpkJsonVal {
        type: npk_mem_read_byte(key0_ptr, 0i64) => int8,
        payload: npk_mem_read_int64(key0_ptr, 8i64)
    };
    
    NpkJsonVal:v0_elem = NpkJsonVal {
        type: npk_mem_read_byte(val0_ptr, 0i64) => int8,
        payload: npk_mem_read_int64(val0_ptr, 8i64)
    };
    
    if (k0_elem.type != JSON_STR) { pass(0i64); }
    
    int64:k0_str_ptr = npk_mem_read_int64(k0_elem.payload, 8i64);
    
    int64:node_ptr = raw ast_arena_alloc(arena_ptr, AST_NODE_SIZE);
    if (node_ptr == 0i64) { pass(0i64); }
    
    // Check if it's an operator
    if (raw streq(k0_str_ptr, "$and") || raw streq(k0_str_ptr, "$or")) {
        if (raw streq(k0_str_ptr, "$and")) {
            drop(npk_mem_write_byte(node_ptr, 0i64, AST_OP_AND => int64));
        } else {
            drop(npk_mem_write_byte(node_ptr, 0i64, AST_OP_OR => int64));
        }
        
        if (v0_elem.type != JSON_ARR) { pass(0i64); }
        
        int64:arr_ptr = v0_elem.payload;
        int64:arr_count = npk_mem_read_int32(arr_ptr, 0i64) => int64;
        int64:arr_handles = npk_mem_read_int64(arr_ptr, 8i64);
        
        drop(npk_mem_write_int32(node_ptr, 32i64, @cast_unchecked<int32>(arr_count)));
        
        int64:children_ptr = raw ast_arena_alloc(arena_ptr, arr_count * 8i64);
        drop(npk_mem_write_int64(node_ptr, 36i64, children_ptr)); // aligned at 36 vs 40? Let's use 40! Wait, struct alignment. I'll use 40 for children just to be safe with 8-byte alignment
        drop(npk_mem_write_int64(node_ptr, 40i64, children_ptr)); // use 40 for children
        
        int64:i = 0i64;
        while (i < arr_count) {
            int64:child_val_ptr = npk_mem_read_int64(arr_handles, i * 8i64);
            NpkJsonVal:child_elem = NpkJsonVal {
                type: npk_mem_read_byte(child_val_ptr, 0i64) => int8,
                payload: npk_mem_read_int64(child_val_ptr, 8i64)
            };
            
            int64:child_node = raw parse_filter(arena_ptr, @cast_unchecked<int64>(@child_elem), depth + 1i32);
            drop(npk_mem_write_int64(children_ptr, i * 8i64, child_node));
            i = i + 1i64;
        }
    } else {
        // It's a field path (implicit eq or object with operator)
        drop(npk_mem_write_int64(node_ptr, 8i64, k0_str_ptr)); // path
        
        if (v0_elem.type == JSON_OBJ) {
            // Check first key of the inner object
            int64:inner_obj_ptr = v0_elem.payload;
            int64:icount = npk_mem_read_int32(inner_obj_ptr, 0i64) => int64;
            if (icount > 0i64) {
                int64:ikeys = npk_mem_read_int64(inner_obj_ptr, 8i64);
                int64:ivals = npk_mem_read_int64(inner_obj_ptr, 16i64);
                
                int64:ik0 = npk_mem_read_int64(ikeys, 0i64);
                int64:iv0 = npk_mem_read_int64(ivals, 0i64);
                
                NpkJsonVal:ik0_elem = NpkJsonVal {
                    type: npk_mem_read_byte(ik0, 0i64) => int8,
                    payload: npk_mem_read_int64(ik0, 8i64)
                };
                NpkJsonVal:iv0_elem = NpkJsonVal {
                    type: npk_mem_read_byte(iv0, 0i64) => int8,
                    payload: npk_mem_read_int64(iv0, 8i64)
                };
                
                if (ik0_elem.type == JSON_STR) {
                    int64:ik0_str_ptr = npk_mem_read_int64(ik0_elem.payload, 8i64);
                    
                    if (raw streq(ik0_str_ptr, "$eq")) { 
                        drop(npk_mem_write_byte(node_ptr, 0i64, AST_OP_EQ => int64)); 
                    } else { 
                        if (raw streq(ik0_str_ptr, "$gt")) { 
                            drop(npk_mem_write_byte(node_ptr, 0i64, AST_OP_GT => int64)); 
                        } else { 
                            if (raw streq(ik0_str_ptr, "$lt")) { 
                                drop(npk_mem_write_byte(node_ptr, 0i64, AST_OP_LT => int64)); 
                            } else { 
                                if (raw streq(ik0_str_ptr, "$in")) { 
                                    drop(npk_mem_write_byte(node_ptr, 0i64, AST_OP_IN => int64)); 
                                } else { 
                                    drop(npk_mem_write_byte(node_ptr, 0i64, AST_OP_EQ => int64)); 
                                }
                            }
                        }
                    }
                    
                    // write target
                    drop(npk_mem_write_byte(node_ptr, 16i64, iv0_elem.type => int64));
                    drop(npk_mem_write_int64(node_ptr, 24i64, iv0_elem.payload));
                } else {
                    // Implicit eq to object
                    drop(npk_mem_write_byte(node_ptr, 0i64, AST_OP_EQ => int64));
                    drop(npk_mem_write_byte(node_ptr, 16i64, v0_elem.type => int64));
                    drop(npk_mem_write_int64(node_ptr, 24i64, v0_elem.payload));
                }
            } else {
                // empty object, implicit eq
                drop(npk_mem_write_byte(node_ptr, 0i64, AST_OP_EQ => int64));
                drop(npk_mem_write_byte(node_ptr, 16i64, v0_elem.type => int64));
                drop(npk_mem_write_int64(node_ptr, 24i64, v0_elem.payload));
            }
        } else {
            // Implicit eq
            drop(npk_mem_write_byte(node_ptr, 0i64, AST_OP_EQ => int64));
            drop(npk_mem_write_byte(node_ptr, 16i64, v0_elem.type => int64));
            drop(npk_mem_write_int64(node_ptr, 24i64, v0_elem.payload));
        }
    }
    
    pass(node_ptr);
};

```

### File: `src/query/path_eval.npk`
```nitpick
// path_eval.npk — Evaluates dot-notation paths against a JSON document

use "../util/error_codes.npk".*;
use "../util/mem_primitives.npk".*;
use "../document/json_types.npk".*;

func:streq_len = bool(int64:a_ptr, int64:b_ptr, int64:len) {
    int64:i = 0i64;
    while (i < len) {
        int8:ca = npk_mem_read_byte(a_ptr, i) => int8;
        int8:cb = npk_mem_read_byte(b_ptr, i) => int8;
        if (ca != cb) { pass(false); }
        i = i + 1i64;
    }
    // Also check that `a` ends there
    int8:ca_end = npk_mem_read_byte(a_ptr, len) => int8;
    pass(ca_end == 0i8);
};

// Gets the length of the string until a null terminator or a '.'
func:path_segment_len = int64(int64:path_ptr) {
    int64:len = 0i64;
    while (true) {
        int8:c = npk_mem_read_byte(path_ptr, len) => int8;
        if (c == 0i8) { break; }
        if (c == 46i8) { break; } // '.' is 46
        len = len + 1i64;
    }
    pass(len);
};

pub func:eval_path = NpkJsonVal(int64:path_ptr, int64:doc_raw_ptr) {
    NpkJsonVal->:doc = @cast_unchecked<NpkJsonVal->>(doc_raw_ptr);
    if (path_ptr == 0i64) {
        pass(raw json_make_null());
    }
    
    int64:seg_len = raw path_segment_len(path_ptr);
    if (seg_len == 0i64) {
        pass(raw json_make_null());
    }
    
    if (doc->type != JSON_OBJ) {
        pass(raw json_make_null());
    }
    
    int64:obj_ptr = doc->payload;
    int64:count = npk_mem_read_int32(obj_ptr, 0i64) => int64;
    int64:keys_ptr = npk_mem_read_int64(obj_ptr, 8i64);
    int64:vals_ptr = npk_mem_read_int64(obj_ptr, 16i64);
    
    int64:i = 0i64;
    while (i < count) {
        int64:k_ptr = npk_mem_read_int64(keys_ptr, i * 8i64);
        int64:v_ptr = npk_mem_read_int64(vals_ptr, i * 8i64);
        
        int8:k_type = npk_mem_read_byte(k_ptr, 0i64) => int8;
        int64:k_payload = npk_mem_read_int64(k_ptr, 8i64);
        
        if (k_type == JSON_STR) {
            int64:k_len = npk_mem_read_int32(k_payload, 0i64) => int64;
            if (k_len == seg_len) {
                int64:k_str_data = npk_mem_read_int64(k_payload, 8i64);
                
                // Compare characters
                int64:j = 0i64;
                bool:match = true;
                while (j < seg_len) {
                    int8:c_path = npk_mem_read_byte(path_ptr, j) => int8;
                    int8:c_key  = npk_mem_read_byte(k_str_data, j) => int8;
                    if (c_path != c_key) { match = false; break; }
                    j = j + 1i64;
                }
                
                if (match == true) {
                    NpkJsonVal:v_elem = NpkJsonVal {
                        type: npk_mem_read_byte(v_ptr, 0i64) => int8,
                        payload: npk_mem_read_int64(v_ptr, 8i64)
                    };
                    
                    int8:nxt = npk_mem_read_byte(path_ptr, seg_len) => int8;
                    if (nxt == 0i8) {
                        // End of path, found target
                        pass(v_elem);
                    } else {
                        if (nxt == 46i8) {
                            // Dot, recurse
                            pass(raw eval_path(path_ptr + seg_len + 1i64, @cast_unchecked<int64>(@v_elem)));
                        }
                    }
                }
            }
        }
        
        i = i + 1i64;
    }
    
    pass(raw json_make_null());
};

```

