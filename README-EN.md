# NinjiaTag  
## DIY Your Own Airtag  
DIY FindMy Network-Compatible Tracking Tag/Device (Long-Term Logging)  
The server-side runs a FindMy network backend to fetch location data and store it in a database. No need to deploy a Mac or virtual machine, nor require an iPhone with the Find My app to view the location and trajectory of your DIY tracking tag/device for any time period (borrow someone else's iPhone temporarily when registering the Apple ID).  

**Current Features:**  
- [x] Server backend runs `request_report` to fetch locations, regularly downloads location data, and stores it in a local server database with **unlimited storage time** (mainstream products typically retain logs for ≤7 days). Trajectories are permanently saved on the server.  
- [x] Supports querying and displaying trajectories of any item for any time period. Shows latitude/longitude and timestamps for each point, with zoomable maps for easy historical review.  
- [x] Supports **heatmap display** (Hotspot), similar to GIS crowd density visualization: frequently visited areas appear darker, while rare locations are lighter.  
- [x] Web frontend supports key management.  
- [x] Uses the open-source **Mapbox-GL 3D engine** for terrain rendering and enhanced aesthetics.  

**Pending Tests:**  
- [ ] Query Apple's Find My network, write to SQLite database, convert tracks to KML/GPX formats.  

---

## Hardware DIY  
Hardware DIY requires technical expertise.  I occasionally list finished products, but **self-hosting the server is recommended** due to my limited bandwidth.  

### Prerequisites:  
- A **Linux server** (any distribution) to run Docker and Python scripts.  
- An **Apple ID** with **SMS-based 2FA (Two-Factor Authentication)** enabled, registered via a physical iOS device.  
  - Use a **new Apple ID** for testing, not your primary one.  
  - If no Apple device is available, borrow a friend’s iPhone/iPad/Mac to register.  
  - **Critical**: The account must have been logged into iCloud (to activate free 5GB storage). Web-only registrations lack sufficient permissions.  

- A **Bluetooth tag device**, currently supporting:  
  - nRF5x Bluetooth modules  
  - ST17H66 Bluetooth modules  
  - *(Future support planned for low-cost domestic Bluetooth chips)*  
  - Minimal PCB design required; self-soldering is possible.  

---

## Hardware Setup  

### 1. Download Firmware & Flashing Scripts  
  - **ST17H66 Chips**: Visit https://github.com/biemster/FindMy/tree/main/Lenze_ST17H66 to download firmware (`FindMy.hex`) and flashing script (`flash_st17h66.py`).  
  - **nRF5x Chips**: Visit https://github.com/acalatrava/openhaystack-firmware/releases to download firmware (`nrf51_firmware.bin` or `nrf52_firmware.bin`).  
  - *Experimental*: https://github.com/biemster/FindMy/blob/main/Telink_TLSR825X/README.md (e.g., Xiaomi Temperature/Humidity Sensor 2, model LYWSD03MMC).  

### 2. Generate Key Pairs  
  - Run `python3 generate_keys.py` in the `keygen` directory (requires `cryptography`; install via `pip3 install cryptography`).  
    - Works on Windows/Linux.  
  - **Multi-Key Support**: Use `python3 generate_keys.py -n 50` to generate 50 keys.  
    - **Why?** Tags with key rotation update locations more frequently (like AirTag), improving accuracy. Default is single-key.  
    - *Trade-off*: Key rotation increases power consumption slightly.  

### 3. Flash Firmware to Device  
  - Follow the flash_guide/nrf5x.md.  

---

## Server Deployment  

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
  - **For China Users**: Add registry mirrors to `/etc/docker/daemon.json`:  
    ```json
    {
      "registry-mirrors": [
        "https://docker.1ms.run",
        "https://hub.1panel.dev",
        "https://docker.itelyou.cf",
        "http://mirrors.ustc.edu.cn",
        "http://mirror.azure.cn"
      ]
    }
    ```  
    Restart Docker:  
    ```bash
    systemctl restart docker  # or service docker restart
    ```  
    Verify with `docker info`.  

### 3. Download This Project  
  Clone via Git or download the ZIP.  

### 4. Place Server Keys  
  Copy the `.key` files (generated in *Hardware Setup*) to the `/key` directory.  

### 5. Install Python Dependencies  
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
  Run the script:  
  ```bash
  ./venv/bin/python3 request_reports.py  # or python3 request_reports.py
  ```  
  - Enter Apple ID credentials and 2FA code when prompted.  

### 6. Install Node.js  
  ```bash
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
  . "$HOME/.nvm/nvm.sh"
  nvm install 22
  node -v  # Verify: v22.17.1
  npm -v   # Verify: 10.9.2
  npm i
  ```  

### 7. Run Services with PM2  
  Install PM2 globally:  
  ```bash
  npm install pm2 -g
  ```  
  Start services:  
  ```bash
  pm2 start server.mjs --name "query-server" --watch
  pm2 start request_reports.mjs --name "report-task" --watch
  pm2 save
  sudo pm2 startup systemd  # Auto-start on boot (Linux)
  ```  
  **Common PM2 Commands**:  
  ```bash
  pm2 list          # View processes
  pm2 logs <name>   # Check logs
  pm2 stop <name>   # Stop a process
  ```  

### 8. Expose Server to the Internet  
  Access the query service at `http://<server_ip>:3000`. For public access:  
  - Use **port forwarding** (router) + **DDNS** (if you have a public IP).  
  - Use **reverse proxies**: https://ngrok.com/, https://iepose.com/, https://www.zeronews.cc/ (free tiers), or https://console.hsk.oray.com/ (¥9.9/month).  
  - *Advanced*: https://www.zerotier.com//https://tailscale.com/ for secure tunnels.  

---

## Frontend Configuration  
Deploy your own or use my hosted page: https://bd8cca.atomgit.net/NinjiaTagPage/.  
Source code: https://atomgit.com/bd8cca/NinjiaTagPage (Vue3 + Mapbox-GL).  

### Usage  
1. In the frontend, configure the server URL (e.g., `http://your_server_ip:3000`).  
2. Import the `.json` key file (from `generate_keys.py`) via the **Item Management** dialog.  
3. Query data:  
   - **Trajectory Points**: Historical points with details on hover/click.  
   - **Heatmap**: Density visualization (darker = more visits).  
   - **Latest Location**: Most recent position as an icon.  
   - *Tip*: If no data appears, carry the tag to crowded areas and wait for server sync.  

---

## Credits & Open-Source Projects  
- FindMy functionality builds on https://github.com/seemoo-lab/openhaystack/.  
- Server deployment simplified by https://github.com/JJTech0130/pypush (no Mac required).  
- Android app alternative: https://gitee.com/lovelyelfpop/macless-haystack.  

---

## Miscellaneous (Pending)  
### Convert Data to KML  
*KML (Keyhole Markup Language) is used in Earth browsers like Google Earth.*  
```bash
./request_reports.py > input.txt      # Generate JSON data
python3 make_kml.py                   # Converts input.txt to KML files per key
```  

---

## Disclaimer  
> This repository is for research purposes only. You are responsible for complying with local laws.  
> I am not liable for any misuse. By using these files, you agree to assume all risks.  
> **Use strictly for anti-loss of personal property. Illegal tracking is prohibited.**  

---