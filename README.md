# NinjiaTag
## DIY你自己的airtag
DIY 兼容 FindMy 网络的定位标签/设备（长期记录）
服务器端运行 FindMy 网络后台抓取位置数据并存入数据库，无需部署 Mac 电脑或虚拟机，也不需要拥有 iPhone 与其上面的查找 app 即可查看回溯任意时间段内您 DIY 的定位标签/设备的位置、轨迹（注册 Apple-ID 时需要借用一下别人的 iPhone）。
目前实现的功能：
- [x] 服务器端后台运行 request_report 获取位置，定期下载位置数据并储存在本地服务器数据库，储存时间不限（目前市面上主流产品记录时长最多为 7 天），轨迹可永久保存于服务器。
- [x] 支持任意时间段任意物品轨迹查询和显示，支持轨迹点的经纬度和时间点显示，可随意缩放查看，方便回溯。
- [x] 支持热图显示（ Hotspot ），类似地理信息系统的人流密度显示，经常去过的地方颜色更深，不去或偶尔去的地方颜色浅。
- [x] Web 前端支持密钥管理
- [x] 地图采用开源的 Mapbox-GL 三维地图引擎，支持三维地形显示，渲染更加美观。

- [ ] 待测试 Query Apple's Find My network,write into sqlite database,
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

2. 执行本仓库的keygen目录下 `python3 generate_keys.py` 来生成密钥对(在当前目录6位随机名称目录下)。(注意: 必须安装依赖 `cryptography`. 用 `pip3 install cryptography` 命令安装)
   Windows 或 Linux 下都可以执行。
   

3. 将固件刷入设备
说明：generate_keys.py在原项目上做了修改，支持多物品多密钥自定义批量生成，如生成5个密钥的8个物品(在不同文件夹)，执行```python3 generate_keys.py -n 5 -i 8```

  `generate_keys.py` 可以指定参数 `python3  generate_keys.py -n 50` 来生成包含多个密钥的 keyfile，其中 50 就是个数，可以自己改。不指定则默认单个密钥，也就是定位标签运行过程中只有一个蓝牙 Mac 地址（密钥其实就是加密了的 Mac 地址），而多密钥就是定位标签可以定时更换 Mac 地址(称为滚动密钥，苹果 AirTag 就是这样)。
   
   经过测试，带密钥轮换机制的标签，其位置会被更频繁的上报，即位置更新更频繁，更能被精确定位。推荐使用多密钥的 keyfile。但是，密钥轮换会增加一定功耗。

   [nrf5x烧录教程](flash_guide/nrf5x.md)
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
  ```
 ###  3. 下载本项目到本地
 使用git clone 或下载zip解压
 
### 4.放置服务端key

将硬件设置步骤中生成的.key后缀的文件放置在本项目/key文件夹下，后续脚本会自动转化
 
 ### 5.安装python3相关库
 
 #### 基础网络和加密组件

安装 python3，并使用pip3安装相关依赖
 ```
pip3 install aiohttp requests cryptography pycryptodome srp pbkdf2 -i https://pypi.tuna.tsinghua.edu.cn/simple
```
#### 创建python3 venv虚拟环境(可选)

如果成功通过[pip3](#基础网络和加密组件)安装完成依赖，该步骤可忽略

```python3 -m venv ./venv/```

##### venv虚拟环境pip3安装相关依赖

```
./venv/bin/pip3 install aiohttp requests cryptography pycryptodome srp pbkdf2 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

在python3 venv环境执行
```./venv/bin/python3 request_reports.py```

或执行```python3 request_reports.py```

开始时会提示输入Apple ID和密码，然后是2FA短信验证，完成后能正常执行位置数据拉取。
### 安装nodejs
执行以下命令安装nodejs和npm用于提供后端服务
```bash
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

### 安装pm2 守护定时执行
长期运行 "server.mjs" 和 "request_reports.mjs" 以保证服务器能定期取回位置数据并存于数据库

#### PM2 安装说明

1. 通过 npm 全局安装

```npm install pm2 -g```

- 验证安装：执行 
"pm2 --version"，输出版本号即安装成功。
- 权限问题（Linux/Mac）：若提示权限不足，可添加 
"sudo" 或执行 
```chmod 777 /usr/local/bin/pm2```授权。

#### PM2 长期运行脚本命令

##### 启动脚本并命名进程

- 运行 
"server.mjs"（数据库查询主服务）：
```pm2 start server.mjs --name "query-server" --watch```

"--name"：自定义进程名称（便于管理）。
"--watch"：监听文件改动自动重启。
- 运行 
"request_reports.mjs"（抓取位置数据任务）：
```pm2 start request_reports.mjs --name "report-task" --watch```

##### 长期运行保障措施

1. 保存进程列表
```pm2 save```
保存当前运行列表，防止重启后丢失。
2. 设置系统开机自启
```pm2 startup```  # 生成启动脚本
```sudo pm2 startup systemd  # Linux systemd 系统```
```pm2 save  # 关联保存的进程列表```
服务器重启后 PM2 自动恢复进程。
3. 日志管理
   - 查看实时日志：
```pm2 logs web-server  # 指定进程名```

##### pm2常用管理命令(部署时可忽略)
- 查看进程状态 
"pm2 list" 显示所有进程及资源占用
- 停止进程 
"pm2 stop server" 停止指定进程（保留配置）
- 重启进程 
"pm2 restart server" 零停机重载（适用服务更新）
- 监控资源 
"pm2 monit" 实时显示 CPU/内存
- 删除进程 
"pm2 delete server" 彻底移除进程

### 6.服务器后端地址远程

前端页面需访问数据查询服务 url 地址" 形如 `http://服务器ip:3000`。  

  若要在公网使用，需将本地部署服务公开到公网，可以用 路由器端口映射 或 内网穿透(比如有公网IP可使用端口映射+DDNS，或使用反向代理 [ngrok](https://ngrok.com/) 、[节点小宝](https://iepose.com/)、[ZeroNews](https://www.zeronews.cc/) 都有免费版；[花生壳](https://console.hsk.oray.com/) 9块9永久用，每月免费1G流量) 
或使用Zerotier tailscale之类的的方式实现。具体操作不属于本文范畴，请自行搜索。

## 前端页面

前端页面可以自行部署，也可以使用我提供的页面[https://bd8cca.atomgit.net/NinjiaTagPage/](https://bd8cca.atomgit.net/NinjiaTagPage/)，页面只是一个查询框架，建议使用我提供的页面。
前端基于vue3框架开发，目前存在少量bug，但整体能用，欢迎提出Issue或Pr，所有打包的前端页面位于[https://atomgit.com/bd8cca/NinjiaTagPage](https://atomgit.com/bd8cca/NinjiaTagPage) 项目，可自行下载部署

### 使用方法

NinjiaTag前端页面，使用Vue3编写，结合Mapbox-gl三维引擎强大的渲染能力，后续可扩展更多的功能（如轨迹导出KML，多物品时空交错）。

#### 简单使用说明

1.  在前端页面有配置服务器地址选项，填入部署的[https://github.com/zhzhzhy/NinjiaTag-backend](https://github.com/zhzhzhy/NinjiaTag-backend)服务器远程地址

2.  将generate_keys.py硬件设置生成的.json密钥文件在```物品管理```对话框```解析json密钥文件```导入即可

3.  在```数据选择```对话框选择物品数据和时间段进行查询，有几个选项：
  
- 轨迹点：历史的轨迹，鼠标悬停或点击可显示详情。

- 热图： 类似地理信息系统的人流密度显示，经常去过的地方颜色更深，不去或偶尔去的地方颜色浅。
  
- 最新位置： 最新的物品位置，以图标的形式显示。

如果没有获取到位置数据，带着diy的NinjiaTag到人流密集的地方走一圈，等待后台服务器获取到位置数据库并存入数据库。

## 基于的开源项目
- 查找部分的工作，主要基于openhaystack开源项目修改后实现，感谢https://github.com/seemoo-lab/openhaystack/项目的所做工作

- Query Apple's Find My network, based on all the hard work of https://github.com/seemoo-lab/openhaystack/ and @hatomist and @JJTech0130 and @Dadoum

- 并且感谢JJTech0130降低部署门槛，目前服务端部署不再需要mac设备了
 https://github.com/JJTech0130/pypush
- lovelyelfpop大佬开发的安卓apk也可以用于本项目，感谢他本地化app做的很多工作
[https://gitee.com/lovelyelfpop/macless-haystack](https://gitee.com/lovelyelfpop/macless-haystack)

## 杂项待开发 convert the data to KML

*KML stands for Keyhole Markup Language. It's a file format used to display geographic data in an Earth browser, such as Google Earth, Google Maps, and various other mapping applications.*

```bash

./request_reports.py > input.txt

```
It will generate a json like file include main data of coordinate & date & time.

```bash

python3 make_kml.py

```
this script reads input.txt generated with request_reports.py and writes for each key a *.kml file

## 免责声明

此存储库仅用于研究目的，此代码的使用由您负责。

对于您选择如何使用此处提供的任何源代码，我概不负责。使用此存储库中提供的任何文件，即表示您同意自行承担使用风险。再次重申，此处提供的所有文件仅用于教育和或研究目的。本项目仅用于物品的防丢，严禁用于非法用途，使用时请遵守当地的法律法规。
