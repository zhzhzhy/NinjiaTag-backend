import sys
import base64
import hashlib
import random
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import argparse
import shutil
import os
import string
from string import Template
import struct
import json
import binascii
import uuid
from filelock import FileLock, Timeout

OUTPUT_FOLDER = 'output/'
CONV_FOLDER = 'convert/'

TEMPLATE = Template('{'
                    '\"id\": $id,'
                    '\"colorComponents\": ['
                    '    0,'
                    '    1,'
                    '    0,'
                    '    1'
                    '],'
                    '\"name\": \"$name\",'
                    '\"privateKey\": \"$privateKey\",'
                    '\"icon\": \"\",'
                    '\"isDeployed\": true,'
                    '\"colorSpaceName\": \"kCGColorSpaceExtendedSRGB\",'
                    '\"usesDerivation\": false,'
                    '\"isActive\": false,'
                    '\"additionalKeys\": [$additionalKeys],'
                    '\"keysMap\": $keysMap'
                    '}')

def int_to_bytes(n, length, endianess='big'):
    h = '%x' % n
    s = bytes.fromhex(h.zfill(length*2))
    return s if endianess == 'big' else s[::-1]

def to_C_byte_array(adv_key, isV3):
    out = '{'
    for element in range(0, len(adv_key)):
        e = adv_key[element] if isV3 else adv_key[element]
        out = out + "0x{:02x}".format(e)
        if element != len(adv_key)-1:
            out = out + ','
    out = out + '}'
    return out

def sha256(data):
    digest = hashlib.new("sha256")
    digest.update(data)
    return digest.digest()

parser = argparse.ArgumentParser()
parser.add_argument('-n', '--nkeys', help='number of keys to generate', type=int, default=1)
parser.add_argument('-i', '--nitems', help='number of items to generate', type=int, default=1)
parser.add_argument('-p', '--prefix', help='prefix of the keyfiles')
parser.add_argument('-y', '--yaml', help='yaml file where to write the list of generated keys')
parser.add_argument('-v', '--verbose', help='print keys as they are generated', action="store_true")
parser.add_argument('-conv', '--convert', action='store_true')
args = parser.parse_args()

MAX_KEYS = 2000
MAX_ITEMS = 1000
MODE = "generate"
if args.convert:
    MODE = "convert"

if args.nkeys < 1 or args.nkeys > MAX_KEYS:
    raise argparse.ArgumentTypeError("Number of keys out of range (between 1 and " + str(MAX_KEYS) + ")")

if args.nitems < 1 or args.nitems > MAX_ITEMS:
    raise argparse.ArgumentTypeError("Number of items out of range (between 1 and " + str(MAX_ITEMS) + ")")

current_directory = os.getcwd()

def random_prefix():
    if args.prefix is None:
        prefix = uuid.uuid4().hex.upper()
    else:
        prefix = args.prefix
    print(f"Using prefix: {prefix}")
    return prefix

def generate_mkeys():
    lock_path = os.path.join(current_directory, 'keyMap.lock')
    file_lock = FileLock(lock_path, timeout=30)
    
    # Create directories and verify keyMap.json within lock
    with file_lock:
        prefix = random_prefix()
        PREFIX_FOLDER = prefix + '/'
        if os.path.exists(PREFIX_FOLDER):
            shutil.rmtree(PREFIX_FOLDER)
        os.makedirs(PREFIX_FOLDER, exist_ok=True)

        keyMap_path = os.path.join(current_directory, 'keyMap.json')
        if not os.path.exists(keyMap_path):
            with open(keyMap_path, 'w') as km:
                json.dump([], km)
        

    # Generate keys outside lock
    new_keys_data = []
    if args.yaml:
        yaml = open(PREFIX_FOLDER + prefix + '_' + args.yaml + '.yaml', 'w')
        yaml.write('  keys:\n')
    
    keyfile = open(PREFIX_FOLDER + prefix + '_keyfile', 'wb')
    if args.nkeys > 255:
        keyfile.write(struct.pack("I", args.nkeys))
        print("Using INT(4 byte) key count in keyfile header!")
    elif args.nkeys <= 255:
        keyfile.write(struct.pack("B", args.nkeys))
        print("Using BYTE(1 byte) key count in keyfile header!")

    devices = open(PREFIX_FOLDER + prefix + '_devices.json', 'w')
    devices.write('[\n')

    fname = f'{prefix}.keys'
    keys = open(PREFIX_FOLDER + fname, 'w')
    
    isV3 = sys.version_info.major > 2
    print('Using python3' if isV3 else 'Using python2')
    print(f'Output will be written to {PREFIX_FOLDER}')
    additionalKeys = []
    keysMap = {}
    i = 0

    while i < args.nkeys:
        priv = random.getrandbits(224)
        adv = ec.derive_private_key(priv, ec.SECP224R1(), default_backend()).public_key().public_numbers().x
        priv_bytes = priv.to_bytes(28, 'big') if isV3 else int_to_bytes(priv, 28)
        adv_bytes = adv.to_bytes(28, 'big') if isV3 else int_to_bytes(adv, 28)

        priv_b64 = base64.b64encode(priv_bytes).decode("ascii")
        adv_b64 = base64.b64encode(adv_bytes).decode("ascii")
        s256_b64 = base64.b64encode(sha256(adv_bytes)).decode("ascii")
        
        if '/' in s256_b64[:7]:
            print('Key skipped and regenerated due to invalid character in hashed pubkey')
            continue
        else:
            i += 1
        
        MAC_ADDRESS = base64_to_modified_hex(adv_b64)
        key_info = {
            "prefix": prefix,
            "macaddress": MAC_ADDRESS,
            "Advertisement key": adv_b64,
            "hashedAdvertisementKey": s256_b64,
            "privateKey": priv_b64
        }
        new_keys_data.append(key_info)

        keyfile.write(base64.b64decode(adv_b64))
        if i < args.nkeys:
            additionalKeys.append(priv_b64)

        if args.verbose:
            print(f'{i})')
            print(f'Private key: {priv_b64}')
            print(f'Advertisement key: {adv_b64}')
            print(f'Hashed adv key: {s256_b64}')

        if '/' not in s256_b64[:7]:
            keys.write(f'Private key: {priv_b64}\n')
            keys.write(f'Advertisement key: {adv_b64}\n')
            keys.write(f'Hashed adv key: {s256_b64}\n')
            keysMap[priv_b64] = s256_b64
            if args.yaml:
                yaml.write(f'    - "{adv_b64}"\n')

    # Update keyMap.json within lock
    try:
        with file_lock:
            keyMap_path = os.path.join(current_directory, 'keyMap.json')
            if os.path.exists(keyMap_path):
                with open(keyMap_path, 'r') as km:
                    updated_keyMap_data = json.load(km)
            else:
                updated_keyMap_data = []
            
            updated_keyMap_data.extend(new_keys_data)
            
            with open(keyMap_path, 'w') as km:
                json.dump(updated_keyMap_data, km, indent=2)
    except Timeout:
        print("Timeout acquiring file lock! Retrying...")
        with file_lock:
            pass

    # Finalize outputs
    print('----------------------------------------------')
    addKeysS = ''
    if len(additionalKeys) > 0:
        addKeysS = "\"" + "\",\"".join(additionalKeys) + "\""

    devices.write(TEMPLATE.substitute(
        name=prefix,
        id=str(random.choice(range(0, 10000000))),
        privateKey=priv_b64,
        additionalKeys=addKeysS,
        keysMap=json.dumps(keysMap)
    ))
    devices.write(']')

def convert_mkeys():
    # Locate device JSON files
    json_files = [f for f in os.listdir(CONV_FOLDER) if f.endswith('_devices.json')]

    if not json_files:
        print(f"No device JSON files found in {CONV_FOLDER}")
        sys.exit(1)

    selected_file = None
    if args.prefix:
        prefix = args.prefix
        target_file = f"{prefix}_devices.json"
        if target_file in os.listdir(CONV_FOLDER):
            selected_file = target_file
        else:
            print(f"Specified file not found: {target_file}")
            sys.exit(1)
    else:
        if len(json_files) == 1:
            selected_file = json_files[0]
            prefix = selected_file.replace('_devices.json', '')
            print(f"Selected file: {selected_file}")
        else:
            print(f"Multiple files found, specify with --prefix:")
            for i, file in enumerate(json_files):
                print(f"{i+1}: {file}")
            sys.exit(1)

    # Process JSON file
    with open(os.path.join(CONV_FOLDER, selected_file), 'r') as f:
        device_data = json.load(f)

    if not device_data or not isinstance(device_data, list) or len(device_data) == 0:
        print("Invalid device file format")
        sys.exit(1)

    # Process all devices
    converted_devices = []
    for device in device_data:
        privateKey = device.get("privateKey", "")
        additionalKeys = device.get("additionalKeys", [])

        if not privateKey:
            print("Missing privateKey field")
            sys.exit(1)

        all_private_keys = []
        if additionalKeys and isinstance(additionalKeys, list):
            all_private_keys.extend(additionalKeys)
        all_private_keys.append(privateKey)

        keysMap = {}
        for priv_b64 in all_private_keys:
            try:
                priv_bytes = base64.b64decode(priv_b64)
                priv = int.from_bytes(priv_bytes, 'big')

                public_key = ec.derive_private_key(
                    priv, ec.SECP224R1(), default_backend()).public_key()
                adv = public_key.public_numbers().x
                adv_bytes = adv.to_bytes(28, 'big')

                s256_b64 = base64.b64encode(sha256(adv_bytes)).decode("ascii")
                keysMap[priv_b64] = s256_b64

            except Exception as e:
                print(f"Error processing private key: {str(e)}")
                continue

        device["keysMap"] = keysMap
        converted_devices.append(device)

    # Save converted data
    new_filename = f"{prefix}_converted_devices.json"
    with open(os.path.join(CONV_FOLDER, new_filename), 'w') as f:
        json.dump(converted_devices, f, indent=2)

    print(f"Conversion complete: {os.path.join(CONV_FOLDER, new_filename)}")

def base64_to_modified_hex(base64_str):
    try:
        decoded_data = base64.b64decode(base64_str)
    except binascii.Error:
        raise ValueError("Invalid Base64 input")

    hex_str = binascii.hexlify(decoded_data).decode('utf-8').upper()
    hex_12 = hex_str[:12].ljust(12, '0')
    first_byte_hex = hex_12[:2]
    rest_hex = hex_12[2:]
    
    first_byte_dec = int(first_byte_hex, 16)
    modified_byte_dec = first_byte_dec | 0xC0
    modified_byte_hex = format(modified_byte_dec, '02X')

    result = modified_byte_hex + rest_hex
    return result

if MODE == "generate":
    for i in range(args.nitems):
        print(f"Generating item {i+1}/{args.nitems} with {args.nkeys} keys...")
        if not args.yaml:
            args.prefix = None
        generate_mkeys()
elif MODE == "convert":
    convert_mkeys()

