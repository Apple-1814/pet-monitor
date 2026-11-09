/**
 ****************************************************************************************************
 * @file        ov7670.c
 * @brief       OV7670 + AL422 FIFO 驱动（战舰V3/V4 板载摄像头接口）
 *
 * 采集链路：
 *   OV7670 → AL422B FIFO → PC0~PC7 读出 → LCD(FSMC) 显示
 *
 * 注意：
 *   1. 本文件只负责传感器初始化与寄存器访问；FIFO 读帧在 main.c 中完成。
 *   2. PB3/PB4 是 JTAG 引脚，初始化时必须关闭 JTAG、保留 SWD。
 *   3. 读像素的字节序取决于模块/寄存器配置：本驱动按“低字节在前”读取；
 *      若颜色明显错乱，可在 main.c 中交换高低字节。
 ****************************************************************************************************
 */

#include "./BSP/OV7725/sccb.h"
#include "./BSP/OV7670/ov7670.h"
#include "./BSP/OV7670/ov7670config.h"
#include "./SYSTEM/usart/usart.h"
#include "./SYSTEM/delay/delay.h"

/**
 * @brief       读 OV7670 寄存器
 * @param       reg : 寄存器地址
 * @retval      读到的值
 */
uint8_t ov7670_read_reg(uint8_t reg)
{
    uint8_t data = 0;

    sccb_start();
    sccb_send_byte(OV7670_ADDR);
    sccb_send_byte(reg);
    sccb_stop();

    sccb_start();
    sccb_send_byte(OV7670_ADDR | 0X01);
    data = sccb_read_byte();
    sccb_nack();
    sccb_stop();

    return data;
}

/**
 * @brief       写 OV7670 寄存器
 * @param       reg  : 寄存器地址
 * @param       data : 要写入的值
 * @retval      0, 成功; 1, 失败
 */
uint8_t ov7670_write_reg(uint8_t reg, uint8_t data)
{
    uint8_t res = 0;

    sccb_start();
    if (sccb_send_byte(OV7670_ADDR)) res = 1;
    if (sccb_send_byte(reg))         res = 1;
    if (sccb_send_byte(data))        res = 1;
    sccb_stop();

    return res;
}

/**
 * @brief       初始化 OV7670（GPIO + SCCB + 寄存器表）
 * @param       无
 * @retval      0, 成功; 1, SCCB 复位失败; 2, ID 不匹配
 */
uint8_t ov7670_init(void)
{
    uint16_t i = 0;
    uint8_t pid = 0;
    uint8_t ver = 0;

    OV7670_VSYNC_GPIO_CLK_ENABLE();
    OV7670_WRST_GPIO_CLK_ENABLE();
    OV7670_RRST_GPIO_CLK_ENABLE();
    OV7670_OE_GPIO_CLK_ENABLE();
    OV7670_RCLK_GPIO_CLK_ENABLE();
    OV7670_WEN_GPIO_CLK_ENABLE();
    RCC->APB2ENR |= 1 << 4;             /* GPIOC（D0~D7）时钟使能 */

    /* VSYNC：输入上拉 */
    sys_gpio_set(OV7670_VSYNC_GPIO_PORT, OV7670_VSYNC_GPIO_PIN,
                 SYS_GPIO_MODE_IN, SYS_GPIO_OTYPE_PP, SYS_GPIO_SPEED_HIGH, SYS_GPIO_PUPD_PU);

    /* FIFO 控制：推挽输出 */
    sys_gpio_set(OV7670_WRST_GPIO_PORT, OV7670_WRST_GPIO_PIN,
                 SYS_GPIO_MODE_OUT, SYS_GPIO_OTYPE_PP, SYS_GPIO_SPEED_HIGH, SYS_GPIO_PUPD_PU);
    sys_gpio_set(OV7670_RRST_GPIO_PORT, OV7670_RRST_GPIO_PIN,
                 SYS_GPIO_MODE_OUT, SYS_GPIO_OTYPE_PP, SYS_GPIO_SPEED_HIGH, SYS_GPIO_PUPD_PU);
    sys_gpio_set(OV7670_OE_GPIO_PORT, OV7670_OE_GPIO_PIN,
                 SYS_GPIO_MODE_OUT, SYS_GPIO_OTYPE_PP, SYS_GPIO_SPEED_HIGH, SYS_GPIO_PUPD_PU);
    sys_gpio_set(OV7670_RCLK_GPIO_PORT, OV7670_RCLK_GPIO_PIN,
                 SYS_GPIO_MODE_OUT, SYS_GPIO_OTYPE_PP, SYS_GPIO_SPEED_HIGH, SYS_GPIO_PUPD_PU);
    sys_gpio_set(OV7670_WEN_GPIO_PORT, OV7670_WEN_GPIO_PIN,
                 SYS_GPIO_MODE_OUT, SYS_GPIO_OTYPE_PP, SYS_GPIO_SPEED_HIGH, SYS_GPIO_PUPD_PU);

    /* D0~D7：输入上拉 */
    sys_gpio_set(GPIOC, 0XFF,
                 SYS_GPIO_MODE_IN, SYS_GPIO_OTYPE_PP, SYS_GPIO_SPEED_HIGH, SYS_GPIO_PUPD_PU);

    /* 空闲电平：写/读指针复位为高，OE 高（禁止输出），RCLK 高，WEN 高（禁止写） */
    OV7670_WRST(1);
    OV7670_RRST(1);
    OV7670_OE(1);
    OV7670_RCLK(1);
    OV7670_WEN(1);

    /* PB3/PB4 是 JTAG 引脚：关闭 JTAG，保留 SWD */
    sys_gpio_remap_set(24, 3, 2);

    sccb_init();

    /* 软复位 */
    if (ov7670_write_reg(0x12, 0x80))
    {
        return 1;
    }

    delay_ms(50);

    /* 读产品 ID：0x0A=PID(0x76)，0x0B=VER(0x73) */
    pid = ov7670_read_reg(0x0A);
    ver = ov7670_read_reg(0x0B);
    printf("OV7670 PID:%02X VER:%02X\r\n", pid, ver);

    if ((pid != OV7670_PID) || (ver != OV7670_VER))
    {
        return 2;
    }

    /* 写入 QVGA RGB565 初始化表 */
    for (i = 0; i < sizeof(ov7670_init_reg_table) / sizeof(ov7670_init_reg_table[0]); i++)
    {
        ov7670_write_reg(ov7670_init_reg_table[i][0], ov7670_init_reg_table[i][1]);
    }

    return 0;
}

/**
 * @brief       设置 OV7670 输出窗口
 * @param       sx, sy     : 起始坐标（按 OV7670 窗口寄存器定义）
 * @param       width, height : 输出宽高
 * @retval      无
 *
 * @note        仅在默认 QVGA 窗口偏移/裁剪不正确时使用。
 *              参考开源工程的用法：OV7670_Window_Set(12, 176, 240, 320)
 */
void ov7670_window_set(uint16_t sx, uint16_t sy, uint16_t width, uint16_t height)
{
    uint16_t endx;
    uint16_t endy;
    uint8_t temp;

    endx = sx + width * 2;
    endy = sy + height * 2;

    if (endy > 784)
    {
        endy -= 784;
    }

    temp = ov7670_read_reg(0x03);
    temp &= 0XF0;
    temp |= ((endx & 0X03) << 2) | (sx & 0X03);
    ov7670_write_reg(0x03, temp);

    ov7670_write_reg(0x19, sx >> 2);
    ov7670_write_reg(0x1A, endx >> 2);

    temp = ov7670_read_reg(0x32);
    temp &= 0XC0;
    temp |= ((endy & 0X07) << 3) | (sy & 0X07);
    ov7670_write_reg(0x32, temp);

    ov7670_write_reg(0x17, sy >> 3);
    ov7670_write_reg(0x18, endy >> 3);
}
