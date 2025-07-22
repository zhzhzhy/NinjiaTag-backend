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
import base64
import binascii
import uuid

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
parser.add_argument(
    '-n', '--nkeys', help='number of keys to generate', type=int, default=1)
parser.add_argument(
    '-i', '--nitems', help='number of items to generate', type=int, default=1)
parser.add_argument('-p', '--prefix', help='prefix of the keyfiles')
parser.add_argument(
    '-y', '--yaml', help='yaml file where to write the list of generated keys')
parser.add_argument(
    '-v', '--verbose', help='print keys as they are generated', action="store_true")
parser.add_argument(
    '-conv', '--convert', action='store_true')


args = parser.parse_args()

MAX_KEYS = 2000
MAX_ITEMS = 1000
MODE = "generate"

if (args.convert):
    MODE = "convert"


if args.nkeys < 1 or args.nkeys > MAX_KEYS:
    raise argparse.ArgumentTypeError(
        "Number of keys out of range (between 1 and " + str(MAX_KEYS) + ")")

if args.nitems < 1 or args.nitems > MAX_ITEMS:
    raise argparse.ArgumentTypeError(
        "Number of items out of range (between 1 and " + str(MAX_ITEMS) + ")")

current_directory = os.getcwd()


prefix = ''


def random_prefix():
    if args.prefix is None:
        # 使用UUID生成8位十六进制大写字符串作为前缀
        prefix = uuid.uuid4().hex.upper()
    else:
        prefix = args.prefix
    return prefix


def generate_mkeys():
    while True:
        prefix = random_prefix()
        PREFIX_FOLDER = prefix+'/'
        if not os.path.exists(PREFIX_FOLDER):
            break

     # 创建keyMap.json文件路径（在当前目录）
    keyMap_path = os.path.join(current_directory, 'keyMap.json')

    # 如果keyMap.json文件不存在，则创建并写入空列表
    if not os.path.exists(keyMap_path):
        with open(keyMap_path, 'w') as km:
            json.dump([], km)

    # 读取现有keyMap数据
    with open(keyMap_path, 'r') as km:
        keyMap_data = json.load(km)

    if args.yaml:
        yaml = open(PREFIX_FOLDER + prefix + '_' + args.yaml + '.yaml', 'w')
        yaml.write('  keys:\n')
    if MODE == "generate":
        if os.path.exists(PREFIX_FOLDER):
            shutil.rmtree(PREFIX_FOLDER)
        final_directory = os.path.join(current_directory, PREFIX_FOLDER)
        os.mkdir(final_directory)
        keyfile = open(PREFIX_FOLDER + prefix + '_keyfile', 'wb')

        if (args.nkeys > 255):
            keyfile.write(struct.pack("I", args.nkeys))
            print("Using INT(4 byte) key count in keyfile header!")
        elif (args.nkeys <= 255):
            keyfile.write(struct.pack("B", args.nkeys))
            print("Using BYTE(1 byte) key count in keyfile header!")

        devices = open(PREFIX_FOLDER + prefix + '_devices.json', 'w')
        devices.write('[\n')

        fname = '%s.keys' % (prefix)
        keys = open(PREFIX_FOLDER + fname, 'w')

        isV3 = sys.version_info.major > 2
        print('Using python3' if isV3 else 'Using python2')
        print(f'Output will be written to {PREFIX_FOLDER}')
        additionalKeys = []
        keysMap = {}
        i = 0

        while i < args.nkeys:
            priv = random.getrandbits(224)
            print("priv", priv)
            adv = ec.derive_private_key(priv, ec.SECP224R1(
            ), default_backend()).public_key().public_numbers().x
            if isV3:
                priv_bytes = priv.to_bytes(28, 'big')
                adv_bytes = adv.to_bytes(28, 'big')
            else:
                priv_bytes = int_to_bytes(priv, 28)
                adv_bytes = int_to_bytes(adv, 28)

            priv_b64 = base64.b64encode(priv_bytes).decode("ascii")
            adv_b64 = base64.b64encode(adv_bytes).decode("ascii")
            s256_b64 = base64.b64encode(sha256(adv_bytes)).decode("ascii")

            MAC_ADDRESS = base64_to_modified_hex(adv_b64)

            # 创建当前密钥的信息字典
            key_info = {
                "prefix": prefix,
                "macaddress": MAC_ADDRESS,
                "Advertisement key": adv_b64,
                "hashedAdvertisementKey": s256_b64,
                "privateKey": priv_b64
            }

            # 添加到keyMap_data
            keyMap_data.append(key_info)

            # 写入更新后的keyMap_data到keyMap.json
            with open(keyMap_path, 'w') as km:
                json.dump(keyMap_data, km, indent=2)
            if '/' in s256_b64[:7]:
                print(
                    'Key skipped and regenerated, because there was a / in the b64 of the hashed pubkey :(')
                continue
            else:
                i += 1

            keyfile.write(base64.b64decode(adv_b64))

            if i < args.nkeys:
                # The last one is the leading one
                additionalKeys.append(priv_b64)

            if args.verbose:
                print('%d)' % (i + 1))
                print('Private key: %s' % priv_b64)
                print('Advertisement key: %s' % adv_b64)
                print('Hashed adv key: %s' % s256_b64)

            if '/' in s256_b64[:7]:
                print(
                    'no key file written, there was a / in the b64 of the hashed pubkey :(')
            else:
                keys.write('Private key: %s\n' % priv_b64)
                keys.write('Advertisement key: %s\n' % adv_b64)
                keys.write('Hashed adv key: %s\n' % s256_b64)
                keysMap[priv_b64] = s256_b64
                if args.yaml:
                    yaml.write('    - "%s"\n' % adv_b64)
        print('----------------------------------------------')
        addKeysS = ''
        if len(additionalKeys) > 0:
            addKeysS = "\"" + "\",\"".join(additionalKeys) + "\""

        devices.write(TEMPLATE.substitute(name=prefix,
                                          id=str(random.choice(
                                              range(0, 10000000))),
                                          privateKey=priv_b64,
                                          additionalKeys=addKeysS,
                                          keysMap=json.dumps(keysMap)
                                          ))

        devices.write(']')


def convert_mkeys():
    # 尝试查找目录下的设备JSON文件
    json_files = [f for f in os.listdir(
        CONV_FOLDER) if f.endswith('_devices.json')]

    if not json_files:
        print(f"找不到任何 *_devices.json 文件于 {CONV_FOLDER} 目录")
        sys.exit(1)

    selected_file = None
    if args.prefix:
        prefix = args.prefix
        target_file = f"{prefix}_devices.json"
        if target_file in os.listdir(CONV_FOLDER):
            selected_file = target_file
        else:
            print(f"找不到指定前缀的文件: {target_file}")
            sys.exit(1)
    else:
        if len(json_files) == 1:
            selected_file = json_files[0]
            prefix = selected_file.replace('_devices.json', '')
            print(f"自动选择文件: {selected_file}")
        else:
            print(f"找到多个设备文件，请使用--prefix参数指定:")
            for i, file in enumerate(json_files):
                print(f"{i+1}: {file}")
            sys.exit(1)

    # 读取JSON文件
    with open(os.path.join(CONV_FOLDER, selected_file), 'r') as f:
        device_data = json.load(f)

    if not device_data or not isinstance(device_data, list) or len(device_data) == 0:
        print("无效的设备文件格式")
        sys.exit(1)

    # 转换所有设备
    converted_devices = []
    for device in device_data:
        privateKey = device.get("privateKey", "")
        additionalKeys = device.get("additionalKeys", [])

        if not privateKey:
            print("缺失 privateKey 字段")
            sys.exit(1)

        # 收集所有私钥
        all_private_keys = []
        if additionalKeys and isinstance(additionalKeys, list):
            all_private_keys.extend(additionalKeys)
        all_private_keys.append(privateKey)

        # 重新计算keysMap
        keysMap = {}
        for priv_b64 in all_private_keys:
            try:
                # 解码Base64并转换为整数
                priv_bytes = base64.b64decode(priv_b64)
                priv = int.from_bytes(priv_bytes, 'big')

                # 生成公钥
                public_key = ec.derive_private_key(
                    priv, ec.SECP224R1(), default_backend()).public_key()
                adv = public_key.public_numbers().x
                adv_bytes = adv.to_bytes(28, 'big')

                # 计算哈希并更新keysMap
                s256_b64 = base64.b64encode(
                    sha256(adv_bytes)).decode("ascii")
                keysMap[priv_b64] = s256_b64

            except Exception as e:
                print(f"处理私钥时出错: {priv_b64[:10]}... {str(e)}")
                continue

        # 更新设备的keysMap
        device["keysMap"] = keysMap
        converted_devices.append(device)

    # 写入新文件
    new_filename = f"{prefix}_converted_devices.json"
    with open(os.path.join(CONV_FOLDER, new_filename), 'w') as f:
        json.dump(converted_devices, f, indent=2)

    print(f"已成功转换并保存到: {os.path.join(CONV_FOLDER, new_filename)}")


def base64_to_modified_hex(base64_str):
    # 解码Base64字符串为二进制数据
    try:
        decoded_data = base64.b64decode(base64_str)
    except binascii.Error:
        raise ValueError("无效的Base64输入")

    # 将二进制数据转换为十六进制字符串
    hex_str = binascii.hexlify(decoded_data).decode('utf-8').upper()

    # 取前12位并补足长度
    hex_12 = hex_str[:12].ljust(12, '0')

    # 处理第一个字节（前2位十六进制）
    first_byte_hex = hex_12[:2]
    rest_hex = hex_12[2:]

    # 将第一个字节转换为整数并修改前2位为11
    first_byte_dec = int(first_byte_hex, 16)
    modified_byte_dec = first_byte_dec | 0xC0  # 0xC0 = 11000000二进制

    # 转换回十六进制并格式化为2位
    modified_byte_hex = format(modified_byte_dec, '02X')

    # 组合最终结果
    result = modified_byte_hex + rest_hex
    return result


if MODE == "generate":
    for i in range(args.nitems):
        print(f"Generating item {i+1}/{args.nitems} with {args.nkeys} keys...")
        prefix = random_prefix()
        print(f"Using prefix: {prefix}")
        if args.yaml:
            args.prefix = prefix
        else:
            args.prefix = None
        if args.verbose:
            print(f"Verbose mode enabled, printing keys as they are generated.")
        else:
            print(f"Verbose mode disabled, keys will not be printed.")
        generate_mkeys()
elif MODE == "convert":
    convert_mkeys()
