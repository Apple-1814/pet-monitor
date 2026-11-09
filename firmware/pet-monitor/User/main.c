/**
 ****************************************************************************************************
 * @file        main.c
 * @brief       宠物视频监控系统 — OV7670 + AL422 FIFO → LCD 实时显示
 *
 * 硬件：正点原子战舰V3（STM32F103ZET6）+ 2.8 寸 LCD + OV7670(带 AL422 FIFO)
 * 接线：板载 P6 摄像头座（见 ov7670.h）
 *
 * 当前阶段：功能①② 保底验证（摄像头采集 + LCD 实时显示）
 ****************************************************************************************************
 */

#include "./SYSTEM/sys/sys.h"
#include "./SYSTEM/usart/usart.h"
#include "./SYSTEM/delay/delay.h"
#include "./BSP/LED/led.h"
#include "./BSP/LCD/lcd.h"
#include "./BSP/EXTI/exti.h"
#include "./BSP/TIMER/btim.h"
#include "./BSP/OV7670/ov7670.h"

extern uint8_t g_ov7670_vsta;       /* exti.c 中定义：帧中断标志 */
extern uint8_t g_camera_frame;      /* btim.c 中定义：每秒帧数 */
extern volatile uint8_t g_camera_fps;
extern volatile uint8_t g_camera_fps_ready;

#define CAM_W       320
#define CAM_H       240

/* 远程视频流：中心裁剪 192x144 RGB332（27648 字节） */
#define REMOTE_W        192
#define REMOTE_H        144
#define REMOTE_X        ((CAM_W - REMOTE_W) / 2)    /* 40 */
#define REMOTE_Y        ((CAM_H - REMOTE_H) / 2)    /* 30 */
#define REMOTE_PAYLOAD  (REMOTE_W * REMOTE_H)
#define REMOTE_HDR      8   /* AA 55 + 4 字节长度 + 2 字节校验和 */

/* 远程帧缓冲：8 字节帧头 + RGB332 像素 */
static uint8_t g_remote_buf[REMOTE_HDR + REMOTE_PAYLOAD];

/* RGB565 -> RGB332：RRRGGGBB */
static uint8_t rgb565_to_rgb332(uint16_t c)
{
    uint8_t r = (c >> 11) & 0x1F;
    uint8_t g = (c >> 5) & 0x3F;
    uint8_t b = c & 0x1F;
    return (uint8_t)(((r >> 2) << 5) | ((g >> 3) << 2) | (b >> 3));
}

/* 读一个 RGB565 像素并写入 LCD；内层循环展开 4 次以减少分支开销 */
#define READ_PIXEL() do { \
    OV7670_RCLK(0); \
    color = OV7670_DATA;        /* 高字节 */ \
    OV7670_RCLK(1); \
    color <<= 8; \
    OV7670_RCLK(0); \
    color |= OV7670_DATA;       /* 低字节 */ \
    OV7670_RCLK(1); \
    LCD->LCD_RAM = color; \
} while (0)

/**
 * @brief       将 OV7670 FIFO 中的一帧读到 LCD
 * @note        读像素顺序为“低字节在前”；若颜色异常，交换高低字节即可。
 */
static void ov7670_camera_refresh(void)
{
    uint16_t i, j;
    uint16_t color;
    uint16_t sum, k;
    uint8_t remote_capture;

    if (g_ov7670_vsta)
    {
        delay_ms(10);               /* 让摄像头先写一段，读指针不容易追上写指针 */
        remote_capture = usart1_dma_ready();    /* 上一帧 DMA 已完成才采集远程帧 */
        lcd_set_window((lcddev.width - CAM_W) / 2, (lcddev.height - CAM_H) / 2,
                       CAM_W, CAM_H);           /* 480x320 横屏下居中：80,40 */
        lcd_write_ram_prepare();                /* 开始写 GRAM */

        /* FIFO 读指针复位：RRST 低 -> RCLK 一个脉冲 -> RRST 高 -> RCLK 高 */
        OV7670_RRST(0);
        OV7670_RCLK(0);
        OV7670_RCLK(1);
        OV7670_RCLK(0);
        OV7670_RRST(1);
        OV7670_RCLK(1);

        for (i = 0; i < CAM_H; i++)
        {
            if (remote_capture && (i >= REMOTE_Y) && (i < (REMOTE_Y + REMOTE_H)))
            {
                /* 裁剪行：左侧只显示，中间填远程缓冲，右侧只显示 */
                for (j = 0; j < REMOTE_X; j++)
                {
                    READ_PIXEL();
                }

                for (j = REMOTE_X; j < (REMOTE_X + REMOTE_W); j++)
                {
                    READ_PIXEL();
                    g_remote_buf[REMOTE_HDR + (i - REMOTE_Y) * REMOTE_W + (j - REMOTE_X)] = rgb565_to_rgb332(color);
                }

                for (j = (REMOTE_X + REMOTE_W); j < CAM_W; j++)
                {
                    READ_PIXEL();
                }
            }
            else
            {
                for (j = 0; j < CAM_W; j++)
                {
                    READ_PIXEL();
                }
            }
        }

        if (remote_capture)
        {
            sum = 0;
            for (k = 0; k < REMOTE_PAYLOAD; k++)
            {
                sum += g_remote_buf[REMOTE_HDR + k];
            }

            g_remote_buf[0] = 0xAA;
            g_remote_buf[1] = 0x55;
            g_remote_buf[2] = (uint8_t)(REMOTE_PAYLOAD & 0xFF);
            g_remote_buf[3] = (uint8_t)((REMOTE_PAYLOAD >> 8) & 0xFF);
            g_remote_buf[4] = 0x00;
            g_remote_buf[5] = 0x00;
            g_remote_buf[6] = (uint8_t)(sum & 0xFF);
            g_remote_buf[7] = (uint8_t)((sum >> 8) & 0xFF);
            usart1_dma_send(g_remote_buf, (uint16_t)(REMOTE_HDR + REMOTE_PAYLOAD));
        }

        g_ov7670_vsta = 0;
        g_camera_frame++;
    }
}

int main(void)
{
    uint8_t ret;

    sys_stm32_clock_init(9);        /* 72 MHz */
    delay_init(72);
    usart_init(72, 1500000);        /* 1.5Mbaud：192x144 RGB332 视频流带宽 */
    usart1_dma_init();              /* USART1 TX DMA */
    printf("\r\n[BOOT] uart ok\r\n");
    led_init();
    printf("[BOOT] led ok\r\n");
    lcd_init();
    printf("[BOOT] lcd init ok\r\n");
    lcd_display_dir(1);             /* 2.8 寸屏横屏：320x240 */
    printf("[LCD] id=%04X w=%d h=%d dir=%d\r\n", lcddev.id, lcddev.width, lcddev.height, lcddev.dir);
    printf("[BOOT] lcd dir ok\r\n");
    lcd_scan_dir(U2D_L2R);          /* 摄像头例程标准扫描方向 */
    lcd_clear(BLACK);
    printf("[BOOT] lcd clear ok\r\n");

    lcd_show_string(10, 10, 200, 16, 16, "Pet Monitor", RED);
    lcd_show_string(10, 30, 220, 16, 16, "OV7670 FIFO Test", RED);
    printf("[BOOT] lcd string ok\r\n");

    while (1)
    {
        printf("[CAM] init try\r\n");
        ret = ov7670_init();
        printf("[CAM] ret=%d\r\n", ret);

        if (ret == 0)
        {
            break;
        }

        lcd_show_string(10, 60, 220, 16, 16, "OV7670 Init Failed", RED);
        printf("OV7670 init failed: %d\r\n", ret);
        delay_ms(500);
    }

    lcd_show_string(10, 60, 220, 16, 16, "OV7670 Init OK   ", GREEN);
    printf("OV7670 init OK\r\n");

    OV7670_OE(0);                   /* 使能 FIFO 数据输出 */
    btim_timx_int_init(10000, 7200 - 1);    /* 1 秒中断，打印帧率 */
    exti_ov7670_vsync_init();       /* 使能 VSYNC 外部中断 */

    while (1)
    {
        ov7670_camera_refresh();
    }
}
