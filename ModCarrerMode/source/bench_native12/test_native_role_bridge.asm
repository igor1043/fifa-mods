option casemap:none
PUBLIC test_native_role_bridge
.code
; Execute the exact isolated native role-limit block in the TEST process.
; RCX=role array, EDX=count, R8=RX instruction block.
test_native_role_bridge PROC
    push rsi
    sub rsp,20h
    xor esi,esi
    mov r11,r8
    mov r8,rcx
    mov r9d,edx
next_role:
    call r11
    add r8,4
    dec r9d
    jnz next_role
    mov eax,esi
    add rsp,20h
    pop rsi
    ret
test_native_role_bridge ENDP
END
