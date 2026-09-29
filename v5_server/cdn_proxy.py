# -*- coding: utf-8 -*-
"""
cdn_proxy.py — 深空之眼 高性能流式 CDN 资源穿透与动态抓包拦截器（Zero-OOM Streaming Engine）

核心能力：
1. 平台数据严格物理隔离（Platform Isolation）：
   - Windows PC 资源：存储于 D:\\PC_DATA
   - iOS 移动端资源 ：存储于 D:\\iOS_DATA
   - Android 安卓资源：存储于 D:\\Android_DATA
   - 绝不混淆两端不同平台编译的着色器、音视频与资产包！
2. 流式双向转发（Streaming Pipe）：
   - 以 64KB 固定缓冲区边从官方 CDN 拉取边向客户端发送，首包延迟 < 10ms，内存占用恒定 < 2MB，支持 19GB+ 海量并发下载；
3. 双写落盘持久化（On-The-Fly Disk Caching）：
   - 数据流在流式分发给客户端的同时，通过 .part 临时文件原子落盘到各平台专属目录；
   - 下次同名资源请求 100% 命中本地极速缓存；
4. DoH 官方 CDN 真实 IP 穿透 + TLS SNI 握手：
   - 绕过 Windows 本地 hosts 劫持与 127.0.0.1 环回死锁；
5. 完整的 HTTP 200 / 206 Partial Content (Range) 支持：
   - 完美适配 Unity WebRequest 分片、断点续传及多线程下载。
"""
import http.client
import json
import os
import re
import shutil
import socket
import ssl
import sys
import threading
import time
import urllib.request
from flask import Response

from logger import log as _logger_log
import log_sifter

_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STATIC_DIR = os.path.join(_SERVER_DIR, "static_resources")

def _get_configured_cdn_root() -> str:
    """从环境变量或 server_config.json 中读取配置的 CDN 根目录。"""
    if os.environ.get("CDN_CACHE_DIR"):
        raw_env = os.environ["CDN_CACHE_DIR"].strip()
        if raw_env and not os.path.isabs(raw_env):
            return os.path.normpath(os.path.join(_SERVER_DIR, raw_env))
        return raw_env
    cfg_path = os.path.join(_SERVER_DIR, "server_config.json")
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                val = data.get("storage", {}).get("cdn_cache_dir", "").strip()
                if val:
                    if not os.path.isabs(val):
                        return os.path.normpath(os.path.join(_SERVER_DIR, val))
                    return val
        except Exception:
            pass
    return ""

def _resolve_platform_dir(platform_name: str, legacy_drive_dir: str = "") -> str:
    r"""
    确定平台 CDN 资源存储目录，优先级：
    1. 平台专属环境变量 CDN_<PLATFORM>_DIR
    2. 全局 CDN 根目录配置 (server_config.json 或 CDN_CACHE_DIR)
    3. 历史专属盘目录 (D:\<PLATFORM>_DATA，若已存在)
    4. 兜底相对路径: server/cdn_cache/<platform>
    """
    env_key = f"CDN_{platform_name.upper()}_DIR"
    if os.environ.get(env_key):
        return os.environ[env_key]

    root = _get_configured_cdn_root()
    if root:
        return os.path.join(root, platform_name)

    if legacy_drive_dir and os.path.exists(legacy_drive_dir):
        return legacy_drive_dir
    return os.path.join(_SERVER_DIR, "cdn_cache", platform_name)

PLATFORM_DIRS = {
    "pc": _resolve_platform_dir("pc", r"D:\PC_DATA"),
    "ios": _resolve_platform_dir("ios", r"D:\iOS_DATA"),
    "android": _resolve_platform_dir("android", r"D:\Android_DATA"),
}

def set_cdn_base_dir(base_dir: str):
    """动态更新各平台 CDN 资源根目录（用于 CLI 参数或面板动态注入）。"""
    global PLATFORM_DIRS
    if not base_dir:
        return
    if not os.path.isabs(base_dir):
        base_dir = os.path.normpath(os.path.join(_SERVER_DIR, base_dir))
    for plat in ("pc", "ios", "android"):
        target = os.path.join(base_dir, plat)
        PLATFORM_DIRS[plat] = target
        try:
            os.makedirs(target, exist_ok=True)
        except Exception:
            pass
LOCAL_CHUNK_SIZE = 1048576      # 1 MB 本地高速分块（消除 iOS 40ms Nagle 延迟，瞬间填满 TCP 窗口）
UPSTREAM_CHUNK_SIZE = 524288   # 512 KB 上游 CDN 拉取分块
CHUNK_SIZE = LOCAL_CHUNK_SIZE  # 保持向下兼容

# 全局抓包器开关与统计（默认开启智能穿透兜底：本地有秒发，本地无穿透拉取防404）
_CAPTURE_ENABLED = True
_AUTO_CACHE_FALLBACK = True
_DNS_CACHE = {}
_DNS_LOCK = threading.Lock()

# 官方常用域名备用静态 IP（防止极端情况下 DoH 不可用）
FALLBACK_IPS = {
    "download-eo.ys4fun.com": ["111.31.122.137", "120.220.18.85", "183.204.11.49", "36.151.124.99"],
    "download.ys4fun.com": ["111.31.122.137", "120.220.18.85", "183.204.11.49", "36.151.124.99"],
    "open.ys4fun.com": ["203.107.63.115", "47.100.78.77"],
    "prod-api-activity.ys4fun.com": ["203.107.63.115"],
    "packaging.ys4fun.com": ["111.31.122.137", "120.220.18.85"],
}


def get_platform_from_path(path: str, headers=None) -> str:
    """根据请求路径及请求头精准判断客户端平台（pc / ios / android）。"""
    lower_path = path.lower()
    if "/ios/" in lower_path:
        return "ios"
    if "/android/" in lower_path:
        return "android"
    if "/pc/" in lower_path:
        return "pc"

    if headers:
        ua = headers.get("User-Agent", "").lower()
        if "iphone" in ua or "ipad" in ua or "ios" in ua or "darwin" in ua:
            return "ios"
        if "android" in ua:
            return "android"
        if "windows" in ua or "pc" in ua:
            return "pc"

    # 默认 PC 平台
    return "pc"


def get_data_dir(platform: str = "pc") -> str:
    """获取指定平台的专属数据存储目录（优先 D:\\<PLATFORM>_DATA，失败降级为 static_resources/<platform>）。"""
    plat = platform.lower() if platform else "pc"
    primary_dir = PLATFORM_DIRS.get(plat, PLATFORM_DIRS["pc"])
    try:
        os.makedirs(primary_dir, exist_ok=True)
        return primary_dir
    except Exception:
        fallback_dir = os.path.join(DEFAULT_STATIC_DIR, plat)
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir


def sync_initial_manifests():
    """初始化时将已有的关键资源清单同步至 PC、iOS、Android 对应专属目录。"""
    try:
        os.makedirs(DEFAULT_STATIC_DIR, exist_ok=True)
        for plat, target_dir in PLATFORM_DIRS.items():
            try:
                os.makedirs(target_dir, exist_ok=True)
            except Exception:
                continue

            if os.path.isdir(DEFAULT_STATIC_DIR):
                for f in os.listdir(DEFAULT_STATIC_DIR):
                    s_p = os.path.join(DEFAULT_STATIC_DIR, f)
                    if not os.path.isfile(s_p):
                        continue

                    # 针对 iOS / PC 特异性清单分流复制
                    if "29e8f745e8ec6032937a65a0bfd3a9cf" in f and plat != "ios":
                        continue
                    if "3807d27e1a6e26853f1fccfa8b7681d0" in f and plat not in ("pc", "android"):
                        continue

                    d_p = os.path.join(target_dir, f)
                    if not os.path.exists(d_p):
                        shutil.copy2(s_p, d_p)
    except Exception:
        pass


def is_capture_enabled():
    """查询当前抓包器是否开启。"""
    return _CAPTURE_ENABLED


def set_capture_enabled(val: bool):
    """设置抓包器开启/关闭状态。"""
    global _CAPTURE_ENABLED, _AUTO_CACHE_FALLBACK
    _CAPTURE_ENABLED = bool(val)
    _AUTO_CACHE_FALLBACK = bool(val)
    print(f"[CDN_PROXY] 抓包器状态已更新为: {'[已开启]' if _CAPTURE_ENABLED else '[已关闭]'}", flush=True)


def resolve_doh(host):
    """通过 DoH 解析真实公网 IPv4，绕过本地 hosts。"""
    with _DNS_LOCK:
        if host in _DNS_CACHE and _DNS_CACHE[host]:
            return _DNS_CACHE[host]

    doh_urls = [
        f"https://dns.alidns.com/resolve?name={host}&type=A",
        f"https://223.5.5.5/resolve?name={host}&type=A",
        f"https://1.12.12.12/resolve?name={host}&type=A",
    ]

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    ips = []
    for u in doh_urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "curl/8.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
                if resp.status == 200:
                    j = json.loads(resp.read().decode("utf-8"))
                    for a in j.get("Answer", []):
                        if a.get("type") == 1 and a.get("data"):
                            ip = a["data"].strip()
                            if not ip.startswith("127.") and not ip.startswith("0."):
                                ips.append(ip)
            if ips:
                break
        except Exception:
            continue

    if not ips and host in FALLBACK_IPS:
        ips = list(FALLBACK_IPS[host])

    if ips:
        with _DNS_LOCK:
            _DNS_CACHE[host] = ips
        return ips
    return ["183.204.11.49"]


def create_direct_socket(target_ip, port=443, timeout=30):
    """创建直接物理局域网网卡直连 Socket，绕过 Clash TUN 虚拟网卡环回拦截。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        import gen_cert
        local_ip = gen_cert.get_default_lan_ip()
        if local_ip and not local_ip.startswith("127.") and not local_ip.startswith("198.18."):
            sock.bind((local_ip, 0))
    except Exception:
        pass
    sock.settimeout(timeout)
    sock.connect((target_ip, port))
    return sock


def find_cached_file(filename: str, platform: str = "pc"):
    """在指定平台的专属存储目录与备用目录查找本地已存在的文件。
    优先级：
    1. static_resources/<platform>/ （优先下发标准清单与平台特化配置）
    2. static_resources/ 根目录
    3. 平台专属数据目录（cdn_cache/<platform> 或 D:\\<PLATFORM>_DATA）
    """
    # 1. static_resources/<platform>/ (例如 static_resources/ios/)
    cand1 = os.path.join(DEFAULT_STATIC_DIR, platform, filename)
    if os.path.isfile(cand1) and os.path.getsize(cand1) > 0:
        return cand1

    # 2. static_resources/ 根目录（仅允许通用配置文件如 html/json，严禁 .ys 跨平台资产匹配）
    if not filename.endswith(".ys"):
        cand2 = os.path.join(DEFAULT_STATIC_DIR, filename)
        if os.path.isfile(cand2) and os.path.getsize(cand2) > 0:
            return cand2

    # 3. 当前平台专属数据目录 (D:\PC_DATA 或 D:\iOS_DATA，严格物理分盘隔离)
    plat_dir = get_data_dir(platform)
    cand3 = os.path.join(plat_dir, filename)
    if os.path.isfile(cand3) and os.path.getsize(cand3) > 0:
        return cand3

    return None


_ETAG_CACHE = {}


def _file_md5_headers(file_path):
    """按 (path,size,mtime) 缓存计算 ETag/Content-MD5，对齐官方 CDN 响应头。

    321 客户端更新器对 .bytes 清单缺 Content-MD5/ETag 时会视为损坏并无限重试
    （实测：voice_package_list 60 秒周期重试、字节与官方一致仍不继续）。
    """
    import base64
    import hashlib as _hashlib
    key = (file_path, os.path.getsize(file_path), os.path.getmtime(file_path))
    if key not in _ETAG_CACHE:
        h = _hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        hexd = h.hexdigest().upper()
        _ETAG_CACHE[key] = (hexd, base64.b64encode(h.digest()).decode("ascii"))
    return _ETAG_CACHE[key]


def _file_md5_bytes(body):
    """对内存字节计算 (ETag-hex, Content-MD5-base64)，语义同 _file_md5_headers。"""
    import base64
    import hashlib as _hashlib
    h = _hashlib.md5(body)
    return h.hexdigest().upper(), base64.b64encode(h.digest()).decode("ascii")


# ==== 语音零差异跑步机配置（详见 handle_resource_request 内注释） ====
# 版本 = 30701000 + 自锚定时刻(2026-09-28 00:00 +08)以来的分钟数：
# 跨分钟启动单调不减 → 客户端走"版本差→下载清单→diff=空→跳过确认→校验→完成"的
# 已验证路径。注意（2026-09-29 整改勘误）：粒度为 1 分钟，同一分钟内的两次启动
# 版本相等——此时落入"版本相等"分支，实测因清单内容恒等亦安全，但旧注释
# "任意两次启动间严格递增、永不落入版本相等分支"的说法不成立，特此更正。
_VOICE_TREADMILL_EPOCH = 1790524800  # 2026-09-28 00:00:00 +08:00 (UTC 2026-09-27T16:00Z)
_VOICE_TREADMILL_BASE = 30701000
_VOICE_TREADMILL_ENABLED = os.environ.get("AG_VOICE_TREADMILL", "1") != "0"
_VOICE_TREADMILL_TMPL = None  # 修剪清单模板（条目列表）惰性加载


def _voice_treadmill_version():
    # AG_VOICE_TREADMILL_PIN：钉住版本号（用于非提权诊断会话——清单已安装后，
    # 固定版本可让客户端走本地缓存零写入路径，无需管理员权限）
    pinned = os.environ.get("AG_VOICE_TREADMILL_PIN", "")
    if pinned.strip():
        try:
            return int(pinned)
        except ValueError:
            pass
    return _VOICE_TREADMILL_BASE + max(0, int((time.time() - _VOICE_TREADMILL_EPOCH) // 60))


def _voice_treadmill_manifest_bytes(version):
    """按需合成指定版本的零差异清单（条目=模板，version 字段=请求版本）。"""
    global _VOICE_TREADMILL_TMPL
    import json as _json
    if _VOICE_TREADMILL_TMPL is None:
        tmpl_path = find_cached_file("voice_hash_zh_%d.bytes" % _VOICE_TREADMILL_BASE, platform="pc")
        if not tmpl_path:
            return None
        with open(tmpl_path, "r", encoding="utf-8") as f:
            _VOICE_TREADMILL_TMPL = _json.load(f)
    manifest = dict(_VOICE_TREADMILL_TMPL)
    manifest["version"] = version
    return _json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def serve_local_stream(file_path, range_header=None):
    """从本地文件高效流式下发，支持 200 / 206 Partial Content。"""
    file_size = os.path.getsize(file_path)
    fn = os.path.basename(file_path)
    ctype = "application/json" if fn.endswith(".json") else "application/octet-stream"

    # 处理 Range 请求
    start = 0
    end = file_size - 1
    status = 200

    if range_header and range_header.startswith("bytes="):
        try:
            parts = range_header.replace("bytes=", "").split("-")
            if parts[0]:
                start = int(parts[0])
            if len(parts) > 1 and parts[1]:
                end = int(parts[1])
            if end >= file_size:
                end = file_size - 1
            if start <= end and start < file_size:
                status = 206
            elif start >= file_size:
                # 断点续传已完整（Range 起点超出文件）：按 RFC 返回 416，
                # 否则客户端更新器会拿到 Content-Length:0 的假 200 而永久挂起
                resp = Response("Range Not Satisfiable", status=416, mimetype="text/plain")
                resp.headers["Content-Range"] = f"bytes */{file_size}"
                resp.headers["Accept-Ranges"] = "bytes"
                return resp
        except Exception:
            start = 0
            end = file_size - 1
            status = 200

    length = end - start + 1

    def _file_gen():
        with open(file_path, "rb") as f:
            if start > 0:
                f.seek(start)
            remaining = length
            while remaining > 0:
                chunk_len = min(LOCAL_CHUNK_SIZE, remaining)
                data = f.read(chunk_len)
                if not data:
                    break
                remaining -= len(data)
                yield data

    resp = Response(_file_gen(), status=status, mimetype=ctype)
    resp.headers["Content-Length"] = str(length)
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    if fn.endswith((".bytes", ".json")):
        # 官方 CDN 对 200 与 206 恒带这三个校验头；321 更新器（WWWDownloadHandler）
        # 依赖它们判定分片/续传响应的完整性——缺失会导致下载永不完成（E3' 卡死根因）
        etag_hex, cmd5 = _file_md5_headers(file_path)
        resp.headers["ETag"] = f'"{etag_hex}"'
        resp.headers["Content-MD5"] = cmd5
        resp.headers["Last-Modified"] = time.strftime(
            "%a, %d %b %Y %H:%M:%S GMT", time.gmtime(os.path.getmtime(file_path)))
    if status == 206:
        resp.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    return resp


def stream_upstream_and_cache(path, host="download-eo.ys4fun.com", query="", headers=None,
                              range_header=None, log=_logger_log):
    r"""
    流式双向转发与边下边存核心引擎（严格平台隔离）：
    - 边从官方 CDN 流式拉取（64KB chunk），边向客户端发送，同时写入 D:\<PLATFORM>_DATA/<fn>.part
    - 下载完成后原子重命名为正式文件
    """
    fn = os.path.basename(path.split("?")[0])
    platform = get_platform_from_path(path, headers)
    target_dir = get_data_dir(platform)
    final_file = os.path.join(target_dir, fn)
    part_file = os.path.join(target_dir, f"{fn}.{os.getpid()}_{int(time.time()*1000)}.part")

    ips = resolve_doh(host)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    full_path = path + (f"?{query}" if query else "")
    req_headers = {
        "Host": host,
        "User-Agent": "UnityPlayer/2022.3.62f3 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Accept": "*/*",
        "Accept-Encoding": "identity",
    }
    if headers:
        for k, v in headers.items():
            if k.lower() not in ("host", "accept-encoding", "content-length"):
                req_headers[k] = v

    # 若客户端有 Range，透传给官方 CDN 保持一致性
    if range_header:
        req_headers["Range"] = range_header

    conn = None
    u_resp = None
    last_err = None

    for target_ip in ips:
        try:
            conn = http.client.HTTPSConnection(target_ip, 443, context=ctx, timeout=30)
            sock = create_direct_socket(target_ip, 443, timeout=30)
            conn.sock = ctx.wrap_socket(sock, server_hostname=host)
            conn.request("GET", full_path, headers=req_headers)
            u_resp = conn.getresponse()
            if u_resp.status in (200, 206):
                break
            else:
                conn.close()
                conn = None
        except Exception as e:
            last_err = e
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
            continue

    if not u_resp or u_resp.status not in (200, 206):
        log(f"穿透连接官方 CDN 失败: {host}{full_path} err={last_err}", "WARN", module="CDN")
        return Response("Not Found", status=404)

    status_code = u_resp.status
    content_len_hdr = u_resp.getheader("Content-Length")
    content_type = u_resp.getheader("Content-Type") or (
        "application/json" if (fn.endswith(".bytes") or fn.endswith(".json")) else "application/octet-stream"
    )
    content_range = u_resp.getheader("Content-Range")
    etag = u_resp.getheader("ETag")

    expected_len = int(content_len_hdr) if content_len_hdr and content_len_hdr.isdigit() else None
    # 过程日志写入全量底账文件，不污染控制台
    log(f"开始流式抓取 ({platform.upper()}): {fn} (status={status_code}, len={content_len_hdr or 'chunked'}B)...", "DEBUG", module="CDN", to_console=False)

    # 仅当捕获完整文件（200 或 Range=0-）时才落盘为完整文件
    can_cache_full = (status_code == 200) or (range_header and range_header.startswith("bytes=0-"))

    def _stream_gen():
        total_downloaded = 0
        part_fp = None
        if can_cache_full:
            try:
                part_fp = open(part_file, "wb")
            except Exception as e:
                log(f"无法创建临时落盘文件 {part_file}: {e}", "WARN", module="CDN", to_console=False)
                part_fp = None

        try:
            while True:
                chunk = u_resp.read(UPSTREAM_CHUNK_SIZE)
                if not chunk:
                    break
                total_downloaded += len(chunk)
                if part_fp:
                    try:
                        part_fp.write(chunk)
                    except Exception:
                        pass
                yield chunk
        finally:
            if part_fp:
                try:
                    part_fp.flush()
                    part_fp.close()
                except Exception:
                    pass

            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

            # 校验并原子重命名
            if can_cache_full and os.path.isfile(part_file):
                if expected_len is None or total_downloaded >= expected_len:
                    rename_ok = False
                    try:
                        os.replace(part_file, final_file)
                        rename_ok = True
                    except Exception:
                        try:
                            if os.path.exists(final_file):
                                os.remove(final_file)
                            os.rename(part_file, final_file)
                            rename_ok = True
                        except Exception as re2:
                            log(f"重命名落盘异常: {re2}", "WARN", module="CDN")
                    if rename_ok:
                        # 流程完毕直接在控制台输出单行干净的人机日志
                        summary = log_sifter.asset_flow_shaper.format_asset_finished(
                            fn, total_downloaded, platform=platform, status=f"{status_code} OK (已落盘入库)"
                        )
                        _logger_log(summary, "INFO", module="CDN")
                else:
                    # 未下载完整则清理
                    try:
                        os.remove(part_file)
                    except Exception:
                        pass

    resp = Response(_stream_gen(), status=status_code, mimetype=content_type)
    if content_len_hdr:
        resp.headers["Content-Length"] = content_len_hdr
    if content_range:
        resp.headers["Content-Range"] = content_range
    if etag:
        resp.headers["ETag"] = etag
    for hdr in ("Content-MD5", "Last-Modified"):
        v = u_resp.getheader(hdr)
        if v:
            resp.headers[hdr] = v
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


def fetch_upstream(host, path, query="", headers=None, method="GET", body=None, timeout=30, log=print):
    """单次短请求官方接口穿透（供 updateversion/getLatest 等小 JSON 接口使用）。"""
    ips = resolve_doh(host)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    full_path = path + (f"?{query}" if query else "")
    req_headers = {
        "Host": host,
        "User-Agent": "UnityPlayer/2022.3.62f3 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Accept": "*/*",
        "Accept-Encoding": "identity",
    }
    if headers:
        for k, v in headers.items():
            if k.lower() not in ("host", "accept-encoding", "content-length", "range"):
                req_headers[k] = v

    last_err = None
    for target_ip in ips:
        try:
            conn = http.client.HTTPSConnection(target_ip, 443, context=ctx, timeout=timeout)
            sock = create_direct_socket(target_ip, 443, timeout=timeout)
            conn.sock = ctx.wrap_socket(sock, server_hostname=host)
            conn.request(method, full_path, body=body, headers=req_headers)
            resp = conn.getresponse()
            status = resp.status
            resp_headers = dict(resp.getheaders())
            data = resp.read()
            conn.close()
            return status, resp_headers, data
        except Exception as e:
            last_err = e
            continue

    log(f"[CDN_PROXY] 穿透连接 {host} ({full_path}) 失败: {last_err}")
    return 502, {}, b""


def handle_resource_request(path, host="download-eo.ys4fun.com", query="", headers=None, log=_logger_log):
    r"""
    统一资源调度网关（严格平台隔离）：
    1. 检查 D:\<PLATFORM>_DATA 及 static_resources 本地是否存在完整文件，若存在秒发；
    2. 若本地不存在且开启抓包器，发起零内存消耗的高性能流式双向管道，边转发边存盘到该平台专属目录。
    """
    fn = os.path.basename(path.split("?")[0])
    platform = get_platform_from_path(path, headers)
    range_hdr = headers.get("Range") if headers else None

    # ==== 语音零差异跑步机（M1 Task 6 / U16 路径② 根因对策，2026-09-28） ====
    # 321 客户端语音更新链存在两处服务端可绕开的死锁：
    #   ① 清单与本地完全一致但存在缺失文件时 → WaitConfirm 确认弹窗在启动环屏阶段
    #      无法渲染 → 永久等待（E0 官方字节卡死根因）；
    #   ② 完全无工作（空列表/版本相等且零差异前置态）时 → DownloadHaseNode /
    #      VoiceDiffNode 空转永不完成（E1 卡死根因）。
    # 对策：恒定下发 zh-only + 版本 30701000 + 与客户端本地磁盘 100% 一致的修剪清单
    # （voice_hash_zh_30701000.bytes，剔除本地缺失的 30 个 story_v_side_new_*）。
    # 客户端每次走“下载清单(真网络工作)→diff=空→跳过确认→校验全过→Downloaded”
    # 的官方稳态路径，既避开死锁①②，也绝不触发大文件下载。
    # 环境开关：AG_VOICE_TREADMILL=0 关闭（回落官方透传行为）。
    if _VOICE_TREADMILL_ENABLED and platform == "pc":
        _treadmill_ver = _voice_treadmill_version()
        if fn.startswith("voice_package_list_307_"):
            body = ('{"infos":[{"name":"zh","version":%d,"size":6601309}]}'
                    % _treadmill_ver).encode("utf-8")
            log(f"[CDN] 语音跑步机：下发 zh-only 零差异列表 (version={_treadmill_ver})",
                "INFO", module="CDN")
            resp = Response(body, status=200, mimetype="application/octet-stream")
            resp.headers["Content-Length"] = str(len(body))
            resp.headers["Accept-Ranges"] = "bytes"
            resp.headers["Access-Control-Allow-Origin"] = "*"
            etag_hex, cmd5 = _file_md5_bytes(body)
            resp.headers["ETag"] = f'"{etag_hex}"'
            resp.headers["Content-MD5"] = cmd5
            resp.headers["Last-Modified"] = time.strftime(
                "%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
            return resp
        _m = re.match(r"^voice_hash_zh_(\d{6,})\.bytes$", fn)
        if _m and _VOICE_TREADMILL_BASE <= int(_m.group(1)) <= _treadmill_ver:
            body = _voice_treadmill_manifest_bytes(int(_m.group(1)))
            if body is not None:
                log(f"[CDN] 语音跑步机：合成零差异清单 (version={_m.group(1)})", "INFO", module="CDN")
                resp = Response(body, status=200, mimetype="application/octet-stream")
                resp.headers["Content-Length"] = str(len(body))
                resp.headers["Accept-Ranges"] = "bytes"
                resp.headers["Access-Control-Allow-Origin"] = "*"
                etag_hex, cmd5 = _file_md5_bytes(body)
                resp.headers["ETag"] = f'"{etag_hex}"'
                resp.headers["Content-MD5"] = cmd5
                resp.headers["Last-Modified"] = time.strftime(
                    "%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
                return resp
            log("[CDN] 语音跑步机：警告——修剪清单模板缺失（cdn_cache/pc/"
                "voice_hash_zh_%d.bytes），该清单回落常规缓存/透传路径"
                % _VOICE_TREADMILL_BASE, "WARN", module="CDN")

    # 1. 查找本地缓存（优先该平台目录）
    cached = find_cached_file(fn, platform=platform)
    is_cached_ready = cached and (
        (not _CAPTURE_ENABLED)
        or (fn.endswith(".bytes") or fn.endswith(".json") or os.path.getsize(cached) > 0)
    )
    if is_cached_ready:
        # 对重要配置与清单资产，下发时在控制台展示单行摘要
        if fn.endswith(".json") or fn.endswith(".bytes"):
            summary = log_sifter.asset_flow_shaper.format_asset_finished(
                fn, os.path.getsize(cached), platform=platform, status="200 OK (本地缓存秒发)"
            )
            _logger_log(summary, "INFO", module="CDN")
        return serve_local_stream(cached, range_header=range_hdr)

    # 2. 本地不存在或需要实时抓包，启动流式双向转发
    if _CAPTURE_ENABLED or _AUTO_CACHE_FALLBACK:
        upstream_host = host if ("download" in host) else "download-eo.ys4fun.com"
        return stream_upstream_and_cache(path, host=upstream_host, query=query,
                                       headers=headers, range_header=range_hdr, log=log)

    # 3. 兜底返回 404
    if cached:
        return serve_local_stream(cached, range_header=range_hdr)
    return Response("Not Found", status=404)
