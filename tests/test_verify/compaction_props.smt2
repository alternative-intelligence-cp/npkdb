; P1: After compaction, total records <= sum of input records
; P2: After compaction, L0 is empty
; P3: Output SSTable key ranges are non-overlapping
; P4: For duplicate keys, only the newest version survives

(declare-const input_records Int)
(declare-const output_records Int)
(assert (>= input_records 0))
(assert (<= output_records input_records))

(declare-const l0_empty Bool)
(assert l0_empty)

(declare-fun sstable_min_key (Int) Int)
(declare-fun sstable_max_key (Int) Int)
(assert (forall ((i Int) (j Int))
  (=> (and (>= i 0) (> j i))
      (< (sstable_max_key i) (sstable_min_key j)))))

(check-sat)
