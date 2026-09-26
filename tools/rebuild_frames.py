#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/rebuild_frames.py — pcap/pcapng → 帧流 JSONL 重建（M0.4 产物生成器）

帧格式权威依据：v5_server/transport.py（直接 import 复用，保证与服务端解析一致）：
  上行（客户端→服务器，TCP 8102/8105）：
    u32 len(LE)=9+payload | u8 ver | u32 cmd(LE) | u16 idx(LE) | u16 srv(LE) | payload
  下行（服务器→客户端）：
    u16 size(BE)=body长 | u8 zlib_flag | 0x00 | u8 high_flag | u16 frame_cmd(BE)
    | u16 idx(BE) | u16 srv(BE) | payload
  payload 以 78 9c 开头 = zlib 压缩。
UDP 6105（战斗）：切帧依据未定（待读 battle_server.py 核定），现按单报文导出 hex。

用法：
  python tools/rebuild_frames.py <raw.pcapng> -o <rebuilt目录>
  python tools/rebuild_frames.py --selftest
依赖：pip install dpkt
"""
import argparse
import json
import os
import socket
import struct
import sys
from collections import defaultdict

import dpkt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "v5_server"))
from transport import FrameParser, pack_up, pack_down, unpack_up, unpack_down  # noqa: E402


def ip_str(b: bytes) -> str:
    if len(b) == 4:
        return socket.inet_ntoa(b)
    return socket.inet_ntop(socket.AF_INET6, b)


def reassemble(segments):
    """同一方向的 [(seq, payload)] → 按序去重重组的字节流。
    简化假设：单场景会话远小于 4GB 无 seq 回绕；忽略 IP 分片。"""
    if not segments:
        return b""
    base = min(seq for seq, _ in segments)
    ordered = sorted(segments, key=lambda t: (t[0] - base) % (1 << 32))
    out = bytearray()
    expect = None
    for seq, payload in ordered:
        if expect is None:
            expect = seq
        if seq + len(payload) <= expect:
            continue  # 纯重传
        if seq > expect:
            print(f"[warn] TCP 流缺口 {seq - expect}B（跳过继续）", file=sys.stderr)
            expect = seq
        out += payload[expect - seq:]
        expect = seq + len(payload)
    return bytes(out)


def iter_ip(buf, datalink):
    if datalink == 1:      # DLT_EN10MB（Windows npcap 常规/回环捕获）
        pkt = dpkt.ethernet.Ethernet(buf)
        return pkt.data if isinstance(pkt.data, dpkt.ip.IP) else None
    if datalink == 0:      # DLT_NULL
        return dpkt.ip.IP(buf[4:])
    if datalink in (12, 101, 14):  # DLT_RAW 变体
        return dpkt.ip.IP(buf)
    if datalink == 113:    # Linux SLL
        pkt = dpkt.sll.SLL(buf)
        return pkt.data if isinstance(pkt.data, dpkt.ip.IP) else None
    raise SystemExit(f"不支持的链路类型 datalink={datalink}，用 Wireshark 另存为 pcap 重试")


def open_reader(path):
    f = open(path, "rb")
    magic = f.read(4)
    f.seek(0)
    if magic == b"\x0a\x0d\x0d\x0a":
        return dpkt.pcapng.Reader(f)
    return dpkt.pcap.Reader(f)


def rebuild(pcap_path, out_dir, tcp_ports, udp_port):
    os.makedirs(out_dir, exist_ok=True)
    reader = open_reader(pcap_path)
    dl = reader.datalink()
    ports = set(tcp_ports)
    tcp_segs = defaultdict(list)   # (src,sport,dst,dport) -> [(seq,payload)]
    udp_dgrams = []
    for ts, buf in reader:
        ip = iter_ip(buf, dl)
        if ip is None:
            continue
        l4 = ip.data
        if isinstance(l4, dpkt.tcp.TCP):
            if not l4.data or not (l4.sport in ports or l4.dport in ports):
                continue
            tcp_segs[(ip.src, l4.sport, ip.dst, l4.dport)].append((l4.seq, bytes(l4.data)))
        elif isinstance(l4, dpkt.udp.UDP):
            if udp_port in (l4.sport, l4.dport) and l4.data:
                udp_dgrams.append((ts, ip.src, l4.sport, ip.dst, l4.dport, bytes(l4.data)))

    summary = []
    n = 0
    for (src, sport, dst, dport), segs in sorted(tcp_segs.items()):
        if dport in ports:
            direction, port = "up", dport
        else:
            direction, port = "down", sport
        stream = reassemble(segs)
        fp = FrameParser(direction)
        frames = fp.feed(stream)
        leftover = len(fp.buf)
        n += 1
        name = f"tcp_{n}_{direction}_{port}.jsonl"
        cmds = []
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as w:
            for fr in frames:
                try:
                    rec = unpack_up(fr) if direction == "up" else unpack_down(fr)
                except Exception as e:
                    w.write(json.dumps({"type": "tcp", "dir": direction, "error": str(e),
                                        "raw_hex": fr.hex()}, ensure_ascii=False) + "\n")
                    continue
                payload = rec.pop("payload", b"")
                rec.update({"type": "tcp", "dir": direction,
                            "payload_len": len(payload), "payload_hex": payload.hex()})
                cmds.append(rec.get("cmd"))
                w.write(json.dumps(rec, ensure_ascii=False) + "\n")
        summary.append(
            f"| {name} | {direction} | {ip_str(src)}:{sport} → {ip_str(dst)}:{dport} "
            f"| {len(stream)} | {len(frames)} | {leftover} | {cmds[:20]}{'…' if len(cmds) > 20 else ''} |")

    if udp_dgrams:
        with open(os.path.join(out_dir, f"udp_{udp_port}.jsonl"), "w", encoding="utf-8") as w:
            for ts, src, sport, dst, dport, data in udp_dgrams:
                w.write(json.dumps({"type": "udp", "port": udp_port,
                                    "dir": "up" if dport == udp_port else "down",
                                    "ts": ts, "from": f"{ip_str(src)}:{sport}",
                                    "to": f"{ip_str(dst)}:{dport}",
                                    "len": len(data), "payload_hex": data.hex()},
                                   ensure_ascii=False) + "\n")
        summary.append(f"| udp_{udp_port}.jsonl | udp | 战斗报文 | "
                       f"{sum(len(d) for *_, d in udp_dgrams)} | {len(udp_dgrams)} | 0 | — |")

    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as w:
        w.write(f"# 帧流重建汇总 — {os.path.basename(pcap_path)}\n\n")
        w.write("| 文件 | 方向 | 端点 | 流字节 | 帧数 | 残留字节 | cmd 序列(前20) |\n"
                "|---|---|---|---|---|---|---|\n")
        w.writelines(s + "\n" for s in summary)
    print(f"重建完成：{n} 个 TCP 方向 + {len(udp_dgrams)} 条 UDP 报文 → {out_dir}")


# ---------------- 自测：手工构造合法 pcap，无需真实抓包 ----------------

def _l3(src, dst, proto, l4):
    total = 20 + len(l4)
    return struct.pack("!BBHHHBBH4s4s", 0x45, 0, total, 0, 0x4000, 64, proto, 0,
                       bytes(int(x) for x in src.split(".")),
                       bytes(int(x) for x in dst.split("."))) + l4


def _eth(ip_pkt):
    return b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\x08\x00" + ip_pkt


def tcp_pkt(src, dst, sport, dport, seq, payload):
    tcp = struct.pack("!HHIIBBHHH", sport, dport, seq, 0, 0x50, 0x18, 8192, 0, 0)
    return _eth(_l3(src, dst, 6, tcp + payload))


def udp_pkt(src, dst, sport, dport, payload):
    udp = struct.pack("!HHHH", sport, dport, 8 + len(payload), 0) + payload
    return _eth(_l3(src, dst, 17, udp))


def write_pcap(path, pkts):
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for i, p in enumerate(pkts):
            f.write(struct.pack("<IIII", 1770000000 + i, 0, len(p), len(p)) + p)


def selftest(tmp="selftest_tmp"):
    up_stream = (pack_up(10038, b"\x08\x01")
                 + pack_up(10042, b"\x08\x02\x12\x02ab")
                 + pack_up(10050, b"\x08\x03"))
    big = bytes(range(256)) * 48  # 12,288B → 触发 pack_down 自动 zlib 压缩
    down_stream = pack_down(10039, b"\x08\x96\x01") + pack_down(14009, big)
    c, s = "192.168.31.10", "203.0.113.7"
    pkts = [
        tcp_pkt(c, s, 55555, 8105, 1000, up_stream[:10]),   # 半个帧头
        tcp_pkt(c, s, 55555, 8105, 1000, up_stream[:10]),   # 重传副本
        tcp_pkt(c, s, 55555, 8105, 1010, up_stream[10:]),
        tcp_pkt(s, c, 8105, 55555, 5000, down_stream),
        udp_pkt(c, s, 6106, 6105, b"\x01\x02\x03"),
    ]
    os.makedirs(tmp, exist_ok=True)
    pcap = os.path.join(tmp, "selftest.pcap")
    write_pcap(pcap, pkts)
    rebuild(pcap, os.path.join(tmp, "rebuilt"), [8102, 8105], 6105)
    lines = []
    for fn in os.listdir(os.path.join(tmp, "rebuilt")):
        if fn.endswith(".jsonl"):
            lines += [json.loads(x) for x in open(os.path.join(tmp, "rebuilt", fn), encoding="utf-8")]
    up_cmds = [r["cmd"] for r in lines if r.get("dir") == "up" and r.get("type") == "tcp"]
    down_cmds = [r["cmd"] for r in lines if r.get("dir") == "down" and r.get("type") == "tcp"]
    udp_n = sum(1 for r in lines if r.get("type") == "udp")
    assert up_cmds == [10038, 10042, 10050], up_cmds
    assert down_cmds == [10039, 14009], down_cmds
    assert udp_n == 1, udp_n
    big_rec = next(r for r in lines if r.get("cmd") == 14009)
    assert big_rec["compressed"] and big_rec["payload_len"] > 12000
    print("自测通过：上行 3 帧(10038/10042/10050)、下行 2 帧(10039/14009，含 zlib 解压)、UDP 1 条、"
          "跨段重组与重传去重正确")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pcap", nargs="?", help="pcap/pcapng 文件")
    ap.add_argument("-o", "--out", help="输出目录（默认 <pcap所在目录>/rebuilt）")
    ap.add_argument("--tcp-ports", default="8102,8105")
    ap.add_argument("--udp-port", type=int, default=6105)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    if not args.pcap:
        ap.error("需提供 pcap 文件，或用 --selftest 自测")
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.pcap)), "rebuilt")
    rebuild(args.pcap, out, [int(x) for x in args.tcp_ports.split(",") if x.strip()],
            args.udp_port)


if __name__ == "__main__":
    main()
