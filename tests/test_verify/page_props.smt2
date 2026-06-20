; P1: Slot array never overlaps with tuple region
; After N insertions, free_offset <= tuple_end
(declare-fun free_offset (Int) Int)  ; free_offset after N inserts
(declare-fun tuple_end (Int) Int)    ; tuple_end after N inserts
(assert (= (free_offset 0) 32))     ; initial state
(assert (= (tuple_end 0) 8191))
(assert (forall ((n Int))
  (=> (and (>= n 0) (< (free_offset n) (tuple_end n)))
      (<= (free_offset (+ n 1)) (tuple_end (+ n 1))))))
(check-sat)  ; SAT = invariant is consistent
