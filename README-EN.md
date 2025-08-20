# NinjiaTag

## DIY Your Own AirTag

### DIY Your Own AirTag (Long-Term Record)

DIY Find My Network-Compatible Tracking Tags/Devices (Long-Term Record)

> "NinjiaTag" is not a misspelling but our redefinition of IoT product value: It serves not only as an agile anti-loss tool (Ninja) but also embodies our vision for next-gen distributed IoT technology—a new solution for decentralized Bluetooth tags (Tag). The 'jia' in the name signifies 'collaborative home,' inviting you to co-build this ecosystem!

**Server-side operation**: The Find My network backend fetches location data and stores it in a database. **No need** to deploy a Mac/VM or use an iPhone with the Find My app to view historical locations. (Note: An iPhone is temporarily required during Apple ID registration.)

### Current Features:

- [x] Server backend runs `request_report` to fetch locations, periodically downloads data to local database (unlimited storage duration vs. 7-day limit in mainstream products).
- [x] Query and display item trajectories for any timeframe with GPS coordinates and timestamps; supports zoomable maps.
- [x] Heatmap (Hotspot) visualization showing location frequency (darker = more visits).
- [x] Web frontend for key management.
- [x] Uses open-source Mapbox-GL 3D engine with terrain rendering.
- [x] Support export tracks to GPX

### README-EN.md

!asset/UI1.png

## Table of Contents

1. #hardware-diy
2. #prerequisites
3. #hardware-setup
4. #server-installation-deployment
5. #frontend-interface
6. #based-on-open-source-projects
7. #disclaimer

---

## Hardware DIY

Hardware DIY requires technical skill.

**Pre-built Guides**:

- ./usr_guide/2032_TAG.md
- ./usr_guide/Mini_TAG.md

## Prerequisites

- **Linux Server**: For Docker and Python scripts.
- **Apple ID**:

  - Must be registered on a physical iOS device with SMS-based 2FA enabled.
  - Use a dedicated ID (not your primary Apple ID).
  - _Critical_: The ID must have accessed iCloud storage (free 5GB) via an Apple device. Web-only registrations lack permissions.

- **Bluetooth Tag Hardware**:
  - Supported: nRF5x modules, ST17H66 modules (low-cost options).
  - Custom PCBs using these chips are feasible.

## Hardware Setup

1. **Download Firmware & Flashing Tools**:

   - ST17H66: Get `FindMy.hex` and `flash_st17h66.py` from https://github.com/biemster/FindMy/tree/main/Lenze_ST17H66.
   - nRF5x: Download `nrf51_firmware.bin`/`nrf52_firmware.bin` from https://github.com/acalatrava/openhaystack-firmware/releases.
   - _Experimental_: TLSR825X chips (e.g., Xiaomi Mijia Hygrometer 2) via https://github.com/biemster/FindMy/blob/main/Telink_TLSR825X/README.md.

2. **Generate Keys**:  
   Run in the `keygen` directory:

   ```bash
   pip3 install cryptography filelock  # Install dependencies first
   python3 generate_keys.py
   ```

   - Use `-n` to specify key count (e.g., `-n 50` for rolling keys).
   - _Rolling keys improve location update frequency but increase power usage_.

3. **Flash Hardware**:
   - flash_guide/nrf5x.md
   - flash_guide/ST17H66.md

---

## Server Installation & Deployment

### 1. Create a Docker Network

```bash
docker network create mh-network
```

### 2. Run https://github.com/Dadoum/anisette-v3-server

```bash
docker run -d --restart always --name anisette -p 6969:6969 \
--volume anisette-v3_data:/home/Alcoholic/.config/anisette-v3/ \
--network mh-network dadoum/anisette-v3-server
```

**Troubleshooting**: If Docker image pull fails in China, configure mirrors in `/etc/docker/daemon.json`:

```json
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://hub.1panel.dev",
    "https://docker.itelyou.cf"
  ]
}
```

Restart Docker: `systemctl restart docker`.

### 3. Clone the Project

```bash
git clone https://github.com/your-repo/NinjiaTag.git
```

### 4. Place Server Keys

Copy `.key` files from hardware setup into the project’s `/keys` folder.

### 5. Install Python Libraries

```bash
pip3 install aiohttp requests cryptography pycryptodome srp pbkdf2 \
-i https://pypi.tuna.tsinghua.edu.cn/simple
```

**Optional**: Use a virtual environment:

```bash
python3 -m venv ./venv/
./venv/bin/pip3 install aiohttp requests cryptography pycryptodome srp pbkdf2 \
-i https://pypi.tuna.tsinghua.edu.cn/simple
```

Test: `./venv/bin/python3 request_reports.py` (enter Apple ID and 2FA code).

**IP Ban Check**: If `gsa_authenticate` fails, verify with:

```bash
curl -k https://gsa.apple.com/grandslam/GsService2 -v
```

If output shows `503 Service Temporarily Unavailable`, change your server IP.

### 6. Install Node.js

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
\. "$HOME/.nvm/nvm.sh"
nvm install 22
node -v  # Verify v22.17.1
npm -v   # Verify v10.9.2
cd /path/to/project
npm i
```

**Edit `request_reports.mjs`**: If using a virtual env, replace `python3 request_reports.py` with `./venv/bin/python3 request_reports.py`.

### 7. Run Services via PM2

```bash
npm install pm2 -g
pm2 start server.mjs --name "query-server" --watch
pm2 start request_reports.mjs --name "report-task" --watch
pm2 save
pm2 startup systemd  # Auto-start on boot
sudo env PATH=$PATH:/home/user/.nvm/versions/node/v22.17.1/bin /home/user/.nvm/versions/node/v22.17.1/lib/node_modules/pm2/bin/pm2 startup systemd -u user --hp /home/user
```

**PM2 Commands**:

- `pm2 list` : View processes
- `pm2 logs <name>` : Check logs
- `pm2 restart <name>` : Reload

### 8. Public Server Access

The frontend accesses the server at `http://<server_ip>:3000`. For public access:

- **Port forwarding** on your router.
- **Reverse proxies**: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/, https://ngrok.com/, or https://www.zeronews.cc/.

---

## Frontend Interface

Deploy your own or use our hosted version:

- HTTP: http://bd8cca.atomgit.net/NinjiaTagPage/
- HTTPS: https://bd8cca.atomgit.net/NinjiaTagPage/ (requires HTTPS backend).

Source: https://atomgit.com/bd8cca/NinjiaTagPage (Vue3 + Mapbox-GL).

### Usage

1. In the frontend, set the **server URL** to `http(s)://<your_server>:3000/query`.
2. Import hardware-generated `.json` keys via the **Item Management** dialog.
3. Query data by item/timeframe:
   - **Track Points**: Historical GPS points (hover for details).
   - **Heatmap**: Location frequency visualization.
   - **Latest Location**: Most recent position (icon-based).  
     _Note_: Walk through crowded areas to trigger location updates if no data appears.

---

## Based on Open-Source Projects

- Core Find My logic: https://github.com/seemoo-lab/openhaystack/
- Server infrastructure: https://github.com/JJTech0130/pypush by @JJTech0130
- Android client: https://gitee.com/lovelyelfpop/macless-haystack by @lovelyelfpop

## To-Do: Convert Data to KML

_KML (Keyhole Markup Language) enables geographic data visualization in tools like Google Earth._

```bash
./request_reports.py > input.txt  # Export raw data
python3 make_kml.py              # Generates KML per key
```

---

## Disclaimer

> This repository is intended **for research purposes only**. You are solely responsible for complying with local laws. By using any code/files herein, you agree to:
>
> - Use this project **exclusively for item recovery**.
> - **Strictly prohibit** illegal activities (e.g., unauthorized tracking).
> - Accept all risks voluntarily.
