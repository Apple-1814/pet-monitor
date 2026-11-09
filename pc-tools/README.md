# PC 中继 + 手机 Web APP（远程监看）

当前远程方案：

```
STM32F103 (OV7670 + FIFO)
  │  USART1: 1.5Mbaud, 8N1
  │  帧: AA 55 + 4 字节长度 + 2 字节校验和 + RGB332 192x144 (27648 字节)
  ▼
PC (本目录 relay_server.py, pyserial + Pillow)
  │  RGB332 -> RGB888 -> JPEG
  │  HTTP: JPEG 轮询 (/snapshot.jpg) + MJPEG (/stream)
  ▼
手机浏览器 (同 WiFi, Web APP)
```

- 远端分辨率：**192×144**（从 320×240 中心裁剪）
- 远端帧率：**约 3.0fps**（有效帧，校验失败自动丢弃）
- 本地 LCD：320×240 居中显示，约 9–10fps，偶发彩色闪帧
- 手机端：JPEG 轮询 5fps，兼容所有手机浏览器

## 1. 启动中继

```bash
C:\Users\18149\miniconda3\python.exe -u pc-tools\relay_server.py ^
    --port COM22 --baud 1500000 --http-port 8000 ^
    --width 192 --height 144
```

- `--port COM22`：板载 CH340 的串口。
- `--baud 1500000`：与固件 `usart_init(72, 1500000)` 一致。
- `--width/--height 192 144`：与固件 `REMOTE_W/REMOTE_H` 一致。
- 不加 `--no-serial` 为串口模式；加 `--no-serial` 只显示测试画面。

启动后终端会打印手机访问地址，例如：

```
http://192.168.1.243:8000/
```

## 2. 手机访问

1. 手机连到与电脑相同的 WiFi。
2. 浏览器打开 `http://<电脑WLAN IP>:8000/`。
3. 页面显示实时画面、FPS、分辨率。
4. 第一次 Windows 防火墙弹窗选“允许访问（专用网络）”；没有弹窗则以管理员运行：

```powershell
New-NetFirewallRule -DisplayName "PetMonitor Relay 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private
```

## 3. 注意

- **DTR/RTS**：脚本打开串口后会立即 `dtr=False; rts=False`。板载一键下载电路由 CH340 的 DTR/RTS 控制，若不释放会拉高 BOOT0，复位后进系统 Bootloader。
- **URL 查询参数**：Web APP 使用 `/snapshot.jpg?t=...`、`/status?t=...`，服务器已用 `urlparse` 去掉查询参数；不要改回精确 `self.path` 匹配。
- **手机兼容性**：MJPEG `<img>` 在部分手机浏览器不显示，因此 Web APP 使用 JPEG 轮询；`/stream` 仍保留给桌面/调试。
- **校验和**：STM32 发送 16 位累加和（payload 逐字节相加），PC 端校验失败直接丢帧；避免彩色横条/错位帧上屏。
- **帧率取舍**：192×144 @1.5M 约 3.0fps；240×180 只有 2.3fps；2Mbaud 下 CH340 丢字节严重（1.5fps），不要用。

## 4. 文件

| 文件 | 用途 |
|---|---|
| `relay_server.py` | PC 中继：串口读帧、校验、RGB332→JPEG、HTTP 服务 |
| `web/index.html` | 手机 Web APP（JPEG 轮询、全屏、状态） |
| `../docs/reference/frame-protocol.md` | 帧协议与参数说明 |

## 5. 后续替换 ESP8266

买到 ATK-ESP8266 后，可把 PC 中继的串口侧换成 ESP8266（ATK MODULE 接口，USART3 PB10/PB11）。帧协议不变；手机页面可继续用 PC 中继，或让 ESP8266 直接做 TCP 服务器 + 手机原生 TCP APP。
