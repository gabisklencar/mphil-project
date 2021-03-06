#!/usr/bin/env python3

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

import argparse
import os
import re
import subprocess
import sys

from checksetup import *
from commandwrapper import findExe

overrides = {}

bindir = os.path.join(IR_WRAPPER_DIR, "bin")
if not os.path.isdir(bindir):
    sys.exit(bindir + "does not exist")


def setIrWrapperVar(var, command):
    # only set those that were explicitly changed
    if not command:
        return
    splitted = command.split()
    command = splitted[0]
    wrapper = os.path.join(bindir, command)
    if not os.path.exists(wrapper):
        sys.exit('could not find ' + wrapper)
    # allow parameters to be passed
    if len(splitted) > 1:
        wrapper = wrapper + ' ' + ' '.join(splitted[1:])
    setOverride(var, wrapper)


# also change the ENV vars
def setOverride(var, value):
    overrides[var] = value
    os.environ[var] = value

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
# parser.add_argument('options', nargs='*', help='Arguments to pass to configure')
parser.add_argument('-f', required=False, default='./Makefile', help='Makefile override')
parser.add_argument('--ld', required=False, default='', type=str,
                    help='LD wrapper script name (and parameters)')
parser.add_argument('--link', required=False, default='', type=str,
                    help='LINK wrapper script name (and parameters)')
parser.add_argument('--ar', required=False, default='', type=str,
                    help='AR wrapper script name (and parameters)')
parser.add_argument('--ranlib', required=False, default='', type=str,
                    help='RANLIB wrapper script name (and parameters)')
parser.add_argument('--var', required=False, action='append', metavar=('VAR=VALUE'),
                    help='override env var [VAR] with [VALUE]. Can be repeated multiple times')
parser.add_argument('--cpp-linker', action='store_true', help='Use C++ compiler for linking')
parser.add_argument('--install-bitcode', action='store_true', help='Install the bitcode files as well')
parser.add_argument('--confirm', action='store_true', help='Confirm before running configure')
parsedArgs, unknownArgs = parser.parse_known_args()
makefile = parsedArgs.f
print('Makefile is:', makefile)
print(parsedArgs)
commandline = [findExe('gmake'), '-f', makefile]

# no need to add an override option for CC and CXX, this can be done via --env
setIrWrapperVar('CC', 'clang')
setIrWrapperVar('LTCC', 'clang')
setIrWrapperVar('CXX', 'clang++')
setIrWrapperVar('AR', parsedArgs.ar)
setIrWrapperVar('RANLIB', parsedArgs.ranlib)

if parsedArgs.cpp_linker:
    if parsedArgs.ld == 'clang':
        parsedArgs.ld = 'clang++'
    if parsedArgs.link == 'clang':
        parsedArgs.link = 'clang++'

setIrWrapperVar('LD', parsedArgs.ld)
setIrWrapperVar('LINK', parsedArgs.link)

# set PATH so that our ln/mv/cp/rm commands are found
if not os.environ["PATH"].startswith(bindir):
    os.environ["PATH"] = bindir + ":" + os.environ["PATH"]


# now replace the manual overrides:
for s in (parsedArgs.var or []):
    (var, value) = s.split('=')
    setOverride(var.strip(), value.strip())

for k, v in overrides.items():
    commandline.append(k + '=' + v)

commandline.extend(unknownArgs)  # append all the user passed flags
if parsedArgs.install_bitcode:
    os.environ[ENVVAR_INSTALL_BITCODE] = "1"
    commandline.append("install")

print('About to run', commandline)

if parsedArgs.confirm:
    result = input('Continue? [y/n] (y)').lower()
    if len(result) > 0 and result[0] != 'y':
        sys.exit()

# no need for subprocess.call, just use execvpe
os.execvpe(commandline[0], commandline, os.environ)
sys.exit('Could not execute ' + str(commandline))


# keep the old makefile parsing code here for now in case it makes sense to reactivate it
'''
buildSystem = 'generic'

# we (currently?) only care about upper case variables
varAssignmentRegex = re.compile(r'^([A-Z_]+)\s*[?:]?=(.*)')
varExpansionRegex = re.compile(r'^(\$[\{\(][\w_]+[\)\}])(.*)')
# TODO: quoted paths with spaces no handled
# dash must not be the first char otherwise it's an option
pathRegex = re.compile(r'^([/\w][/\w-]*)(.*)')


def getAssignmentType(assigment):
    expansion = re.match(varExpansionRegex, value)
    path = re.match(pathRegex, value)
    if expansion:
        print('Variable expansion of', expansion.group(1))
    elif path:
        print('path/cmd assignment', path.group(1))
    else:
        print('other var assign:', assigment)
    return (expansion, path)


def isCommand(path, commands):
    for c in commands:
        if path == c:
            return c
        if path.endswith('/' + c):
            return c
    return None

lineBuffer = ''
lineContinuation = False
# for now just check for qmake, perhaps some other changes will be required for other systems
for index, line in enumerate(open(makefile)):
    if lineContinuation:
        lineBuffer = lineBuffer + line.strip()
    else:
        lineBuffer = line.strip()
    if lineBuffer.endswith('\\'):
        lineBuffer = lineBuffer[:-1]  # remove the backslash
        lineContinuation = True
        continue  # add the next line as well
    else:
        lineContinuation = False

    # print(index, lineBuffer)

    # The qmake generated Makefiles need AR='ar cqs' (i.e. with paramters), autoconf without params
    # Test by looking at the makefile
    if 'Generated by qmake' in lineBuffer:
        varOverrides['LINK'] = overrideCmd('clang++'),
        # for some reason the QMake makefiles expect the cqs inside the AR variable !!
        varOverrides['AR'] = overrideCmd('ar') + ' cqs'
        buildSystem = 'qmake'
        break

    if 'generated by automake' in lineBuffer:
        buildSystem = 'automake'
        # TODO: anything special here?

    m = re.match(varAssignmentRegex, lineBuffer)
    if not m:
        continue

    variable = m.group(1)
    value = m.group(2).strip()

    if variable == 'LINK':
        print('FOUND LINK assignemnt:', variable, value)
        expansion, path = getAssignmentType(value)
        if expansion:
            print('Not overriding LINK since it is a variable expansion:', value)
            continue
        sys.exit('COULD NOT HANDLE LINK assignment: ' + value)
    elif variable == 'LD':
        print('FOUND LD assignment:', variable, value)
        expansion, path = getAssignmentType(value)
        if expansion:
            print('Not overriding LD since it is a variable expansion:', value)
            continue

        # relative/absolute path -> we have to override it
        command = path.group(1)
        commandArgs = path.group(2)
        if isCommand(command, ['clang', 'gcc', 'cc']):
            varOverrides['LD'] = overrideCmd('clang') + commandArgs
        elif isCommand(command, ['clang++', 'g++', 'c++']):
            varOverrides['LD'] = overrideCmd('clang++') + commandArgs
        elif isCommand(command, ['ld', 'lld', 'gold']):
            varOverrides['LD'] = overrideCmd('ld') + commandArgs
        else:
            sys.exit('COULD NOT HANDLE LD assignment: ' + value)

print('Detected build system is', buildSystem)
'''
