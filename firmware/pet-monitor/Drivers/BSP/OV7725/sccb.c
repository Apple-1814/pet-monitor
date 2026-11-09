/**
 ****************************************************************************************************
 * @file        sccb.c
 * @brief       SCCB 驱动（软件模拟，适配战舰V3 无外部上拉的情况）
 *
 * 关键改动（相对 ALIENTEK 原版）：
 *   原版把 SDA 配成“开漏输出 + 内部上拉”，但 STM32F1 在输出模式下内部上拉无效，
 *   V3 板又没有 V4 新增的 4.7K 外部上拉，导致 SDA 浮在 0V，读 ID 全是 0x00。
 *   本版在“发 1 / 读数据”时把 SDA 切成输入上拉，在“发 0”时切成开漏输出，
 *   用 MCU 内部上拉顶替外部上拉；SCCB 速率降到约 50kHz 留出上升时间。
 ****************************************************************************************************
 */

#include "./BSP/OV7725/sccb.h"
#include "./SYSTEM/delay/delay.h"

/**
 * @brief       SCCB 延时（约 50kHz）
 */
static void sccb_delay(void)
{
    delay_us(10);
}

/**
 * @brief       释放 SDA：输入模式 + 内部上拉（输出高电平）
 */
static void sccb_sda_release(void)
{
    sys_gpio_set(SCCB_SDA_GPIO_PORT, SCCB_SDA_GPIO_PIN,
                 SYS_GPIO_MODE_IN, SYS_GPIO_OTYPE_PP, SYS_GPIO_SPEED_MID, SYS_GPIO_PUPD_PU);
    SCCB_SDA(1);    /* 输入模式下 ODR=1 选择上拉 */
}

/**
 * @brief       拉低 SDA：开漏输出 + 输出 0
 */
static void sccb_sda_low(void)
{
    sys_gpio_set(SCCB_SDA_GPIO_PORT, SCCB_SDA_GPIO_PIN,
                 SYS_GPIO_MODE_OUT, SYS_GPIO_OTYPE_OD, SYS_GPIO_SPEED_MID, SYS_GPIO_PUPD_NONE);
    SCCB_SDA(0);
}

/**
 * @brief       初始化 SCCB
 */
void sccb_init(void)
{
    SCCB_SCL_GPIO_CLK_ENABLE();
    SCCB_SDA_GPIO_CLK_ENABLE();

    /* SCL：推挽输出，空闲高 */
    sys_gpio_set(SCCB_SCL_GPIO_PORT, SCCB_SCL_GPIO_PIN,
                 SYS_GPIO_MODE_OUT, SYS_GPIO_OTYPE_PP, SYS_GPIO_SPEED_MID, SYS_GPIO_PUPD_PU);
    SCCB_SCL(1);

    /* SDA：默认输入上拉（释放状态） */
    sccb_sda_release();
}

/**
 * @brief       产生 SCCB 起始信号
 */
void sccb_start(void)
{
    sccb_sda_release();     /* SDA 高 */
    sccb_delay();
    SCCB_SCL(1);            /* SCL 高 */
    sccb_delay();
    sccb_sda_low();         /* SCL 高时 SDA 由高变低 = START */
    sccb_delay();
    SCCB_SCL(0);
    sccb_delay();
}

/**
 * @brief       产生 SCCB 停止信号
 */
void sccb_stop(void)
{
    sccb_sda_low();         /* SDA 低 */
    sccb_delay();
    SCCB_SCL(1);            /* SCL 高 */
    sccb_delay();
    sccb_sda_release();     /* SCL 高时 SDA 由低变高 = STOP */
    sccb_delay();
}

/**
 * @brief       不产生 ACK（主机 NACK）
 */
void sccb_nack(void)
{
    sccb_sda_release();     /* SDA 高 */
    sccb_delay();
    SCCB_SCL(1);
    sccb_delay();
    SCCB_SCL(0);
    sccb_delay();
}

/**
 * @brief       SCCB 发送一个字节
 * @param       data: 要发送的数据
 * @retval      0, 收到 ACK; 1, 未收到 ACK
 */
uint8_t sccb_send_byte(uint8_t data)
{
    uint8_t t, res;

    for (t = 0; t < 8; t++)
    {
        if (data & 0x80)
        {
            sccb_sda_release();     /* 发 1：输入上拉 */
        }
        else
        {
            sccb_sda_low();         /* 发 0：开漏输出低 */
        }

        sccb_delay();
        SCCB_SCL(1);
        sccb_delay();
        SCCB_SCL(0);
        sccb_delay();
        data <<= 1;
    }

    /* 第 9 个时钟：释放 SDA，读从机 ACK */
    sccb_sda_release();
    sccb_delay();
    SCCB_SCL(1);
    sccb_delay();
    res = SCCB_READ_SDA ? 1 : 0;
    SCCB_SCL(0);
    sccb_delay();

    return res;
}

/**
 * @brief       SCCB 读取一个字节
 * @retval      读到的数据
 */
uint8_t sccb_read_byte(void)
{
    uint8_t i, receive = 0;

    sccb_sda_release();         /* 读之前释放 SDA，靠内部上拉拉高 */

    for (i = 0; i < 8; i++)
    {
        receive <<= 1;
        SCCB_SCL(1);
        sccb_delay();

        if (SCCB_READ_SDA)
        {
            receive++;
        }

        SCCB_SCL(0);
        sccb_delay();
    }

    return receive;
}
