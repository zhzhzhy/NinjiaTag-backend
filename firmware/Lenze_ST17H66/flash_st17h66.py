#!/usr/bin/env python3
import sys,time
import base64

pubkey = ''
if len(sys.argv) != 2:
    print(f'Usage: {sys.argv[0]} <pubkey base64>')
    print('Using default key instead')
else:
    pubkey = sys.argv[1]

xip = bytearray()
jump_table = bytearray()
irom1 = bytearray()

with open('./FindMy.hex') as f:
    # hex file order is assumed to be ER_ROM_XIP - JUMP_TABLE - ER_IROM1
    sections = ['ER_ROM_XIP','JUMP_TABLE','ER_IROM1']
    infiles = [xip,jump_table,irom1]
    infile_current = -1
    inbuf = None
    for line in f:
        if line[7:9] == '04':
            infile_current += 1
            print(f'Start of new ihex section found, assuming {sections[infile_current]}')
            inbuf = infiles[infile_current]
        elif line[7:9] == '00':
            inbuf.extend(bytearray.fromhex(line[9:-3]))


c0 = bytearray() # hexf header

c0.extend(bytearray.fromhex('03000000FFFFFFFF3818FF1FFFFFFFFF')) # initial support only for files with 3 ihex sections
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'))
c0.extend(bytearray.fromhex('00000200FFFF000000000211FFFFFFFF'))
c0.extend(bytearray.fromhex('00500000FFFF00000000FF1FFFFFFFFF'))
c0.extend(bytearray.fromhex('14540000FFFF00003818FF1FFFFFFFFF'))

c0[-44:-42] = int.to_bytes(len(xip), 2, 'little') # length ER_ROM_XIP
c0[-28:-26] = int.to_bytes(len(jump_table), 2, 'little') # length JUMP_TABLE
c0[-12:-10] = int.to_bytes(len(irom1), 2, 'little') # length ER_IROM1

c1 = bytearray() # JUMP_TABLE + ER_IROM1
c1.extend(jump_table)
c1.extend(bytearray.fromhex('0' *16))
c1.extend(irom1)

c2 = bytearray() # ER_ROM_XIP
c2.extend(xip)
c = [c0,c1,c2]

print(f'{bytes(c0[:10])} ... {bytes(c0[-10:])}, len {len(c0)} sum {sum(c0)}')
print(f'{bytes(c0[-44:-42])} ... {bytes(c0[-28:-26])} ... {bytes(c0[-12:-10])}')
print(f'{bytes(c1[:10])} ... {bytes(c1[-10:])}, len {len(c1)} sum {sum(c1)}')
print(f'{bytes(c2[:10])} ... {bytes(c2[-10:])}, len {len(c2)} sum {sum(c2)}')
print(f'key: {bytes(c1[-150:-122])}')


import serial
uart = serial.Serial('COM3', 9600, timeout=0.01, inter_byte_timeout=0.01)
res = uart.read(10)
while not res.endswith(b'cmd>>:'):
    uart.write(b'UXTDWU')
    time.sleep(0.05)
    res = uart.read(10)
    if res: print(res)

print('RESET MODE activated. Changing baudrate to 115200')
uart.baudrate = 115200


print('Erase + Write')
cmds = []
cmds.append(b'er512') # erase
cmds.append(b'rdrev+')
cmds.append(b'wrreg4000c890 ab000001 ')
cmds.append(b'wrreg4000c838 ff010005 ')
cmds.append(b'spifs 0 1 3 0 ')
cmds.append(b'sfmod 2 2 ')
cmds.append(b'cpnum ffffffff ')
cmds.append(b'cpbin c0 002000 ' + b'%x' % len(c0) + b' 11002000')
cmds.append(b'cpbin c1 005000 ' + b'%x' % len(c1) + b' 11005000')
cmds.append(b'cpbin c2 020000 ' + b'%x' % len(c2) + b' 11020000')

for cmd in cmds:
    uart.write(cmd)
    print('sent', cmd)
    while not uart.in_waiting:
        time.sleep(0.3)
    msg = uart.read(uart.in_waiting)
    print('Response is:', msg)

    if cmd[5:9] in [b' c0 ', b' c1 ', b' c2 ']:
        cfile = cmd[7] -48
        data = c[cfile]

        if cfile == 1 and pubkey and data[-150:-122] == b'\x11"3DUfw\x88\x99\xaa\xbb\xcc\xdd\xef\xfe\xdd\xcc\xbb\xaa\x99\x88wfUD3"\x11':
            print('pubkey:', pubkey)
            key_bytes = base64.b64decode(pubkey)
            if len(key_bytes) == 28:
                data[-150:-122] = key_bytes
            else:
                print('ERROR: wrong key length, using default key')

        ldata = uart.write(data)
        print('sent c%d (len=%d)' % (cfile, ldata))
        while not uart.in_waiting:
            time.sleep(0.3)
        msg = uart.read(uart.in_waiting)
        print('Response is:', msg)

        uart.write(b'%08x' % sum(data))
        print('sent checksum')
        while not uart.in_waiting:
            time.sleep(0.3)
        msg = uart.read(uart.in_waiting)
        print('Response is:', msg)
