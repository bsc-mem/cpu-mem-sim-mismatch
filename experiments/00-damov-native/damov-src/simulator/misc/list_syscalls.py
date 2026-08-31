#!/usr/bin/python
# Produces a list of syscalls in the current system
import re
import subprocess

syscallDefs = subprocess.check_output(
    ["gcc", "-E", "-dD", "-include", "asm/unistd.h", "-"],
    input=b"",
).decode()
sysList = [(int(numStr), name) for (name, numStr) in re.findall("#define __NR_(.*?) (\d+)", syscallDefs)]
if not sysList:
    raise RuntimeError("No syscall definitions found through <asm/unistd.h>")
denseList = ["INVALID"]*(max([num for (num, name) in sysList]) + 1)
for (num, name) in sysList: denseList[num] = name
print ('"' + '",\n"'.join(denseList) + '"')
