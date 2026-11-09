# AGENTS.md — 宠物视频监控系统（物联网课设）

本文件是本项目的代理工作约定。`.agents/skills/` 下的技能正文来自 `D:\starters`，默认按模板路径与 WSL/gcc 工具链书写；**实际执行以本文件为准**。

## 1. 项目

- 题目：宠物视频监控系统
- 平台：正点原子战舰V3（STM32F103ZET6，512KB Flash / 64KB RAM）
- 外设：OV7670 + AL422 FIFO、2.8 寸 LCD（FSMC）、ATK-ESP8266、安卓 APP
- 指标：本地 QVGA ≥10 fps；远程 QQVGA ≥3 fps；端到端延迟 <1 s
- 总计划：`README.md`；执行清单：`TASKS.md`；当前状态：`HANDOFF.md`

## 2. 当前环境（2026-11-09 检测）

| 项 | 状态 |
|---|---|
| 开发板 | 战舰V3 已上电，板载 CH340 在线，**COM22**，驱动正常 |
| ST-Link | **未连接**（驱动已装，无下载器） |
| 烧录 | 当前只能串口 ISP：BOOT0=1 + ATK-XISP；ST-Link 到位后走 SWD |
| Keil | MDK 5.24a，`C:\Keil_v5\UV4\UV4.exe`，ARMCC/AC5，STM32F1xx_DFP 2.2.0 |
| CubeMX | 6.13.0，`D:\stm32cubemx\STM32CubeMX.exe`；CubeMX 工程仅作备选 |
| F1 固件包 | `C:\Users\18149\STM32Cube\Repository\STM32Cube_FW_F1_V1.8.6` |
| Python | `C:\Users\18149\miniconda3\python.exe` 已带 pyserial 3.5；PATH 中的 Python 3.11 未装 pyserial |
| 摄像头 | OV7670 已插在板上，**是否带 AL422 FIFO 尚未确认（T0.1）** |
| WiFi | ATK-ESP8266 **未到货** |
| Android Studio | **未安装** |
| 正点原子资料 | `D:\BaiduNetdiskDownload\【正点原子】战舰STM32F103开发板V4 资料盘(A盘)` |

## 3. 技能与路径映射

技能目录：`.agents/skills/`

| 技能 | 本项目用途 |
|---|---|
| `fw-init` | 确认标准库/HAL/寄存器层级；本项目默认标准库 |
| `toolchain-check` | 按 `docs/reference/toolchains.json` 核对 Keil/DFP/串口 |
| `driver-writer` | LCD、OV7670、SCCB、USART、FIFO 驱动三件套 |
| `build-flash` | Keil 构建 + 串口 ISP/ST-Link 烧录门禁 |
| `hil-test` | 按 `docs/reference/hil-checklist.md` 做硬件在环记录 |
| `iter-close` | 阶段收尾、交付文档、版本 tag |
| `experiment-log` | 帧率/延迟/吞吐测试登记 |
| `figure-check` | 报告图表质检 |

**路径映射（技能正文 → 本项目实际路径）**

| 技能里写的 | 实际使用 |
|---|---|
| `fw/` | `firmware/` |
| `drivers/` | `firmware/drivers/` |
| `tests/` | `firmware/tests/` |
| `tooling/toolchains.json` | `docs/reference/toolchains.json` |
| `HANDOFF.md` | 根目录 `HANDOFF.md` |
| `paper/` | `docs/report/` |
| `experiments/` | `docs/experiments/` |
| `literature/` | `reference/` |
| `compliance/` | 不适用（课设无伦理审查） |

## 4. 目录约定

```
firmware/      Keil 工程与固件源码（drivers/、tests/ 在此之下）
app/           安卓 APP 工程
pc-tools/      PC 收流脚本（pyserial + 帧解析）
docs/
  reference/   工具链契约、HIL 清单、flow、图表规范
  logs/        每日调试日志 YYYY-MM-DD.md
  experiments/ 帧率/延迟/吞吐测试记录
  report/      设计报告
  deliverables/原理图 PDF、使用说明、PPT、演示视频
reference/     芯片手册、正点原子资料、开源参考工程
agents/        角色提示词模板（不自动加载）
scripts/       read-doc.py 等工具
```

## 5. 工具链与构建

- 目标：`stm32f103zetx`，512KB Flash / 64KB RAM，战舰V3。
- 编译：`"C:\Keil_v5\UV4\UV4.exe" -b <project.uvprojx> -j0 -o build.log`，以 `build.log` 中 `0 Error(s)` 为准。
- 默认使用**标准外设库（StdPeriph V3.5.0）**，与正点原子例程一致；选择 HAL 必须写明理由与迁移成本。
- Keil 构建产物（`Objects/`、`Listings/`、`*.hex` 等）不进 git。
- 例程基线：
  - LCD：`4，程序源码/1，标准例程-寄存器版本/.../实验13 TFTLCD（MCU屏）实验/Projects/MDK-ARM/atk_f103.uvprojx`
  - 串口：`实验5 串口实验`
  - 摄像头参考：`实验34 摄像头实验`（注意是 **OV7725**，不是 OV7670，寄存器需改写）

## 6. 烧录与调试

### 当前路线（无 ST-Link）

1. BOOT0 跳线置 1，按复位，进入系统 Bootloader。
2. 打开 `ATK-XISP.exe`，选 **COM22**，下载 Keil 生成的 `.hex`。
3. BOOT0 回 0，按复位运行。
4. 每次下载都要重复改 BOOT0；串口 ISP **不支持断点/单步**。

路径：`D:\BaiduNetdiskDownload\【正点原子】战舰STM32F103开发板V4 资料盘(A盘)\6，软件资料\1，软件\5，其他软件\STM32串口下载软件（ATK-XISP）\ATK-XISP.exe`

### ST-Link 到位后

- SWD 四线：SWDIO / SWCLK / GND / 3.3V。
- Keil → Options for Target → Debug → **ST-Link Debugger**。
- 调试优先级：断点 > 串口打点 > LED。

### 调试手段

- `printf` → USART1 @115200 → CH340 → COM22。
- LCD 状态栏（FPS、IP、错误码）。
- 有条件时用逻辑分析仪看 VSYNC / PCLK / RCLK / WEN 时序。

## 7. 串口分配（不得随意占用）

| 外设 | 引脚 | 波特率 | 用途 |
|---|---|---|---|
| USART1 | PA9(TX) / PA10(RX) | 115200 | 调试 printf，板载 CH340 → COM22 |
| USART2 | PA2(TX) / PA3(RX) | 460800 / 921600 | ATK-ESP8266（预留，模块未到货） |

- USART1 推流时**禁止同时 printf**，否则破坏帧协议；推流与日志分时或分口。
- 接 OV7670 时避开 USART1/USART2、FSMC-LCD、JTAG 引脚；以 `战舰V4 IO引脚分配表.xlsx` 和 `WARSHIP_DNF103P.pdf` 为准。

## 8. 编码与记录约定

- C 语言，跟随正点原子标准库风格；文件/函数小写下划线。
- 驱动三件套：`xxx.h` + `xxx.c` + `test_xxx.c`（可在宿主侧验证的部分先验证）。
- 中断服务函数短小；共享变量加 `volatile`；FIFO 读帧期间是否关中断必须写明理由。
- 每完成一项：更新 `docs/logs/YYYY-MM-DD.md`、`HANDOFF.md`、`docs/reference/hil-checklist.md`。
- 版本命名 `v0.YYMMDD`；阶段验收通过打 git tag。
- **不伪造验证**：未执行的项写“未跑（需 HIL）”，阻塞项写清缺什么。

## 9. 单人执行顺序

见 `TASKS.md`。主线：

`环境/串口 ISP → Keil + LCD 骨架 → OV7670+FIFO（保底） → 降采样+JPEG → PC 直连收流 → ESP8266 → 安卓 APP → 联调测试 → 报告/PPT`

## 10. 禁止 / 注意

- 不要复制或启用 starters 的 `.zcode/config.json` 与 `hooks/`：模板守卫会把构建强制走 WSL，与 Windows 下的 Keil 冲突。
- 不要修改 `.agents/skills/*/SKILL.md`：那是上游模板；项目适配统一写在本文件。
- 不要把 OV7670 当 OV7725 用：正点原子例程的寄存器/时序按 OV7725 写，OV7670 必须按自己的手册改。
- 不要忽略 RAM 预算：QQVGA RGB565 缓冲约 37.5 KB，F103 只有 64 KB。
- 不要在未确认 OV7670 是否带 FIFO 前开始摄像头接线：不带 FIFO 的模块无法按本方案采集。
