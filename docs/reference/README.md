# docs/reference — 参考与规范索引

本目录存放从 `D:\starters` 复制的参考文档，以及按本课设适配后的规范。技能正文里引用的路径以根 `AGENTS.md` 的映射表为准。

| 文件 | 来源 | 用途 |
|---|---|---|
| `toolchains.json` | `embedded-fw-starter/tooling/`（已适配） | 工具链版本唯一来源：F103ZET6、Keil 5.24a、串口 ISP/ST-Link |
| `flash-debug.md` | `embedded-fw-starter/tooling/` | 原模板烧录/调试说明（GCC 版，仅参考） |
| `hil-guide.md` | `embedded-fw-starter/tooling/` | HIL 执行方法 |
| `peripheral-select.md` | `embedded-fw-starter/tooling/` | 外设选型检查 |
| `hil-checklist.md` | `embedded-fw-starter/tests/hil/`（已增补） | 39 项 HIL 检查单，覆盖 LCD/OV7670/JPEG/ESP8266/APP |
| `交付模板.md` | `embedded-fw-starter/docs/交付文档/` | 阶段交付文档模板 |
| `figure-specs.md` | `research-starter/tooling/` | 报告图表规格 |
| `experiments/exp-template.md` | `research-starter/experiments/protocols/` | 实验记录模板 |
| `flow/01-requirements.md` | `embedded-fw-starter/flow/` | 需求阶段流程 |
| `flow/02-platform-select.md` | 同上 | 平台选型流程 |
| `flow/03-coding.md` | 同上 | 编码阶段流程 |
| `flow/04-static-check.md` | 同上 | 静态检查流程 |
| `flow/05-flash-hil.md` | 同上 | 烧录与 HIL 流程 |
| `flow/README.md` | 同上 | 流程总览 |

## 本课设自己的规范（待补）

- `pinmap.md`：OV7670/FIFO ↔ F103 引脚分配表（T2.1 产出）
- `frame-protocol.md`：`AA 55 + 4 字节长度 + JPEG` 帧协议（T3.4 产出）
- `ram-budget.md`：RAM 预算表（T3.3 产出）
- `test-cases.md`：系统测试用例（T6.1 产出）

## 相关文档

- 项目总计划：`../../README.md`
- 单人任务清单：`../../TASKS.md`
- 代理工作约定：`../../AGENTS.md`
- 当前状态：`../../HANDOFF.md`
