#!/bin/sh
# Build the star2lte XNU BOOT image: loader + ADT + KERNEL appended to the
# stock BOOT's kernel slot. Host-side only; flashing is a separate step.
#   tools/star2lte-pack-xnu.sh KERNEL OUT.img ["extra boot args"]
# Needs backup/BOOT.img (stock) and CROSS (or the toolchain/ download).
set -eu
cd "$(dirname "$0")/.."
kernel=$1; out=$2; extra=${3:-}
: "${CROSS:=$(ls -d "$PWD"/toolchain/*/bin)/aarch64-none-elf-}"
(cd shim/star2lte && CROSS=$CROSS sh build.sh >/dev/null)
mkdir -p out
# ADT_ARGS="--scale2" for the iPhone XR canvas (see mkadt_star2lte.py).
python3 tools/mkadt_star2lte.py out/star2lte.adt ${ADT_ARGS:-}
# No rd=: the S9+ UFS driver is not ported, so XNU should stop at the root
# device. Console stays on (no a5fb_noconsole) and DECON sync is off.
# cpus=1 unless the extra arguments choose (XNU takes the first cpus=).
case " $extra " in *" cpus="*) cpus= ;; *) cpus="cpus=1 " ;; esac
cmdline="debug=0xc serial=3 ${cpus}keepsyms=1 -enable_kprintf_spam -noprogress \
wdt=-1 -wdt_no_pmu sweetfb_nosync=1 $extra"
rm -f out/star2lte.payload "$out"
python3 tools/mkpayload.py "$kernel" out/star2lte.adt out/star2lte.payload --cmdline "$cmdline"
python3 tools/herolte-pack-boot.py pack backup/BOOT.img shim/star2lte/out/xnu_boot.Image "$out" \
    --append out/star2lte.payload --chip 9810 --partition-size 57671680
