#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成课程设计报告用图：
  - system-block.png       系统总体框图
  - flow-main.png          主程序流程图
  - flow-camera-fifo.png   OV7670 初始化 + FIFO 读帧流程图
  - flow-remote.png        远程推流 / PC 中继 / Web APP 流程图
  - hardware-interface.png 硬件接口电路（接口级原理图）
  - hardware-interface.pdf PDF 版（报告/提交用）

运行：
  C:\\Users\\18149\\miniconda3\\python.exe scripts\\make_figures.py
"""

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "docs" / "deliverables" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# ----------------------------- 字体 -----------------------------
def F(size, bold=False):
    path = "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", size)

F_TITLE = F(40, True)
F_BOX = F(24)
F_BOX_S = F(20)
F_LABEL = F(20)
F_SMALL = F(17)


# ----------------------------- 绘图工具 -----------------------------
def text_center(d, box, text, font, fill="#111"):
    x0, y0, x1, y1 = box
    b = d.multiline_textbbox((0, 0), text, font=font, spacing=6, align="center")
    tw, th = b[2] - b[0], b[3] - b[1]
    d.multiline_text(
        (x0 + (x1 - x0 - tw) / 2 - b[0], y0 + (y1 - y0 - th) / 2 - b[1]),
        text, font=font, fill=fill, spacing=6, align="center",
    )


def box(d, xy, text, fill="#ffffff", outline="#2f6fb2", font=None, radius=16, width=3, text_fill="#111"):
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    text_center(d, xy, text, font or F_BOX, text_fill)


def hexagon(d, xy, text, fill="#fff3e0", outline="#d35400", font=None, width=3):
    x0, y0, x1, y1 = xy
    w, h = x1 - x0, y1 - y0
    k = w * 0.12
    pts = [(x0 + k, y0), (x1 - k, y0), (x1, y0 + h / 2), (x1 - k, y1), (x0 + k, y1), (x0, y0 + h / 2)]
    d.polygon(pts, fill=fill, outline=outline, width=width)
    text_center(d, xy, text, font or F_BOX, "#111")


def arrow(d, points, color="#333333", width=4, head=16):
    """折线箭头，points=[(x,y), ...]"""
    for i in range(len(points) - 1):
        d.line([points[i], points[i + 1]], fill=color, width=width, joint="curve")
    p1, p2 = points[-2], points[-1]
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    if L == 0:
        return
    ux, uy = dx / L, dy / L
    left = (p2[0] - head * ux + head * 0.5 * uy, p2[1] - head * uy - head * 0.5 * ux)
    right = (p2[0] - head * ux - head * 0.5 * uy, p2[1] - head * uy + head * 0.5 * ux)
    d.polygon([p2, left, right], fill=color)


def label(d, xy, text, font=None, fill="#333", anchor="mm"):
    d.text(xy, text, font=font or F_LABEL, fill=fill, anchor=anchor)


def new_canvas(w, h, title):
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 24), title, font=F_TITLE, fill="#111")
    return img, d


# ----------------------------- 1. 系统总体框图 -----------------------------
def fig_system():
    W, H = 2000, 1200
    img, d = new_canvas(W, H, "宠物视频监控系统 · 总体框图")

    mcu = (760, 440, 1240, 720)
    cam = (80, 330, 640, 780)
    lcd = (660, 880, 1340, 1120)
    uart = (1540, 300, 1940, 500)
    pc = (1540, 560, 1940, 760)
    phone = (1540, 820, 1940, 1040)
    swd = (1540, 70, 1940, 240)

    box(d, cam, "OV7670 + AL422 FIFO\n（22 脚模块）\n\nD0–D7 / VSYNC\nWRST / RRST / RCLK\nWEN / OE / SCCB", "#eaf4ff", "#2f6fb2")
    box(d, mcu, "STM32F103ZET6\nCortex-M3  72MHz\n512KB Flash / 64KB RAM\n\nLCD 显示 + 远程 RGB332", "#ffffff", "#1f3b73", F(28, True))
    box(d, lcd, "NT35310  3.5 寸 LCD\n480×320 横屏（横屏使用）\nFSMC 16 位并口\n320×240 居中显示", "#eefbf4", "#2e8b57")
    box(d, uart, "USART1  PA9/PA10\n1.5Mbaud  8N1\nCH340 → USB_232 → COM22", "#fff8e8", "#b7791f")
    box(d, pc, "PC 中继\nRGB332 → JPEG\nHTTP: /snapshot.jpg", "#fff8e8", "#b7791f")
    box(d, phone, "手机 Web APP\n同一 WiFi\nJPEG 轮询 5fps", "#fff8e8", "#b7791f")
    box(d, swd, "ST-Link V2\nSWDIO / SWCLK\n烧录 + 调试", "#f3f0ff", "#6b46c1")

    # 数据流
    arrow(d, [(640, 520), (760, 520)], "#2f6fb2", 5)
    label(d, (650, 470), "DVP/FIFO", F_SMALL, anchor="lm")
    arrow(d, [(640, 620), (760, 620)], "#2f6fb2", 5)
    label(d, (700, 650), "SCCB 配置", F_SMALL)

    arrow(d, [(1000, 720), (1000, 880)], "#2e8b57", 5)
    label(d, (1070, 800), "FSMC RGB565", F_SMALL)

    arrow(d, [(1240, 500), (1540, 430)], "#b7791f", 5)
    label(d, (1380, 440), "RGB332 192×144", F_SMALL)
    arrow(d, [(1740, 500), (1740, 560)], "#b7791f", 5)
    label(d, (1800, 530), "USB/COM22", F_SMALL)
    arrow(d, [(1740, 760), (1740, 820)], "#b7791f", 5)
    label(d, (1800, 790), "WiFi", F_SMALL)

    arrow(d, [(1740, 240), (1740, 300)], "#6b46c1", 4)
    label(d, (1800, 270), "SWD", F_SMALL)

    # 本地/远程标注
    d.rounded_rectangle([80, 1030, 600, 1130], radius=14, fill="#f7fbff", outline="#2f6fb2", width=2)
    d.text((100, 1050), "本地链路：OV7670 → FIFO → GPIO 读取 → LCD", font=F_SMALL, fill="#1f3b73")
    d.rounded_rectangle([1400, 1080, 1940, 1160], radius=14, fill="#fffaf0", outline="#b7791f", width=2)
    d.text((1420, 1098), "远程链路：FIFO → RGB332 → USART1 → PC 中继 → 手机", font=F_SMALL, fill="#8a5a00")

    img.save(OUT / "system-block.png")


# ----------------------------- 2. 主程序流程图 -----------------------------
def fig_main():
    W, H = 1400, 1800
    img, d = new_canvas(W, H, "主程序流程图")

    x, w = 430, 540
    y = 110
    h = 90
    gap = 55
    items = [
        ("开始", "start"),
        ("系统时钟 72MHz / delay_init\nUSART1 1.5Mbaud + TX DMA", "proc"),
        ("LCD 初始化\nNT35310，480×320 横屏", "proc"),
        ("OV7670 初始化\nSCCB、PID/VER、QVGA RGB565 寄存器表", "proc"),
        ("使能 FIFO 输出（OE=0）\n使能 VSYNC 外部中断", "proc"),
        ("收到帧标志？", "dec"),
        ("读 FIFO 一帧\n写 LCD（320×240 居中）", "proc"),
        ("DMA 空闲？", "dec"),
        ("中心 192×144 → RGB332\n计算校验和 → 组帧 → DMA 发送", "proc"),
    ]
    boxes = []
    for text, kind in items:
        if kind == "start":
            box(d, (x, y, x + w, y + h), text, "#e8f7ef", "#2e8b57", F(26, True), radius=40)
        elif kind == "dec":
            hexagon(d, (x - 60, y, x + w + 60, y + h + 20), text, "#fff3e0", "#d35400", F(24, True))
        else:
            box(d, (x, y, x + w, y + h), text, "#ffffff", "#2f6fb2", F_BOX)
        boxes.append((x, y, x + w, y + h, kind))
        y += h + gap

    # 主链箭头
    for i in range(len(boxes) - 1):
        b = boxes[i]
        n = boxes[i + 1]
        arrow(d, [((b[0] + b[2]) / 2, b[3]), ((n[0] + n[2]) / 2, n[1])], "#333", 4)

    # 决策 1 的“否”回环（回到判断本身）
    bx = boxes[5]
    cx = (bx[0] + bx[2]) / 2
    arrow(d, [(bx[2] + 60, (bx[1] + bx[3]) / 2), (bx[2] + 140, (bx[1] + bx[3]) / 2),
              (bx[2] + 140, bx[1] - 20), (cx, bx[1] - 20)], "#999", 3)
    label(d, (bx[2] + 160, (bx[1] + bx[3]) / 2), "否", F_LABEL, "#666", "lm")

    # 决策 2 的“否”跳过发送
    b8 = boxes[7]
    b9 = boxes[8]
    arrow(d, [(b8[2] + 60, (b8[1] + b8[3]) / 2), (b8[2] + 150, (b8[1] + b8[3]) / 2),
              (b8[2] + 150, b9[3] + 40), ((b9[0] + b9[2]) / 2, b9[3] + 40)], "#999", 3)
    label(d, (b8[2] + 170, (b8[1] + b8[3]) / 2), "否", F_LABEL, "#666", "lm")

    # 循环回主判断
    last = boxes[-1]
    arrow(d, [((last[0] + last[2]) / 2, last[3]), ((last[0] + last[2]) / 2, last[3] + 80),
              (x - 190, last[3] + 80), (x - 190, (boxes[5][1] + boxes[5][3]) / 2),
              (boxes[5][0], (boxes[5][1] + boxes[5][3]) / 2)], "#2e8b57", 4)
    label(d, (x - 210, last[3] + 80), "主循环", F_LABEL, "#2e8b57", "rm")

    # 说明
    d.text((80, 1680), "注：VSYNC 中断负责 WRST/WEN 时序；主循环读帧并同时完成 LCD 显示与远程 RGB332 采样。",
           font=F_SMALL, fill="#555")

    img.save(OUT / "flow-main.png")


# ----------------------------- 3. 摄像头初始化 + FIFO 读帧 -----------------------------
def fig_camera_fifo():
    W, H = 1700, 2000
    img, d = new_canvas(W, H, "OV7670 初始化 + FIFO 读帧流程图")

    # 左列：初始化
    lx, lw = 90, 620
    ly, lh, lg = 120, 86, 38
    left = [
        ("开始 OV7670_Init", "start"),
        ("GPIO 初始化\nVSYNC/WRST/RRST/OE/RCLK/WEN/D0-D7", "proc"),
        ("关闭 JTAG，保留 SWD\nPB3/PB4 作普通 IO", "proc"),
        ("SCCB 初始化\nSCL=PD3，SDA=PG13", "proc"),
        ("写 COM7=0x80 软复位\n延时 50ms", "proc"),
        ("读 PID(0x0A) / VER(0x0B)", "proc"),
        ("PID=0x76 且 VER=0x73？", "dec"),
        ("写 170+ 条 QVGA RGB565\n初始化寄存器", "proc"),
        ("返回成功", "end"),
    ]
    lb = []
    yy = ly
    for text, kind in left:
        if kind == "start":
            box(d, (lx, yy, lx + lw, yy + lh), text, "#e8f7ef", "#2e8b57", F(24, True), radius=38)
        elif kind == "end":
            box(d, (lx, yy, lx + lw, yy + lh), text, "#e8f7ef", "#2e8b57", F(24, True), radius=38)
        elif kind == "dec":
            hexagon(d, (lx - 40, yy, lx + lw + 40, yy + lh + 10), text, "#fff3e0", "#d35400", F(22, True))
        else:
            box(d, (lx, yy, lx + lw, yy + lh), text, "#ffffff", "#2f6fb2", F_BOX_S)
        lb.append((lx, yy, lx + lw, yy + lh, kind))
        yy += lh + lg

    for i in range(len(lb) - 1):
        b, n = lb[i], lb[i + 1]
        arrow(d, [((b[0] + b[2]) / 2, b[3]), ((n[0] + n[2]) / 2, n[1])], "#333", 4)

    # 失败分支
    bdec = lb[6]
    arrow(d, [(bdec[0], (bdec[1] + bdec[3]) / 2), (lx - 80, (bdec[1] + bdec[3]) / 2),
              (lx - 80, lb[-1][1] - 100), (lx, lb[-1][1] - 100)], "#c0392b", 3)
    label(d, (lx - 95, (bdec[1] + bdec[3]) / 2), "否：返回错误\n主循环重试", F_SMALL, "#c0392b", "rm")

    # 右列：VSYNC + 读帧
    rx, rw = 940, 660
    ry = 120
    right = [
        ("VSYNC 下降沿中断", "start"),
        ("上一帧已处理？", "dec"),
        ("WRST 低脉冲\nWEN=1\n置帧标志", "proc"),
        ("WEN=0\n停止写 FIFO", "proc"),
        ("主循环检测帧标志", "proc"),
        ("延时 10ms\n让写指针领先", "proc"),
        ("RRST 低脉冲复位读指针\nRCLK 高", "proc"),
        ("设置 LCD 窗口\n(80,40,320,240)", "proc"),
        ("循环 240 行 × 320 列\n读高字节/低字节\n写 LCD_RAM", "proc"),
        ("裁剪区 192×144\n转 RGB332 填远程缓冲", "proc"),
        ("清帧标志\n帧计数++", "proc"),
    ]
    rb = []
    yy = ry
    for text, kind in right:
        if kind == "start":
            box(d, (rx, yy, rx + rw, yy + lh), text, "#e8f7ef", "#2e8b57", F(24, True), radius=38)
        elif kind == "dec":
            hexagon(d, (rx - 30, yy, rx + rw + 30, yy + lh + 8), text, "#fff3e0", "#d35400", F(22, True))
        else:
            box(d, (rx, yy, rx + rw, yy + lh), text, "#ffffff", "#2f6fb2", F_BOX_S)
        rb.append((rx, yy, rx + rw, yy + lh, kind))
        yy += lh + 34

    # 右列主链（跳过“WEN=0”分支，单独画）
    chain = [0, 1, 2, 4, 5, 6, 7, 8, 9, 10]
    for a, b in zip(chain, chain[1:]):
        bb, nn = rb[a], rb[b]
        arrow(d, [((bb[0] + bb[2]) / 2, bb[3]), ((nn[0] + nn[2]) / 2, nn[1])], "#333", 4)
    # 判断“否”到 WEN=0
    b1, b3 = rb[1], rb[3]
    arrow(d, [((b1[0] + b1[2]) / 2, b1[3]), ((b3[0] + b3[2]) / 2, b3[1])], "#c0392b", 3)
    label(d, ((b1[0] + b1[2]) / 2 + 20, (b1[3] + b3[1]) / 2), "否", F_LABEL, "#c0392b", "lm")
    # 判断“是”到 WRST
    b2 = rb[2]
    label(d, ((b1[0] + b1[2]) / 2 + 20, (b1[3] + b2[1]) / 2 - 10), "是", F_LABEL, "#2e8b57", "lm")

    # 循环回“主循环检测帧标志”
    arrow(d, [((rb[-1][0] + rb[-1][2]) / 2, rb[-1][3]), ((rb[-1][0] + rb[-1][2]) / 2, rb[-1][3] + 60),
              (rx - 90, rb[-1][3] + 60), (rx - 90, (rb[4][1] + rb[4][3]) / 2),
              (rb[4][0], (rb[4][1] + rb[4][3]) / 2)], "#2e8b57", 4)
    label(d, (rx - 110, rb[-1][3] + 60), "下一帧", F_LABEL, "#2e8b57", "rm")

    d.text((90, 1900), "注：字节序为高字节在前；LCD 扫描方向 U2D_L2R；远程采样为中心 192×144。",
           font=F_SMALL, fill="#555")
    img.save(OUT / "flow-camera-fifo.png")


# ----------------------------- 4. 远程推流 / PC 中继 / Web APP -----------------------------
def fig_remote():
    W, H = 2000, 1200
    img, d = new_canvas(W, H, "远程推流 + PC 中继 + 手机 Web APP 流程图")

    col_w = 520
    xs = [80, 740, 1400]
    ys = 150
    h = 100
    gap = 55

    stm = [
        "读 FIFO 一帧\n（320×240 RGB565）",
        "中心裁剪 192×144\n逐像素转 RGB332",
        "计算 16 位累加和\n（payload 逐字节相加）",
        "组帧：AA 55 + 长度\n+ 校验和 + payload",
        "USART1 TX DMA\n1.5Mbaud → CH340/COM22",
    ]
    pc = [
        "串口线程\n找 AA 55 / 读长度",
        "校验和验证\n失败丢帧并重同步",
        "有效帧入队\n（生产者/消费者）",
        "JPEG 线程\nRGB332 → RGB888 → JPEG",
        "HTTP 服务\n/snapshot.jpg /status /stream",
    ]
    phone = [
        "手机浏览器\n打开 Web APP",
        "每 200ms 拉取\n/snapshot.jpg",
        "显示画面 / FPS / 分辨率\n支持全屏",
    ]

    def column(x, title, items, color, fill):
        d.text((x, 100), title, font=F(28, True), fill=color)
        bs = []
        yy = ys
        for it in items:
            box(d, (x, yy, x + col_w, yy + h), it, fill, color, F_BOX_S)
            bs.append((x, yy, x + col_w, yy + h))
            yy += h + gap
        for a, b in zip(bs, bs[1:]):
            arrow(d, [((a[0] + a[2]) / 2, a[3]), ((b[0] + b[2]) / 2, b[1])], "#333", 4)
        return bs

    sb = column(xs[0], "STM32 固件", stm, "#2f6fb2", "#ffffff")
    pb = column(xs[1], "PC 中继（Python）", pc, "#b7791f", "#fffaf0")
    hb = column(xs[2], "手机 Web APP", phone, "#2e8b57", "#eefbf4")

    # 列间箭头
    arrow(d, [(sb[4][2], (sb[4][1] + sb[4][3]) / 2), (pb[0][0], (pb[0][1] + pb[0][3]) / 2)], "#b7791f", 5)
    label(d, ((sb[4][2] + pb[0][0]) / 2, (sb[4][1] + sb[4][3]) / 2 - 30), "AA 55 + len + sum + RGB332", F_SMALL, "#8a5a00")
    arrow(d, [(pb[4][2], (pb[4][1] + pb[4][3]) / 2), (hb[0][0], (hb[0][1] + hb[0][3]) / 2)], "#2e8b57", 5)
    label(d, ((pb[4][2] + hb[0][0]) / 2, (pb[4][1] + pb[4][3]) / 2 - 30), "WiFi / HTTP", F_SMALL, "#2e8b57")

    # 说明
    d.rounded_rectangle([80, 950, 1920, 1120], radius=16, fill="#f7fbff", outline="#1f3b73", width=3)
    d.text((110, 975), "关键设计：", font=F(24, True), fill="#1f3b73")
    d.text((110, 1020), "① 帧头 + 长度 + 16 位累加和：PC 端校验失败直接丢帧，避免彩色横条上屏。", font=F_SMALL, fill="#222")
    d.text((110, 1055), "② 串口读帧与 JPEG 编码分线程：避免编码阻塞导致 CH340 驱动缓冲溢出丢字节。", font=F_SMALL, fill="#222")
    d.text((110, 1090), "③ 手机端用 JPEG 轮询而不是 MJPEG：兼容所有手机浏览器（MJPEG 在部分手机不显示）。", font=F_SMALL, fill="#222")

    img.save(OUT / "flow-remote.png")


# ----------------------------- 5. 硬件接口电路（接口级原理图） -----------------------------
def fig_hardware():
    W, H = 2200, 1600
    img, d = new_canvas(W, H, "硬件接口电路（接口级原理图）")

    mcu = (820, 560, 1380, 900)
    box(d, mcu, "STM32F103ZET6\nLQFP144\n3.3V / GND\nFSMC · USART1 · GPIO · SWD", "#ffffff", "#1f3b73", F(28, True))

    # 摄像头
    cam = (70, 300, 720, 980)
    box(d, cam, "", "#eaf4ff", "#2f6fb2", F_BOX)
    d.text((100, 325), "OV7670 + AL422 FIFO（22 脚模块）", font=F(26, True), fill="#1f3b73")
    cam_lines = [
        ("3V3", "P6-17", "3.3V"),
        ("GND", "P6-18", "GND"),
        ("SIOC", "P6-2", "PD3"),
        ("SIOD", "P6-4", "PG13"),
        ("VSY", "P6-15", "PA8"),
        ("WRST", "P6-1", "PD6"),
        ("WR", "P6-16", "PB3"),
        ("RRST", "P6-3", "PG14"),
        ("RCK", "P6-14", "PB4"),
        ("OE", "P6-5", "PG15"),
        ("D0–D7", "P6-6..13", "PC0–PC7"),
        ("RST", "—", "3.3V（10K）"),
        ("PWDN", "—", "GND"),
        ("STR/HREF", "—", "悬空"),
    ]
    yy = 375
    for a, b, c in cam_lines:
        d.text((105, yy), a, font=F_SMALL, fill="#111")
        d.text((300, yy), b, font=F_SMALL, fill="#555")
        d.text((500, yy), c, font=F_SMALL, fill="#1f3b73")
        yy += 40

    # LCD
    lcd = (650, 1100, 1500, 1480)
    box(d, lcd, "", "#eefbf4", "#2e8b57", F_BOX)
    d.text((680, 1125), "NT35310 3.5 寸 LCD（480×320，34 脚）", font=F(26, True), fill="#1b5e20")
    lcd_lines = [
        ("CS", "PG12 / FSMC_NE4"),
        ("RS", "PG0 / FSMC_A10"),
        ("WR / RD", "PD5 / PD4"),
        ("BL", "PB0"),
        ("D0–D15", "PD0/1/8/9/10/14/15 + PE7–PE15"),
        ("RST", "板级 RESET"),
    ]
    yy = 1175
    for a, b in lcd_lines:
        d.text((685, yy), a, font=F_SMALL, fill="#111")
        d.text((835, yy), b, font=F_SMALL, fill="#1b5e20")
        yy += 42

    # USART1 / CH340
    uart = (1520, 300, 2100, 560)
    box(d, uart, "USART1 → CH340 → USB_232\n\nPA9(TX) / PA10(RX)\n1.5Mbaud，8N1\nPC: COM22", "#fff8e8", "#b7791f", F_BOX_S)
    # SWD
    swd = (1520, 640, 2100, 900)
    box(d, swd, "ST-Link V2（SWD）\n\n3.3V → JTAG 1/2\nSWDIO → JTAG 7\nSWCLK → JTAG 9\nGND → JTAG 4/6/8", "#f3f0ff", "#6b46c1", F_BOX_S)
    # 电源
    pwr = (1520, 980, 2100, 1180)
    box(d, pwr, "电源\n\n3.3V：MCU / OV7670 / LCD\n5V：LCD 背光 / USB\nGND 共地", "#f5f5f5", "#555", F_BOX_S)

    # 连线
    arrow(d, [(720, 520), (820, 620)], "#2f6fb2", 5)
    label(d, (770, 545), "P6 18 针", F_SMALL, "#1f3b73")
    arrow(d, [(1000, 900), (1000, 1100)], "#2e8b57", 5)
    label(d, (1030, 1000), "FSMC 16 位", F_SMALL, "#1b5e20")
    arrow(d, [(1380, 620), (1520, 450)], "#b7791f", 5)
    label(d, (1450, 510), "USART1", F_SMALL, "#8a5a00")
    arrow(d, [(1380, 720), (1520, 740)], "#6b46c1", 5)
    label(d, (1450, 700), "SWD", F_SMALL, "#4a2f9a")
    arrow(d, [(1380, 840), (1520, 1050)], "#555", 4)
    label(d, (1450, 960), "3.3V/GND", F_SMALL, "#333")

    # 说明
    d.rounded_rectangle([70, 1520, 2100, 1570], radius=10, fill="#f7fbff", outline="#1f3b73", width=2)
    d.text((90, 1532), "注：本图为接口级原理图，摄像头 P6 为板载 2×9 接口；RST/PWDN 在模块侧外接 3.3V/GND，STR/HREF 悬空。",
           font=F_SMALL, fill="#1f3b73")

    img.save(OUT / "hardware-interface.png")
    img.save(OUT / "hardware-interface.pdf", "PDF", resolution=200.0)


if __name__ == "__main__":
    fig_system()
    fig_main()
    fig_camera_fifo()
    fig_remote()
    fig_hardware()
    print("figures written to", OUT)
    for p in sorted(OUT.glob("*")):
        print(" ", p.name)
