# NinjiaTag(DIY你自己的airtag)
DIY 兼容 FindMy 网络的定位标签/设备（长期记录）
服务器端运行 FindMy 网络后台抓取位置数据并存入数据库，无需部署 Mac 电脑或虚拟机，也不需要拥有 iPhone 与其上面的查找 app 即可查看回溯任意时间段内您 DIY 的定位标签/设备的位置、轨迹（注册 Apple-ID 时需要借用一下别人的 iPhone）。
目前实现的功能：
- 服务器端后台运行 request_report 获取位置，定期下载位置数据并储存在本地服务器数据库，储存时间不限（目前市面上主流产品记录时长最多为 7 天），轨迹可永久保存于服务器。
-支持任意时间段任意物品轨迹查询和显示，支持轨迹点的经纬度和时间点显示，可随意缩放查看，方便回溯。
-支持热图显示（ Hotspot ），类似地理信息系统的人流密度显示，经常去过的地方颜色更深，不去或偶尔去的地方颜色浅。
-Web 前端支持密钥管理
-地图采用开源的 Mapbox-GL 三维地图引擎，支持三维地形显示，渲染更加美观。

- Query Apple's Find My network,write into sqlite database,
convert to tracks(KML/GPX etc.)
## 硬件DIY
硬件DIY需要一定门槛，如果你不想自己动手，可以咸鱼搜索 “自制Airtag”（用户名 Dijkstra很贪心 ），我会不定时上架一些成品，但建议你自己搭建服务，我提供的服务器带宽有限。

## 准备条件：
- 一台Linux 服务器（任意Linux）。用来运行 Docker 服务和 Python 脚本。
- 需要一个使用实体IOS设备注册的，已启用 2FA (双重认证)的 Apple-ID。
建议不要使用个人常用的 Apple ID，而是注册一个新的 Apple ID 用于实验目的。 没有 Apple ID 的 可以找朋友借用一下苹果设备（iPad、Macbook、iPhone），注册一个。仅支持短信方式作为双重认证！如果有苹果设备登录着该 Apple ID，最好退出，否则有可能收不到短信验证码。
您需要在苹果设备上登录过该帐户才可以（获得了 iCloud 的 5G 免费空间才是有效的 Apple ID）。仅在 iCloud 网页上注册的 Apple ID 权限不足。
Only a free Apple ID is required, with SMS 2FA properly setup. If you don't have any, follow one of the many guides found on the internet.
- 一个蓝牙标签设备，目前支持nRF5x 蓝牙模块，ST17H66蓝牙模块，后续会支持更多低成本国产蓝牙模块
只需要最小系统模块，所以也可以购买nRF5x ST17H66芯片自己进行PCB打样。


## 硬件设置

1. 下载刷机固件和刷机脚本
   - ST17H66 芯片前往 [Lenze_ST17H66](https://github.com/biemster/FindMy/tree/main/Lenze_ST17H66) 下载所需固件(FindMy.hex)和刷机脚本(flash_st17h66.py)  
   - nRF5x 前往 [openhaystack-firmware](https://github.com/acalatrava/openhaystack-firmware/releases) 下载所需固件(nrf51_firmware.bin或nrf52_firmware.bin) 
   - [TLSR825X 芯片](https://github.com/biemster/FindMy/blob/main/Telink_TLSR825X/README.md)，比如米家温湿度计2(型号 LYWSD03MMC)也可以刷机成定位标签，但我没有尝试

2. 执行本仓库的 `python3 generate_keys.py` 来生成密钥对(在 `keys/` 目录下)。(注意: 必须安装依赖 `cryptography`. 用 `pip3 install cryptography` 命令安装)
   Windows 或 Linux 下都可以执行。

3. 将固件刷入设备
   这里说一下，`generate_keys.py` 可以指定参数 `python3  generate_keys.py -n 50` 来生成包含多个密钥的 keyfile，其中 50 就是个数，可以自己改。不指定则默认单个密钥，也就是定位标签运行过程中只有一个蓝牙 Mac 地址（密钥其实就是加密了的 Mac 地址），而多密钥就是定位标签可以定时更换 Mac 地址(称为滚动密钥，苹果 AirTag 就是这样)。
   
   经过测试，带密钥轮换机制的标签，其位置会被更频繁的上报，即位置更新更频繁，更能被精确定位。推荐使用多密钥的 keyfile。但是，密钥轮换会增加一定功耗。
## 服务端安装部署
### 1. 创建一个 docker 网络

在终端中执行以下命令，创建一个新的docker网络
```bash
docker network create mh-network
```

### 2. 运行 [Anisette Server](https://github.com/Dadoum/anisette-v3-server)

```bash
docker run -d --restart always --name anisette -p 6969:6969 --volume anisette-v3_data:/home/Alcoholic/.config/anisette-v3/ --network mh-network dadoum/anisette-v3-server
```
注意：首次执行该命令会自动从 docker 官方仓库拉取镜像，因国内网络环境的原因，需要设置镜像仓库。如下修改 docker 的配置文件`/etc/docker/daemon.json`（不存在就新建），增加 `registry-mirrors`：
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
之后运行如下命令重启 docker 服务：
```bash
systemctl restart docker
# 或者
service docker restart
```

此时，镜像源应该生效了。可以用 `docker info` 命令验证，如果输出末尾有如下`Registry Mirrors`，说明镜像源配置成功了：
```
Registry Mirrors:
  https://docker.1ms.run/
  https://hub.1panel.dev/
  https://docker.itelyou.cf/
  ......
  
 ###  3. 下载本项目到本地
 使用git clone 或下载zip解压
 ### 4.安装python3相关库
安装 python3，在python3 venv环境执行python3 request_reports.py

开始时会提示输入Apple ID和密码，然后是2FA短信验证，完成后能正常执行位置数据拉取。
# 安装nodejs
执行以下命令安装nodejs和npm用于提供后端服务
```
# Download and install nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
# in lieu of restarting the shell
\. "$HOME/.nvm/nvm.sh"
# Download and install Node.js:
nvm install 22
# Verify the Node.js version:
node -v # Should print "v22.17.1".
nvm current # Should print "v22.17.1".
# Verify npm version:
npm -v # Should print "10.9.2".
```

完成后在项目目录下执行：
```
npm i
```
安装node_modules相关依赖

# 基于的开源项目
查找部分的工作，主要基于openhaystack开源项目修改后实现，感谢https://github.com/seemoo-lab/openhaystack/项目的所做工作
Query Apple's Find My network, based on all the hard work of https://github.com/seemoo-lab/openhaystack/ and @hatomist and @JJTech0130 and @Dadoum.
并且感谢JJTech0130降低部署门槛，目前服务端部署不再需要mac设备了
 https://github.com/JJTech0130/pypush.



 

## Run
1. `cd` into the `FindMy` directory and generate keys using `./generate_keys.py`.
2. Deploy your advertisement keys on devices supported by OpenHaystack. The ESP32 firmware is a mirror of the OpenHaystack binary, the Lenze 17H66 is found in many 1$ tags obtained from Ali.
An nRF51 firmware can be found here: https://github.com/dakhnod/FakeTag
3. run
```bash
../anisette-v3-server/anisette-v3-server & ./request_reports.py ; killall anisette-v3-server
```
in the same directory as your `.keys` files.

Alternatively to step 3 you could install `https://github.com/Dadoum/pyprovision` (first install `anisette-v3-server` though to get a nice D environment and the required android libs),
make a folder `anisette` in your working directory and just run
```bash
./request_reports.py
```
The script should pick up the python bindings to provision and use that instead.

This command will print json like texts include *timestamp*,*isodatetime*,*latitude*,*longitude* etc.
## convert the data to KML

*KML stands for Keyhole Markup Language. It's a file format used to display geographic data in an Earth browser, such as Google Earth, Google Maps, and various other mapping applications.*

```bash

./request_reports.py > input.txt

```
It will generate a json like file include main data of coordinate & date & time.

```bash

python3 make_kml.py

```
this script reads input.txt generated with request_reports.py and writes for each key a *.kml file

This current non-Mac workflow is not optimal yet, mainly because the anisette server is a bit of a workaround. A python solution for retrieving this is being
developed in the pypush discord, please join there if you want to contribute!
