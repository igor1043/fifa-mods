option casemap:none
.code
test_bench_render_load_bridge PROC FRAME
    push r12
    .pushreg r12
    sub rsp,20h
    .allocstack 20h
    .endprolog
    mov r12b,r8b
    call r9
    add rsp,20h
    pop r12
    ret
test_bench_render_load_bridge ENDP
END
