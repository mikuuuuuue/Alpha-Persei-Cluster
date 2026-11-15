"""Build a new single-account save from one captured login snapshot."""
from dataclasses import dataclass, field
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

    def __post_init__(self):
        messages = [mail for frame in self.supplement_frames
                    for mail in frame.decoded.get('mail_list', [])]
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
        if len(cells) < 4 or not cells[0].endswith(".jsonl"):
            continue
        endpoint = cells[2]
        match = re.fullmatch(r"(.+):(\d+)\s*→\s*(.+):(\d+)", endpoint)
        if not match:
            continue
        direction = cells[1]
        source_host, source_port = match.group(1), int(match.group(2))
        target_host, target_port = match.group(3), int(match.group(4))
        if direction == "up":
            if target_port != 8105:
                continue
            local_port, remote_host = source_port, target_host
        elif direction == "down":
            if source_port != 8105:
                continue
            local_port, remote_host = target_port, source_host
        else:
            continue
        local_host = source_host if direction == 'up' else target_host
        if cells[0] in found:
            raise ValueError(f'{cells[0]} 的连接摘要重复')
        found[cells[0]] = (direction, local_port, remote_host.strip(), local_host.strip())
    return found, hashlib.sha256(raw).hexdigest()


def _load_stream(path, connection_map):
    summary = connection_map.get(path.name)
    if summary is None:
        raise ValueError(f"缺少 {path.name} 的连接归属摘要")
    expected_dir, local_port, remote_host, local_host = summary
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


def _assess(snapshot):
    missing = []
    reasons = list(snapshot.issues)
    for cmd in REQUIRED_COMMANDS:
        if not snapshot.protocol_data.get(cmd):
            missing.append(dict(data=f"协议 {cmd}", method=f"同一 8105 登录流捕获 sc_{cmd}"))
        elif cmd != 60201 and len(snapshot.protocol_data[cmd]) != 1:
            reasons.append(f'协议 {cmd} 不是唯一全量快照')
    if snapshot.client_build != '307' or snapshot.resource_version != '321':
        missing.append(dict(data='该客户端版本的已审核目录', method='提供与客户端构建和资源版本一致的配置审计'))
    for cmd, field, key in ((13009, 'equip_list', 'equip_id'), (15009, 'currency_list', 'id'),
                            (17009, 'material_list', 'id'), (46011, 'servant_list', 'uid'),
                            (28001, 'assignment_list', 'id'), (28019, 'pt_list', 'activity_pt_id')):
        seen = set()
        for packet in snapshot.protocol_data.get(cmd, []):
            for item in packet.get(field, []):
                item_id = item.get(key)
                if type(item_id) is not int or item_id <= 0 or item_id in seen:
                    reasons.append(f'协议 {cmd} 的 {field}.{key} 无效或重复')
                seen.add(item_id)
    unsupported = sorted({frame.cmd for frame in snapshot.login_frames} - MAPPED_COMMANDS)
    if unsupported:
        missing.append(dict(data="未审核登录协议",
                            protocol_commands=unsupported,
                            method="审核协议归属；账号帧补齐目标状态映射，静态帧提供账号无关证据"))
    heroes = (snapshot.protocol_data.get(14009) or [{}])[0].get("hero_info_list", [])
    if heroes and not any(isinstance(hero, dict) and "equip" in hero for hero in heroes):
        missing.append(dict(data="角色携带刻印槽", method="从同一登录段的 sc_14009 取得 hero_net_rec.equip"))
    if not snapshot.protocol_data.get(13009):
        missing.append(dict(data="刻印库存", method="补抓 sc_13009；不得用角色装备槽代替库存"))
    summaries = snapshot.protocol_data.get(30001, [])
    summary = summaries[0] if len(summaries) == 1 else None
    if summary is None:
        missing.append(dict(data="普通邮箱摘要 30001", method="从同一次登录取得 sc_30001"))
    else:
        total = int(summary.get("total_number", -1))
        unread = int(summary.get("unread_number", -1))
        if total < 0 or unread < 0 or unread > total:
            reasons.append("30001 邮箱数量无效")
        elif total:
            details = [frame for frame in snapshot.supplement_frames if frame.cmd == 30003]
            if not details:
                missing.append(dict(data=f"普通邮箱明细 {total} 封", method=
                    "登录后、读信或领取前，在同一连接发送 cs_30002 并保存完整 sc_30003"))
            else:
                messages_by_id = {}
                for frame in details:
                    for message in frame.decoded.get("mail_list", []):
                        mail_id = int(message.get("id", 0))
                        prior = messages_by_id.get(mail_id)
                        if prior is not None and _canonical(prior) != _canonical(message):
                            reasons.append(f"30003 邮件 ID {mail_id} 的重复记录内容冲突")
                        else:
                            messages_by_id[mail_id] = message
                messages = [_mail_record(row, snapshot._mail_templates) for row in messages_by_id.values()]
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
        elif unread:
            reasons.append("30001 总数为 0 但未读数大于 0")
    return missing, reasons


def read_snapshot(capture_dir) -> CaptureSnapshot:
    """Read one 8105 login flow and its permitted mailbox query supplement."""
    root = Path(capture_dir).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("抓包路径必须是目录")
    connection_map, summary_hash = _summary_connections(root)
    files = sorted(root.glob("tcp_*_*_8105.jsonl"))
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
    if not login_frames or not any(frame.cmd == 10043 for frame in login_frames):
        raise ValueError("10201 前未见登录确认帧")
    post_frames = down_frames[marker + 1:]
    if end_frame.timestamp is None:
        raise ValueError("10201 缺少可核验时间戳，不能绑定结束后的邮箱补抓")
    up_post = [frame for frame in up_frames
               if frame.timestamp is not None and frame.timestamp > end_frame.timestamp]
    issues = []
    mail_queries = [frame for frame in up_post if frame.cmd == 30002]
    mail_responses = [frame for frame in post_frames if frame.cmd == 30003]
    if len(mail_queries) > 1 or len(mail_responses) > 1 or bool(mail_queries) != bool(mail_responses):
        issues.append("结束帧后的邮箱查询/应答不能唯一配对")
    if mail_queries:
        query = mail_queries[0]
        if len(mail_responses) != 1:
            response = None
            issues.append("30002 查询缺少唯一的同会话 30003 应答")
        else:
            response = mail_responses[0]
        if (query.timestamp is None or response is None or response.timestamp is None
                or response.timestamp <= query.timestamp):
            issues.append("30002 查询与 30003 应答缺少可核验的先后时间")
        if response is not None:
            if any(frame.cmd in MAIL_MUTATION_COMMANDS and frame.timestamp <= response.timestamp
                   for frame in up_post):
                issues.append("邮箱补抓完成前已发生读信、领取、删除或收藏动作")
            if any(frame.cmd in MAIL_RESPONSE_MUTATIONS | {30001}
                   and frame.timestamp <= response.timestamp for frame in post_frames):
                issues.append("邮箱补抓完成前收到邮件状态变更")
    protocol_data = {}
    for frame in login_frames:
        if frame.cmd == 10043:
            continue
        protocol_data.setdefault(frame.cmd, []).append(frame.decoded)
    for frame in mail_responses:
        protocol_data.setdefault(frame.cmd, []).append(frame.decoded)
    chapter_frames = [frame for frame in login_frames if frame.cmd == 24009]
    if chapter_frames:
        protocol_data[24009] = [dict(user_chapter_list=_merge_chapters(chapter_frames, issues))]
    for cmd in (30001,):
        if len(protocol_data.get(cmd, [])) > 1:
            issues.append(f"同一登录段出现多个 {cmd}，无法确定快照")
    snapshot = CaptureSnapshot(
        source_uid=int(login_info["user_id"]),
        client_build=str(login_info["client_vs"]),
        resource_version=str(login_info["resource_vs"]),
        session_id=hashlib.sha256(f"{local_port}:{up_name}:{down_name}".encode()).hexdigest()[:16],
        login_frames=login_frames,
        supplement_frames=mail_responses,
        source_sha256=hashes,
        protocol_data=protocol_data,
        end_frame=end_frame,
        issues=issues)
    snapshot.unsupported_login_commands = sorted(
        {frame.cmd for frame in login_frames} - MAPPED_COMMANDS)
    snapshot.missing_data, snapshot.issues = _assess(snapshot)
    return snapshot


def _report(snapshot, target_uid=None):
    missing, issues = _assess(snapshot)
    return ImportReport(target_uid=target_uid, missing_data=missing,
                        source_sha256=dict(snapshot.source_sha256), issues=issues,
                        snapshot=snapshot,
                        validation=dict(session_id=snapshot.session_id,
                                        source_uid_present=bool(snapshot.source_uid),
                                        client_build=snapshot.client_build,
                                        resource_version=snapshot.resource_version,
                                        login_frames=len(snapshot.login_frames),
                                        supplement_frames=len(snapshot.supplement_frames)))


def _one(snapshot, cmd):
    rows = snapshot.protocol_data.get(cmd, [])
    if len(rows) != 1:
        raise ValueError(f"协议 {cmd} 必须恰有一份全量快照")
    return rows[0]


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _build_rows(db, snapshot, uid):
    """Apply the reviewed login snapshot fields to account-owned tables."""
    import save_generator

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
            trust_mood=int(trust.get("mood", 1)), relation_net=_json(relation),
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
        db.upsert("task", uid, dict(task_id=int(row["id"]), progress=int(row.get("progress", 0)),
            complete_flag=int(row.get("complete_flag", 0)), expired_ts=int(row.get("expired_timestamp", 0))),
            keys=("uid", "task_id"))
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

    mail_rows = [_mail_record(mail, snapshot._mail_templates) for frame in snapshot.supplement_frames
                 for mail in frame.decoded.get("mail_list", [])]
    for mail in mail_rows:
        body = mail.get("content_list") or mail.get("content")
        if not body:
            raise ValueError("30003 邮件缺少已解析的正文文本")
        if isinstance(body, str):
            content = [{"text": body, "content_type": 2}]
        elif isinstance(body, list):
            content = body
        else:
            content = [body]
        db.upsert("mail", uid, dict(mail_id=int(mail["id"]), mail_type=1,
            template_id=0, title=str(mail.get("title", "")), sender="",
            content_json=_json(content),
            send_time=int(mail.get("date", 0)), expire_time=int(mail.get("timeout_timestamp", 0)),
            read_flag=int(mail.get("read_flag", 0)), attach_flag=int(mail.get("attach_flag", 0)),
            star_state=int(mail.get("star_state", 0)),
            attachment_json=_json(mail.get("attachment_list", [])), update_ts=timestamp),
            keys=("uid", "mail_id"))
    # Dynamic rows are generated from this target account at login. Captured
    # payload bytes are never copied into the target account.
    sequence = []
    for frame in snapshot.login_frames:
        cmd = frame.cmd
        if cmd == 12009:
            sequence.append((frame, 0, _json(dict(user_level=level))))
            continue
        if cmd == 60201:
            activity_id = int(frame.decoded["activity_id"])
            if activity_id == 323801:
                payload_json = _json(dict(activity_id=activity_id))
                sequence.append((frame, 1, payload_json))
            else:
                state = db.query("SELECT point FROM activity_point WHERE uid=? AND activity_id=?",
                                 (uid, activity_id))
                rewards = [int(row["reward_id"]) for row in db.query(
                    "SELECT reward_id FROM activity_point_reward WHERE uid=? AND activity_id=? "
                    "ORDER BY reward_id", (uid, activity_id))]
                if not state:
                    raise ValueError(f"60201 活动 {activity_id} 缺目标库积分状态")
                payload_json = _json(dict(activity_id=activity_id,
                                          point=int(state[0]["point"]), reward_list=rewards))
                sequence.append((frame, 0, payload_json))
            continue
        sequence.append((frame, 1, None))
    if sum(frame.cmd == 10201 for frame, _, _ in sequence) != 0:
        raise ValueError("10201 不得在登录快照帧中重复")
    if snapshot.end_frame is None or snapshot.end_frame.cmd != 10201:
        raise ValueError('缺少原始 10201 结束帧')
    sequence.append((snapshot.end_frame, 0, _json(snapshot.end_frame.decoded)))
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


def _protocol_state(command, packets):
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
    with tempfile.TemporaryDirectory(prefix='capture-login-') as temporary:
        directory = Path(temporary)
        save_path = directory / 'isolated.db'
        with closing(sqlite3.connect(save_path)) as target:
            db._conn().backup(target)
        expected = directory / 'expected.json'
        expected.write_text(_json(dict(
            protocols={str(cmd): rows for cmd, rows in snapshot.protocol_data.items()
                       if cmd in REQUIRED_COMMANDS},
            order=list(dict.fromkeys(frame.cmd for frame in snapshot.login_frames
                                     if frame.cmd in REQUIRED_COMMANDS)),
            mail=[_mail_record(mail, snapshot._mail_templates) for frame in snapshot.supplement_frames
                  for mail in frame.decoded.get('mail_list', [])],
            resource_version=snapshot.resource_version, snapshot_time=snapshot.end_frame.timestamp)), encoding='utf-8')
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
from capture_import import REQUIRED_COMMANDS, _wire_state, _protocol_state
expected=json.loads(Path(sys.argv[4]).read_text('utf-8'))
import time
time.time=lambda: expected['snapshot_time']
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
        if not isinstance(value,dict): raise RuntimeError('协议解码失败:'+str(command))
        packets.setdefault(command,[]).append(value)
    if commands.count(10201)!=1:
        raise RuntimeError('10201必须唯一')
    marker=commands.index(10201)
    if any(command in REQUIRED_COMMANDS for command in commands[marker+1:]):
        raise RuntimeError('必需账号帧出现在10201之后')
    required=set(REQUIRED_COMMANDS)
    if required-set(commands): raise RuntimeError('缺少必需账号帧')
    actual_order=list(dict.fromkeys(cmd for cmd in commands if cmd in required))
    if actual_order!=expected['order']: raise RuntimeError('必需账号帧顺序改变')
    def first_difference(left,right,path=''):
        if type(left) is not type(right): return path+':type'
        if isinstance(left,dict):
            if left.keys()!=right.keys(): return path+':fields'
            for key in left:
                found=first_difference(left[key],right[key],path+'/'+str(key))
                if found: return found
        elif isinstance(left,list):
            if len(left)!=len(right): return path+':length('+str(len(left))+','+str(len(right))+')'
            for index,(a,b) in enumerate(zip(left,right)):
                found=first_difference(a,b,path+'/'+str(index))
                if found: return found
        elif left!=right: return path+':value'
        return ''
    differences=[]
    for command, source in expected['protocols'].items():
        if int(command)==30001:
            source=[dict(total_number=db.query('SELECT COUNT(*) n FROM mail WHERE uid=? AND mail_type=1',(uid,))[0]['n'],
                         unread_number=db.query('SELECT COUNT(*) n FROM mail WHERE uid=? AND mail_type=1 AND read_flag=1',(uid,))[0]['n'])]
        wanted_state=_protocol_state(int(command),source)
        received_state=_protocol_state(int(command),packets.get(int(command),[]))
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
    for row in expected['mail']:
        content=MailService.get_instance(db).get_mail_detail(uid,row['id'])
        if _wire_state(content['content_list'])!=_wire_state(row.get('content_list') or
                [{'text':row.get('content',''),'content_type':2}]):
            raise RuntimeError('普通邮箱正文不符')
    print(json.dumps({'frames':len(commands),'decoded':len(commands),'sent':sent,
                      'normal_login_added_mail_ids':[row['id'] for row in mailbox if row['id'] not in source_ids],
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
            return dict(passed=False, reason='隔离挂载或登录失败：'+error[:400])
        try:
            value = json.loads(result.stdout.splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            return dict(passed=False, reason='隔离进程没有返回有效核验报告')
        return dict(passed=True, frames=value['frames'], decoded=value['decoded'],
                    compared=value['compared'], mounted=value['mounted'],
                    normal_login_added_mail_ids=value['normal_login_added_mail_ids'])


def build_imported_save(snapshot: CaptureSnapshot, target_uid):
    """Build a complete candidate in RAM; never persist or allocate a UID here."""
    import save_generator

    uid = save_generator.validate_uid(target_uid)
    report = _report(snapshot, uid)
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
        counts = _build_rows(db, snapshot, uid)
        integrity = db._conn().execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError("内存候选库完整性检查失败")
        report.row_counts = counts["rows"]
        report.validation.update(integrity_check=True, owner_uid=True,
            static_catalogs=copied)
        report.validation['isolated_login'] = False
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
        candidate, published = build_imported_save(report.snapshot, uid)
        published.validation['uid_generated'] = generated
        stage_dir = staging_root / uuid.uuid4().hex
        stage_created = False
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
                normal_login_added_mail_ids=isolated['normal_login_added_mail_ids'])
            if staging_root.is_symlink() or is_reparse(staging_root):
                raise ValueError('导入暂存根不能是符号链接或重解析点')
            staging_root.mkdir(parents=True, exist_ok=True)
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
            if stage_created and (stage_dir.exists() or stage_dir.is_symlink()):
                if stage_dir.is_symlink() or is_reparse(stage_dir):
                    raise ValueError('拒绝删除已被替换为链接的暂存目录')
                resolved = stage_dir.resolve(strict=True)
                if (resolved.parent != root_resolved or is_reparse(resolved)
                        or staging_root.is_symlink() or is_reparse(staging_root)):
                    raise ValueError('拒绝删除受控根以外的暂存目录')
                shutil.rmtree(stage_dir)
            if staging_root.exists() and not staging_root.is_symlink() and not is_reparse(staging_root):
                try:
                    staging_root.rmdir()
                except OSError:
                    if not any(staging_root.iterdir()):
                        raise
        return published
