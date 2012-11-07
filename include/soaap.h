/*
 * File: soaap.h
 *
 *      This is a sample header file that is global to the entire project.
 *      It is located here so that everyone will find it.
 */

#ifndef SOAAP_H
#define SOAAP_H 1

#include "valgrind/taintgrind.h"
#include <stdio.h>

// types of sandboxes
#define SANDBOX_PERSISTENT "SANDBOX_PERSISTENT"
#define SANDBOX_EPHEMERAL "SANDBOX_EPHEMERAL"

// permissions for variables
#define VAR_READ "VAR_READ"
#define VAR_READ_MASK 0x1
#define VAR_WRITE "VAR_WRITE"
#define VAR_WRITE_MASK 0x2

// permissions for file descriptors
#define FD_READ "FD_READ"
#define FD_READ_MASK 0x1
#define FD_WRITE "FD_WRITE"
#define FD_WRITE_MASK 0x2

#define __sandbox __sandbox_persistent
#define __sandbox_persistent __attribute__((annotate(SANDBOX_PERSISTENT))) __attribute__((noinline))
#define __sandbox_ephemeral __attribute__((annotate(SANDBOX_EPHEMERAL))) __attribute__((noinline))
#define __var_read __attribute__((annotate(VAR_READ)))
#define __var_write __attribute__((annotate(VAR_WRITE)))
#define __fd_read __attribute__((annotate(FD_READ)))
#define __indirect_fd_read(F) __attribute__((annotate(F##"_"##FD_READ)))
#define __indirect_fd_write(F) __attribute__((annotate(F##"_"##FD_WRITE)))
#define __fd_write __attribute__((annotate(FD_WRITE)))
#define __callgates(fns...) \
	void __declare_callgates() { \
		__declare_callgates_helper(0, fns); \
	}

extern void __declare_callgates_helper(int unused, ...);

extern void soaap_create_sandbox();
extern void soaap_enter_persistent_sandbox();
extern void soaap_exit_persistent_sandbox();
extern void soaap_enter_ephemeral_sandbox();
extern void soaap_exit_ephemeral_sandbox();

extern void soaap_shared_var(char* var_name, int perms);
extern void soaap_shared_fd(int fd, int perms);
extern void soaap_shared_file(FILE* file, int perms);

extern void soaap_enter_callgate();
extern void soaap_exit_callgate();
extern void soaap_printf(char* str);

extern int printf(const char*, ...);

// functions for valgrind-function-wrapping
// (see http://valgrind.org/docs/manual/manual-core-adv.html#manual-core-adv.wrapping)
extern void valgrind_get_orig_fn(OrigFn* fn);

extern void call_unwrapped_function_w_v(OrigFn* fn, unsigned long* retval);
extern void call_unwrapped_function_w_w(OrigFn* fn, unsigned long* retval, unsigned long arg1);
extern void call_unwrapped_function_w_ww(OrigFn* fn, unsigned long* retval, unsigned long arg1, unsigned long arg2);
extern void call_unwrapped_function_w_www(OrigFn* fn, unsigned long* retval, unsigned long arg1, unsigned long arg2, unsigned long arg3);
extern void call_unwrapped_function_w_wwww(OrigFn* fn, unsigned long* retval, unsigned long arg1, unsigned long arg2, unsigned long arg3, unsigned long arg4);
extern void call_unwrapped_function_w_5w(OrigFn* fn, unsigned long* retval, unsigned long arg1, unsigned long arg2, unsigned long arg3, unsigned long arg4, unsigned long arg5);
extern void call_unwrapped_function_w_6w(OrigFn* fn, unsigned long* retval, unsigned long arg1, unsigned long arg2, unsigned long arg3, unsigned long arg4, unsigned long arg5, unsigned long arg6);
extern void call_unwrapped_function_w_7w(OrigFn* fn, unsigned long* retval, unsigned long arg1, unsigned long arg2, unsigned long arg3, unsigned long arg4, unsigned long arg5, unsigned long arg6, unsigned long arg7);

#endif /* SOAAP_H */