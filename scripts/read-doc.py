#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""read-doc.py — Office 文档阅读工具（只读提取，不修改原文档）

用法:
  python3 scripts/read-doc.py <文件>                 # 提取文本/表格/备注/嵌入图片
  python3 scripts/read-doc.py <文件> --no-images     # 不提取图片
  python3 scripts/read-doc.py <文件> --images-dir D  # 指定图片输出目录
  python3 scripts/read-doc.py <文件> --rows 500      # 调大 xlsx 行数上限(默认 200)
  python3 scripts/read-doc.py --setup                # 安装 python 依赖并探测环境

支持格式:
  新格式  .docx / .pptx / .xlsx  直接解析
  旧格式  .doc  / .ppt  / .xls   自动经 LibreOffice(soffice) 无头转换后提取

输出: UTF-8 Markdown 到 stdout; 图片保存到 <文件名>_images/(或 --images-dir)。
emf/wmf 元文件按原样保存并标注, 不做格式转换。
退出码: 0 成功; 2 依赖或参数错误; 3 缺 soffice; 4 转换失败。
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

DOC_EXTS = {".doc": "docx", ".ppt": "pptx", ".xls": "xlsx"}
NEW_EXTS = (".docx", ".pptx", ".xlsx")

SUPPORTS = ".docx/.pptx/.xlsx（新格式）; .doc/.ppt/.xls（经 LibreOffice 转换）"

# ---------------------------------------------------------------- 图片辅助

# 魔数 -> (扩展名, 说明, 是否元文件)
def sniff_image(data: bytes, fallback_ext: str):
    """按魔数识别图片真实格式, 防止扩展名与实际内容不符。"""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "png 位图", False
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg", "jpg 位图", False
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif", "gif 位图", False
    if data.startswith(b"BM"):
        return "bmp", "bmp 位图", False
    head = data[:512].lstrip()
    if head.startswith(b"<?xml") or head[:5].lower() == b"<svg " or head[:4].lower() == b"<svg":
        return "svg", "svg 矢量图", False
    if len(data) >= 44 and data[40:44] == b" EMF":
        return "emf", "EMF 矢量元文件（Read 工具可能无法直接预览）", True
    if data.startswith(b"\xd7\xcd\xc6\x9a") or data.startswith(b"\x01\x00\x09\x00"):
        return "wmf", "WMF 矢量元文件（Read 工具可能无法直接预览）", True
    ext = (fallback_ext or "bin").lstrip(".").lower() or "bin"
    return ext, f"未识别格式（按扩展名 .{ext} 保存）", False


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 / 1024:.2f} MB"


class ImageSink:
    """接收图片字节, 按真实格式落盘, 记录清单, 返回 [图片 N: ...] 标注。"""

    def __init__(self, images_dir, enabled=True):
        self.dir = Path(images_dir) if images_dir else None
        self.enabled = enabled
        self.records = []  # (序号, 文件名, 格式说明, 大小, 是否元文件)
        if self.enabled and self.dir is not None:
            self.dir.mkdir(parents=True, exist_ok=True)

    def add(self, data: bytes, suggested_name: str) -> str:
        stem = Path(suggested_name).stem or "image"
        ext, desc, is_meta = sniff_image(data, Path(suggested_name).suffix)
        idx = len(self.records) + 1
        if not self.enabled or self.dir is None:
            self.records.append((idx, None, desc, len(data), is_meta))
            return f"[图片 {idx}: {desc}, {human_size(len(data))}（未提取, --images-dir 可指定保存）]"
        name = f"{idx:02d}-{stem}.{ext}"
        n = 1
        while (self.dir / name).exists():
            n += 1
            name = f"{idx:02d}-{stem}-{n}.{ext}"
        (self.dir / name).write_bytes(data)
        self.records.append((idx, name, desc, len(data), is_meta))
        return f"[图片 {idx}: {name} — {desc}, {human_size(len(data))}]"

    def summary(self) -> str:
        if not self.records:
            return "无嵌入图片。"
        lines = ["| # | 文件 | 格式 | 大小 |", "|---|------|------|------|"]
        for idx, name, desc, size, _meta in self.records:
            lines.append(f"| {idx} | {name or '（未提取）'} | {desc} | {human_size(size)} |")
        return "\n".join(lines)


def md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").strip()


def md_table(rows) -> str:
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(out)


def need_libs():
    """导入解析库, 缺失时给出安装指引。"""
    missing = []
    try:
        import docx  # noqa: F401
    except ImportError:
        missing.append("python-docx")
    try:
        import pptx  # noqa: F401
    except ImportError:
        missing.append("python-pptx")
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        missing.append("openpyxl")
    if missing:
        print(f"错误: 缺少 python 依赖 {', '.join(missing)}。", file=sys.stderr)
        print("请运行: python3 scripts/read-doc.py --setup", file=sys.stderr)
        print(f"或手动安装: pip3 install --user --break-system-packages {' '.join(missing)}", file=sys.stderr)
        sys.exit(2)


def find_soffice():
    return shutil.which("soffice") or shutil.which("libreoffice")


def convert_legacy(src: Path) -> Path:
    """旧格式经 LibreOffice 无头转换为新格式, 返回转换后文件路径。"""
    target = DOC_EXTS[src.suffix.lower()]
    outdir = Path.cwd() / "tmp" / "read-doc-converted"
    try:
        outdir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"错误: 无法创建转换目录 {outdir}: {e}", file=sys.stderr)
        sys.exit(4)
    soffice = find_soffice()
    if not soffice:
        print(f"错误: 读取 {src.suffix} 旧格式需要 LibreOffice, 当前 WSL 未安装 soffice。", file=sys.stderr)
        print("请在 WSL 内安装后重试（如需 AI 代装请明确告知）: sudo apt install libreoffice", file=sys.stderr)
        sys.exit(3)
    cmd = [soffice, "--headless", "--convert-to", target, "--outdir", str(outdir), str(src)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=180)
    except subprocess.TimeoutExpired:
        print("错误: LibreOffice 转换超时（180 秒）。", file=sys.stderr)
        sys.exit(4)
    out = outdir / (src.stem + "." + target)
    if r.returncode != 0 or not out.exists():
        print(f"错误: LibreOffice 转换失败（退出码 {r.returncode}）。", file=sys.stderr)
        if r.stderr:
            print(r.stderr.strip(), file=sys.stderr)
        sys.exit(4)
    return out


# ---------------------------------------------------------------- docx

def read_docx(path: Path, sink: ImageSink, out):
    from docx import Document
    from docx.document import Document as _Doc
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(str(path))
    out.append(f"# {path.name}\n")

    def para_images(p: Paragraph):
        rids = p._p.xpath(".//a:blip/@r:embed")
        for rid in rids:
            try:
                part = doc.part.related_parts[rid]
                out.append(sink.add(part.blob, Path(str(part.partname)).name))
            except (KeyError, AttributeError):
                pass

    def emit_table(tbl: Table):
        rows = [[md_cell(c.text) for c in row.cells] for row in tbl.rows]
        t = md_table(rows)
        if t:
            out.append(t + "\n")

    body = doc.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            p = Paragraph(child, doc)
            para_images(p)
            txt = p.text.strip()
            if txt:
                out.append(txt + "\n")
        elif isinstance(child, CT_Tbl):
            emit_table(Table(child, doc))

    if sink.records:
        out.append("\n## 图片清单\n")
        out.append(sink.summary() + "\n")


# ---------------------------------------------------------------- pptx

def read_pptx(path: Path, sink: ImageSink, out):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER

    prs = Presentation(str(path))
    out.append(f"# {path.name}\n")

    def walk_shapes(shapes, slide_out):
        for shape in shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP or hasattr(shape, "shapes") and not hasattr(shape, "image"):
                try:
                    walk_shapes(shape.shapes, slide_out)
                except (AttributeError, ValueError):
                    pass
                continue
            if shape.is_placeholder and shape.placeholder_format.type in (
                PP_PLACEHOLDER.TITLE,
                PP_PLACEHOLDER.CENTER_TITLE,
            ):
                continue  # 标题已在页头输出, 不重复
            if getattr(shape, "has_table", False) and shape.has_table:
                rows = [[md_cell(c.text) for c in row.cells] for row in shape.table.rows]
                t = md_table(rows)
                if t:
                    slide_out.append(t + "\n")
                continue
            try:
                img = shape.image  # 图片类 shape
            except (AttributeError, ValueError):
                img = None
            if img is not None:
                slide_out.append(sink.add(img.blob, img.filename or "image"))
                continue
            if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
                txt = shape.text_frame.text.strip()
                if txt:
                    slide_out.append(txt + "\n")

    for i, slide in enumerate(prs.slides, 1):
        title = ""
        try:
            if slide.shapes.title is not None:
                title = slide.shapes.title.text.strip()
        except (AttributeError, Exception):
            title = ""
        out.append(f"\n## 幻灯片 {i}" + (f"：{title}" if title else "") + "\n")
        slide_out = []
        walk_shapes(slide.shapes, slide_out)
        out.extend(slide_out)
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                out.append(f"> 备注：{notes}\n")

    if sink.records:
        out.append("\n## 图片清单\n")
        out.append(sink.summary() + "\n")


# ---------------------------------------------------------------- xlsx

def col_letter(c0: int) -> str:
    s = ""
    c0 += 1
    while c0:
        c0, r = divmod(c0 - 1, 26)
        s = chr(65 + r) + s
    return s


def read_xlsx(path: Path, sink: ImageSink, out, max_rows: int, max_cols: int):
    import openpyxl

    wb = openpyxl.load_workbook(str(path), data_only=True)
    out.append(f"# {path.name}\n")

    for ws in wb.worksheets:
        out.append(f"\n## 工作表：{ws.title}\n")
        n_rows = 0
        for row in ws.iter_rows(max_row=min(ws.max_row or 1, max_rows), max_col=min(ws.max_column or 1, max_cols)):
            cells = [md_cell("" if c.value is None else str(c.value)) for c in row]
            if any(cells):
                n_rows += 1
                out.append("| " + " | ".join(cells) + " |")
                if n_rows == 1:
                    out.append("|" + "---|" * len(cells))
        if not n_rows:
            out.append("（空工作表）\n")
        total = ws.max_row or 0
        if total > max_rows:
            out.append(f"\n（已截断：共 {total} 行，仅显示前 {max_rows} 行；--rows 可调大）\n")
        if (ws.max_column or 0) > max_cols:
            out.append(f"（已截断：共 {ws.max_column} 列，仅显示前 {max_cols} 列；--cols 可调大）\n")

    # 单元格图片（openpyxl 仅在普通加载模式下可读）
    found = False
    for ws in wb.worksheets:
        for img in getattr(ws, "_images", []):
            try:
                data = img._data()
                anchor = getattr(img.anchor, "_from", None)
                where = ""
                if anchor is not None:
                    where = f"（位于 {col_letter(anchor.col)}{anchor.row + 1} 附近）"
                out.append(f"\n工作表「{ws.title}」{where}: " + sink.add(data, "sheet-image"))
                found = True
            except (AttributeError, OSError, ValueError):
                continue
    if found or sink.records:
        out.append("\n## 图片清单\n")
        out.append(sink.summary() + "\n")


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description="Office 文档只读提取工具")
    ap.add_argument("file", nargs="?", help="待读取的文档路径")
    ap.add_argument("--no-images", action="store_true", help="不提取嵌入图片")
    ap.add_argument("--images-dir", default=None, help="图片输出目录（默认 <文件名>_images/）")
    ap.add_argument("--rows", type=int, default=200, help="xlsx 行数上限（默认 200）")
    ap.add_argument("--cols", type=int, default=50, help="xlsx 列数上限（默认 50）")
    ap.add_argument("--setup", action="store_true", help="安装 python 依赖并探测环境")
    args = ap.parse_args()

    if args.setup:
        do_setup()
        return

    if not args.file:
        ap.error("请提供文档路径，或使用 --setup 安装依赖")
    src = Path(args.file)
    if not src.exists():
        print(f"错误: 文件不存在: {src}", file=sys.stderr)
        sys.exit(2)
    ext = src.suffix.lower()

    converted = None
    if ext in DOC_EXTS:
        need_libs()
        print(f"> 注：旧格式 {ext} 经 LibreOffice 转换为 .{DOC_EXTS[ext]} 后提取，版式可能有差异。\n", file=sys.stderr)
        converted = convert_legacy(src)
        src = converted
        ext = src.suffix.lower()
    elif ext not in NEW_EXTS:
        print(f"错误: 暂不支持的格式 {ext}。当前支持: {SUPPORTS}。", file=sys.stderr)
        sys.exit(2)
    need_libs()

    if args.images_dir:
        images_dir = Path(args.images_dir)
    else:
        images_dir = src.parent / f"{src.stem}_images"
    sink = ImageSink(images_dir, enabled=not args.no_images)

    out = []
    try:
        if ext == ".docx":
            read_docx(src, sink, out)
        elif ext == ".pptx":
            read_pptx(src, sink, out)
        elif ext == ".xlsx":
            read_xlsx(src, sink, out, args.rows, args.cols)
    except Exception as e:  # 解析失败给出可定位的信息
        print(f"错误: 解析 {src.name} 失败: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(4)
    print("\n".join(out))
    if sink.enabled and sink.records and images_dir is not None:
        print(f"\n（图片已保存到: {images_dir}）", file=sys.stderr)


def do_setup():
    print("== read-doc.py 环境安装与探测 ==")
    missing = []
    for mod, pkg in (("docx", "python-docx"), ("pptx", "python-pptx"), ("openpyxl", "openpyxl")):
        try:
            __import__(mod)
            print(f"[已安装] {pkg}")
        except ImportError:
            missing.append(pkg)
    if missing:
        base = [sys.executable, "-m", "pip", "install", "--user"] + missing
        print(f"[安装] {', '.join(missing)} …")
        r = subprocess.run(base, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
        if r.returncode != 0:  # PEP 668 受管环境回退
            r = subprocess.run(base + ["--break-system-packages"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print("错误: 安装失败：\n" + (r.stderr or r.stdout), file=sys.stderr)
            sys.exit(2)
        for pkg in missing:
            print(f"[已安装] {pkg}")
    soffice = find_soffice()
    if soffice:
        print(f"[可用] LibreOffice: {soffice}")
    else:
        print("[缺失] LibreOffice（仅旧格式 .doc/.ppt/.xls 需要）")
        print("        如需读取旧格式，请在 WSL 内安装: sudo apt install libreoffice")
    print("完成。用法: python3 scripts/read-doc.py <文件>")


if __name__ == "__main__":
    main()
