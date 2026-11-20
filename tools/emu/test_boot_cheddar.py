#!/usr/bin/env python3
"""Vérifie les pixels et le contrat de la tâche de démarrage Supermodel 3.06."""
import argparse
from pathlib import Path

from test_boot_anim import Rig, TASK, BUF_PTRS, STACK, TICK_CB, SEM_TICK, SEM_DONE, contract, save
from test_sdvintage import main_os_from_syx
import gen_boot_cheddar


def boot_rig(main, capture):
    if not capture:
        return Rig(main)
    rig = Rig((capture / "native.bin").read_bytes())
    for name, address in (("runtime", 0x46700000), ("sram", 0x80000000)):
        data = (capture / f"{name}.bin").read_bytes()
        rig.uc.mem_map(address, len(data))
        rig.uc.mem_write(address, data)
    return rig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("patched", type=Path)
    parser.add_argument("--original-capture", type=Path)
    parser.add_argument("--patched-capture", type=Path)
    parser.add_argument("--gif")
    args = parser.parse_args()
    original = main_os_from_syx(args.original)
    patched = main_os_from_syx(args.patched)
    offset = TASK - 0x40000400
    code = gen_boot_cheddar.assemble()
    assert patched == original[:offset] + code + original[offset + len(code):]

    before = boot_rig(original, args.original_capture)
    after = boot_rig(patched, args.patched_capture)
    before.run(TASK)
    after.run(TASK)
    assert contract(after.calls) == contract(before.calls) == [
        (("minuteur+", TICK_CB, 2), 1), (("attente", SEM_TICK), 90),
        (("signal", SEM_DONE), 1), (("minuteur-", TICK_CB), 1),
        (("fin", SEM_TICK), 1),
    ]
    assert not before.bad and not after.bad
    buffers = [after.r32(BUF_PTRS), after.r32(BUF_PTRS + 4)]
    ranges = [(b, b + 1024) for b in buffers] + [
        (BUF_PTRS, BUF_PTRS + 8), (0xfc03c000, 0xfc03c040), (STACK - 0x4000, STACK),
    ]
    stray = sorted(address for address in after.writes - before.writes
                   if not any(lo <= address < hi for lo, hi in ranges))
    assert not stray, [hex(address) for address in stray[:16]]

    lcd = (gen_boot_cheddar.SOURCE / "cheddar-portrait.lcd").read_bytes()
    portrait = [[int(bool(lcd[y * 16 + x // 8] & (128 >> (x % 8)))) for x in range(128)] for y in range(64)]
    assert after.frames[0] == [[0] * 128 for _ in range(64)]
    for frame, columns in enumerate(range(4, 129, 4), start=1):
        assert after.frames[frame] == [row[:columns] + [1] * (128 - columns) for row in portrait], frame
    assert all(image == portrait for image in after.frames[32:])
    print(f"PASS {args.patched.name}: portrait Redux exact, 90 ticks, retour au démarrage natif")
    if args.gif:
        save(after.frames, args.gif, None)


if __name__ == "__main__":
    main()
