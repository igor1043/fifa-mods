; Copied native instruction adapter. No call into C or external game process.
; Preserve all volatile registers, SIMD values and the original flags.
; Drain the existing native batch only before its fixed node array fills.
option casemap:none
PUBLIC bench_job_template_begin, bench_job_template_end
PUBLIC bench_job_flush_pointer
PUBLIC bench_job_original_instruction, bench_job_counter_pointer
PUBLIC bench_job_owner_before, bench_job_owner_after
PUBLIC bench_job_flags_restore
PUBLIC bench_job_owner_shift_before, bench_job_owner_shift_after
PUBLIC bench_job_stack_release
.code
bench_job_template_begin LABEL BYTE
    pushfq
    sub rsp, 0C0h
    mov [rsp+20h], rax
    mov [rsp+28h], rcx
    mov [rsp+30h], rdx
    mov [rsp+38h], r8
    mov [rsp+40h], r9
    mov [rsp+48h], r10
    mov [rsp+50h], r11
    movdqu [rsp+60h], xmm0
    movdqu [rsp+70h], xmm1
    movdqu [rsp+80h], xmm2
    movdqu [rsp+90h], xmm3
    movdqu [rsp+0A0h], xmm4
    movdqu [rsp+0B0h], xmm5
bench_job_owner_before LABEL BYTE
    mov rcx, [rsp+28h]
bench_job_owner_shift_before LABEL BYTE
    DB 4 DUP(090h)
    cmp DWORD PTR [rcx+0C7Ch], 192
    jae drain_batch
    cmp DWORD PTR [rcx+0C90h], 192
    jb restore_arguments
drain_batch:
    call QWORD PTR [bench_job_flush_pointer]
bench_job_owner_after LABEL BYTE
    mov rcx, [rsp+28h]
bench_job_owner_shift_after LABEL BYTE
    DB 4 DUP(090h)
    mov DWORD PTR [rcx+0C90h], 0
    mov rax, QWORD PTR [bench_job_counter_pointer]
    lock inc QWORD PTR [rax]
restore_arguments:
    movdqu xmm0, [rsp+60h]
    movdqu xmm1, [rsp+70h]
    movdqu xmm2, [rsp+80h]
    movdqu xmm3, [rsp+90h]
    movdqu xmm4, [rsp+0A0h]
    movdqu xmm5, [rsp+0B0h]
    mov rax, [rsp+20h]
    mov rcx, [rsp+28h]
    mov rdx, [rsp+30h]
    mov r8, [rsp+38h]
    mov r9, [rsp+40h]
    mov r10, [rsp+48h]
    mov r11, [rsp+50h]
bench_job_original_instruction LABEL BYTE
    DB 7 DUP(090h)
bench_job_stack_release LABEL BYTE
    lea rsp, [rsp+0C0h]
bench_job_flags_restore LABEL BYTE
    popfq
    ret
ALIGN 8
bench_job_flush_pointer DQ 0
bench_job_counter_pointer DQ 0
bench_job_template_end LABEL BYTE
END
