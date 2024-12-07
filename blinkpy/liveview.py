import subprocess
import threading
from time import sleep, time
import requests
import socket
import ssl

BASE_API_URL = "https://rest-e002.immedia-semi.com"

## REPLACE THESE WITH YOUR OWN VALUES
BLINK_TOKEN = "lVAR-lD5DyqiEkcgwBGOgw"
ACCOUNT_ID = 512141
NETWORK_ID = 669977
CAMERA_ID = 605820


def get_liveview():
    headers = {
        'app-build': 'ANDROID_28799573',
        'user-agent': '37.0ANDROID_28799573',
        # 'locale': 'en_US',
        # 'x-blink-time-zone': 'America/New_York',
        'token-auth': BLINK_TOKEN,
        'content-type': 'application/json; charset=UTF-8',
    }

    json_data = {
        'intent': 'liveview',
    }

    response = requests.post(
        f'{BASE_API_URL}/api/v3/accounts/{ACCOUNT_ID}/networks/{NETWORK_ID}/owls/{CAMERA_ID}/liveview',
        headers=headers,
        json=json_data,
    )

    print(f'Get LiveView Response: {response.text}')

    return response.json()

def poll(network_id, command_id, interval):
    headers = {
        'app-build': 'ANDROID_28799573',
        'user-agent': '37.0ANDROID_28799573',
        'locale': 'en_US',
        'x-blink-time-zone': 'America/New_York',
        'token-auth': BLINK_TOKEN,
        'content-type': 'application/json; charset=UTF-8',
    }
        
    while True:
        response = requests.get(
            f'{BASE_API_URL}/network/{network_id}/command/{command_id}',
            headers=headers,
        )

        print(f"Command Response: {response.text}")
        sleep(interval)
        


liveview = get_liveview()

immis = liveview["server"]

host = immis.split('/')[2].split(':')[0]
conn_id = immis.split('/')[-1].split('_')[0]
client_id = int(immis.split('?client_id=')[1])

print(f"{immis=}")
print(f"{conn_id=}")
print(f"{client_id=}")

context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

with socket.create_connection((host, 443)) as sock:
    command_poll = threading.Thread(target=poll, args=(NETWORK_ID, liveview["command_id"], liveview["polling_interval"]))
    command_poll.start()

    conn_header = bytes([
        0x00, 0x00, 0x00, 0x28, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00] + list(client_id.to_bytes(4)) + [0x01, 0x08, 0x00, 0x00, 
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
        0x00, 0x00, 0x00, 0x00, 0x00, 0x10] + list(bytes(conn_id, 'ASCII')) + [0x00, 0x00, 0x00, 0x01, 0x0a, 0x00, 0x00, 0x00, 0x00, 0x00, 
        0x00, 0x00, 0x00,
    ])

    keep_alive = bytes([
        0x12, 0x00, 0x00, 0x03, 0xe8, 0x00, 0x00, 0x00, 0x18, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00,
        0x00,
    ])

    with context.wrap_socket(sock, server_hostname=host) as ssock:
        start = time()
        ssock.send(conn_header)

        ffplay_process = subprocess.Popen(
            ['ffplay', '-f', 'mpegts', '-err_detect', 'ignore_err', '-'], 
            stdin=subprocess.PIPE
        )

        try:
            data = ssock.recv(64)
            while data:
                ffplay_process.stdin.write(data)
                data = ssock.recv(64)
                if time() - start > 1:
                    ssock.send(keep_alive)
                    start = time()
        except KeyboardInterrupt:
            ffplay_process.kill()
            exit()