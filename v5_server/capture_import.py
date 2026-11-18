"""Build a new single-account save from one captured login snapshot."""
from dataclasses import dataclass, field
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime


REQUIRED_COMMANDS = (12009, 13009, 14009, 15009, 17009, 20009, 23009,
                    24009, 24017, 28001, 28019, 30001, 41001, 46011, 60201)
MAPPED_COMMANDS = frozenset(REQUIRED_COMMANDS) | {10043}
HERO_COMMANDS = (12009, 13009, 14009, 46011)
MAIL_MUTATION_COMMANDS = frozenset((30004, 30006, 30008, 30010, 30012, 30014))
MAIL_RESPONSE_MUTATIONS = frozenset((30005, 30007, 30009, 30011, 30013, 30015))


@dataclass(frozen=True)
class CapturedFrame:
    cmd: int
    payload: bytes
    source_file: str
    source_line: int
    server_idx: int
    compressed: bool
    decoded: dict = field(compare=False, repr=False)
    timestamp: float | None = None
    frame_index: int = 0
    frame_flag: int = 0


@dataclass
class CaptureSnapshot:
    source_uid: int
    client_build: str
    resource_version: str
    session_id: str
    login_frames: list[CapturedFrame]
    supplement_frames: list[CapturedFrame]
    source_sha256: dict[str, str]
    protocol_data: dict[int, list[dict]]
    end_frame: CapturedFrame | None = None
    unsupported_login_commands: list[int] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    missing_data: list[dict] = field(default_factory=list)
    _mail_templates: dict[int, dict] = field(default_factory=dict, init=False, repr=False)
    _mail_records: list[dict] = field(default_factory=list, init=False, repr=False)
    _collected_mail_records: list[dict] = field(default_factory=list, init=False, repr=False)
    _mail_detail_supplements: dict[int, dict] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        messages = [mail for frame in self.supplement_frames
                    for field in ('mail_list', 'collect_mail_list')
                    for mail in frame.decoded.get(field, [])]
        if not any(not (mail.get('content_list') or mail.get('content')) or not mail.get('title')
                   for mail in messages):
            return
        from mail_service import TEMPLATES_PATH
        try:
            raw = Path(TEMPLATES_PATH).read_bytes()
            rows = json.loads(raw)
        except (OSError, ValueError) as exc:
            self.issues.append('邮件模板归档不可用：' + str(exc))
            return
        self._mail_templates = {int(row['id']): row for row in rows}
        self.source_sha256 = dict(self.source_sha256)
        self.source_sha256['catalog:mail_archive/mail_templates.json'] = hashlib.sha256(raw).hexdigest()


@dataclass
class ImportReport:
    target_uid: int | None
    row_counts: dict[str, int] = field(default_factory=dict)
    missing_data: list[dict] = field(default_factory=list)
    validation: dict = field(default_factory=dict)
    output_path: str = ""
    slot_registration: dict = field(default_factory=dict)
    source_sha256: dict[str, str] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    snapshot: CaptureSnapshot | None = field(default=None, repr=False)

    def public_data(self):
        return {key: value for key, value in vars(self).items() if key != 'snapshot'}


def _decode_frame(row, source_file, source_line):
    import codec

    try:
        cmd = int(row["cmd"])
        raw = bytes.fromhex(row["payload_hex"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{source_file}:{source_line}: 帧字段无效") from exc
    if not isinstance(row.get('compressed'), bool):
        raise ValueError(f'{source_file}:{source_line}: 缺少布尔压缩标志')
    for key in ('index', 'server_idx', 'flag'):
        if key == 'flag' and row.get('dir') == 'up' and row.get(key) is None:
            continue
        if type(row.get(key)) is not int or not 0 <= row[key] <= (1 if key == 'flag' else 65535):
            raise ValueError(f'{source_file}:{source_line}: 帧头字段 {key} 无效')
    frame_cmd = row.get("frame_cmd")
    if frame_cmd is not None and (int(frame_cmd) & 0xFFFF) != (cmd & 0xFFFF):
        raise ValueError(f"{source_file}:{source_line}: cmd 与 frame_cmd 不一致")
    if row.get("dir") not in ("up", "down") or row.get("type") != "tcp":
        raise ValueError(f"{source_file}:{source_line}: 不是 TCP 应用帧")
    if len(raw) != int(row.get("payload_len", len(raw))):
        raise ValueError(f"{source_file}:{source_line}: payload_len 不匹配")
    schema = ("cs_" if row["dir"] == "up" else "sc_") + str(cmd)
    try:
        decoded = codec.decode(raw, schema)
    except Exception as exc:
        raise ValueError(f"{source_file}:{source_line}: {schema} 解码失败") from exc
    if not isinstance(decoded, dict):
        raise ValueError(f'{source_file}:{source_line}: {schema} 未返回协议对象')
    stamp = row.get("timestamp") or row.get("ts")
    try:
        if isinstance(stamp, str):
            stamp_value = datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
        else:
            stamp_value = float(stamp) if stamp is not None else None
        if stamp_value is not None and not math.isfinite(stamp_value):
            stamp_value = None
    except (TypeError, ValueError, OverflowError):
        stamp_value = None
    return CapturedFrame(cmd, raw, source_file, source_line,
                         int(row.get("server_idx") or 0),
                         bool(row.get("compressed")), decoded, stamp_value,
                         int(row.get("index") or 0), int(row.get("flag") or 0))


def _summary_connections(root):
    """Map rebuilt streams to their local TCP port without reading payloads."""
    path = root / "summary.md"
    if not path.is_file():
        raise ValueError('缺少 summary.md 连接归属摘要')
    found = {}
    raw = path.read_bytes()
    for line in raw.decode('utf-8').splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or not cells[0].endswith('_8105.jsonl'):
            continue
        if len(cells) < 5 or not re.fullmatch(r'tcp_\d+_(up|down)_8105\.jsonl', cells[0]):
            raise ValueError('8105 连接摘要缺少文件名、帧数或重建残留数量')
        endpoint = cells[2]
        match = re.fullmatch(r"(.+):(\d+)\s*→\s*(.+):(\d+)", endpoint)
        if not match:
            raise ValueError(f'{cells[0]} 的连接端点无效')
        try:
            frame_count, residual = int(cells[3]), int(cells[4])
        except ValueError as exc:
            raise ValueError(f'{cells[0]} 的帧数或重建残留数量无效') from exc
        if frame_count < 0 or residual != 0:
            raise ValueError(f'{cells[0]} 的帧数无效或存在重建残留')
        direction = cells[1]
        source_host, source_port = match.group(1), int(match.group(2))
        target_host, target_port = match.group(3), int(match.group(4))
        if direction == "up":
            if target_port != 8105:
                raise ValueError(f'{cells[0]} 的目标端口不是 8105')
            local_port, remote_host = source_port, target_host
        elif direction == "down":
            if source_port != 8105:
                raise ValueError(f'{cells[0]} 的来源端口不是 8105')
            local_port, remote_host = target_port, source_host
        else:
            raise ValueError(f'{cells[0]} 的连接方向无效')
        local_host = source_host if direction == 'up' else target_host
        if cells[0] in found:
            raise ValueError(f'{cells[0]} 的连接摘要重复')
        found[cells[0]] = (direction, local_port, remote_host.strip(), local_host.strip(), frame_count)
    return found, hashlib.sha256(raw).hexdigest()


def _load_stream(path, connection_map):
    summary = connection_map.get(path.name)
    if summary is None:
        raise ValueError(f"缺少 {path.name} 的连接归属摘要")
    expected_dir, local_port, remote_host, local_host, frame_count = summary
    frames = []
    raw = path.read_bytes()
    for line_number, line in enumerate(raw.decode('utf-8').splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{line_number}: JSONL 行无效") from exc
        if row.get("dir") != expected_dir:
            raise ValueError(f"{path.name}:{line_number}: 帧方向与 summary.md 不一致")
        frames.append(_decode_frame(row, path.name, line_number))
    if len(frames) != frame_count:
        raise ValueError(f'{path.name}: 实际帧数与 summary.md 不一致')
    if any(frame.timestamp is None for frame in frames):
        raise ValueError(f'{path.name}: 缺少连续记录的时间戳')
    if any(right.timestamp < left.timestamp for left, right in zip(frames, frames[1:])):
        raise ValueError(f'{path.name}: 帧时间倒序，不能证明会话连续')
    return expected_dir, local_port, remote_host, local_host, frames, hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _merge_chapters(frames, issues):
    merged = {}
    for frame in frames:
        for item in frame.decoded.get("user_chapter_list", []):
            if not isinstance(item, dict) or "id" not in item:
                issues.append(f"{frame.source_file}:{frame.source_line}: 24009 缺少章节主键 id")
                continue
            key = int(item["id"])
            prior = merged.get(key)
            if prior is not None and _canonical(prior) != _canonical(item):
                issues.append(f"24009 主键 {key} 的分段值冲突")
                continue
            merged[key] = item
    return [merged[key] for key in sorted(merged)]


def _mail_record(message, templates):
    record = dict(message)
    record.setdefault('attachment_list', [])
    record.setdefault('star_state', 0)
    body = record.get('content_list') or record.get('content')
    if not body or not record.get('title'):
        template = templates.get(record.get('mail_template_id'), {})
        if not body:
            text = template.get('desc')
            if isinstance(text, str) and text.strip() and not re.search(r'%|\{[^}]*\}', text):
                body = text
        if not record.get('title'):
            title = template.get('title')
            if isinstance(title, str) and title.strip() and not re.search(r'%|\{[^}]*\}', title):
                record['title'] = title
    if isinstance(body, str) and body.strip():
        record['content_list'] = [dict(text=body, content_type=2)]
    elif isinstance(body, list) and body and all(
            isinstance(item, dict) and isinstance(item.get('text'), str) and item['text'].strip()
            and item.get('content_type') in (1, 2) for item in body):
        record['content_list'] = body
    else:
        record['content_list'] = []
    return record


def _normalize_mail_records(snapshot: CaptureSnapshot, list_command: int, list_field: str,
                            detail_command: int, issues: list[str]) -> list[dict]:
    """Join mailbox summaries with details from the same validated session."""
    records = {}
    for frame in snapshot.supplement_frames:
        if frame.cmd != list_command:
            continue
        for message in frame.decoded.get(list_field, []):
            record = _mail_record(message, snapshot._mail_templates)
            mail_id = int(record.get('id', 0))
            prior = records.get(mail_id)
            if prior is not None and _canonical(prior) != _canonical(record):
                issues.append(f'{list_command} 邮件 ID {mail_id} 的重复记录内容冲突')
            else:
                records[mail_id] = record
    details = {}
    for frame in snapshot.supplement_frames:
        if frame.cmd != detail_command:
            continue
        detail = frame.decoded.get('detail_info') or {}
        mail_id = int(detail.get('id', 0))
        record = records.get(mail_id)
        if frame.decoded.get('result', 0) != 0 or record is None:
            issues.append(f'{detail_command} 邮件 {mail_id} 缺少成功且可绑定的详情')
            continue
        if mail_id in details and _canonical(details[mail_id]) != _canonical(detail):
            issues.append(f'{detail_command} 邮件 {mail_id} 的重复详情内容冲突')
            continue
        details[mail_id] = detail
        if 'sender' in detail:
            record['sender'] = detail['sender']
        if 'attachment_list' in detail:
            if list_command == 30003 and _canonical(record['attachment_list']) != _canonical(detail['attachment_list']):
                issues.append(f'{detail_command} 邮件 {mail_id} 的附件与摘要冲突')
            else:
                record['attachment_list'] = deepcopy(detail['attachment_list'])
        if detail.get('content_list'):
            record['content_list'] = _mail_record(detail, snapshot._mail_templates)['content_list']
    for mail_id, supplement in snapshot._mail_detail_supplements.items():
        if supplement['list_command'] != list_command:
            continue
        record = records.get(mail_id)
        if record is None or any(_canonical(record.get(key)) != _canonical(value)
                                 for key, value in supplement['identity'].items()):
            issues.append(f'邮件补充来源与当前摘要不符：{mail_id}')
            continue
        if record['content_list'] and _wire_state(record['content_list']) != _wire_state(supplement['content_list']):
            issues.append(f'邮件正文在两个来源中冲突：{mail_id}')
            continue
        if record.get('sender') and supplement['sender'] and record['sender'] != supplement['sender']:
            issues.append(f'邮件发件人在两个来源中冲突：{mail_id}')
            continue
        record['content_list'] = deepcopy(supplement['content_list'])
        if supplement['sender']:
            record['sender'] = supplement['sender']
    return list(records.values())


def supplement_mail_details(snapshot: CaptureSnapshot, source: CaptureSnapshot) -> None:
    """Reuse matching mail text without copying another session's account state."""
    if source._mail_detail_supplements:
        raise ValueError('邮件详情来源必须是原始重建快照；请分别提供各原始来源')
    if (snapshot.source_uid, snapshot.client_build, snapshot.resource_version) != (
            source.source_uid, source.client_build, source.resource_version):
        raise ValueError('邮件补充来源的账号或版本不一致')
    for current in (snapshot, source):
        missing, issues = _assess(current, scope='available')
        if missing or issues:
            raise ValueError('邮件补充来源未通过快照核验：' + str(missing + issues))
    supplements = deepcopy(snapshot._mail_detail_supplements)
    for list_command, current_rows, source_rows, fields in (
            (30003, snapshot._mail_records, source._mail_records,
             ('title', 'date', 'timeout_timestamp', 'mail_template_id', 'attachment_list')),
            (30021, snapshot._collected_mail_records, source._collected_mail_records,
             ('title', 'mail_timestamp', 'collect_date', 'mail_template_id'))):
        sources = {row['id']: row for row in source_rows}
        for row in current_rows:
            prior = sources.get(row['id'])
            if prior is None or not prior['content_list']:
                continue
            if any(_canonical(row.get(key)) != _canonical(prior.get(key)) for key in fields):
                raise ValueError(f'邮件补充来源与当前摘要不符：{row["id"]}')
            if row.get('sender') and prior.get('sender') and row['sender'] != prior['sender']:
                raise ValueError(f'邮件发件人在两个来源中冲突：{row["id"]}')
            if row['content_list']:
                if _wire_state(row['content_list']) != _wire_state(prior['content_list']):
                    raise ValueError(f'邮件正文在两个来源中冲突：{row["id"]}')
                continue
            supplements[row['id']] = dict(
                mail_id=row['id'], list_command=list_command,
                identity={key: deepcopy(row.get(key)) for key in fields},
                content_list=deepcopy(prior['content_list']), sender=prior.get('sender', ''),
                source_uid=source.source_uid, session_id=source.session_id,
                source_sha256=dict(source.source_sha256))
    snapshot._mail_detail_supplements = supplements


def _assess(snapshot, *, scope='full'):
    if scope not in ('full', 'heroes', 'available'):
        raise ValueError('导入范围无效')
    missing = []
    reasons = [] if scope == 'heroes' else list(snapshot.issues)
    required = (*HERO_COMMANDS, 23009) if scope == 'heroes' else REQUIRED_COMMANDS
    for cmd in required:
        if not snapshot.protocol_data.get(cmd):
            missing.append(dict(data=f"协议 {cmd}", method=f"同一 8105 登录流捕获 sc_{cmd}"))
        elif cmd != 60201 and len(snapshot.protocol_data[cmd]) != 1:
            reasons.append(f'协议 {cmd} 不是唯一全量快照')
    versions = {('307', '321'), ('308', '332')} if scope != 'full' else {('307', '321')}
    if (snapshot.client_build, snapshot.resource_version) not in versions:
        missing.append(dict(data='该客户端版本的已审核目录', method='提供与客户端构建和资源版本一致的配置审计'))
    for cmd, field, key in ((13009, 'equip_list', 'equip_id'), (15009, 'currency_list', 'id'),
                            (17009, 'material_list', 'id'), (46011, 'servant_list', 'uid'),
                            (28001, 'assignment_list', 'id'), (28019, 'pt_list', 'activity_pt_id')):
        if cmd not in required:
            continue
        seen = set()
        for packet in snapshot.protocol_data.get(cmd, []):
            for item in packet.get(field, []):
                item_id = item.get(key)
                if type(item_id) is not int or item_id <= 0 or item_id in seen:
                    reasons.append(f'协议 {cmd} 的 {field}.{key} 无效或重复')
                seen.add(item_id)
    unsupported = sorted({frame.cmd for frame in snapshot.login_frames} - MAPPED_COMMANDS)
    if unsupported and scope == 'full':
        missing.append(dict(data="未审核登录协议",
                            protocol_commands=unsupported,
                            method="审核协议归属；账号帧补齐目标状态映射，静态帧提供账号无关证据"))
    heroes = (snapshot.protocol_data.get(14009) or [{}])[0].get("hero_info_list", [])
    if heroes and not any(isinstance(hero, dict) and "equip" in hero for hero in heroes):
        missing.append(dict(data="角色携带刻印槽", method="从同一登录段的 sc_14009 取得 hero_net_rec.equip"))
    if not snapshot.protocol_data.get(13009):
        missing.append(dict(data="刻印库存", method="补抓 sc_13009；不得用角色装备槽代替库存"))
    if scope == 'heroes':
        return missing, reasons
    messages = _normalize_mail_records(snapshot, 30003, 'mail_list', 30009, reasons)
    snapshot._mail_records = messages
    collected = _normalize_mail_records(snapshot, 30021, 'collect_mail_list', 30023, reasons)
    snapshot._collected_mail_records = collected
    collection_frames = [frame for frame in snapshot.supplement_frames if frame.cmd == 30021]
    if collection_frames:
        total = collection_frames[0].decoded.get('collect_total_num', 0)
        if total != len(collected) or any(int(mail.get('id', 0)) <= 0 for mail in collected):
            reasons.append('30021 收藏邮件数量或 ID 无效')
        if {mail['id'] for mail in messages} & {mail['id'] for mail in collected}:
            reasons.append('普通邮箱与收藏邮箱存在重复邮件 ID，不能确定所属邮箱')
        if any(not mail.get('title') or not mail.get('collect_date') or not mail.get('mail_timestamp') for mail in collected):
            missing.append(dict(data='收藏邮件摘要', method='补抓同一会话的完整 sc_30021'))
        if scope == 'full' and any(not mail['content_list'] for mail in collected):
            missing.append(dict(data='收藏邮件正文', method='打开收藏邮件，补抓同一会话的 cs_30022/sc_30023'))
    summaries = snapshot.protocol_data.get(30001, [])
    summary = summaries[0] if len(summaries) == 1 else None
    if summary is None:
        missing.append(dict(data="普通邮箱摘要 30001", method="从同一次登录取得 sc_30001"))
    else:
        total = int(summary.get("total_number", -1))
        unread = int(summary.get("unread_number", -1))
        if total < 0 or unread < 0 or unread > total:
            reasons.append("30001 邮箱数量无效")
        elif total or messages:
            details = [frame for frame in snapshot.supplement_frames if frame.cmd == 30003]
            if not details:
                missing.append(dict(data=f"普通邮箱明细 {total} 封", method=
                    "登录后、读信或领取前，在同一连接发送 cs_30002 并保存完整 sc_30003"))
            else:
                if any(int(message.get('id', 0)) <= 0 for message in messages):
                    reasons.append('30003 邮件 ID 无效')
                if len(messages) != total:
                    reasons.append("30003 邮件唯一 ID 数量与 30001 摘要不一致")
                unread_actual = sum(1 for message in messages
                                    if int(message.get("read_flag", 0)) == 1)
                if unread_actual != unread:
                    reasons.append("30003 未读状态数量与 30001 摘要不一致")
                if any(int(message.get("read_flag", 0)) not in (1, 2) for message in messages):
                    reasons.append("30003 存在未知邮件已读状态")
                if any(not message.get("title") for message in messages):
                    missing.append(dict(data="普通邮件标题", method="补抓同一会话的完整 30003 邮件记录"))
                if any(not isinstance(message.get("attachment_list"), list) or
                       int(message.get("attach_flag", -1)) not in (1, 2)
                       for message in messages):
                    missing.append(dict(data="普通邮件附件及领取状态", method="补抓完整 30003 邮件列表"))
                if any(any(not isinstance(item, dict) or int(item.get("id", 0)) <= 0 or
                           int(item.get("number", 0)) <= 0
                           for item in message.get("attachment_list", [])) for message in messages):
                    reasons.append("30003 附件 ID 或数量无效")
                if any(not message['content_list'] for message in messages):
                    missing.append(dict(data="模板正文解析", method=
                        "提供对应版本邮件模板正文的审计来源；不能用标题替代正文"))
    if scope == 'available':
        missing = [item for item in missing if item['data'] != '模板正文解析']
    return missing, reasons


def read_snapshot(capture_dir) -> CaptureSnapshot:
    """Read one 8105 login flow and its permitted mailbox query supplement."""
    root = Path(capture_dir).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("抓包路径必须是目录")
    connection_map, summary_hash = _summary_connections(root)
    files = sorted(root.glob("tcp_*_*_8105.jsonl"))
    if {path.name for path in files} != set(connection_map):
        raise ValueError('8105 流文件与 summary.md 声明不一致，不能唯一绑定完整连接')
    if not files:
        raise ValueError("目录中没有 8105 TCP 重建流")
    loaded = {}
    hashes = {'summary.md': summary_hash}
    for path in files:
        expected_dir, local_port, remote_host, local_host, frames, source_hash = _load_stream(path, connection_map)
        loaded[path.name] = (expected_dir, local_port, remote_host, local_host, frames)
        hashes[path.name] = source_hash
    up = [(name, port, remote, local, frames) for name, (direction, port, remote, local, frames) in loaded.items() if direction == "up"]
    down = [(name, port, remote, local, frames) for name, (direction, port, remote, local, frames) in loaded.items() if direction == "down"]
    paired = [(u, d) for u in up for d in down if u[1:4] == d[1:4]]
    if len(up) != 1 or len(down) != 1 or len(paired) != 1:
        raise ValueError("8105 上下行不能唯一绑定到同一 TCP 连接")
    (up_name, local_port, _, _, up_frames), (down_name, _, _, _, down_frames) = paired[0]
    login_requests = [frame for frame in up_frames if frame.cmd == 10042]
    login_starts = [frame for frame in up_frames if frame.cmd == 10200]
    markers = [i for i, frame in enumerate(down_frames) if frame.cmd == 10201]
    if len(login_requests) != 1 or len(login_starts) != 1 or len(markers) != 1:
        raise ValueError("必须有且仅有一个 10042、10200 与 10201 登录段")
    login_req = login_requests[0]
    if up_frames.index(login_req) > up_frames.index(login_starts[0]):
        raise ValueError("10042 必须先于 10200")
    login_info = login_req.decoded
    if not login_info.get("user_id") or not login_info.get("client_vs") or not login_info.get("resource_vs"):
        raise ValueError("10042 缺少来源 UID、客户端版本或资源版本")
    marker = markers[0]
    login_frames = down_frames[:marker]
    end_frame = down_frames[marker]
    if (login_req.timestamp > login_starts[0].timestamp or login_starts[0].timestamp > end_frame.timestamp
            or any(frame.timestamp < login_starts[0].timestamp
                   for frame in login_frames if frame.cmd != 10043)):
        raise ValueError('登录账号帧不属于 10042/10200/10201 的时间区间')
    confirmations = [frame for frame in down_frames if frame.cmd == 10043]
    if (len(confirmations) != 1 or confirmations[0] not in login_frames
            or confirmations[0].decoded.get('result') != 0):
        raise ValueError('10201 前必须有且仅有一个成功的 10043 登录确认帧')
    if not login_req.timestamp <= confirmations[0].timestamp <= login_starts[0].timestamp:
        raise ValueError('10042、10043、10200、10201 登录顺序无效')
    post_frames = down_frames[marker + 1:]
    if end_frame.timestamp is None:
        raise ValueError("10201 缺少可核验时间戳，不能绑定结束后的邮箱补抓")
    up_post = [frame for frame in up_frames
               if frame.timestamp is not None and frame.timestamp > end_frame.timestamp]
    issues = []
    mailbox_responses = []
    mail_details = []
    for query_command, response_command, detail_query, detail_response, id_field in (
            (30002, 30003, 30008, 30009, 'id'),
            (30020, 30021, 30022, 30023, 'mail_id')):
        mail_queries = [frame for frame in up_post if frame.cmd == query_command]
        mail_responses = [frame for frame in post_frames if frame.cmd == response_command]
        if len(mail_queries) > 1 or bool(mail_queries) != bool(mail_responses):
            issues.append(f'结束帧后的 {query_command}/{response_command} 查询与应答不能唯一配对')
        if mail_responses and any(_canonical(frame.decoded) != _canonical(mail_responses[0].decoded)
                                  for frame in mail_responses[1:]):
            issues.append(f'同一邮箱查询的重复 {response_command} 应答内容冲突')
        if mail_queries:
            query = mail_queries[0]
            response = mail_responses[-1] if mail_responses else None
            if (query.timestamp is None or response is None or response.timestamp is None
                    or any(frame.timestamp is None or frame.timestamp <= query.timestamp for frame in mail_responses)):
                issues.append(f'{query_command} 查询与 {response_command} 应答缺少可核验的先后时间')
            if response is not None and response.timestamp is not None:
                mutations = MAIL_MUTATION_COMMANDS if query_command == 30002 else {30014, 30018}
                response_mutations = MAIL_RESPONSE_MUTATIONS | {30001} if query_command == 30002 else {30015, 30019}
                if any(frame.cmd in mutations and frame.timestamp <= response.timestamp for frame in up_post):
                    issues.append('邮箱补抓完成前已发生读信、领取、删除或收藏动作')
                if any(frame.cmd in response_mutations and frame.timestamp <= response.timestamp for frame in post_frames):
                    issues.append('邮箱补抓完成前收到邮件状态变更')
        mailbox_responses.extend(mail_responses)
        for frame in post_frames:
            if frame.cmd != detail_response:
                continue
            mail_id = (frame.decoded.get('detail_info') or {}).get('id')
            queries = [query for query in up_post if query.cmd == detail_query and query.decoded.get(id_field) == mail_id
                       and mail_responses and mail_responses[-1].timestamp is not None
                       and frame.timestamp is not None and mail_responses[-1].timestamp < query.timestamp < frame.timestamp]
            if len(queries) != 1:
                issues.append(f'{detail_response} 正文与邮箱列表之后的 {detail_query} 查询不能唯一配对')
            else:
                mail_details.append(frame)
    protocol_data = {}
    for frame in login_frames:
        if frame.cmd == 10043:
            continue
        protocol_data.setdefault(frame.cmd, []).append(frame.decoded)
    for frame in mailbox_responses:
        protocol_data.setdefault(frame.cmd, []).append(frame.decoded)
    chapter_frames = [frame for frame in login_frames if frame.cmd == 24009]
    if chapter_frames:
        protocol_data[24009] = [dict(user_chapter_list=_merge_chapters(chapter_frames, issues))]
    if protocol_data.get(30001):
        protocol_data[30001] = protocol_data[30001][-1:]
    snapshot = CaptureSnapshot(
        source_uid=int(login_info["user_id"]),
        client_build=str(login_info["client_vs"]),
        resource_version=str(login_info["resource_vs"]),
        session_id=hashlib.sha256(f"{local_port}:{up_name}:{down_name}".encode()).hexdigest()[:16],
        login_frames=login_frames,
        supplement_frames=sorted(mailbox_responses + mail_details, key=lambda frame: frame.source_line),
        source_sha256=hashes,
        protocol_data=protocol_data,
        end_frame=end_frame,
        issues=issues)
    snapshot.unsupported_login_commands = sorted(
        {frame.cmd for frame in login_frames} - MAPPED_COMMANDS)
    snapshot.missing_data, snapshot.issues = _assess(snapshot)
    return snapshot


def _report(snapshot, target_uid=None, *, scope='full'):
    missing, issues = _assess(snapshot, scope=scope)
    return ImportReport(target_uid=target_uid, missing_data=missing,
                        source_sha256=dict(snapshot.source_sha256), issues=issues,
                        snapshot=snapshot,
                        validation=dict(import_scope=scope,
                                        unrestored_commands=sorted({frame.cmd for frame in snapshot.login_frames}
                                            - set(HERO_COMMANDS) - {10043, 23009}) if scope == 'heroes' else [],
                                        session_id=snapshot.session_id,
                                        source_uid_present=bool(snapshot.source_uid),
                                        client_build=snapshot.client_build,
                                        resource_version=snapshot.resource_version,
                                        login_frames=len(snapshot.login_frames),
                                        supplement_frames=len(snapshot.supplement_frames),
                                        unrestored_mail_ids=[mail['id'] for mail in snapshot._mail_records if not mail['content_list']],
                                        unrestored_collect_mail_ids=[mail['id'] for mail in snapshot._collected_mail_records if not mail['content_list']],
                                        mail_detail_sources=[{key: value for key, value in row.items() if key != 'content_list'}
                                            for row in snapshot._mail_detail_supplements.values()],
                                        mail_summary_frames=[dict(source_file=frame.source_file,
                                            source_line=frame.source_line, summary=frame.decoded)
                                            for frame in snapshot.login_frames if frame.cmd == 30001]))


def _one(snapshot, cmd):
    rows = snapshot.protocol_data.get(cmd, [])
    if len(rows) != 1:
        raise ValueError(f"协议 {cmd} 必须恰有一份全量快照")
    return rows[0]


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _build_hero_rows(db, snapshot, uid, timestamp):
    """Restore the shared hero, equipment, servant, skin and archive projection."""
    hero_packet = _one(snapshot, 14009)
    hero_rows = hero_packet["hero_info_list"]
    blueprint_ids = {int(row[0]) for row in db._conn().execute("SELECT hero_id FROM hero_cfg")}
    favorites = {int(hero_id) for hero_id in hero_packet.get("favorites", [])}
    skin_map = __import__("hero_codec")._get_skin_hero_map()
    for hero in hero_rows:
        net = hero
        if not isinstance(net, dict) or not isinstance(net.get("hero_base_info"), dict):
            raise ValueError("14009 英雄缺少 hero_base_info")
        base = net["hero_base_info"]
        required = ("id", "level", "star", "exp")
        if any(key not in base for key in required):
            raise ValueError("14009 英雄核心字段不完整")
        hid = int(base["id"])
        if hid not in blueprint_ids:
            raise ValueError(f"14009 英雄 {hid} 不在已审核 hero_blueprint.json 中")
        skills = base.get("skill", [])
        equipment = net.get("equip", [])
        equip_slot = {str(int(item["pos"])): int(item["equip_id"])
                      for item in equipment if "pos" in item and "equip_id" in item}
        weapon = base.get("weapon") or {}
        trust = net.get("trust") or {}
        relation = trust.get("relation") or {}
        exclusive = base.get("exclusive_skill_list", [])
        hero_db_row = dict(id=hid, level=int(base["level"]), star=int(base["star"]),
            exp=int(base["exp"]), skill_list=_json([[int(skill["skill_id"]), int(skill["skill_level"])]
                for skill in skills]), weapon_exp=int(base.get("weapon", {}).get("exp", 0)),
            weapon_break=int(weapon.get("breakthrough", 0)),
            weapon_servant_uid=int(weapon.get("servant_uid", 0)),
            servant=_json(base.get("servant", {})), using_astrolabe=_json(base.get("using_astrolabe", [])),
            unlock_astrolabe=_json(base.get("unlock_astrolabe", [])),
            using_skin=int(base.get("using_skin", hid)), break_level=int(base.get("break_level", 0)),
            exclusive_skill_list=_json({str(int(record["slot_id"])): dict(skill_list=[
                dict(skill_id=int(item["skill_id"]), skill_level=int(item["skill_level"]))
                for item in record.get("skill_list", [])],
                talent_points=int(record.get("talent_points", 0)))
                for record in exclusive}),
            weapon_module_level=int(base.get("weapon_module_level", 0)),
            skill_intensify=_json(base.get("skill_intensify_attribute_list", [])),
            battle_using_skin=int(base.get("battle_using_skin", hid)),
            clear_times=int(net.get("clear_times", 0)), unlock=int(net.get("unlock", 0)),
            equip_slot=_json(equip_slot), module_level=int(base.get("weapon_module_level", 0)),
            module_assignment=int(net.get("weapon_module_assignment", 0)), update_ts=timestamp,
            trust_level=int(trust.get("level", 0)), trust_exp=int(trust.get("exp", 0)),
            trust_mood=int(trust.get("mood", 1)), relation_net=_json(relation.get('tier_list', [])),
            clear_mission_list=_json(net.get("clear_mission_list", [])),
            is_favorite=1 if hid in favorites else 0)
        db.upsert("hero", uid, hero_db_row, keys=("uid", "id"))
        for skin in net.get("unlocked_skin", []):
            skin_id = int(skin["skin_id"])
            if skin_id not in skin_map or int(skin.get("time", 0)) != 0:
                raise ValueError("14009 皮肤缺英雄映射或含无法持久化的限时状态")
            db.upsert("player_skin_unlocked", uid, dict(skin_id=skin_id,
                unlock_ts=0, update_ts=timestamp), keys=("uid", "skin_id"))
    for archive in hero_packet.get("archives", []):
        if "archive_id" not in archive:
            raise ValueError("14009 档案缺少 archive_id")
        db.upsert("hero_archive", uid, dict(archive_id=int(archive["archive_id"]),
            exp=int(archive.get("exp", 0)), text_list=_json(archive.get("text_list", [])),
            video_list=_json(archive.get("video_list", [])), gift_list=_json(archive.get("gift_list", [])),
            selected_picture=_json(archive.get("selected_picture", {})),
            super_heart_link_list=_json(archive.get('super_heart_link_list', [])),
            hero_story_list=_json(archive.get("hero_story_list", []))),
            keys=("uid", "archive_id"))
    for piece in hero_packet.get("piece_list", []):
        if "id" not in piece or "num" not in piece:
            raise ValueError("14009 碎片缺少 id/num")
        db.upsert("hero_piece", uid, dict(hero_id=int(piece["id"]), num=int(piece["num"])),
                  keys=("uid", "hero_id"))
    for row in _one(snapshot, 13009).get("equip_list", []):
        if not all(key in row for key in ("equip_id", "prefab_id")):
            raise ValueError("13009 装备缺少实例或配置 ID")
        slots = row.get("enchant_slot_list")
        db.upsert("equip", uid, dict(id=int(row["equip_id"]), prefab_id=int(row["prefab_id"]),
            exp=int(row.get("exp", 0)), hero_id=int(row.get("hero_id", 0)),
            is_lock=int(row.get("is_lock", 0)), now_break_level=int(row.get("now_break_level", 0)),
            enchant_slots=_json(slots if slots is not None else []), race=int(row.get("race", 0)),
            race_preview=int(row.get("race_preview", 0)), update_ts=timestamp), keys=("uid", "id"))

    for row in _one(snapshot, 46011).get('servant_list', []):
        db.upsert('servant', uid, dict(id=int(row['uid']), prefab_id=int(row['id']),
            stage=int(row['stage']), is_locked=int(row['is_locked']), owned=1), keys=('uid', 'id'))


def _build_rows(db, snapshot, uid, *, scope='full'):
    """Apply the reviewed login snapshot fields to account-owned tables."""
    source = _one(snapshot, 23009)
    level = int(_one(snapshot, 12009).get("user_level", 0))
    if level < 1:
        raise ValueError("12009 缺少有效等级")
    nick = source.get("nick")
    if not isinstance(nick, str) or not nick:
        raise ValueError("23009 缺少昵称")
    hero_packet = _one(snapshot, 14009)
    hero_rows = hero_packet.get("hero_info_list")
    if not isinstance(hero_rows, list):
        raise ValueError("14009 缺少 hero_info_list")
    if int(source.get("hero_num", -1)) != len(hero_rows):
        raise ValueError("14009 英雄条数与 23009.hero_num 不一致")
    currency_packet = _one(snapshot, 15009)
    material_packet = _one(snapshot, 17009)
    shop_packet = _one(snapshot, 20009)
    task_packet = _one(snapshot, 28001)
    chapter_packet = _one(snapshot, 24009)
    tower_packet = _one(snapshot, 41001)
    timestamp = int(time.time())
    snapshot_time = int(snapshot.end_frame.timestamp) if snapshot.end_frame else 0
    if snapshot_time <= 0:
        raise ValueError('缺少有效的捕获结束时间')
    from lazy_timer import (get_daily_5am_ts, get_weekly_mon_5am_ts,
                            get_weekly_thu_5am_ts, get_monthly_5am_ts)
    db.update_timer_watermark(uid, last_pulse_ts=snapshot_time,
        last_daily_5am_ts=get_daily_5am_ts(snapshot_time),
        last_weekly_mon_ts=get_weekly_mon_5am_ts(snapshot_time),
        last_weekly_thu_ts=get_weekly_thu_5am_ts(snapshot_time),
        last_monthly_ts=get_monthly_5am_ts(snapshot_time))

    # Do not import an account name, login token, API profile, or default gift.
    db.upsert("users", uid, dict(account=f"capture_{uid}", server_id=1, nick=nick,
        level=level, exp=int(source.get("total_exp", 0)), extra="{}",
        hero_num=len(hero_rows), plot_progress=int(source.get("plot_progress", 0)),
        is_changed_nick=int(source.get("is_changed_nick", 0)),
        change_nick_times=int(source.get("system_change_nick_times", 0)),
        sign="", portrait=0, icon_frame=0, likes=0, ip_location="", register_ts=timestamp))
    db.set_system_config("save.owner_uid", str(uid))
    db.set_system_config("save.profile", "capture_import_v1")
    db.set_system_config("save.initialized_at", str(timestamp))
    db.set_system_config("save.import_source_sha256", _json(snapshot.source_sha256))
    db.set_system_config("ai.api_profiles.v1", _json(
        dict(version=1, active_id="", profiles={}, routes={})))

    for row in currency_packet.get("currency_list", []):
        if "id" not in row or "num" not in row:
            raise ValueError("15009 货币条目缺少 id/num")
        db.upsert("currency", uid, dict(id=int(row["id"]), num=int(row["num"]),
            last_fatigue_recover_time=int(currency_packet.get("last_fatigue_recover_time", 0))),
            keys=("uid", "id"))
    for row in material_packet.get("material_list", []):
        if "id" not in row or "num" not in row:
            raise ValueError("17009 材料条目缺少 id/num")
        db.upsert("material", uid, dict(id=int(row["id"]), num=int(row["num"])),
                  keys=("uid", "id"))

    _build_hero_rows(db, snapshot, uid, timestamp)
    for row in _one(snapshot, 28019).get('pt_list', []):
        db.upsert('activity_pt', uid, dict(activity_pt_id=int(row['activity_pt_id']),
            active_point=int(row['active_point']), get_id_list=_json(row.get('get_id_list', []))),
            keys=('uid', 'activity_pt_id'))

    for row in shop_packet.get("shop_item_list", []):
        shop_id = int(row["shop_id"])
        if shop_id == 2:
            last_refresh = max((frame.timestamp or 0 for frame in snapshot.login_frames), default=0)
            daily_goods = [{"goods_id": int(goods["goods_id"]),
                            "buy_times": int(goods.get("buy_times", 0)),
                            "next_refresh_timestamp": int(goods.get("next_refresh_timestamp", 0))}
                           for goods in row.get("goods_list", [])]
            db.upsert("user_daily_shop", uid, dict(refresh_times=int(row.get("refresh_times", 0)),
                goods_list_json=_json(daily_goods), last_refresh_ts=int(last_refresh),
                update_ts=timestamp))
        for goods in row.get("goods_list", []):
            if "goods_id" not in goods:
                raise ValueError("20009 商品条目缺少 goods_id")
            db.upsert("store_purchase", uid, dict(shop_id=shop_id,
                goods_id=int(goods["goods_id"]), buy_times=int(goods.get("buy_times", 0)),
                next_refresh_timestamp=int(goods.get("next_refresh_timestamp", 0)), update_ts=timestamp),
                keys=("uid", "shop_id", "goods_id"))
    for row in task_packet.get("assignment_list", []):
        if "id" not in row:
            raise ValueError("28001 任务条目缺少 id")
        task_id = int(row['id'])
        configs = db.query('SELECT task_type FROM task_cfg WHERE task_id=?', (task_id,))
        flag = int(row.get('complete_flag', 0))
        if flag not in (0, 1):
            raise ValueError(f'28001 任务 {task_id} 的领取标记无效')
        db.upsert("task", uid, dict(task_id=task_id,
            task_type=int(configs[0]['task_type'] or 0) if configs else 0,
            progress=int(row.get("progress", 0)),
            complete_flag=flag, expired_ts=int(row.get("expired_timestamp", 0))),
            keys=("uid", "task_id"))
        if flag:
            if configs:
                db.claim_task(uid, task_id, now_ts=snapshot_time)
            else:
                db.execute('UPDATE task SET claimed_ts=? WHERE uid=? AND task_id=?', (snapshot_time, uid, task_id))
    for row in chapter_packet.get("user_chapter_list", []):
        db.upsert("chapter", uid, dict(id=int(row["id"]),
            star_list=_json(row.get("star_list", [])), clear_times=int(row.get("clear_times", 0))),
            keys=("uid", "id"))
    for row in tower_packet.get("info_list", []):
        if "area" not in row or "stage" not in row:
            raise ValueError("41001 塔层记录缺少 area/stage")
        db.upsert("tower", uid, dict(area=int(row["area"]), stage=int(row["stage"])),
                  keys=("uid", "area"))

    for row in _one(snapshot, 24017).get("gain_list", []):
        for reward in row.get("reward_list", []):
            if int(reward.get("is_received", 0)):
                db.upsert("chapter_star_reward", uid, dict(chapter_id=int(row["id"]),
                    reward_order=int(reward["reward_order"])),
                    keys=("uid", "chapter_id", "reward_order"))
    for activity in snapshot.protocol_data.get(60201, []):
        activity_id = int(activity["activity_id"])
        db.upsert("activity_point", uid, dict(activity_id=activity_id,
            point=int(activity.get("point", 0)), update_ts=timestamp),
            keys=("uid", "activity_id"))
        for reward_id in activity.get("reward_list", []):
            db.upsert("activity_point_reward", uid, dict(activity_id=activity_id,
                reward_id=int(reward_id), update_ts=timestamp),
                keys=("uid", "activity_id", "reward_id"))

    for mail_type, messages in ((1, snapshot._mail_records), (2, snapshot._collected_mail_records)):
        for mail in messages:
            db.upsert("mail", uid, dict(mail_id=int(mail["id"]), mail_type=mail_type,
                template_id=0, title=str(mail.get("title", "")), sender=str(mail.get('sender', '')),
                content_json=_json(mail['content_list']),
                send_time=int(mail.get('date', mail.get('mail_timestamp', 0))),
                expire_time=int(mail.get("timeout_timestamp", 0)),
                read_flag=int(mail.get('read_flag', 2)), attach_flag=int(mail.get('attach_flag', 2)),
                star_state=1 if mail_type == 2 else int(mail.get("star_state", 0)),
                attachment_json=_json(mail['attachment_list']),
                collect_time=int(mail.get('collect_date', 0)), update_ts=timestamp),
                keys=("uid", "mail_id"))
    for mail_id, supplement in snapshot._mail_detail_supplements.items():
        db.upsert('ops_common', uid, dict(kind='capture_mail_details', item_id=str(mail_id),
            value_json=_json(supplement)), keys=('uid', 'kind', 'item_id'))
    # Dynamic rows are generated from this target account at login. Captured
    # payload bytes are never copied into the target account.
    sequence = []
    if scope == 'available':
        from capture_account_state import ACCOUNT_COMMANDS, LOCAL_COMMANDS, verified_commands
        allowed_commands = MAPPED_COMMANDS | ACCOUNT_COMMANDS | LOCAL_COMMANDS.keys()
        verified = set(verified_commands(snapshot))
        allowed_commands -= {12099, 17021, 24019, 42001, 43001, 75009, 75017, 80115, 88023, 89207} - verified
    for frame in snapshot.login_frames:
        cmd = frame.cmd
        if scope == 'available' and cmd not in allowed_commands:
            continue
        if cmd == 30001 and any(prior.cmd == 30001 for prior, _, _ in sequence):
            continue
        if cmd == 60201:
            activity_id = int(frame.decoded["activity_id"])
            sequence.append((frame, 1, _json(dict(activity_id=activity_id))))
            continue
        if scope == 'available' and (cmd in LOCAL_COMMANDS or cmd in (10503, 11071, 12019, 12099, 12123, 15007, 17021, 23015, 24019,
                                             24045, 34021, 35011, 42001, 43001, 44007, 44009, 44019, 44021, 44023, 55001,
                                             59001, 60105, 60107, 80115, 81001, 83020, 85035,
                                             51001, 68151, 68155, 68161, 75009, 75017, 83401, 85105, 88023, 88305,
                                             89207, 89421, 89801)):
            sequence.append((frame, 1, None))
            continue
        # Keep the reviewed source object as the fallback for account protocols
        # that do not have a generator. Dynamic generators still take priority.
        sequence.append((frame, 1, _json(frame.decoded)))
    if sum(frame.cmd == 10201 for frame, _, _ in sequence) != 0:
        raise ValueError("10201 不得在登录快照帧中重复")
    if snapshot.end_frame is None or snapshot.end_frame.cmd != 10201:
        raise ValueError('缺少原始 10201 结束帧')
    sequence.append((snapshot.end_frame, 1, None))
    for seq, (frame, dynamic, payload_json) in enumerate(sequence, 1):
        cmd = frame.cmd
        high_flag = 1 if cmd > 65535 or frame.frame_flag == 1 else 0
        header = (struct.pack(">H", 9) + bytes((1 if frame.compressed else 0, 0, high_flag))
                  + struct.pack(">HHH", cmd & 0xFFFF, frame.frame_index & 0xFFFF,
                                frame.server_idx & 0xFFFF))
        db.execute("INSERT INTO login_push(seq,cmd,header,payload,dynamic,payload_json) VALUES(?,?,?,?,?,?)",
                   (seq, cmd, header, b"", dynamic, payload_json))

    row = db._conn().execute("SELECT COUNT(*) n,MIN(uid) lo,MAX(uid) hi FROM users").fetchone()
    if row["n"] != 1 or int(row["lo"]) != uid or int(row["hi"]) != uid:
        raise ValueError("目标库必须只包含唯一目标主人")
    api = db.get_system_config("ai.api_profiles.v1")
    if json.loads(api) != dict(version=1, active_id="", profiles={}, routes={}):
        raise ValueError("目标库 API 配置必须为空")
    return dict(rows={table: int(db._conn().execute(
        f'SELECT COUNT(*) FROM "{table}" WHERE uid=?', (uid,)).fetchone()[0])
        for table in ("users", "currency", "material", "hero", "equip", "store_purchase",
                      "task", "chapter", "tower", "mail", "activity_point",
                      "activity_point_reward", "hero_archive", "hero_piece", "user_daily_shop",
                      "player_skin_unlocked", "servant", "activity_pt")})


def _wire_state(value):
    """Ignore record order while preserving ordered scalar lists and every field."""
    if isinstance(value, dict):
        return {key: _wire_state(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        rows = [_wire_state(item) for item in value]
        return sorted(rows, key=_canonical) if rows and all(isinstance(row, dict) for row in rows) else rows
    return value


def _protocol_state(command, packets, *, scope='full'):
    from capture_account_state import ACCOUNT_COMMANDS, account_protocol_state
    if scope == 'available':
        return account_protocol_state(command, packets)
    if command == 13009:
        from enchant_slots_util import normalize_enchant_slots
        packets = [dict(packet, equip_list=[dict(row,
            enchant_slot_list=normalize_enchant_slots(row.get('enchant_slot_list')))
            for row in packet.get('equip_list', [])]) for packet in packets]
    if command == 20009:
        shops = [shop for packet in packets for shop in packet.get('shop_item_list', [])]
        return _wire_state(dict(
            purchases=[dict(shop_id=shop['shop_id'], **goods) for shop in shops
                       for goods in shop.get('goods_list', []) if int(goods.get('buy_times', 0)) > 0],
            daily=[shop for shop in shops if shop['shop_id'] == 2]))
    return _wire_state(packets)


def _verify_isolated_login(db, report):
    """Mount a disposable copy and compare actual wire values with captured state."""
    from contextlib import closing

    snapshot = report.snapshot
    if snapshot is None:
        return dict(passed=False, reason='缺少已冻结快照，不能重新验证')
    server = Path(__file__).resolve().parent
    original = list(db._conn().iterdump())
    scope = report.validation.get('import_scope', 'full')
    required_commands = HERO_COMMANDS if scope == 'heroes' else REQUIRED_COMMANDS
    if scope == 'available':
        required_commands = tuple(report.validation['verified_commands'])
    validation_time = int(time.time()) if scope == 'heroes' else int(snapshot.end_frame.timestamp)
    protocols = {str(cmd): deepcopy(rows) for cmd, rows in snapshot.protocol_data.items()
                 if cmd in required_commands}
    for packet in protocols.get('11001', []):
        for activity in packet.get('activity_list', []):
            row = db.get('activity', report.target_uid, 'AND activity_id=?', (activity['activity_id'],))
            fields = ('start_time', 'stop_time', 'state', 'theme', 'template')
            if (not row or any(row[field] != activity.get(field, 0) for field in fields)
                    or json.loads(row['sub_activity_id_list']) != activity.get('sub_activity_id_list', [])):
                return dict(passed=False, reason=f"活动来源行未完整持久化：{activity['activity_id']}")
    if scope == 'available' and '63005' in protocols:
        from capture_account_state import team_protocol_state
        protocols['63005'] = [team_protocol_state(frame.payload) for frame in snapshot.login_frames if frame.cmd == 63005]
    servants = {int(row['uid']): row for row in _one(snapshot, 46011).get('servant_list', [])}
    for packet in protocols.get('14009', []):
        for hero in packet.get('hero_info_list', []):
            base = hero['hero_base_info']
            servant = servants.get(int((base.get('weapon') or {}).get('servant_uid', 0)))
            base.setdefault('servant', dict(id=int(servant['id']), stage=int(servant['stage']))
                            if servant else dict(id=0, stage=0))
    with tempfile.TemporaryDirectory(prefix='capture-login-') as temporary:
        directory = Path(temporary)
        save_path = directory / 'isolated.db'
        with closing(sqlite3.connect(save_path)) as target:
            db._conn().backup(target)
        expected = directory / 'expected.json'
        expected.write_text(_json(dict(
            scope=scope, required_commands=required_commands,
            protocols=protocols,
            order=list(dict.fromkeys(frame.cmd for frame in snapshot.login_frames
                                     if frame.cmd in required_commands)),
            mail=[] if scope == 'heroes' else snapshot._mail_records,
            collected_mail=[] if scope == 'heroes' else snapshot._collected_mail_records,
            resource_version=snapshot.resource_version, validation_time=validation_time)), encoding='utf-8')
        script = r'''import json, os, socket, sqlite3, struct, sys, zlib
from pathlib import Path
from contextlib import closing
sys.path.insert(0, sys.argv[1])
root=Path.cwd()
os.environ['ACCOUNT_DB_PATH']=str(root/'default.db')
os.environ['APPDATA']=str(root/'config')
os.environ['LOCALAPPDATA']=str(root/'local')
def deny_network(*args, **kwargs): raise RuntimeError('导入验证禁止网络连接')
socket.socket.connect=deny_network
socket.socket.connect_ex=deny_network
import account_db, generator, login, save_generator, save_slot_manager, launch_settings
import gm_reader, res_version_manager as versions, codec
import logger
logger._LOG_DIR=str(root/'logs')
import timer_listeners
timer_listeners.register_timer_listeners()
from capture_import import _wire_state, _protocol_state
expected=json.loads(Path(sys.argv[4]).read_text('utf-8'))
import time
time.time=lambda: expected['validation_time']
uid=int(sys.argv[3])
save_generator.SLOTS=root
launch_settings.CONFIG=root/'config'/'launch.json'
versions.DYNAMIC_VERSIONS_PATH=str(root/'config'/'dynamic_versions.json')
versions.STATIC_RESOURCES_DIR=str(root/'resources')
save_slot_manager._SLOT_MANAGER=save_slot_manager.SaveSlotManager(str(root))
account_db.DEFAULT_DB=str(root/'default.db')
gm_reader.DEFAULT_DB=account_db.DEFAULT_DB
# Use the normal mount; route its real SQLite backup into this isolated directory.
def backup(path):
    destination=root/'backups'/'before-mount.db'
    destination.parent.mkdir(exist_ok=True)
    with closing(sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True)) as source:
        with closing(sqlite3.connect(destination)) as target: source.backup(target)
    return str(destination)
account_db.AccountDB.backup_save_file=staticmethod(backup)
class Socket:
    def __init__(self): self.frames=[]
    def settimeout(self, value): pass
    def sendall(self, frame): self.frames.append(bytes(frame))
sock=Socket()
db=None
try:
    mounted, reason=save_slot_manager.switch_active_database(sys.argv[2])
    if not mounted: raise RuntimeError(reason)
    db=account_db._db
    if generator.resolve_save_owner_uid(db)!=uid: raise RuntimeError('挂载主人不符')
    with versions.connection_version(expected['resource_version']):
        sent, dynamic=login.send_login_flood(sock,db,uid,generator,frame_delay=0,log=lambda *a,**k:None)
    commands=[]; packets={}
    for frame in sock.frames:
        if len(frame)<11: raise RuntimeError('短帧')
        if struct.unpack('>H',frame[:2])[0]!=len(frame)-2: raise RuntimeError('帧长度不符')
        command=struct.unpack('>H',frame[5:7])[0] | (65536 if frame[4]&1 else 0)
        commands.append(command)
        payload=zlib.decompress(frame[11:]) if frame[2]&1 else frame[11:]
        value=codec.decode(payload,'sc_'+str(command)) if payload else {}
        if command==63005 and expected['scope']=='available':
            from capture_account_state import team_protocol_state
            value=team_protocol_state(payload)
        if not isinstance(value,dict): raise RuntimeError('协议解码失败:'+str(command))
        packets.setdefault(command,[]).append(value)
    if commands.count(10201)!=1:
        raise RuntimeError('10201必须唯一')
    if packets[10201][0].get('timestamp')!=expected['validation_time']:
        raise RuntimeError('10201不是本次登录时钟')
    marker=commands.index(10201)
    required=set(expected['required_commands'])-{68155,88023}
    after=set(commands[marker+1:])
    if required&after:
        raise RuntimeError('必需账号帧出现在10201之后')
    if required-set(commands):
        raise RuntimeError('缺少必需账号帧:'+','.join(map(str,sorted(required-set(commands)))))
    actual_order=list(dict.fromkeys(cmd for cmd in commands if cmd in required))
    if expected['scope']=='full' and actual_order!=expected['order']:
        raise RuntimeError('必需账号帧顺序改变')
    def first_difference(left,right,path=''):
        if type(left) is not type(right): return path+':type'
        if isinstance(left,dict):
            if left.keys()!=right.keys(): return path+':fields('+str(sorted(left.keys()-right.keys()))+','+str(sorted(right.keys()-left.keys()))+')'
            for key in left:
                found=first_difference(left[key],right[key],path+'/'+str(key))
                if found: return found
        elif isinstance(left,list):
            if len(left)!=len(right): return path+':length('+str(len(left))+','+str(len(right))+')'
            for index,(a,b) in enumerate(zip(left,right)):
                found=first_difference(a,b,path+'/'+str(index))
                if found: return found
        elif left!=right: return path+':value('+repr(left)[:60]+','+repr(right)[:60]+')'
        return ''
    differences=[]; response_omissions=[]; added_tasks=[]
    for command, source in expected['protocols'].items():
        received=packets.get(int(command),[])
        if int(command) in (10600,11001,20007,49023):
            if int(command)==10600:
                from multiplayer_policy import CLOSED_SYSTEMS
                if not received[0].get('open_system') or CLOSED_SYSTEMS.intersection(received[0]['open_system']):
                    raise RuntimeError('系统开放列表违反本地策略')
            if int(command)==49023:
                opened={row['chapter_id']:row['timestamp'] for packet in received for row in packet.get('chess_open_info_list',[])}
                for packet in source:
                    if any(opened.get(row['chapter_id'])!=row['timestamp'] for row in packet.get('chess_open_info_list',[])):
                        raise RuntimeError('因果观测来源章节开放时间不符')
            with versions.connection_version(expected['resource_version']):
                raw=generator.gen_payload(int(command),uid=uid,db=db,res_version=expected['resource_version'])
            if raw is None:
                raise RuntimeError('本地目录生成失败:'+command)
            source=[codec.decode(raw,'sc_'+command) if raw else {}]
        if int(command)==10503 and any(row.get('timestamp')!=expected['validation_time'] for row in received):
            raise RuntimeError('10503 服务器时钟不是本次登录时钟')
        if int(command)==88023 and not received and source==[{'event_id':0}]:
            continue
        if int(command)==68155 and not received and all(not row.get('skin_id') for row in source):
            continue
        if int(command)==68151:
            from skin_draw_service import active_pools
            pools={cfg['activity_id'][0]:cfg for cfg in active_pools(expected['resource_version']).values()}
            observed={row['activity_id']:{item['drop_id'] for item in row.get('info',[])} for row in source}
            received=[row for row in received if row['activity_id'] in observed]
            for row in received:
                aid=row['activity_id']
                known=observed[aid]
                locked=[item for item in row['info'] if item['drop_id'] not in known]
                if any(item['num']!=pools[aid]['drops'][str(item['drop_id'])]['total'] for item in locked):
                    raise RuntimeError('来源未开启的奖池阶段具有抽取记录')
                row['info']=[item for item in row['info'] if item['drop_id'] in known]
        if int(command)==51001:
            source_stats={row['id'] for packet in source for row in packet.get('data_list',[])}
            received=[dict(data_list=[row for row in packet.get('data_list',[]) if row['id'] in source_stats])
                      for packet in received]
        if int(command)==88305:
            from rogueteam_service import RogueTeamService
            relay=RogueTeamService.get(db=db)
            actual_by_template={row['template_id']:row for row in received}
            for row in source:
                template=row['template_id']
                flags=db.get('ops_common',uid,"AND kind='rogueteam_collection_flags' AND item_id=?",(str(template),))
                unlock=set(row.get('unlock_collection',[]))
                viewed=set(row.get('view_collection',[]))
                if not flags or json.loads(flags['value_json'])!=dict(unlock=row.get('unlock_collection',[]),viewed=sorted(viewed)):
                    raise RuntimeError('推演来源图鉴标记缺少持久记录')
                actual=actual_by_template[template]
                local_unlock=set(actual.get('unlock_collection',[]))
                grouped={item for entry in row.get('collection_list',[]) for item in entry['item_list']}
                expected_unlock=relay._relic_item_ids() | (relay._valid_item_ids() & (unlock | grouped))
                if not unlock.issubset(local_unlock) or local_unlock!=expected_unlock:
                    raise RuntimeError('推演解锁图鉴与来源或本地目录不符')
                # Additional valid display slots belong to the client catalogue.
                row['unlock_collection']=sorted(unlock)
                actual['unlock_collection']=sorted(unlock)
        if int(command)==68161:
            from skin_draw_service import completed_story_ids
            merged=completed_story_ids(db,uid,expected['resource_version'])
            by_activity={row['activity_id']:row for row in received}
            for row in source:
                persisted=db.get_skin_story_state(uid,row['activity_id'])
                actual=by_activity.get(row['activity_id'])
                if (set(persisted)!=set(row.get('finished_story',[])) or actual is None
                    or actual.get('story_stage',0)!=row.get('story_stage',0)
                    or set(actual.get('finished_story',[]))!=merged
                    or not set(persisted).issubset(merged)):
                    raise RuntimeError('换装剧情与来源不符:'+str(row['activity_id']))
            continue
        if int(command)==89101 and expected['scope']=='available':
            from autochess_service import AutoChessService
            idle=AutoChessService.get_instance(db)._build_empty_89101()
            if received!=[codec.decode(idle,'sc_89101')] or any(row.get('state')!=0 for row in packets.get(89125,[])):
                raise RuntimeError('自走棋空闲存档生成了活动棋盘')
            continue
        if expected['scope']=='available' and int(command)==24009:
            visible={row['id'] for packet in received for row in packet.get('user_chapter_list',[])}
            for packet in source:
                kept=[]
                for row in packet['user_chapter_list']:
                    if row['id'] not in visible and (row.get('clear_times') or any(row.get('star_list',[]))):
                        saved=db.get('chapter',uid,'AND id=?',(row['id'],))
                        if not saved or saved['clear_times']!=row['clear_times'] or json.loads(saved['star_list'])!=row.get('star_list',[]):
                            raise RuntimeError('目录未展示的来源关卡未保存在数据库')
                        response_omissions.append(dict(command=24009,stage_id=row['id'],reason='current_client_catalog',stored=True))
                    else: kept.append(row)
                packet['user_chapter_list']=kept
        if expected['scope']=='available' and int(command)==20009:
            visible={(shop['shop_id'],goods['goods_id']) for packet in received for shop in packet.get('shop_item_list',[]) for goods in shop.get('goods_list',[])}
            for packet in source:
                for shop in packet['shop_item_list']:
                    kept=[]
                    for row in shop.get('goods_list',[]):
                        if row.get('buy_times') and (shop['shop_id'],row['goods_id']) not in visible:
                            saved=db.get('store_purchase',uid,'AND shop_id=? AND goods_id=?',(shop['shop_id'],row['goods_id']))
                            if not saved or any(saved[key]!=row[key] for key in ('buy_times','next_refresh_timestamp')):
                                raise RuntimeError('目录未展示的商店购买记录未保存在数据库')
                            response_omissions.append(dict(command=20009,shop_id=shop['shop_id'],goods_id=row['goods_id'],reason='current_client_catalog',stored=True))
                        else: kept.append(row)
                    shop['goods_list']=kept
        if expected['scope']=='available' and int(command)==28001:
            source_ids={row['id'] for packet in source for row in packet['assignment_list']}
            for packet in received:
                extras=[row for row in packet['assignment_list'] if row['id'] not in source_ids]
                if any(row.get('complete_flag') for row in extras):
                    raise RuntimeError('登录领取了来源外任务')
                added_tasks.extend(dict(id=row['id'],progress=row.get('progress',0)) for row in extras)
                packet['assignment_list']=[row for row in packet['assignment_list'] if row['id'] in source_ids]
        if int(command)==30001:
            source=[dict(total_number=db.query('SELECT COUNT(*) n FROM mail WHERE uid=? AND mail_type=1',(uid,))[0]['n'],
                         unread_number=db.query('SELECT COUNT(*) n FROM mail WHERE uid=? AND mail_type=1 AND read_flag=1',(uid,))[0]['n'])]
        if int(command)==83020:
            from sphero_battle_service import opened
            if any(row.get('is_start') != opened(db,uid,row['activity_id']) for row in received):
                raise RuntimeError('薇儿 Boss 开放状态与本地活动时限不符')
        wanted_state=_protocol_state(int(command),source,scope=expected['scope'])
        received_state=_protocol_state(int(command),received,scope=expected['scope'])
        if wanted_state!=received_state:
            detail=first_difference(wanted_state,received_state)
            if int(command)==20009:
                wanted={row['shop_id'] for row in source[0]['shop_item_list']}
                got={row['shop_id'] for row in packets[20009][0]['shop_item_list']}
                detail+=' missing-shops:'+str(sorted(wanted-got))
            differences.append(command+detail)
    if differences: raise RuntimeError('快照与实际登录值不符:'+','.join(differences))
    from mail_service import MailService
    mailbox=MailService.get_instance(db).get_inbox_list(uid)
    metadata=[{key: row[key] for key in ('id','date','title','attach_flag','read_flag',
              'attachment_list','timeout_timestamp','star_state')} for row in expected['mail']]
    source_ids={row['id'] for row in metadata}
    actual=[{key: row[key] for key in metadata[0]} for row in mailbox if row['id'] in source_ids] if metadata else []
    if _wire_state(metadata)!=_wire_state(actual): raise RuntimeError('普通邮箱明细不符')
    collected_payload=generator.gen_payload(30021,uid=uid,db=db)
    collected=codec.decode(collected_payload,'sc_30021').get('collect_mail_list',[])
    collect_keys=('id','collect_date','title','mail_timestamp')
    wanted_collect=[{key:row[key] for key in collect_keys} for row in expected['collected_mail']]
    actual_collect=[{key:row[key] for key in collect_keys} for row in collected]
    if _wire_state(wanted_collect)!=_wire_state(actual_collect):
        raise RuntimeError('收藏邮箱摘要不符')
    for detail_command, messages in ((30009,expected['mail']),(30023,expected['collected_mail'])):
        for row in messages:
            content=MailService.get_instance(db).get_mail_detail(uid,row['id'])
            content=codec.decode(codec.encode('sc_'+str(detail_command),dict(result=0,detail_info=content)),
                                 'sc_'+str(detail_command))['detail_info']
            wanted=row['content_list'] or [{'text':'此邮件正文未抓取。请在原账号打开此邮件后补抓。','content_type':2}]
            if _wire_state(content['content_list'])!=_wire_state(wanted):
                raise RuntimeError('邮箱正文不符:'+str(row['id']))
            if row.get('sender') and content.get('sender')!=row['sender']:
                raise RuntimeError('邮箱发件人不符:'+str(row['id']))
    collected_after=codec.decode(generator.gen_payload(30021,uid=uid,db=db),'sc_30021')
    if _wire_state(collected_after.get('collect_mail_list',[]))!=_wire_state(collected):
        raise RuntimeError('阅读邮件改变了收藏时间')
    print(json.dumps({'frames':len(commands),'decoded':len(commands),'sent':sent,
                      'normal_login_added_mail_ids':[row['id'] for row in mailbox if row['id'] not in source_ids],
                      'validation_clock':packets[10201][0]['timestamp'],
                      'response_omissions':response_omissions,'normal_login_added_task_ids':added_tasks,
                      'dynamic':dynamic,'mounted':True,'compared':len(expected['protocols'])}))
finally:
    if db is not None: db.close()
'''
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', script, str(server), str(save_path),
                                 str(report.target_uid), str(expected)], cwd=directory,
                                capture_output=True, text=True, encoding='utf-8', timeout=180)
        if list(db._conn().iterdump()) != original:
            return dict(passed=False, reason='隔离验证改变了待发布候选库')
        if result.returncode:
            error = next((line.strip() for line in reversed(result.stderr.splitlines())
                          if line.strip()), '没有返回错误详情')
            return dict(passed=False, reason='隔离挂载或登录失败：'+error[:4000])
        try:
            value = json.loads(result.stdout.splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            return dict(passed=False, reason='隔离进程没有返回有效核验报告')
        return dict(passed=True, frames=value['frames'], decoded=value['decoded'],
                    response_omissions=value['response_omissions'], normal_login_added_task_ids=value['normal_login_added_task_ids'],
                    compared=value['compared'], mounted=value['mounted'],
                    validation_clock=value['validation_clock'],
                    normal_login_added_mail_ids=value['normal_login_added_mail_ids'])


def build_imported_save(snapshot: CaptureSnapshot, target_uid, *, scope='full'):
    """Build a complete candidate in RAM; never persist or allocate a UID here."""
    import save_generator

    uid = save_generator.validate_uid(target_uid)
    report = _report(snapshot, uid, scope=scope)
    if report.issues or report.missing_data:
        raise ValueError(report)
    from account_db import AccountDB
    db = AccountDB.new_save_workspace()
    try:
        db.execute("ALTER TABLE hero ADD COLUMN clear_mission_list TEXT DEFAULT '[]'")
        master = save_generator.SERVER / "account.db"
        copied = save_generator.copy_static_catalogs(
            db, master, save_generator.IMPORT_STATIC_CATALOG_TABLES)
        blueprints = json.loads((save_generator.SERVER / "data/hero_blueprint.json").read_text("utf-8"))
        for hero_id, item in blueprints.items():
            db.execute("INSERT INTO hero_cfg(hero_id,unlock_star,name,race) VALUES(?,?,?,?)",
                       (int(hero_id), int(item["unlock_star"]), item["full_name"], int(item["race"])))
        counts = _build_rows(db, snapshot, uid, scope=scope)
        if scope == 'available':
            from capture_account_state import restore_account_state, verified_commands
            report.validation['recovery_manifest'] = restore_account_state(db, snapshot, uid)
            report.validation['verified_commands'] = verified_commands(snapshot)
            report.validation['unrestored_mail_ids'] = [row['id'] for row in snapshot._mail_records if not row['content_list']]
            report.row_counts = {row['name']: db.query(f'SELECT COUNT(*) n FROM "{row["name"]}" WHERE uid=?', (uid,))[0]['n']
                for row in db.query("SELECT name FROM sqlite_master WHERE type='table'")
                if any(column['name'] == 'uid' for column in db.query(f'PRAGMA table_info("{row["name"]}")'))}
        integrity = db._conn().execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError("内存候选库完整性检查失败")
        if scope != 'available':
            report.row_counts = counts["rows"]
        report.validation.update(integrity_check=True, owner_uid=True,
            static_catalogs=copied)
        report.validation['isolated_login'] = False
        return db, report
    except BaseException:
        db.close()
        raise


def build_imported_hero_save(snapshot: CaptureSnapshot, target_uid):
    """Restore captured hero assets onto an ordinary new single-account save."""
    import save_generator

    uid = save_generator.validate_uid(target_uid)
    report = _report(snapshot, uid, scope='heroes')
    if report.issues or report.missing_data:
        raise ValueError(report)
    heroes = _one(snapshot, 14009).get('hero_info_list', [])
    hero_ids = [int(hero['hero_base_info']['id']) for hero in heroes]
    if not hero_ids or len(set(hero_ids)) != len(hero_ids):
        raise ValueError('角色记录必须非空，角色 ID 不得重复')
    source = _one(snapshot, 23009)
    if int(source.get('hero_num', -1)) != len(heroes):
        raise ValueError('角色数量与来源账号摘要不一致')
    level = int(_one(snapshot, 12009).get('user_level', 0))
    options = save_generator.SaveOptions(uid=uid, nick=source.get('nick'), level=level,
        skip_intro=True, skip_feature_guides=True, support_mail=False)
    db, plan = save_generator.build_save_workspace(options, uid)
    try:
        db.execute("ALTER TABLE hero ADD COLUMN clear_mission_list TEXT DEFAULT '[]'")
        tables = ('hero', 'equip', 'servant', 'hero_archive', 'hero_piece', 'player_skin_unlocked')
        for table in tables:
            db.execute(f'DELETE FROM {table} WHERE uid=?', (uid,))
        _build_hero_rows(db, snapshot, uid, int(time.time()))
        db.execute('UPDATE users SET hero_num=? WHERE uid=?', (len(heroes), uid))
        db.execute('UPDATE game_user SET board_hero=?,show_hero=? WHERE uid=?',
                   (hero_ids[0], _json([hero_ids[0]]), uid))
        db.set_system_config('save.import_source_sha256', _json(snapshot.source_sha256))
        db.set_system_config('ai.api_profiles.v1', _json(
            dict(version=1, active_id='', profiles={}, routes={})))
        for row in db.query('SELECT id,equip_slot,weapon_servant_uid FROM hero WHERE uid=?', (uid,)):
            for equip_id in json.loads(row['equip_slot']).values():
                if equip_id and not db.get('equip', uid, 'AND id=?', (equip_id,)):
                    raise ValueError(f"角色 {row['id']} 引用不存在的刻印 {equip_id}")
            servant_id = row['weapon_servant_uid']
            if servant_id and not db.get('servant', uid, 'AND id=?', (servant_id,)):
                raise ValueError(f"角色 {row['id']} 引用不存在的钥从 {servant_id}")
        import generator
        if generator.resolve_save_owner_uid(db) != uid:
            raise ValueError('角色档主人不一致')
        if db.query('PRAGMA integrity_check')[0]['integrity_check'] != 'ok':
            raise ValueError('角色档完整性检查失败')
        report.row_counts = {table: db.query(f'SELECT COUNT(*) n FROM {table} WHERE uid=?', (uid,))[0]['n']
                             for table in tables}
        report.validation.update(integrity_check=True, owner_uid=True, isolated_login=False,
            static_catalogs=plan['static_tables'], base_profile='new_player_v1',
            source_hero_count=len(heroes), equipment_references=True, servant_references=True)
        return db, report
    except BaseException:
        db.close()
        raise


def publish_imported_save(db, report: ImportReport, name):
    """Rebuild with the final UID inside the ordinary creation lock, then publish."""
    from contextlib import closing
    import save_generator
    import save_slot_manager

    if report.snapshot is None or report.missing_data or report.issues:
        raise ValueError(report)
    if not all(report.validation.get(key) for key in ('integrity_check', 'owner_uid')):
        raise ValueError(report)
    import generator
    if generator.resolve_save_owner_uid(db) != report.target_uid:
        raise ValueError('候选库与报告的主人不一致')
    filename = save_generator.save_filename(name)
    directory = Path(save_generator.SLOTS).resolve()
    target = directory / filename
    staging_root = directory / '.import-staging'

    def is_reparse(path):
        try:
            return bool(getattr(path.stat(follow_symlinks=False), 'st_file_attributes', 0) & 0x400)
        except FileNotFoundError:
            return False

    with save_generator._creation_lock(directory):
        if target.exists():
            raise FileExistsError('存档名称已存在')
        occupied = save_generator.used_uids(directory)
        generated = report.validation.get('uid_generated', False)
        uid = save_generator.allocate_uid(occupied) if generated else save_generator.validate_uid(report.target_uid)
        if uid in occupied:
            raise ValueError('目标 UID 已被本地存档使用')
        builder = build_imported_hero_save if report.validation.get('import_scope') == 'heroes' else build_imported_save
        build_options = {} if report.validation.get('import_scope') == 'heroes' else dict(scope=report.validation.get('import_scope', 'full'))
        candidate, published = builder(report.snapshot, uid, **build_options)
        published.validation['uid_generated'] = generated
        stage_dir = staging_root / uuid.uuid4().hex
        stage_created = False
        root_created = False
        try:
            isolated = _verify_isolated_login(candidate, published)
            published.validation['isolated_login'] = isolated['passed']
            if not isolated['passed']:
                published.missing_data.append(dict(data='隔离子进程登录洪流验收', method=isolated['reason']))
                raise ValueError(published)
            published.validation.update(
                isolated_login_frames=isolated['frames'], decoded_login_frames=isolated['decoded'],
                compared_protocols=isolated['compared'], mounted=isolated['mounted'],
                snapshot_clock=published.snapshot.end_frame.timestamp,
                validation_clock=isolated['validation_clock'],
                normal_login_added_mail_ids=isolated['normal_login_added_mail_ids'],
                normal_login_added_task_ids=isolated['normal_login_added_task_ids'])
            if staging_root.is_symlink() or is_reparse(staging_root):
                raise ValueError('导入暂存根不能是符号链接或重解析点')
            try:
                staging_root.mkdir()
                root_created = True
            except FileExistsError:
                pass
            root_resolved = staging_root.resolve(strict=True)
            if root_resolved != staging_root.absolute() or is_reparse(root_resolved):
                raise ValueError('导入暂存根解析路径不安全')
            stage_dir.mkdir(exist_ok=False)
            stage_created = True
            resolved = stage_dir.resolve(strict=True)
            if resolved.parent != root_resolved or is_reparse(resolved):
                raise ValueError('导入暂存目录越出受控根')
            stage = resolved / (filename + '.stage')
            with closing(sqlite3.connect(stage)) as staged:
                candidate._conn().backup(staged)
                if staged.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('暂存库完整性检查失败')
                if list(staged.iterdump()) != list(candidate._conn().iterdump()):
                    raise ValueError('暂存库与已验证候选库不一致')
            if uid in save_generator.used_uids(directory):
                raise ValueError('目标 UID 在发布前已被占用')
            os.link(stage, target)
            published.output_path = str(target)
            published.validation['published_integrity'] = True
            try:
                manager = save_slot_manager.SaveSlotManager(str(directory))
                slot = manager.register_new_save(filename)
                registry = manager._load_registry()
                matching = [key for key, value in registry.items()
                            if value.casefold() == filename.casefold()]
                if slot is None or matching != [slot]:
                    published.slot_registration = dict(registered=False, reason='已导入、未分槽：没有可用槽位')
                else:
                    published.slot_registration = dict(registered=True, slot=slot)
            except Exception as exc:
                published.slot_registration = dict(registered=False,
                    reason='已导入、未分槽：'+str(exc))
        finally:
            candidate.close()
            try:
                if stage_created and (stage_dir.exists() or stage_dir.is_symlink()):
                    if stage_dir.is_symlink() or is_reparse(stage_dir):
                        raise ValueError('拒绝删除已被替换为链接的暂存目录')
                    resolved = stage_dir.resolve(strict=True)
                    if (resolved.parent != root_resolved or is_reparse(resolved)
                            or staging_root.is_symlink() or is_reparse(staging_root)):
                        raise ValueError('拒绝删除受控根以外的暂存目录')
                    shutil.rmtree(stage_dir)
                if root_created and staging_root.exists() and not staging_root.is_symlink() and not is_reparse(staging_root):
                    try:
                        staging_root.rmdir()
                    except OSError:
                        if not any(staging_root.iterdir()):
                            raise
            except Exception as exc:
                if not published.output_path:
                    raise
                published.issues.append('文件已发布，暂存清理失败：' + str(exc))
        return published
