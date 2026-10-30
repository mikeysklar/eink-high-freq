#!/bin/bash
# flash.sh <usb-path> <uf2>: 1200 touch, wait for RPI-RP2 on the same path, copy
P=$1; U=$2
TTY=/dev/serial/by-path/pci-0000:00:14.0-usb-0:${P#*-}:1.0
python3 -c "import serial,time; s=serial.Serial('$TTY',1200); time.sleep(0.15); s.close()"
for i in $(seq 1 30); do
  sleep 1
  blk=$(ls -d /sys/bus/usb/devices/$P/$P:1.0/host*/target*/*/block/* 2>/dev/null | head -1)
  [ -n "$blk" ] && break
done
[ -z "$blk" ] && { echo "no bootloader drive"; exit 1; }
dev=/dev/$(basename $blk)1
sleep 2
grep -q RPI-RP2 <(lsblk -no LABEL $dev) || { echo "not RPI-RP2: $(lsblk -no LABEL $dev)"; exit 1; }
mnt=$(findmnt -n -o TARGET $dev); [ -z "$mnt" ] && udisksctl mount -b $dev >/dev/null && mnt=$(findmnt -n -o TARGET $dev)
cat $mnt/INFO_UF2.TXT | head -3
cp $U $mnt/ && sync; echo copied to $mnt
