; P1: No false negatives — if key was added, check always returns true
; P2: bloom_check on empty filter always returns false
; P3: Number of hash functions is positive

(declare-fun bloom_added (Int) Bool)
(declare-fun bloom_check (Int) Bool)

; P1: No false negatives
(assert (forall ((k Int)) (=> (bloom_added k) (bloom_check k))))

; P2: Empty filter check is false
(declare-const is_empty Bool)
(assert (=> is_empty (forall ((k Int)) (not (bloom_check k)))))

; P3: Number of hash functions > 0
(declare-const num_hashes Int)
(assert (> num_hashes 0))

(check-sat)
