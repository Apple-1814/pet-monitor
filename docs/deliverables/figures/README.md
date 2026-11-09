# 报告插图清单

| 文件 | 内容 | 建议放入报告章节 |
|---|---|---|
| `system-block.png` | 系统总体框图：OV7670+FIFO、STM32、LCD、USART1/CH340、PC 中继、手机 Web APP、ST-Link | 2 系统总体方案 |
| `flow-main.png` | 主程序流程图：时钟/串口/LCD/OV7670 初始化、帧标志判断、LCD 显示、DMA 空闲判断、RGB332 发送 | 4 软件设计 |
| `flow-camera-fifo.png` | 左：OV7670 初始化（SCCB、PID/VER、寄存器表）；右：VSYNC 中断 + FIFO 读帧 + LCD 显示 + 远程采样 | 4 软件设计（驱动/采集） |
| `flow-remote.png` | STM32 端 RGB332 组帧/校验/DMA → PC 中继（串口线程/校验/队列/JPEG/HTTP）→ 手机 Web APP | 4 软件设计（远程链路） |
| `hardware-interface.png` | 硬件接口电路（接口级原理图）：P6 摄像头 18 针映射、LCD FSMC、USART1/CH340、SWD、电源 | 3 硬件设计 |
| `hardware-interface.pdf` | 同上，PDF 版，可直接作为“硬件接口电路原理图”提交/附图 | 3 硬件设计 |

## 说明

- `hardware-interface` 是**接口级原理图**，重点是把 22 脚 OV7670 模块与板载 P6 的 18 针、LCD FSMC、USART1、SWD 的对应关系画清楚；不包含完整的电阻/电容/电源树。
- 如果学校要求完整的电气原理图，可在立创 EDA 里按 `docs/reference/pinmap.md` 重绘，导出 PDF 替换本图。
- 图已生成；生成脚本仅本地保留，不随仓库提交。
