option casemap:none
EXTERN test_job_drain:PROC
PUBLIC test_job_bridge, test_job_resume, test_job_flush_clobber
.code
; RCX=queue, RDX=adapter, R8D=producer kind, R9=capture.
test_job_bridge PROC
    push rbx
    push rbp
    push rdi
    push r12
    sub rsp, 28h
    mov rbx, rcx
    mov r12, rdx
    mov ebp, r8d
    mov rdi, r9
    movdqu xmm0, XMMWORD PTR [test_simd_pattern]
    movdqu xmm1, xmm0
    movdqu xmm2, xmm0
    movdqu xmm3, xmm0
    movdqu xmm4, xmm0
    movdqu xmm5, xmm0
    mov rax, 1111h
    mov rdx, 3333h
    mov r9, 4444h
    mov r10, 5555h
    mov r11, 6666h
    cmp ebp, 1
    je owner_in_r8
    mov rcx, rbx
    mov r8, 7777h
    cmp ebp, 3
    jne prepared
    lea rcx, [rbx-20h]
    jmp prepared
owner_in_r8:
    mov rcx, 2222h
    mov r8, rbx
prepared:
    cmp ebp, 2
    jae leaf_call
    push 246h
    popfq
    call r12
    jmp test_job_resume
leaf_call:
    sub rsp, 8
    push 246h
    popfq
    call r12
    lea rsp, [rsp+8]
    jmp test_job_resume
test_job_bridge ENDP
test_job_resume PROC
    mov [rdi], rax
    mov [rdi+8], rcx
    mov [rdi+10h], rdx
    mov [rdi+18h], r8
    mov [rdi+20h], r9
    mov [rdi+28h], r10
    mov [rdi+30h], r11
    pushfq
    pop QWORD PTR [rdi+38h]
    mov [rdi+40h], rsp
    movdqu [rdi+48h], xmm0
    movdqu [rdi+58h], xmm1
    movdqu [rdi+68h], xmm2
    movdqu [rdi+78h], xmm3
    movdqu [rdi+88h], xmm4
    movdqu [rdi+98h], xmm5
    add rsp, 28h
    pop r12
    pop rdi
    pop rbp
    pop rbx
    ret
test_job_resume ENDP
; Deliberately clobber every volatile argument/SIMD register and flags.
test_job_flush_clobber PROC
    sub rsp, 28h
    mov rdx, rsp
    call test_job_drain
    add rsp, 28h
    mov rax, 9999h
    mov rcx, 9999h
    mov rdx, 9999h
    mov r8, 9999h
    mov r9, 9999h
    mov r10, 9999h
    mov r11, 9999h
    pcmpeqb xmm0, xmm0
    pcmpeqb xmm1, xmm1
    pcmpeqb xmm2, xmm2
    pcmpeqb xmm3, xmm3
    pcmpeqb xmm4, xmm4
    pcmpeqb xmm5, xmm5
    stc
    ret
test_job_flush_clobber ENDP
.const
test_simd_pattern DB 16 DUP(05Ah)
END
