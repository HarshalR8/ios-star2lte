# Working on the star2lte port (Galaxy S9+ SM-G965F, Exynos 9810)

- Read `docs/star2lte-bringup.md` first: hardware map, device evidence, the fixes so far and the
  plan. Record every new boot result there (what was flashed, what the log or photo showed) and
  commit it. Keep observations and guesses apart.
- The S9+ is the `STAR2LTE` variant of the HEROLTE kernel: all S9+ kernel changes live in
  `xnu/patches/0318-star2lte-board.patch`, built on top of patches 0001-0317. Edit them in an
  applied XNU tree (`research/xnu`, gitignored) and regenerate 0318 with `git diff`.
- Prefer boot-args over rebuilds: new drivers and experiments get a boot-arg switch so a test
  needs only `tools/star2lte-pack-xnu.sh` (seconds) instead of a kernel build (~17 min on GitHub
  Actions, `xnu` workflow, `star2lte` branch).
- Never print from exception or interrupt context (boot 5 panicked on it); record into memory and
  print from the persistent log's heartbeat (`bsd/dev/herolte_ufs.c`).

## Device safety

- Trials write only BOOT (`/dev/block/platform/11120000.ufs/by-name/BOOT`, sda10) from TWRP, and
  verify by reading it back. USERDATA (sda25) holds the iOS root; rewrite it only when the user
  asks. Never write EFS, CPEFS, PARAM, RECOVERY or the bootloader partitions.
- Stock BOOT, EFS, CPEFS, PARAM, DTB, DTBO and RECOVERY backups are in `backup/` (gitignored).
- Keep Apple software, device dumps, logs and photos out of git (`research/`, `out/`, `backup/`).
  The iOS root image is built only in a private repository (`ios-root` workflow).

## Test loop

1. Pack: `tools/star2lte-pack-xnu.sh KERNEL out/xnu-boot-N.img "BOOT ARGS"`.
2. Flash from TWRP, read back, `adb reboot`; the user watches the screen.
3. Back in TWRP: `HEROLTE_LOG_DEV=/dev/block/platform/11120000.ufs/by-name/USERDATA
   tools/herolte-log-pull.py adb out/bootN.txt`. Symbolize kernel PCs with the kernel's LC_SYMTAB.
