# docs/reference — 项目规范索引

本目录只保留与课设直接相关的规范与接线资料。从 `D:\starters` 复制的通用模板/流程文档已从仓库移除（本地仍保留，未提交）。

| 文件 | 用途 |
|---|---|
| `toolchains.json` | 工具链版本唯一来源：F103ZET6、Keil 5.24a、OpenOCD/ST-Link、串口 ISP |
| `hil-checklist.md` | HIL 检查单（39 项，覆盖 LCD/OV7670/JPEG/ESP8266/APP） |
| `course-requirements.md` | 课程要求（第 4 题）与当前完成情况 |
| `pinmap.md` | OV7670/FIFO ↔ 战舰V3 P6 引脚分配表 |
| `frame-protocol.md` | 远程帧协议 v2：`AA 55 + 4B 长度 + 2B 校验 + RGB332` |
| `stlink-wiring.md` | ST-Link/J-Link 与板上 20 脚 JTAG 的接线 |
| `jtag_pinout.png` | 20 脚 JTAG 引脚图 |
| `jtag_physical_view.png` | JTAG 俯视引脚编号图 |
| `jtag_schematic.png` | 板上 JTAG 原理图截图 |
| `stlink_to_jtag_wiring.png` | ST-Link 4 针（3.3/GND/Dio/clk）接线图 |
| `p4_usart1_jumper.png` | P4（USART1/CH340）跳线图 |

## 相关文档

- 项目总计划：`../../README.md`
- 单人任务清单：`../../TASKS.md`
- 代理工作约定：`../../AGENTS.md`
- 本地工作状态：`../../HANDOFF.md`（不提交）
- PC 中继说明：`../../pc-tools/README.md`
