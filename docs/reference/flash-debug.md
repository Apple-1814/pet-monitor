# 烧录与调试

- 工具与版本以 `toolchains.json` 对应目标条目为准;版本不符先报告再继续。
- ST-Link:`st-flash write build/fw.bin 0x08000000`;调试:`openocd -f interface/stlink.cfg -f target/stm32f1x.cfg`。
- J-Link:按芯片型号选 device 脚本;烧录前确认目标板供电与复位方式。
- 调试输出统一走 `BOARD_UART_DEBUG`(见 `fw/stm32f103c8/board.h`),波特率 115200。
- 烧录产物先算 sha256 并登记到交付文档;烧录后回读版本信息核对。
