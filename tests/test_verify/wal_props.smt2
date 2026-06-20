; P1: CRC32 detects single-bit errors
; P2: WAL sequence numbers are strictly monotonic
; P3: Record length = header + payload (always >= 16)
(declare-fun record_length (Int) Int)
(assert (forall ((seq Int))
  (>= (record_length seq) 16)))
(check-sat)
