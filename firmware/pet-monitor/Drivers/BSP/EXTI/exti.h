/**
 ****************************************************************************************************
 * @file        exti.h
 * @brief       OV7670 VSYNC 外部中断（项目实际使用部分）
 ****************************************************************************************************
 */

#ifndef __EXTI_H
#define __EXTI_H

#include "./SYSTEM/sys/sys.h"

/* OV7670 VSYNC所在引脚 中断编号 & 中断服务函数 定义 */
#define OV7670_VSYNC_INT_IRQn           EXTI9_5_IRQn
#define OV7670_VSYNC_INT_IRQHandler     EXTI9_5_IRQHandler

void exti_ov7670_vsync_init(void);  /* OV7670 VSYNC所在引脚中断初始化 */

#endif
