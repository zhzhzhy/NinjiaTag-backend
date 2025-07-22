# nRF5x
- nRF5x 蓝牙信标  
优点是刷机方便，一般都有引脚/焊盘，刷机完直接装上纽扣电池就好了。  
缺点是价格比较贵，推荐阿里巴巴采购，最便宜的也要20左右(加邮费)。需要从商品页面详情获取或向商家询问蓝牙信标电路板上 SWCLK/SWDIO 引脚/焊盘的位置。  

- nRF5x 蓝牙模块  
优点是便宜，特别是闲鱼上两三块钱一个。模块体积小可以做出的定位标签也小。但是模块引脚太小要考验焊工，另外还需要网上找相应模块资料或询问卖家，找出 VCC/GND/SWCLK/SWDIO 四个引脚。最后成品如何接电池需要自己处理。  
缺点是引脚小，焊接不方便，需要网上找模块的资料，找到引脚的位置

- nRF52810 PCB打样  
有同学在嘉立创分享了 [nRF52810 信标 PCB 设计图](https://oshwhub.com/bitshen/lan-ya-xin-biao-findmy_copy_copy)，可以自己打样、焊接元件，成本非常低，但是自己焊元件难度很大。


# 刷机硬件工具
- ST-Link v2 编程器  

- 如果遇到 nRF52xxx(比如 nRF52810/nRF52832)刷机失败，可能是因为模块有写保护(AP PROTECT)，需要另外准备 J-link 编程器，用于给模块解除保护



# 下载刷机工具和固件
- 前往 [openhaystack-firmware](https://github.com/acalatrava/openhaystack-firmware/releases) 下载所需固件(`nrf51_firmware.bin`或`nrf52_firmware.bin`) 

- 下载 [OpenOCD v20231002](https://gnutoolchains.com/arm-eabi/openocd/)
下载后解压到合适的位置，比如 `D:\OpenOCD-20231002-0.12.0`，然后将 `D:\OpenOCD-20231002-0.12.0\bin` 加到 `PATH` 环境变量中

- Windows 系统需要安装 ST-LINK 驱动程序，位于 openocd 中：`D:\OpenOCD-20231002-0.12.0\drivers\ST-Link`

- 给 ST-Link 编程器固件升级：[官方工具 STSW-LINK007](https://www.st.com/en/development-tools/stsw-link007.html)

- 安装 hex2bin
```shell
pip3 install IntelHex
```



# 刷机接线
根据布局焊接电线并相应地连接到 ST-LINK 编程器
SWDCLK、SWDIO、GND、VDD(或3.3V或VCC)。GND 和 VDD 可以使用纽扣电池座的正负极弹片，好焊接。



# 刷机
- 执行本仓库的 `python3 generate_keys.py -n 50` 来生成密钥对(在 `keys/` 目录下)。(注意: 必须安装依赖 `cryptography`. 用 `pip3 install cryptography` 命令安装)
Windows 或 Linux 下都可以执行。其中 `-n 50` 是指定生成 50 个密钥对，可以按需修改

- 将之前下载的固件(`nrf51_firmware.bin`或`nrf52_firmware.bin`)和上一步生成的密钥文件(`XXXX_keyfile`)放在同一个目录下

- 使用您的密钥文件修补固件（如有必要，更改路径！）  
此步骤的命令必须在 linux 下执行，因为是 shell 语法，不是 bat 语法。  
也可以在 windows 下安装模拟 linux 的终端后执行（比如 Git 安装后右键有个 Git Bash，或者 Cygwin、w64devkit 等等）
```shell
# 如果是 nrf51
export LC_CTYPE=C
xxd -p -c 100000 XXXX_keyfile | xxd -r -p | dd of=nrf51_firmware.bin skip=1 bs=1 seek=$(grep -oba OFFLINEFINDINGPUBLICKEYHERE! nrf51_firmware.bin | cut -d ':' -f 1) conv=notrunc
```

```shell
# 如果是 nrf52
export LC_CTYPE=C
xxd -p -c 100000 XXXX_keyfile | xxd -r -p | dd of=nrf52_firmware.bin skip=1 bs=1 seek=$(grep -oba OFFLINEFINDINGPUBLICKEYHERE! nrf52_firmware.bin | cut -d ':' -f 1) conv=notrunc
```

输出应该是类似这样的，取决于你的键的数量（在这个例子中是 3 个键 => 3*28=84 字节）：
```
84+0 records in
84+0 records out
84 bytes copied, 0.00024581 s, 346 kB/s
```

- 刷入固件
```shell
openocd openocd.cfg -c "init; halt; nrf51 mass_erase; program nrf51_firmware.bin; reset; exit"
```
`openocd.cfg` 来自 https://github.com/pix/heystack-nrf5x/blob/master/nrf52810/armgcc/openocd.cfg
刷机成功的输出应该如下
```
Open On-Chip Debugger 0.12.0 (2023-10-02) [https://github.com/sysprogs/openocd]
Licensed under GNU GPL v2
libusb1 09e75e98b4d9ea7909e8837b7a3f00dda4589dc3
For bug reports, read
        http://openocd.org/doc/doxygen/bugs.html
Info : auto-selecting first available session transport "hla_swd". To override use 'transport select <transport>'.
Info : The selected transport took over low-level target control. The results might differ compared to plain JTAG/SWD
Info : clock speed 1000 kHz
Info : STLINK V2J43S7 (API v2) VID:PID 0483:3748
Info : Target voltage: 3.274766
Info : [nrf51.cpu] Cortex-M0 r0p0 processor detected
Info : [nrf51.cpu] target has 4 breakpoints, 2 watchpoints
Info : starting gdb server for nrf51.cpu on 3333
Info : Listening on port 3333 for gdb connections
Warn : target was in unknown state when halt was requested
[nrf51.cpu] halted due to debug-request, current mode: Thread
xPSR: 0x61000000 pc: 0x00011480 msp: 0x20003550
Info : nRF51822-QFAA(build code: H0) 256kB Flash, 16kB RAM
Info : Mass erase completed.
Info : A reset or power cycle is required if the flash was protected before.
[nrf51.cpu] halted due to debug-request, current mode: Thread
xPSR: 0xc1000000 pc: 0xfffffffe msp: 0xfffffffc
** Programming Started **
Warn : Adding extra erase range, 0x0001cc70 .. 0x0001cfff
** Programming Finished **
```

- 如果刷机失败，报错 `Contrl-AP`，是因为 nRF52xxx 有写保护，防止读出固件和二次写入，可以[使用 J-link 编程器解除 nRF52xxx 写保护](nRF52xxx_disable_AP.md)。然后重新用 ST-Link 刷机

- 为了测试是否成功刷成定位标签，可以使用
nrf connect 或[AirGuard app](https://github.com/seemoo-lab/AirGuard/releases) 扫描 Apple/FindMy 设备
点击 Locate Tracker 还能看信号强度，根据蓝牙信号强度确定标签的室内位置（如果你有很多定位标签分不清的话，这个功能很实用）


# 注意
另一个固件 [heystack-nrf5x](https://github.com/pix/heystack-nrf5x) 的固件（需要自己编译）。  
本固件提供了一些编译参数，比如是否启用DC/DC稳压器、是否启用电量报告、密钥轮换间隔、蓝牙广播间隔等。  
编译需要用到如下工具：  
- 如果在 Windows 上编译，需要 make 工具。有很多选择，比如 GNUWin32、MinGW、Cygwin、[w64devkit](https://github.com/skeeto/w64devkit/releases)(我用的这个)
- ARM 架构编译器 [gcc-arm-none-eabi-6-2017-q2-update](https://developer.arm.com/downloads/-/gnu-rm/6-2017-q2-update)
- nRF 命令行工具 [nrf-command-line-tools-10.24.2](https://www.nordicsemi.com/Products/Development-tools/nRF-Command-Line-Tools/Download) 
- nRF SDK [nRF51822 需 nRF5_SDK_12.3.0 + S130，nRF52810 需 nRF5_SDK_15.3.0 + S112，nRF52832 需 nRF5_SDK_15.3.0 + S132](https://www.nordicsemi.com/Products/Development-software/nRF5-SDK/Download)

以上工具，Windows 上编译就下 windows 版本, Linux 下编译就下 Linux 版本

如固件支持电量报告。本项目的安卓 app/web前端，可以从位置报告中解析出电量并显示在界面上；也可以使用 [nRF Connect app](https://github.com/NordicSemiconductor/Android-nRF-Connect) 蓝牙搜索定位标签，实时查看设备的电量，如下图



如果板子上有 32.768kHz 低频晶振，建议使用支持外部晶振(XTAL)的固件，比使用内部低频 RC 振荡器功耗低。
为了使固件功耗最低，建议如果板子上有 32.768kHz 低频晶振，最好把编译参数 `HAS_DCDC` 设为 0，即不启用 DC/DC 稳压器，听说功耗可以达到最低。


网友的功耗测试结果：  
- nRF52832 QFAAB0，平均电流消耗为 14 µA（无 32.768kHz 晶振，2000 毫秒广告间隔、15 分钟密钥轮换间隔）
- nRF52832 CIAAB0，平均电流消耗为 20 µA（无 32.768kHz 晶振，2000 毫秒广告间隔、15 分钟密钥轮换间隔）
- nRF52810 QFAAD0，平均电流消耗为 10 µA（无 32.768kHz 晶振，3000 毫秒广告间隔、15 分钟密钥轮换间隔）
- nRF51822，平均电流消耗为 18 µA（无 32.768kHz 晶振，2000 毫秒广告间隔、15 分钟密钥轮换间隔）
- nRF51822，平均电流消耗为 16 µA（带 32.768kHz 晶振，2000 毫秒广告间隔、15 分钟密钥轮换间隔）

一颗容量 210 毫安的 cr2032 纽扣电池（好一点的品牌比如松下），  
- 按照功耗 14 µA 算，至少可以用 210*1000/14/24 = 625 天
- 按照功耗 20 µA 算，至少可以用 210*1000/20/24 = 437 天




# 参考
- [StepByStep](https://github.com/acalatrava/openhaystack-firmware/blob/main/apps/openhaystack-alternative/iBeacon%20StepByStep.md)  
(步骤里面可能用到 MacOS，实际不需要，用 Windows 即可修补固件和刷机) 
- [功耗相关讨论](https://github.com/seemoo-lab/openhaystack/issues/57)
