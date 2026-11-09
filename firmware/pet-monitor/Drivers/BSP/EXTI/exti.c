/**
 ****************************************************************************************************
 * @file        exti.c
 * @brief       OV7670 VSYNC 外部中断（项目实际使用部分）
 *
 * 说明：本文件由正点原子 EXTI 例程裁剪而来，只保留 OV7670 帧同步中断；
 *       按键/蜂鸣器/触摸按键相关代码已移除。
 ****************************************************************************************************
 */

#include "./SYSTEM/sys/sys.h"
#include "./BSP/EXTI/exti.h"
#include "./BSP/OV7670/ov7670.h"

/* OV7670 帧中断标志
 * 0, 表示上一帧数据已经处理完了, 新的帧中断到来, 可以往FIFO写数据
 * 1, 表示上一帧数据还没有处理完, 新的帧中断到来, 不能往FIFO写数据
 */
uint8_t g_ov7670_vsta = 0;

/**
 * @brief       OV7670 VSYNC 外部中断服务程序
 * @param       无
 * @retval      无
 */
void OV7670_VSYNC_INT_IRQHandler(void)
{
    if (EXTI->PR & OV7670_VSYNC_GPIO_PIN)   /* 是OV7670_VSYNC_GPIO_PIN线的中断 */
    {
        if (g_ov7670_vsta == 0) /* 上一帧数据已经处理了? */
        {
            OV7670_WRST(0);     /* 复位写指针 */
            OV7670_WRST(1);     /* 结束复位 */
            OV7670_WEN(1);      /* 允许写入FIFO */
            g_ov7670_vsta = 1;  /* 标记帧中断 */
        }
        else
        {
            OV7670_WEN(0);      /* 禁止写入FIFO */
        }
    }

    EXTI->PR = OV7670_VSYNC_GPIO_PIN;   /* 清除OV7670_VSYNC_GPIO_PIN上的中断标志位 */
}

/**
 * @brief       OV7670 VSYNC外部中断初始化程序
 * @param       无
 * @retval      无
 */
void exti_ov7670_vsync_init(void)
{
    sys_nvic_ex_config(OV7670_VSYNC_GPIO_PORT, OV7670_VSYNC_GPIO_PIN, SYS_GPIO_FTIR);   /* OV7670 VSYNC脚 下降沿触发中断 */
    sys_nvic_init(0, 0, OV7670_VSYNC_INT_IRQn, 2);                                      /* 抢占0，子优先级0，组2 */
}
