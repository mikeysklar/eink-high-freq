#!/usr/bin/env python3
"""Run a file of CircuitPython code on a board over raw REPL, by USB path.

usage: cprun.py <usb-path> <file.py|-> [timeout_s]
Globals persist between runs (raw REPL does not soft reset).
"""
import sys
import time
import serial

path, src = sys.argv[1], sys.argv[2]
timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 60
tty = f"/dev/serial/by-path/pci-0000:00:14.0-usb-0:{path.split('-', 1)[1]}:1.0"
code = sys.stdin.read() if src == "-" else open(src).read()

s = serial.Serial(tty, 115200, timeout=0.1, write_timeout=5)


def read_until(tok, t):
    buf = b""
    end = time.monotonic() + t
    while time.monotonic() < end:
        buf += s.read(4096)
        if tok in buf:
            return buf
    raise TimeoutError(f"waiting for {tok!r}, got tail {buf[-300:]!r}")


# interrupt whatever runs, enter raw REPL, sync on its prompt
s.write(b"\r\x03\x03")
time.sleep(0.3)
s.read(65536)
s.write(b"\r\x01")
read_until(b"raw REPL; CTRL-B to exit\r\n>", 5)

for i in range(0, len(code), 256):
    s.write(code[i:i + 256].encode())
    time.sleep(0.01)
s.write(b"\x04")
out = read_until(b"\x04>", timeout).partition(b"OK")[2]
body, _, rest = out.partition(b"\x04")
err = rest.partition(b"\x04")[0]
sys.stdout.write(body.decode(errors="replace"))
if err:
    sys.stdout.write("ERR: " + err.decode(errors="replace"))
s.close()
sys.exit(1 if err else 0)
