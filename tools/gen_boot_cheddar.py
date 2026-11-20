#!/usr/bin/env python3
"""Génère la tâche de démarrage 3.06 à partir du portrait OLED de Redux."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/machines/boot_cheddar"
OUTPUT = ROOT / "docs/flasher/boot-cheddar-data.js"
BODY, BODY_END = 0x40053a6c, 0x40053e74


def portrait():
    rows = (SOURCE / "cheddar-portrait.lcd").read_bytes()
    assert hashlib.sha256(rows).hexdigest() == "356198a98f4a1c2c1a534e6cf9f61cef80ebe3d4a6a7a0694a6f28179c2671e9"
    return bytes(sum(1 << bit for bit in range(8)
                     if rows[(page * 8 + bit) * 16 + x // 8] & (128 >> (x % 8)))
                 for page in range(7, -1, -1) for x in range(128))


def compress(data):
    """Choisit les commandes littérales et les copies LZ les plus courtes."""
    cost = [0] + [float("inf")] * len(data)
    steps = [None] * (len(data) + 1)

    def offer(start, length, command):
        end = start + length
        candidate = cost[start] + len(command)
        if candidate < cost[end]:
            cost[end] = candidate
            steps[end] = (start, command)

    for start in range(len(data)):
        for length in range(1, min(128, len(data) - start) + 1):
            offer(start, length, bytes([length - 1]) + data[start:start + length])
        for distance in range(1, min(256, start) + 1):
            length = 0
            while length < min(130, len(data) - start) and data[start + length] == data[start + length - distance]:
                length += 1
                if length >= 3:
                    offer(start, length, bytes([128 + length - 3, distance - 1]))
    end, commands = len(data), []
    while end:
        end, command = steps[end]
        commands.append(command)
    return b"".join(reversed(commands))


def assemble():
    cross = next(prefix for prefix in ("m68k-linux-gnu-", "m68k-elf-") if shutil.which(prefix + "as"))
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        (folder / "cheddar-portrait.lz").write_bytes(compress(portrait()))
        obj, elf, binary = (folder / f"boot.{ext}" for ext in ("o", "elf", "bin"))
        subprocess.run([cross + "as", "-mcpu=54418", "-I", tmp, SOURCE / "boot_cheddar.S", "-o", obj], check=True)
        subprocess.run([cross + "ld", "-T", SOURCE.parent / "boot_anim/boot_anim.ld", "-o", elf, obj], check=True)
        subprocess.run([cross + "objcopy", "-O", "binary", "-j", ".anim", elf, binary], check=True)
        code = binary.read_bytes()
    if len(code) > BODY_END - BODY:
        raise ValueError(f"Tâche trop grande : {len(code)} octets")
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    code = assemble()
    result = f'/* tools/gen_boot_cheddar.py */\nwindow.MCBootCheddarData = "{code.hex()}";\n'
    if args.check:
        if result != OUTPUT.read_text(encoding="ascii"):
            raise SystemExit(f"{OUTPUT.name} doit être régénéré")
    else:
        OUTPUT.write_text(result, encoding="ascii")
    print(f"Cheddar Butt : {len(code)} / {BODY_END - BODY} octets")


if __name__ == "__main__":
    main()
