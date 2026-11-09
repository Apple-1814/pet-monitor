#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正版：只重新生成两张流程图
  - flow-camera-fifo.png  （ISR 与主循环分开）
  - flow-remote.png       （跨列箭头改为间隙折线，不斜穿方框）
运行前先运行 make_figures.py 生成其它图。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_figures as mf
from make_figures import (
    box, hexagon, arrow, label, new_canvas,
    F, F_TITLE, F_BOX, F_BOX_S, F_LABEL, F_SMALL, OUT,
)


# ----------------------------- 修正版：摄像头初始化 + FIFO 读帧 -----------------------------
def fig_camera_fifo_fixed():
    W, H = 1700, 1750
    img, d = new_canvas(W, H, "OV7670 初始化 + FIFO 读帧流程图")

    # ---------- 左列：初始化 ----------
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
        if kind in ("start", "end"):
            box(d, (lx, yy, lx + lw, yy + lh), text, "#e8f7ef", "#2e8b57", F(24, True), radius=38)
        elif kind == "dec":
            hexagon(d, (lx - 20, yy, lx + lw + 20, yy + lh + 6), text, "#fff3e0", "#d35400", F(22, True))
        else:
            box(d, (lx, yy, lx + lw, yy + lh), text, "#ffffff", "#2f6fb2", F_BOX_S)
        lb.append((lx, yy, lx + lw, yy + lh, kind))
        yy += lh + lg

    for i in range(len(lb) - 1):
        b, n = lb[i], lb[i + 1]
        arrow(d, [((b[0] + b[2]) / 2, b[3]), ((n[0] + n[2]) / 2, n[1])], "#333", 4)

    # PID 判断：是 -> 写寄存器；否 -> 右侧“返回错误”
    dec = lb[6]
    label(d, ((dec[0] + dec[2]) / 2 + 24, dec[3] + 10), "是", F_LABEL, "#2e8b57", "lm")
    err = (760, dec[1] - 8, 920, dec[3] + 8)
    box(d, err, "返回错误\n主循环重试", "#fff0f0", "#c0392b", F_BOX_S)
    arrow(d, [(lx + lw + 20, (dec[1] + dec[3]) / 2), (err[0], (err[1] + err[3]) / 2)], "#c0392b", 3)
    label(d, (755, (dec[1] + dec[3]) / 2 - 22), "否", F_LABEL, "#c0392b", "mm")

    # ---------- 右列：VSYNC 中断 ----------
    rx, rw = 940, 660
    start = (rx, 120, rx + rw, 200)
    box(d, start, "VSYNC 下降沿中断", "#e8f7ef", "#2e8b57", F(24, True), radius=38)

    dec2 = (rx - 20, 240, rx + rw + 20, 330)
    hexagon(d, dec2, "上一帧已处理？", "#fff3e0", "#d35400", F(22, True))

    yes = (rx, 380, rx + rw * 0.48, 480)
    no = (rx + rw * 0.52, 380, rx + rw, 480)
    box(d, yes, "WRST 低脉冲\nWEN=1\n置帧标志", "#ffffff", "#2f6fb2", F_BOX_S)
    box(d, no, "WEN=0\n停止写 FIFO", "#ffffff", "#2f6fb2", F_BOX_S)

    irq_end = (rx + rw * 0.25, 530, rx + rw * 0.75, 610)
    box(d, irq_end, "中断返回", "#e8f7ef", "#2e8b57", F(24, True), radius=38)

    arrow(d, [(rx + rw / 2, 200), (rx + rw / 2, 240)], "#333", 4)
    arrow(d, [(rx + rw * 0.35, 330), (rx + rw * 0.24, 380)], "#2e8b57", 4)
    label(d, (rx + rw * 0.32, 350), "是", F_LABEL, "#2e8b57", "lm")
    arrow(d, [(rx + rw * 0.65, 330), (rx + rw * 0.76, 380)], "#c0392b", 4)
    label(d, (rx + rw * 0.69, 350), "否", F_LABEL, "#c0392b", "lm")
    arrow(d, [(rx + rw * 0.24, 480), (rx + rw * 0.40, 530)], "#333", 4)
    arrow(d, [(rx + rw * 0.76, 480), (rx + rw * 0.60, 530)], "#333", 4)

    # 分隔线
    d.line([(rx, 650), (rx + rw, 650)], fill="#999", width=2)
    d.text((rx, 630), "主循环（与中断异步）", font=F_SMALL, fill="#666")

    # ---------- 右列：主循环读帧 ----------
    items = [
        "主循环检测帧标志",
        "延时 10ms\n让写指针领先",
        "RRST 低脉冲复位读指针\nRCLK 高",
        "设置 LCD 窗口\n(80,40,320,240)",
        "循环 240 行 × 320 列\n读高/低字节，写 LCD_RAM",
        "裁剪区 192×144\n转 RGB332 填远程缓冲",
        "清帧标志，帧计数++",
    ]
    bs = []
    yy = 690
    bh = 80
    bg = 28
    for it in items:
        box(d, (rx, yy, rx + rw, yy + bh), it, "#ffffff", "#2f6fb2", F_BOX_S)
        bs.append((rx, yy, rx + rw, yy + bh))
        yy += bh + bg

    for a, b in zip(bs, bs[1:]):
        arrow(d, [((a[0] + a[2]) / 2, a[3]), ((b[0] + b[2]) / 2, b[1])], "#333", 4)

    # 循环线
    last = bs[-1]
    arrow(d, [((last[0] + last[2]) / 2, last[3]), ((last[0] + last[2]) / 2, last[3] + 50),
              (rx - 60, last[3] + 50), (rx - 60, 730), (rx, 730)], "#2e8b57", 4)
    label(d, (rx - 70, last[3] + 50), "下一帧", F_LABEL, "#2e8b57", "rm")

    d.text((90, 1650), "注：字节序为高字节在前；LCD 扫描方向 U2D_L2R；远程采样为中心 192×144。",
           font=F_SMALL, fill="#555")
    img.save(OUT / "flow-camera-fifo.png")


# ----------------------------- 修正版：远程推流 / PC 中继 / Web APP -----------------------------
def fig_remote_fixed():
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

    # 跨列折线：在列间隙里走竖线，不斜穿方框
    y_stm = (sb[4][1] + sb[4][3]) / 2
    y_pc = (pb[0][1] + pb[0][3]) / 2
    gx = sb[4][2] + 70
    arrow(d, [(sb[4][2], y_stm), (gx, y_stm), (gx, y_pc), (pb[0][0], y_pc)], "#b7791f", 4)
    d.rounded_rectangle([gx - 52, 470, gx + 52, 510], radius=6, fill="white")
    d.text((gx, 490), "RGB332 帧", font=F_SMALL, fill="#8a5a00", anchor="mm")

    y_pc2 = (pb[4][1] + pb[4][3]) / 2
    y_ph = (hb[0][1] + hb[0][3]) / 2
    gx2 = pb[4][2] + 70
    arrow(d, [(pb[4][2], y_pc2), (gx2, y_pc2), (gx2, y_ph), (hb[0][0], y_ph)], "#2e8b57", 4)
    d.rounded_rectangle([gx2 - 40, 470, gx2 + 40, 510], radius=6, fill="white")
    d.text((gx2, 490), "HTTP", font=F_SMALL, fill="#2e8b57", anchor="mm")

    # 说明
    d.rounded_rectangle([80, 950, 1920, 1120], radius=16, fill="#f7fbff", outline="#1f3b73", width=3)
    d.text((110, 975), "关键设计：", font=F(24, True), fill="#1f3b73")
    d.text((110, 1020), "① 帧头 + 长度 + 16 位累加和：PC 端校验失败直接丢帧，避免彩色横条上屏。", font=F_SMALL, fill="#222")
    d.text((110, 1055), "② 串口读帧与 JPEG 编码分线程：避免编码阻塞导致 CH340 驱动缓冲溢出丢字节。", font=F_SMALL, fill="#222")
    d.text((110, 1090), "③ 手机端用 JPEG 轮询而不是 MJPEG：兼容所有手机浏览器（MJPEG 在部分手机不显示）。", font=F_SMALL, fill="#222")

    img.save(OUT / "flow-remote.png")


if __name__ == "__main__":
    fig_camera_fifo_fixed()
    fig_remote_fixed()
    print("fixed figures written to", OUT)
