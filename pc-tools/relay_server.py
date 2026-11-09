#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宠物视频监控 · PC 中继 + 手机 Web APP

数据链路（当前阶段）：
    STM32 USART1(COM22, 921600) --RGB332 QQVGA帧--> PC 本脚本 --MJPEG--> 手机浏览器

用法：
    C:\\Users\\18149\\miniconda3\\python.exe pc-tools\\relay_server.py
    C:\\Users\\18149\\miniconda3\\python.exe pc-tools\\relay_server.py --no-serial   # 测试画面
    C:\\Users\\18149\\miniconda3\\python.exe pc-tools\\relay_server.py --port COM22 --baud 921600 --http-port 8000

帧协议 v1：
    0xAA 0x55 + 4 字节长度(小端) + RGB332 像素数据（160x120 = 19200 字节）
"""

import argparse
import io
import json
import math
import queue
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception as e:
    raise SystemExit("需要 Pillow：pip install pillow\n" + str(e))

try:
    import serial
except Exception:
    serial = None


# ----------------------------- 全局状态 -----------------------------
class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.jpeg = b""
        self.frame_count = 0
        self.serial_frames = 0
        self.checksum_errors = 0
        self.last_frame_time = 0.0
        self.fps = 0.0
        self.serial_connected = False
        self.serial_port = ""
        self.serial_baud = 0
        self.resolution = "160x120"
        self.last_error = ""

    def set_jpeg(self, jpeg: bytes):
        with self.lock:
            now = time.time()
            if self.last_frame_time:
                dt = now - self.last_frame_time
                if dt > 0:
                    inst = 1.0 / dt
                    self.fps = inst if self.fps == 0 else (self.fps * 0.8 + inst * 0.2)
            self.last_frame_time = now
            self.jpeg = jpeg
            self.frame_count += 1


STATE = State()
HTML_PATH = Path(__file__).resolve().parent / "web" / "index.html"
FRAME_QUEUE = queue.Queue(maxsize=3)      # 串口线程 -> JPEG 工作线程


# ----------------------------- 工具 -----------------------------
def rgb332_to_jpeg(payload: bytes, width: int, height: int, quality: int = 60) -> bytes:
    """把 RGB332 字节流转成 JPEG。RGB332: RRRGGGBB"""
    if len(payload) != width * height:
        raise ValueError(f"payload size {len(payload)} != {width*height}")

    palette = []
    for i in range(256):
        r = ((i >> 5) & 0x07) * 255 // 7
        g = ((i >> 2) & 0x07) * 255 // 7
        b = (i & 0x03) * 255 // 3
        palette.extend((r, g, b))

    img = Image.frombytes("P", (width, height), payload)
    img.putpalette(palette)
    img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality)
    return out.getvalue()


def make_test_jpeg(width: int, height: int, tick: float) -> bytes:
    """没有串口时生成的测试画面，方便先验证手机访问。"""
    img = Image.new("RGB", (width, height), (18, 24, 38))
    d = ImageDraw.Draw(img)

    # 渐变背景
    for y in range(height):
        c = int(20 + 40 * y / max(1, height - 1))
        d.line([(0, y), (width, y)], fill=(c, c + 8, min(255, c + 24)))

    # 移动的亮条
    x = int((tick * 40) % (width + 60)) - 30
    d.rectangle([x, 0, x + 18, height], fill=(0, 180, 255))

    # 文字
    try:
        font_big = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 16)
        font_small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 11)
    except Exception:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    d.text((8, 10), "PET MONITOR", font=font_big, fill=(255, 255, 255))
    d.text((8, 30), "PC Relay Test", font=font_small, fill=(180, 230, 255))
    d.text((8, height - 22), time.strftime("%H:%M:%S"), font=font_small, fill=(200, 200, 200))
    d.text((width - 78, height - 22), "WAIT UART", font=font_small, fill=(255, 200, 80))

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=70)
    return out.getvalue()


def guess_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


# ----------------------------- 串口读帧 -----------------------------
def serial_reader(port: str, baud: int, width: int, height: int, quality: int, state: State):
    if serial is None:
        state.last_error = "pyserial 未安装"
        return

    expected = width * height
    state.serial_port = port
    state.serial_baud = baud

    while True:
        try:
            ser = serial.Serial(port, baud, timeout=0.02)
            # 关键：释放 DTR/RTS，避免触发板载一键下载电路
            try:
                ser.dtr = False
                ser.rts = False
            except Exception:
                pass
            ser.reset_input_buffer()
            state.serial_connected = True
            state.last_error = ""
            print(f"[UART] {port} @ {baud} opened")
            buf = bytearray()

            while True:
                # 一次把驱动缓冲区里的数据全部读走，避免高波特率下溢出
                n = ser.in_waiting
                chunk = ser.read(n if n > 0 else 1)
                if chunk:
                    buf.extend(chunk)

                # 解析帧：AA 55 + 4 字节长度(小端) + payload
                while True:
                    idx = buf.find(b"\xAA\x55")
                    if idx < 0:
                        # 保留最后 1 字节，避免跨包漏掉 AA
                        if len(buf) > 1:
                            del buf[:-1]
                        break
                    if idx > 0:
                        del buf[:idx]
                    if len(buf) < 8:
                        break
                    length = int.from_bytes(buf[2:6], "little")
                    if length <= 0 or length > 4 * 1024 * 1024:
                        del buf[:2]
                        continue
                    if len(buf) < 8 + length:
                        break
                    checksum = int.from_bytes(buf[6:8], "little")
                    payload = bytes(buf[8:8 + length])
                    del buf[:8 + length]

                    if length != expected:
                        state.last_error = f"帧长 {length} != {expected}"
                        continue

                    calc = sum(payload) & 0xFFFF
                    if calc != checksum:
                        with state.lock:
                            state.checksum_errors += 1
                        state.last_error = f"校验和 {calc:04X} != {checksum:04X}"
                        continue

                    try:
                        FRAME_QUEUE.put_nowait(payload)
                    except queue.Full:
                        # 丢最旧的一帧，保持低延迟
                        try:
                            FRAME_QUEUE.get_nowait()
                        except queue.Empty:
                            pass
                        try:
                            FRAME_QUEUE.put_nowait(payload)
                        except queue.Full:
                            pass

                if len(buf) > 8 * 1024 * 1024:
                    del buf[:-1024]

        except Exception as e:
            state.serial_connected = False
            state.last_error = str(e)
            print(f"[UART] {port} 打开/读取失败: {e}；2 秒后重试")
            time.sleep(2.0)


def frame_worker(width: int, height: int, quality: int, state: State):
    """独立线程做 RGB332 -> JPEG，避免阻塞串口读取。"""
    while True:
        payload = FRAME_QUEUE.get()
        try:
            jpeg = rgb332_to_jpeg(payload, width, height, quality)
            state.set_jpeg(jpeg)
            with state.lock:
                state.serial_frames += 1
        except Exception as e:
            state.last_error = f"解码失败: {e}"


def test_pattern_loop(width: int, height: int, fps: float, state: State):
    while True:
        # 串口已经开始出帧后，停止测试画面，避免覆盖真实视频
        if state.serial_frames > 0:
            time.sleep(0.5)
            continue
        try:
            state.set_jpeg(make_test_jpeg(width, height, time.time()))
        except Exception as e:
            state.last_error = str(e)
        time.sleep(1.0 / max(1.0, fps))


# ----------------------------- HTTP -----------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "PetMonitorRelay/1.0"

    def log_message(self, fmt, *args):
        # 静默 HTTP 访问日志，避免刷屏
        pass

    def _send_bytes(self, data: bytes, content_type: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path      # 去掉 ?t=... 查询参数

        if path in ("/", "/index.html"):
            try:
                html = HTML_PATH.read_bytes()
                self._send_bytes(html, "text/html; charset=utf-8")
            except Exception as e:
                self._send_bytes(f"index.html 读取失败: {e}".encode("utf-8"), "text/plain; charset=utf-8", 500)

        elif path == "/status":
            with STATE.lock:
                data = {
                    "serial_connected": STATE.serial_connected,
                    "serial_port": STATE.serial_port,
                    "serial_baud": STATE.serial_baud,
                    "resolution": STATE.resolution,
                    "fps": round(STATE.fps, 1),
                    "frames": STATE.frame_count,
                    "serial_frames": STATE.serial_frames,
                    "checksum_errors": STATE.checksum_errors,
                    "last_error": STATE.last_error,
                }
            self._send_bytes(json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        elif path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                while True:
                    with STATE.lock:
                        jpeg = STATE.jpeg
                    if not jpeg:
                        time.sleep(0.05)
                        continue
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii"))
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                    time.sleep(0.05)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return

        elif path == "/snapshot.jpg":
            with STATE.lock:
                jpeg = STATE.jpeg
            if jpeg:
                self._send_bytes(jpeg, "image/jpeg")
            else:
                self._send_bytes(b"no frame", "text/plain; charset=utf-8", 503)
        else:
            self._send_bytes(b"404", "text/plain; charset=utf-8", 404)


def main():
    ap = argparse.ArgumentParser(description="Pet monitor PC relay (RGB332 -> MJPEG)")
    ap.add_argument("--port", default="COM22", help="串口，默认 COM22")
    ap.add_argument("--baud", type=int, default=921600, help="波特率，默认 921600")
    ap.add_argument("--http-port", type=int, default=8000, help="HTTP 端口，默认 8000")
    ap.add_argument("--width", type=int, default=160, help="图像宽，默认 160")
    ap.add_argument("--height", type=int, default=120, help="图像高，默认 120")
    ap.add_argument("--quality", type=int, default=60, help="JPEG 质量，默认 60")
    ap.add_argument("--no-serial", action="store_true", help="只显示测试画面，不打开串口")
    args = ap.parse_args()

    STATE.resolution = f"{args.width}x{args.height}"

    if args.no_serial:
        t = threading.Thread(target=test_pattern_loop, args=(args.width, args.height, 5.0, STATE), daemon=True)
        t.start()
        print("[MODE] 测试画面（未打开串口）")
    else:
        fw = threading.Thread(target=frame_worker,
                              args=(args.width, args.height, args.quality, STATE),
                              daemon=True)
        fw.start()
        t = threading.Thread(target=serial_reader,
                             args=(args.port, args.baud, args.width, args.height, args.quality, STATE),
                             daemon=True)
        t.start()
        # 串口还没来帧时，也显示测试画面，避免页面全黑
        tp = threading.Thread(target=test_pattern_loop, args=(args.width, args.height, 2.0, STATE), daemon=True)
        tp.start()

    ip = guess_lan_ip()
    print("=" * 60)
    print("宠物视频监控 · PC 中继 / Web APP")
    print(f"手机与电脑连同一 WiFi，浏览器打开：")
    print(f"    http://{ip}:{args.http_port}/")
    print(f"本机也可打开：http://127.0.0.1:{args.http_port}/")
    print(f"串口：{args.port} @ {args.baud}  分辨率：{STATE.resolution}")
    print("=" * 60)

    httpd = ThreadingHTTPServer(("0.0.0.0", args.http_port), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[EXIT] 用户中断")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
