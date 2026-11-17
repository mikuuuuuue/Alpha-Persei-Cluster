"""Rebuild one complete TCP 8105 capture using TShark and transport.py."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'v5_server'))
from transport import FrameParser, unpack_down, unpack_up


def _reassemble(packets, direction):
    """Check byte continuity and retain first-arrival packet provenance."""
    syn = [p for p in packets if p['syn']]
    if not syn:
        raise ValueError(f'{direction} 缺少 SYN；请从启动游戏前开始捕获')
    starts = {(p['seq'] + 1) & 0xFFFFFFFF for p in syn}
    if len(starts) != 1:
        raise ValueError(f'{direction} SYN 序号冲突')
    start = starts.pop()
    memory = {}
    retransmitted = 0
    for packet in packets:
        if packet['reset']:
            raise ValueError('连接被重置，请重新捕获完整登录')
        offset = (packet['seq'] + int(packet['syn']) - start) & 0xFFFFFFFF
        if packet['payload'] and offset >= 2**31:
            raise ValueError(f'{direction} TCP 序号超出连接范围')
        for index, value in enumerate(packet['payload'], offset):
            prior = memory.get(index)
            if prior:
                if prior[0] != value:
                    raise ValueError(f'{direction} TCP 重叠字节冲突：{index}')
                retransmitted += 1
            else:
                memory[index] = (value, packet['number'], packet['time'])
    if not memory or len(memory) != max(memory) + 1:
        raise ValueError(f'{direction} TCP 存在缺口或没有应用数据')
    ordered = [memory[index] for index in range(len(memory))]
    parser = FrameParser(direction)
    frames = parser.feed(bytes(item[0] for item in ordered))
    if parser.buf:
        raise ValueError(f'{direction} 应用帧残留 {len(parser.buf)} 字节')
    output = []
    cursor = 0
    delivered = 0.0
    for frame in frames:
        decoded = (unpack_up if direction == 'up' else unpack_down)(frame)
        if not decoded:
            raise ValueError(f'{direction} 存在无效应用帧')
        provenance = ordered[cursor:cursor + len(frame)]
        delivered = max(delivered, max(item[2] for item in provenance))
        payload = decoded.pop('payload')
        decoded.update(type='tcp', dir=direction, payload_hex=payload.hex(), payload_len=len(payload),
            ts=delivered, pcap_packets=sorted({item[1] for item in provenance}), tcp_offset=cursor, wire_len=len(frame))
        decoded.setdefault('flag', 0)
        decoded.setdefault('frame_cmd', decoded['cmd'] & 0xFFFF)
        output.append(decoded)
        cursor += len(frame)
    return output, dict(bytes=len(memory), frames=len(frames), retransmitted_bytes=retransmitted,
                        residual=0, gaps=0, conflicting_bytes=0)


def rebuild(source, destination):
    """Create a new evidence directory; never modify or overwrite an input."""
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('输出目录已存在；请使用新的目录名')
    tshark = shutil.which('tshark') or str(Path('C:/Program Files/Wireshark/tshark.exe'))
    if not Path(tshark).is_file():
        raise ValueError('没有找到 TShark；请安装 Wireshark 的命令行工具')
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    fields = ('frame.number', 'frame.time_epoch', 'frame.len', 'frame.cap_len', 'tcp.stream',
        'ip.src', 'tcp.srcport', 'ip.dst', 'tcp.dstport', 'tcp.seq_raw', 'tcp.flags.syn',
        'tcp.flags.fin', 'tcp.flags.reset', 'tcp.len', 'tcp.payload')
    command = [tshark, '-r', str(source), '-Y', 'tcp.port == 8105', '-T', 'fields',
        '-E', 'header=y', '-E', 'separator=/t', '-E', 'occurrence=f']
    for field in fields:
        command.extend(('-e', field))
    result = subprocess.run(command, capture_output=True, check=True, encoding='utf-8', timeout=180)
    streams = {}
    for row in csv.DictReader(io.StringIO(result.stdout), delimiter='\t'):
        if int(row['frame.len']) != int(row['frame.cap_len']):
            raise ValueError(f"数据包 {row['frame.number']} 被截断")
        if not row['ip.src'] or not row['ip.dst']:
            raise ValueError('当前重建只接受 IPv4 TCP 8105 连接')
        payload = bytes.fromhex(row['tcp.payload'].replace(':', ''))
        if len(payload) != int(row['tcp.len']):
            raise ValueError(f"数据包 {row['frame.number']} 的 TCP 载荷长度不符")
        packet = dict(number=int(row['frame.number']), time=float(row['frame.time_epoch']),
            seq=int(row['tcp.seq_raw']), payload=payload,
            syn=row['tcp.flags.syn'].lower() in ('1', 'true'), fin=row['tcp.flags.fin'].lower() in ('1', 'true'),
            reset=row['tcp.flags.reset'].lower() in ('1', 'true'),
            source=f"{row['ip.src']}:{row['tcp.srcport']}", target=f"{row['ip.dst']}:{row['tcp.dstport']}")
        direction = 'down' if row['tcp.srcport'] == '8105' else 'up'
        streams.setdefault(int(row['tcp.stream']), {}).setdefault(direction, []).append(packet)
    if len(streams) != 1 or set(next(iter(streams.values()), {})) != {'up', 'down'}:
        raise ValueError('需要唯一双向 TCP 8105 连接；请退出游戏后重新捕获一次登录')
    stream_id, directions = next(iter(streams.items()))
    frames = {}
    audit = dict(source_name=source.name, source_sha256=source_hash, stream=stream_id, directions={})
    table = ['| file | direction | endpoints | frames | residual bytes |', '|---|---|---|---|---|']
    for direction in ('up', 'down'):
        frames[direction], audit['directions'][direction] = _reassemble(directions[direction], direction)
        packet = directions[direction][0]
        table.append(f"| tcp_{stream_id}_{direction}_8105.jsonl | {direction} | {packet['source']} → {packet['target']} | {len(frames[direction])} | 0 |")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.capture-', dir=destination.parent) as temporary:
        stage = Path(temporary) / 'rebuilt'
        stage.mkdir()
        for direction, rows in frames.items():
            (stage / f'tcp_{stream_id}_{direction}_8105.jsonl').write_text(
                ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
        (stage / 'summary.md').write_text(f'Source capture: {source.name}\nSHA256: {source_hash}\n\n' + '\n'.join(table) + '\n', encoding='utf-8')
        from capture_import import read_snapshot
        snapshot = read_snapshot(stage)
        audit.update(login_frames=len(snapshot.login_frames), end_command=snapshot.end_frame.cmd,
                     client_build=snapshot.client_build, resource_version=snapshot.resource_version)
        (stage / 'reconstruction.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
        if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
            raise ValueError('捕获文件在重建期间发生变化')
        stage.rename(destination)
    return audit


def main(argv=None):
    parser = argparse.ArgumentParser(description='从完整 pcapng 重建单次 8105 登录流')
    parser.add_argument('capture', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(rebuild(args.capture, args.output), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps(dict(ready=False, error=str(exc)), ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
