/*
 * Copyright (c) 2015 Alex Richardson
 * All rights reserved.
 *
 * This software was developed by SRI International and the University of
 * Cambridge Computer Laboratory under DARPA/AFRL contract FA8750-10-C-0237
 * ("CTSRD"), as part of the DARPA CRASH research programme.
 *
 * This software was developed at the University of Cambridge Computer
 * Laboratory with support from a grant from Google, Inc.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
 * OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
 * OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 */

import os
from commandwrapper import *


class CompilerWrapper(CommandWrapper):
    def __init__(self, originalCommandLine):
        # TODO: do we need to support -S flag (generate assembly)
        # And then of course we also need to wrap the assembler...
        super().__init__(originalCommandLine)
        self.mode = Mode.object_file

    def computeWrapperCommand(self):
        if '-E' in self.realCommand:
            # only run the preprocessor
            self.nothingToDo = True
            return

        assert '-c' in self.realCommand or '-S' in self.realCommand

        self.mode = Mode.object_file
        self.generateIrCommand.append(soaapLlvmBinary(self.executable))  # clang or clang++

        skipNext = True  # skip executable
        inputFiles = []
        # make a copy since we might be modifying self.realCommand
        self.generateEmptyOutput = False
        originalRealCommand = list(self.realCommand)
        for index, param in enumerate(originalRealCommand):
            if skipNext:
                skipNext = False
                continue
            elif param.startswith('-'):
                # TODO: strip optimization flags?
                if param.startswith('-g'):
                    # strip all -g parameters, we only want '-gline-tables-only'
                    continue
                elif param == '-Werror' or param.startswith("-Werror="):
                    # This can cause errors since we are using a newer compiler that might have new warnings
                    # Fixes e.g. krb5 build due to the following error:
                    # cc_kcm.c:397:13: error: variable 'reply_len' is used uninitialized whenever 'if' condition is false [-Werror,-Wsometimes-uninitialized]
                    self.realCommand.remove(param)
                    continue
                elif param == '-finline':
                    continue  # finline should never be part of the wrapper command since we add -fno-inline
                elif param in ('-fexcess-precision=standard', '-frounding-math'):
                    # Fix the following (both when compiling and when generating LLVM IR):
                    # error: unknown argument: '-fexcess-precision=standard'
                    # warning: optimization flag '-frounding-math' is not supported
                    self.realCommand.remove(param)
                    continue
                elif param == '-Wa,--noexecstack':
                    # this is required in the real command, but not when emitting LLVM IR
                    continue
                elif param in clangParamsWithArgument():
                    if index + 1 >= len(originalRealCommand):
                        raise CommandWrapperError(param + ' flag without parameter!', originalRealCommand)
                    skipNext = True
                    next = originalRealCommand[index + 1]
                    if param == '-o':
                        # work around libtool create object files in ./.libs/foo.o and deletes all other files!
                        # -> we just create the file one level higher and work around it in the linker wrapper again..
                        # if next.startswith('.libs/'):
                        #     next = next.replace('.libs/', '')
                        self.output = correspondingBitcodeName(next)
                    else:
                        self.generateIrCommand.append(param)
                        self.generateIrCommand.append(next)
                elif param.startswith('-D' + ENVVAR_NO_EMIT_IR) or param.startswith('-L' + ENVVAR_NO_EMIT_IR):
                    # allow selectively skipping targets by setting this #define or linker search path
                    # e.g. using target_compile_definitions(foo PRIVATE LLVM_IR_WRAPPER_NO_EMIT_LLVM_IR=1)
                    # or using target_link_libraries(foo PRIVATE -LLLVM_IR_WRAPPER_NO_EMIT_LLVM_IR=1)
                    self.nothingToDo = True
                    self.realCommand.remove(param)
                    return
                else:
                    self.generateIrCommand.append(param)
            else:
                # this must be an input file
                if param.endswith('.s') or param.endswith('.S'):
                    valid = False
                    if '/x86_64/' in param:
                        origParam = param
                        # workaround for musl libc: compile the stub files instead
                        param = param.replace('/x86_64/', '/').replace('.s', '.c').replace('.S', '.c')
                        if os.path.isfile(param):
                            print(infoMsg('Workaround for musl libc: ' + origParam + ' -> ' + param))
                            valid = True
                    if os.getenv(ENVVAR_SKIP_ASM_FILES):
                        self.generateEmptyOutput = True
                        valid = True

                    if not valid:
                        raise CommandWrapperError('Attempting to compile assembly file (export SKIP_ASSEMBLY_FILES=1' +
                                                  ' to generate an empty file instead): ' + param, self.realCommand)
                inputFiles.append(param)
                self.generateIrCommand.append(param)

        if len(inputFiles) == 0:
            raise CommandWrapperError('No input files found!', self.realCommand)
        # add the required compiler flags for analysis
        # FIXME: Is -gline-tables-only enough?
        self.generateIrCommand.append('-gline-tables-only')  # soaap needs debug info
        self.generateIrCommand.append('-emit-llvm')
        self.generateIrCommand.append('-fno-inline')  # make sure functions are not inlined

        if not self.output:
            if len(inputFiles) != 1:
                raise CommandWrapperError('No -o flag, but multiple input files:' + str(inputFiles), self.realCommand)
            root, ext = os.path.splitext(inputFiles[0])  # src/foo.c -> ('src/foo', '.c')
            self.output = correspondingBitcodeName(root + '.o')
        # make sure the output file is right at the end so we can see easily which file is being compiled
        self.generateIrCommand.append('-o')
        self.generateIrCommand.append(self.output)

    def runGenerateIrCommand(self):
        if self.generateEmptyOutput:
            self.createEmptyBitcodeFile(self.output)
        else:
            super().runGenerateIrCommand()
