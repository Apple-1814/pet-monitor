---
name: toolchain-check
description: 核对工具链契约:arm-none-eabi-gcc/pio/idf.py/openocd 等版本与 toolchains.json 逐项比对
---

# toolchain-check

## 输入

- `tooling/toolchains.json` 的目标条目(以 `default_target` 为起点,或任务指定目标)。
- 本机可用的 shell(WSL 内执行验证命令;Windows 侧烧录器按环境要点说明)。

## 步骤

1. 读取契约:目标条目下每个工具的 `name` / `version` / `verify` 命令。
2. 逐项执行 `verify` 命令(WSL),把实际版本与契约 `version` 比对。
3. 输出三态结论:一致 / 不一致(记实际版本)/ 缺失(工具未装)。
4. 不一致或缺失时:报告差异,由使用者决定改本机工具链还是改契约(改契约须在交付文档记录原因)。

## 输出

- 逐项核对表(工具/契约版本/实际版本/结论)。
- 结论写入 HANDOFF"当前状态";不影响其他工具链版本的前提下不放行后续构建。
