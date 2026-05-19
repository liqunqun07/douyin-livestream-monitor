#!/usr/bin/env python3
"""抖音直播间监控 - 配置面板服务器
提供 API 供前端读写配置和查看监控状态。
实际采集由 Claude Code 执行，通过 status.json 同步进度。
"""

import json
import os
import sys
import threading
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(FRONTEND_DIR)
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.json")
STATUS_PATH = os.path.join(PROJECT_DIR, "status.json")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self._send_json({})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/config":
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {
                    "brands": "",
                    "savePath": os.path.expanduser("~/Desktop/抖音直播间截图"),
                    "strictMatch": True,
                }
            return self._send_json(data)

        elif path == "/api/status":
            if os.path.exists(STATUS_PATH):
                with open(STATUS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {
                    "status": "idle",
                    "currentBrand": "",
                    "currentStep": "",
                    "progress": "",
                    "completedBrands": [],
                    "errors": [],
                    "startedAt": "",
                    "updatedAt": "",
                }
            return self._send_json(data)

        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/config":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            brands_text = data.get("brands", "")
            brands = []
            for sep in [",", "，", "、", ";", "；"]:
                brands_text = brands_text.replace(sep, ",")
            for b in brands_text.split(","):
                b = b.strip()
                if b:
                    brands.append(b)
            save_data = {
                "brands": brands,
                "savePath": data.get("savePath", os.path.expanduser("~/Desktop/抖音直播间截图")),
                "strictMatch": data.get("strictMatch", True),
                "createdAt": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            return self._send_json({"success": True, "brands": brands})

        elif path == "/api/start":
            # 重置状态，等待 Claude Code 执行
            started_at = time.strftime("%Y-%m-%d %H:%M:%S")
            status_init = {
                "status": "waiting",
                "currentBrand": "",
                "currentStep": "请在 Claude Code 中输入采集指令",
                "progress": "",
                "completedBrands": [],
                "errors": [],
                "startedAt": started_at,
                "updatedAt": started_at,
            }
            with open(STATUS_PATH, "w", encoding="utf-8") as f:
                json.dump(status_init, f, ensure_ascii=False, indent=2)
            return self._send_json({
                "success": True,
                "message": "状态已就绪，请在 Claude Code 中输入「看直播间」开始采集",
            })

        elif path == "/api/reset":
            if os.path.exists(STATUS_PATH):
                os.remove(STATUS_PATH)
            return self._send_json({"success": True})

        return self._send_json({"error": "not found"}, 404)


def open_browser(port):
    time.sleep(1.5)
    url = f"http://localhost:{port}"
    print(f"📋 正在打开浏览器: {url}")
    webbrowser.open(url)


def main():
    ports = [7890, 7893, 7895, 7898, 7900, 8100, 8200]
    server = None
    for port in ports:
        try:
            server = HTTPServer(("127.0.0.1", port), Handler)
            actual_port = port
            break
        except OSError:
            continue
    if server is None:
        print("❌ 错误: 无法找到可用端口，请检查网络配置")
        sys.exit(1)
    print("=" * 50)
    print("  🎯 抖音直播间监控 - 配置面板")
    print(f"  📍 本地地址: http://localhost:{actual_port}")
    print("  ⌨️ 按 Ctrl+C 停止服务")
    print("=" * 50)
    threading.Thread(target=open_browser, args=(actual_port,), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
        server.server_close()


if __name__ == "__main__":
    main()
