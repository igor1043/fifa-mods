OPTION CASEMAP:NONE
PUBLIC SubsonImportBegin, SubsonImportEnd, SubsonImportPolicy, SubsonImportResume
PUBLIC SubsonCapacityBegin, SubsonCapacityEnd, SubsonCapacityPolicy, SubsonCapacityResume

SAVE_VOLATILE MACRO
    pushfq
    sub rsp,0E8h
    mov [rsp+20h],rax
    mov [rsp+28h],rcx
    mov [rsp+30h],rdx
    mov [rsp+38h],r8
    mov [rsp+40h],r9
    mov [rsp+48h],r10
    mov [rsp+50h],r11
    movdqu [rsp+60h],xmm0
    movdqu [rsp+70h],xmm1
    movdqu [rsp+80h],xmm2
    movdqu [rsp+90h],xmm3
    movdqu [rsp+0A0h],xmm4
    movdqu [rsp+0B0h],xmm5
ENDM
RESTORE_VOLATILE MACRO
    movdqu xmm0,[rsp+60h]
    movdqu xmm1,[rsp+70h]
    movdqu xmm2,[rsp+80h]
    movdqu xmm3,[rsp+90h]
    movdqu xmm4,[rsp+0A0h]
    movdqu xmm5,[rsp+0B0h]
    mov rax,[rsp+20h]
    mov rcx,[rsp+28h]
    mov rdx,[rsp+30h]
    mov r8,[rsp+38h]
    mov r9,[rsp+40h]
    mov r10,[rsp+48h]
    mov r11,[rsp+50h]
    add rsp,0E8h
    popfq
ENDM
.code
; Native importer uses R13 as GameSettings. The policy only changes the
; request for the currently active PlayNow state and preserves C14.
SubsonImportBegin LABEL BYTE
    SAVE_VOLATILE
    mov rcx,r13
    mov edx,[r13+0C10h]
    db 48h,0B8h
SubsonImportPolicy LABEL BYTE
    dq 0
    call rax
    mov [r13+0C10h],eax
    RESTORE_VOLATILE
    mov ebx,[r13+0C10h]
    db 0FFh,25h,0,0,0,0
SubsonImportResume LABEL BYTE
    dq 0
SubsonImportEnd LABEL BYTE

; The native FCE export otherwise reclassifies everything beyond seven.
; Retain its exact original cap outside PlayNow. No player IDs are fabricated.
SubsonCapacityBegin LABEL BYTE
    SAVE_VOLATILE
    db 48h,0B8h
SubsonCapacityPolicy LABEL BYTE
    dq 0
    call rax
    lea r14d,[rdi+rax]
    RESTORE_VOLATILE
    mov ebx,edi
    db 0FFh,25h,0,0,0,0
SubsonCapacityResume LABEL BYTE
    dq 0
SubsonCapacityEnd LABEL BYTE
END
