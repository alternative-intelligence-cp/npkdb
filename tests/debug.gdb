b *npk_mem_read_string+209
commands
  silent
  printf "Calling memcpy. rdi=%llx, rsi=%llx, rdx=%lld\n", $rdi, $rsi, $rdx
  stepi
  stepi
  stepi
  stepi
  stepi
  stepi
  stepi
  stepi
  stepi
  stepi
  stepi
  stepi
  stepi
  stepi
  stepi
  stepi
  info registers rax rdx rbp
  continue
end
run
