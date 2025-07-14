#!/usr/bin/env python3
import os
import glob
import datetime
import argparse
import base64
import json
import hashlib
import struct
import asyncio  # 新增 asyncio
import aiohttp  # 替换 requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import sqlite3
from pypush_gsa_icloud import icloud_login_mobileme, generate_anisette_headers


def sha256(data):
    digest = hashlib.new("sha256")
    digest.update(data)
    return digest.digest()


def decrypt(enc_data, algorithm_dkey, mode):
    decryptor = Cipher(algorithm_dkey, mode, default_backend()).decryptor()
    return decryptor.update(enc_data) + decryptor.finalize()


def decode_tag(data):
    latitude = struct.unpack(">i", data[0:4])[0] / 10000000.0
    longitude = struct.unpack(">i", data[4:8])[0] / 10000000.0
    confidence = int.from_bytes(data[8:9], 'big')
    status = int.from_bytes(data[9:10], 'big')
    return {'lat': latitude, 'lon': longitude, 'conf': confidence, 'status': status}


def getAuth(regenerate=False, second_factor='sms'):
    CONFIG_PATH = os.path.dirname(os.path.realpath(__file__)) + "/auth.json"
    if os.path.exists(CONFIG_PATH) and not regenerate:
        with open(CONFIG_PATH, "r") as f:
            j = json.load(f)
    else:
        mobileme = icloud_login_mobileme(second_factor=second_factor)
        j = {'dsid': mobileme['dsid'], 'searchPartyToken': mobileme['delegates']
             ['com.apple.mobileme']['service-data']['tokens']['searchPartyToken']}
        with open(CONFIG_PATH, "w") as f:
            json.dump(j, f)
    return (j['dsid'], j['searchPartyToken'])


async def fetch_report(session, semaphore, id, auth, headers, startdate, unixEpoch):
    """异步获取单个ID的报告"""
    data = {
        "search": [{
            "startDate": startdate * 1000,
            "endDate": unixEpoch * 1000,
            "ids": [id]  # 每次只请求一个ID
        }]
    }

    async with semaphore:  # 信号量控制并发数
        try:
            async with session.post(
                "https://gateway.icloud.com/acsnservice/fetch",
                auth=auth,
                headers=headers,
                json=data
            ) as response:
                if response.status == 200:
                    res_data = await response.json()
                    results = res_data['results']
                    print("Request ID:", data["search"][0]["ids"])
                    print(f'{response.status}: {len(results)} reports received.')
                    return res_data.get('results', [])
                else:
                    print(f"Error {response.status} for ID {id}")
                    return []
        except Exception as e:
            print(f"Exception for ID {id}: {str(e)}")
            return []


async def main_async(args, privkeys, names):
    """异步主函数"""
    # 初始化数据库
    db_path = os.path.dirname(os.path.realpath(__file__)) + '/reports.db'
    sq3db = sqlite3.connect(db_path)
    sq3 = sq3db.cursor()

    # 获取认证信息
    dsid, searchPartyToken = getAuth(
        regenerate=args.regen,
        second_factor='trusted_device' if args.trusteddevice else 'sms'
    )
    auth = aiohttp.BasicAuth(dsid, searchPartyToken)
    headers = generate_anisette_headers()

    # 计算时间范围
    unixEpoch = int(datetime.datetime.now().timestamp())
    startdate = unixEpoch - (60 * 60 * args.hours)

    # 设置信号量（并发数=4）
    semaphore = asyncio.Semaphore(1000)
    ordered = []
    found = set()

    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_report(session, semaphore, id, auth,
                         headers, startdate, unixEpoch)
            for id in names.keys()
        ]
        results = await asyncio.gather(*tasks)

    # 合并所有报告
    all_reports = [report for sublist in results for report in sublist]
    print(f'Total: {len(all_reports)} reports received.')
    """ for report in all_reports: print(report) """

    # 处理报告
    for report in all_reports:
        if report['id'] not in privkeys:
            continue

        priv = int.from_bytes(base64.b64decode(privkeys[report['id']]), 'big')
        data = base64.b64decode(report['payload'])
        if len(data) > 88:
            data = data[:4] + data[5:]

        # 解密处理（保持原逻辑）
        timestamp = int.from_bytes(data[0:4], 'big') + 978307200
        """ sq3.execute(f"INSERT OR REPLACE INTO reports VALUES ('{names[report['id']]}', {timestamp}, {report['datePublished']}, '{report['payload']}', '{report['id']}', {report['statusCode']})") """

        """ print("t,s:",timestamp,startdate) """

        if timestamp >= startdate:
            eph_key = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP224R1(), data[5:62])
            shared_key = ec.derive_private_key(
                priv, ec.SECP224R1(), default_backend()).exchange(ec.ECDH(), eph_key)
            symmetric_key = sha256(
                shared_key + b'\x00\x00\x00\x01' + data[5:62])
            decryption_key = symmetric_key[:16]
            iv = symmetric_key[16:]
            enc_data = data[62:72]
            tag = data[72:]

            decrypted = decrypt(enc_data, algorithms.AES(
                decryption_key), modes.GCM(iv, tag))
            tag = decode_tag(decrypted)
            tag['timestamp'] = timestamp
            tag['isodatetime'] = datetime.datetime.fromtimestamp(
                timestamp).isoformat()
            tag['key'] = names[report['id']]
            tag['goog'] = 'https://maps.google.com/maps?q=' + \
                str(tag['lat']) + ',' + str(tag['lon'])
            found.add(tag['key'])
            ordered.append(tag)
            sq3.execute(
                f"INSERT OR REPLACE INTO reports_detail VALUES ('{names[report['id']]}', {timestamp},'{tag['isodatetime']}', {report['datePublished']}, {tag['lat']}, {tag['lon']},'{report['payload']}', '{report['id']}',{tag['status']},{report['statusCode']})")

    # 输出结果
    print(f'{len(ordered)} reports processed.')
    ordered.sort(key=lambda item: item.get('timestamp'))
    for rep in ordered:
        print(rep)
    print(f'Found:   {list(found)}')
    print(f'Missing: {[key for key in names.values() if key not in found]}')

    # 关闭数据库
    sq3.close()
    sq3db.commit()
    sq3db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-H', '--hours', help='only show reports not older than these hours', type=int, default=24)
    parser.add_argument(
        '-p', '--prefix', help='only use keyfiles starting with this prefix', default='')
    parser.add_argument(
        '-r', '--regen', help='regenerate search-party-token', action='store_true')
    parser.add_argument('-t', '--trusteddevice',
                        help='use trusted device for 2FA instead of SMS', action='store_true')
    args = parser.parse_args()

    # Connect to the database
    db_path = os.path.dirname(os.path.realpath(__file__)) + '/reports.db'
    sq3db = sqlite3.connect(db_path)
    sq3 = sq3db.cursor()

    # Create keyMap table if not exists
    sq3.execute('''CREATE TABLE IF NOT EXISTS keyMap (
                    name TEXT,
                    private_key TEXT,
                    advertisement_key TEXT,
                    hashed_adv_key TEXT,
                    PRIMARY KEY (name, hashed_adv_key)
                )''')
    sq3db.commit()

    # Read key files and store keys in dictionaries/database
    privkeys = {}
    names = {}
    for keyfile in glob.glob(os.path.dirname(os.path.realpath(__file__)) + '/keys/' + args.prefix + '*.keys'):
        with open(keyfile) as f:
            name = os.path.basename(keyfile)[len(args.prefix):-5]
            current_priv = None
            current_hashed_adv = None
            current_adv = None
            isempty = True

            for line in f:
                key = line.rstrip('\n').split(': ')
                if key[0] == 'Private key':
                    current_priv = key[1]
                elif key[0] == 'Advertisement key':
                    current_adv = key[1]
                elif key[0] == 'Hashed adv key':
                    current_hashed_adv = key[1]

                # When we have a complete key set, store it
                if current_priv and current_adv and current_hashed_adv:
                    # Insert or replace in database
                    sq3.execute("INSERT OR REPLACE INTO keyMap VALUES (?, ?, ?, ?)",
                                (name, current_priv, current_adv, current_hashed_adv))

                    # Add to dictionaries
                    privkeys[current_hashed_adv] = current_priv
                    names[current_hashed_adv] = name

                    # Reset for next key pair
                    current_priv = current_adv = current_hashed_adv = None
                    if isempty:
                        isempty = False

            # If we didn't find any key pairs in this file
            if isempty is True:
                print(f"Couldn't find valid key pair in {keyfile}")

    sq3db.commit()
    sq3.close()
    sq3db.close()

    # 运行异步主函数
    asyncio.run(main_async(args, privkeys, names))
