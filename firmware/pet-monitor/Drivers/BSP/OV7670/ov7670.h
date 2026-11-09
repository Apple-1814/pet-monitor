/**
 ****************************************************************************************************
 * @file        ov7670.h
 * @brief       OV7670 + AL422 FIFO 驱动（战舰V3/V4 板载摄像头接口）
 *
 * 接线（板载 P6 摄像头座，18 脚）：
 *   VSYNC  PA8      WRST  PD6      RRST  PG14     OE    PG15
 *   RCLK   PB4      WEN   PB3      D0-D7 PC0-PC7
 *   SCCB   SCL=PD3  SDA=PG13（见 sccb.h）
 ****************************************************************************************************
 */

#ifndef __OV7670_H
#define __OV7670_H

#include "./SYSTEM/sys/sys.h"

/* VSYNC：帧同步输入 */
#define OV7670_VSYNC_GPIO_PORT          GPIOA
#define OV7670_VSYNC_GPIO_PIN           SYS_GPIO_PIN8
#define OV7670_VSYNC_GPIO_CLK_ENABLE()  do{ RCC->APB2ENR |= 1 << 2; }while(0)

/* WRST：FIFO 写指针复位 */
#define OV7670_WRST_GPIO_PORT           GPIOD
#define OV7670_WRST_GPIO_PIN            SYS_GPIO_PIN6
#define OV7670_WRST_GPIO_CLK_ENABLE()   do{ RCC->APB2ENR |= 1 << 5; }while(0)

/* RRST：FIFO 读指针复位 */
#define OV7670_RRST_GPIO_PORT           GPIOG
#define OV7670_RRST_GPIO_PIN            SYS_GPIO_PIN14
#define OV7670_RRST_GPIO_CLK_ENABLE()   do{ RCC->APB2ENR |= 1 << 8; }while(0)

/* OE：FIFO 输出使能（低有效） */
#define OV7670_OE_GPIO_PORT             GPIOG
#define OV7670_OE_GPIO_PIN              SYS_GPIO_PIN15
#define OV7670_OE_GPIO_CLK_ENABLE()     do{ RCC->APB2ENR |= 1 << 8; }while(0)

/* RCLK：FIFO 读时钟 */
#define OV7670_RCLK_GPIO_PORT           GPIOB
#define OV7670_RCLK_GPIO_PIN            SYS_GPIO_PIN4
#define OV7670_RCLK_GPIO_CLK_ENABLE()   do{ RCC->APB2ENR |= 1 << 3; }while(0)

/* WEN：FIFO 写使能（低有效） */
#define OV7670_WEN_GPIO_PORT            GPIOB
#define OV7670_WEN_GPIO_PIN             SYS_GPIO_PIN3
#define OV7670_WEN_GPIO_CLK_ENABLE()    do{ RCC->APB2ENR |= 1 << 3; }while(0)

/* IO 操作宏 */
#define OV7670_VSYNC(x)     sys_gpio_pin_set(OV7670_VSYNC_GPIO_PORT, OV7670_VSYNC_GPIO_PIN, x)
#define OV7670_WRST(x)      sys_gpio_pin_set(OV7670_WRST_GPIO_PORT,  OV7670_WRST_GPIO_PIN,  x)
#define OV7670_RRST(x)      sys_gpio_pin_set(OV7670_RRST_GPIO_PORT,  OV7670_RRST_GPIO_PIN,  x)
#define OV7670_OE(x)        sys_gpio_pin_set(OV7670_OE_GPIO_PORT,    OV7670_OE_GPIO_PIN,    x)
#define OV7670_RCLK(x)      x ? (OV7670_RCLK_GPIO_PORT->BSRR = OV7670_RCLK_GPIO_PIN) : (OV7670_RCLK_GPIO_PORT->BRR = OV7670_RCLK_GPIO_PIN)
#define OV7670_WEN(x)       sys_gpio_pin_set(OV7670_WEN_GPIO_PORT,   OV7670_WEN_GPIO_PIN,   x)
#define OV7670_DATA         (GPIOC->IDR & 0X00FF)   /* D0~D7 -> PC0~PC7 */

/* OV7670 SCCB 地址与 ID */
#define OV7670_ADDR         0X42
#define OV7670_PID          0X76    /* 寄存器 0x0A */
#define OV7670_VER          0X73    /* 寄存器 0x0B */

uint8_t ov7670_init(void);
uint8_t ov7670_read_reg(uint8_t reg);
uint8_t ov7670_write_reg(uint8_t reg, uint8_t data);

void ov7670_window_set(uint16_t sx, uint16_t sy, uint16_t width, uint16_t height);

#endif
