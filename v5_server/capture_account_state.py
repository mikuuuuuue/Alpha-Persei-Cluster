"""Restore reviewed account fields into the existing domain tables."""
import json
from copy import deepcopy


DOMAIN_COMMANDS = {
    'profile': (12029, 12033, 12039, 12045, 12089, 13057, 14201, 14501, 14503, 21001, 32009, 32011),
    'collections': (12001, 12011, 12111, 50001, 52001, 52021, 52025, 53001, 56001),
    'entitlements': (11013, 11015, 17027, 17033, 34007, 34023, 34031, 34101),
    'backhome': (58001, 58063),
    'progress': (25009, 43001, 47001, 47003, 63005),
    'games': (24051, 61047, 68171, 68181, 83026, 83124, 84331, 89011, 89401, 89601, 89701),
    'exploration': (24029, 24043, 24061, 28801, 28837, 49001, 79601, 86035),
    'communications': (12023, 12119, 28001, 30017, 73001, 73005, 73007, 91001),
    'activities': (11001, 18001, 35011, 44007, 44019, 44023, 45201, 48001, 48003, 55001,
                   59001, 62019, 64031, 83020, 83021, 85101, 86037, 88305, 88309,
                   88315, 89101, 89125, 89201, 90051, 89021),
    'idol': (58169, 58173, 58189, 58191, 58195, 58203),
    'rogueteam': (88001, 88013, 88019, 88029),
    'admin_cat': (67001,),
}
ACCOUNT_COMMANDS = frozenset(cmd for commands in DOMAIN_COMMANDS.values() for cmd in commands)

PARTIAL_COMMANDS = {
    16015: dict(
        fields_restored=('draw_info_list',),
        missing_fields=('since_sr', 'is_up_guaranteed'),
        reason='抽取记录缺少保底状态；up_times 不能当作总抽数。',
        recapture='如需抽卡历史，可选补抓记录查询；重复 16015 不会提供隐藏保底字段。'),
    75009: dict(
        fields_restored=('now_cycle', 'next_cycle', 'stage_info', 'reward_list',
                         'lock_list', 'refresh_timestamp', 'max_score_info'),
        missing_fields=('完整登录响应结构',),
        reason='来源关卡与奖励字段已持久化；当前生成器尚不能逐值重建全部来源响应。零进度保持原值。',
        recapture='无需为了补抓制造通关记录；先完成现有载荷与消费者的对应核验。'),
    83020: dict(
        fields_restored=('activity_id', 'fight_cnt', 'score_info_list', 'is_start',
                         'got_award_cfg_list'),
        missing_fields=('多阶段持久结构',),
        reason='现有 Boss 表与来源多阶段结构不能完整对应。',
        recapture='现有来源已含多阶段数据；先补字段映射，无需为恢复已有状态重新战斗。'),
    85035: dict(fields_restored=(), missing_fields=('章节状态',),
                reason='载荷只有 chapter_id，持久语义未闭合。',
                recapture='先核对已抓章节与现有局内模型；只有界面显示进行中且缺局内详情时再补抓。'),
    85105: dict(fields_restored=(), missing_fields=('选项状态',),
                reason='载荷只有 opt_list，未确认其与持久表的对应关系。',
                recapture='现有 opt_list 已保存；先审核消费字段，无需重复执行选项操作。'),
    89421: dict(fields_restored=(), missing_fields=('多阶段 Boss 战状态',),
                reason='载荷含多阶段 Boss 状态，现有表不能无损承接。',
                recapture='现有载荷已含关卡、Boss、血量和成绩；先补持久映射，无需重新挑战。'),
    89801: dict(fields_restored=(), missing_fields=('持久进度',),
                reason='载荷 first_enter/max_point 的持久消费者尚未闭合。',
                recapture='先核对当前成绩；实际为 0 时保留原值，无需创建新成绩。'),
    60105: dict(fields_restored=(), missing_fields=('常驻积分',),
                reason='来源 repeated score_info_list 为空；当前生成器会混入其他活动积分，完整投影尚未闭合。',
                recapture='已有登录载荷，先修复积分投影；无需为了补抓新增积分。'),
    60107: dict(fields_restored=(), missing_fields=('已领奖励',),
                reason='来源 repeated reward_info_list 为空；当前生成器还会输出其他活动的领奖记录。',
                recapture='已有登录载荷，先核对领奖记录归属；无需为补抓领取奖励。'),
    89101: dict(fields_restored=(), missing_fields=('进行中棋局',),
                reason='棋盘载荷存在，但 89125.state=0；不能把已结束的局恢复为进行中。',
                recapture='如确有进行中棋局，在同一登录会话补抓非零 89125 与对应 89101。'),
    11001: dict(
        fields_restored=('activity_list',),
        missing_fields=('当前客户端目录未展示的来源活动响应',),
        reason='来源活动行已写入 activity；当前客户端目录只回放其中有效活动。',
        recapture='如需核验全部活动响应，使用匹配来源版本的客户端资源目录补抓。'),
    35011: dict(
        fields_restored=('stage_id', 'challenge_rate', 'affix_info', 'today_max_score',
                         'sum_score', 'refresh_timestamp', 'got_reward_id_list'),
        missing_fields=('捕获周期的每日关卡和词缀轮换',),
        reason='持久分数和奖励已恢复；当前登录按新周期生成关卡与词缀。',
        recapture='已抓到来源周期数据；先修复周期投影，无需重复登录。'),
    44007: dict(
        fields_restored=('difficulty_list', 'next_refresh_timestamp', 'recommend_team',
                         'affix_list'),
        missing_fields=('捕获周期的轮换布局',),
        reason='当前周期生成新的轮换布局，不能证明与来源逐值相同。',
        recapture='已抓到来源周期数据；先核对轮换投影，无需重复登录。'),
    44019: dict(
        fields_restored=('difficulty', 'is_new_difficulty', 'open_difficulty_list'),
        missing_fields=('捕获周期的轮换状态',),
        reason='当前周期生成新的轮换状态，不能证明与来源逐值相同。',
        recapture='已抓到来源周期数据；先核对轮换投影，无需重复登录。'),
    44023: dict(
        fields_restored=('now_difficulty', 'difficulty_id_can_choose', 'receive_reward',
                         'clear_list', 'challenge_info', 'is_new_difficulty'),
        missing_fields=('捕获周期的轮换进度',),
        reason='持久进度已写入；当前周期仍会改变部分轮换字段。',
        recapture='已抓到来源周期数据；先核对轮换投影，无需重复登录。'),
    55001: dict(
        fields_restored=('activity_id', 'is_back', 'history_max_layer',
                         'layer_reset_time', 'stage_reset_time',
                         'last_version_max_unlock_layer', 'refresh_timestamp',
                         'layer_info_list', 'got_reward_id_list'),
        missing_fields=('完整登录响应结构',),
        reason='持久层字段已恢复；当前消费者尚不能逐值重建完整来源响应。',
        recapture='已有完整来源载荷；先修复响应映射，无需重复登录。'),
    59001: dict(
        fields_restored=('newbie_sign', 'newbie_level_reward', 'newbie_recharge_reward',
                         'trigger_time', 'is_completed'),
        missing_fields=('完整登录响应结构',),
        reason='新手活动持久字段已恢复；当前版本默认生成结构不能逐值回放来源响应。',
        recapture='已有来源载荷；先修复版本响应映射。'),
    88305: dict(
        fields_restored=('template_id', 'difficult', 'max_difficult', 'his_difficult',
                         'his_avg', 'collection_list', 'view_collection', 'tree_list',
                         'last_id'),
        missing_fields=('unlock_collection 的来源精确列表',),
        reason='来源图鉴项已写入持久表；当前客户端为防崩溃下发兼容超集。',
        recapture='无需补抓；按当前客户端目录核验持久图鉴项。'),
}

EVIDENCE_ONLY_COMMANDS = {
    89207: dict(reason='历史战绩没有现有持久表。', recapture=''),
    30099: dict(reason='公告属于静态内容，按原始证据保存。', recapture=''),
}

def _equip_dungeon_gap(packets, timestamp):
    from stage_service import EQUIP_GROUP_FIRST_STAGE
    rows = packets.get(43001, [])
    if len(rows) != 1 or rows[0].get('stage_base_id') not in EQUIP_GROUP_FIRST_STAGE:
        return '没有唯一且已审核的刻印关卡组。'
    row = rows[0]
    counts = row.get('insure_list', [])
    if (sorted(item.get('difficulty', 0) for item in counts) != [1, 2, 3, 4, 5]
            or any(item.get('insure_times', -1) < 0 for item in counts)
            or row.get('equip_suit_id', 0) <= 0 or row.get('next_refresh_time', 0) <= timestamp):
        return '缺少五档保底、选中套装或有效的来源刷新时间。'
    return ''


def recovery_manifest(snapshot):
    """List the evidence disposition without implying that a missing field is empty."""
    from capture_import import MAPPED_COMMANDS
    from multiplayer_policy import blocks_command

    records = []
    for command in sorted(snapshot.protocol_data):
        domain = next((name for name, commands in DOMAIN_COMMANDS.items() if command in commands), '')
        details = PARTIAL_COMMANDS.get(command) or EVIDENCE_ONLY_COMMANDS.get(command, {})
        if command in (30003, 30021):
            domain = 'mailbox'
            if command == 30021 and any(not row['content_list'] for row in snapshot._collected_mail_records):
                status = 'partial'
                details = dict(fields_restored=('collect_mail_list', 'collect_date', 'mail_timestamp'),
                    missing_fields=('收藏邮件正文与附件',),
                    reason='收藏摘要已持久化；未捕获详情的邮件不补写正文或附件。',
                    recapture='打开收藏邮箱中的每封邮件，补抓同一连接的 cs_30022/sc_30023。')
            else:
                status = 'restored'
        elif command == 43001 and (gap := _equip_dungeon_gap(snapshot.protocol_data, snapshot.end_frame.timestamp)):
            status = 'partial'
            details = dict(reason=gap, missing_fields=('可核验的刻印副本快照',))
        elif command in PARTIAL_COMMANDS:
            status = 'partial'
        elif command in EVIDENCE_ONLY_COMMANDS:
            status = 'evidence-only'
        elif command in MAPPED_COMMANDS or domain:
            status = 'core' if command in MAPPED_COMMANDS else 'restored'
        elif blocks_command(command):
            status = 'excluded'
        else:
            status = 'pending'
        records.append(dict(command=command, domain=domain or ('core' if command in MAPPED_COMMANDS else ''),
                            status=status, fields_restored=list(details.get('fields_restored', ())),
                            missing_fields=list(details.get('missing_fields', ())),
                            reason=details.get('reason', ''),
                            recapture=details.get('recapture', '')))
    return records


def verified_commands(snapshot):
    """Return commands that were restored and must round-trip through login."""
    from capture_import import MAPPED_COMMANDS

    login_commands = (MAPPED_COMMANDS | ACCOUNT_COMMANDS) - {10043}
    return [row['command'] for row in recovery_manifest(snapshot)
            if row['command'] in login_commands and row['status'] in ('core', 'restored')]


def restore_account_state(db, snapshot, uid):
    """Apply only source-owned fields; normal services remain their consumers."""
    packets = snapshot.protocol_data
    manifest = recovery_manifest(snapshot)
    disposition = {record['command']: record for record in manifest}
    db.set_system_config('capture.resource_version', snapshot.resource_version)
    for restore in (_restore_profile, _restore_collections, _restore_entitlements,
                    _restore_backhome, _restore_progress, _restore_games,
                    _restore_exploration, _restore_communications, _restore_activities,
                    _restore_idol, _restore_rogueteam, _restore_admin_cat,
                    _restore_autochess):
        restore(db, packets, uid, int(snapshot.end_frame.timestamp))
    for frame in snapshot.login_frames:
        if frame.cmd == 63005:
            _restore_teams(db, frame.payload, uid)
    for command in sorted(packets):
        record = disposition[command]
        if record['status'] not in ('partial', 'evidence-only', 'pending'):
            continue
        evidence = dict(
            command=command,
            status=record['status'],
            domain=record['domain'],
            reason=record['reason'],
            recapture=record['recapture'],
            session_id=snapshot.session_id,
            source_sha256=snapshot.source_sha256,
            payloads=packets[command])
        db.upsert(
            'ops_common',
            uid,
            dict(kind='capture_evidence', item_id=str(command),
                 value_json=json.dumps(
                     evidence, ensure_ascii=False, separators=(',', ':'))),
            keys=('uid', 'kind', 'item_id'))
    return manifest


def _restore_profile(db, packets, uid, timestamp):
    from capture_import import _json

    profile = (packets.get(32009) or [{}])[0]
    birthday = (packets.get(12033) or [{}])[0]
    values = dict(update_ts=timestamp)
    for command, fields in ((12089, ('is_first_draw', 'is_first_draw_limited', 'is_first_draw_lucky', 'total_buy_fatigue_times')),):
        for field in fields:
            if field in (packets.get(command) or [{}])[0]:
                values[field] = int(packets[command][0][field])
    if birthday:
        values.update(birth_month=int(birthday['month']), birth_day=int(birthday['day']))
    if packets.get(12029):
        values['bgm_id'] = int(packets[12029][0]['id'])
    for field, column in (('icon', 'cur_portrait'), ('icon_frame', 'cur_icon_frame'),
                          ('poster_girl', 'board_hero'), ('information_background_id', 'cur_card_bg'),
                          ('chat_bubble', 'cur_bubble'), ('sticker_background', 'cur_sticker_bg'),
                          ('poster_background_id', 'cur_scene')):
        if field in profile:
            values[column] = int(profile[field])
    if 'heroes' in profile:
        values['show_hero'] = _json(profile['heroes'])
    for dessert in (packets.get(12045) or [{}])[0].get('daily_fatigue_dessert_list', []):
        kind = int(dessert['type'])
        if kind not in (11, 18):
            raise ValueError('未知体力补给类型')
        values[f'dessert_{kind}_got'] = int(dessert['is_got'])
        if dessert['is_got']:
            from daily_fatigue_codec import get_today_date_str
            db.upsert('daily_fatigue', uid, dict(type=kind, date_str=get_today_date_str(timestamp)), keys=('uid', 'type', 'date_str'))
    db.upsert('game_user', uid, values)
    extra = json.loads(db.get('users', uid).get('extra') or '{}')
    if packets.get(28001):
        extra.update(task_newbie_phase=int(packets[28001][0].get('newbie_phase', 1)),
                     task_assignment_phase=int(packets[28001][0].get('assignment_phase', 1)))
    extra_fields = {'used_tag_list': 'profile_tags', 'sticker_show_info': 'sticker_show_info',
        'admitted_suit_reaward_list': 'sticker_suit_rewarded', 'random_info': 'random_info',
        'table_setting': 'pure_mode', 'table_setting_module': 'table_modules', 'info_list': 'profile_like_history',
        'game_icon': 'game_icon'}
    for source, target in extra_fields.items():
        if source in profile:
            extra[target] = deepcopy(profile[source])
    asset_times = {}
    for field, kind in (('icon_list', 'portrait'), ('icon_frame_list', 'icon_frame'),
                        ('information_background_list', 'card_bg'), ('chat_bubble_list', 'bubble'),
                        ('tag_info_list', 'title')):
        asset_times[field] = {}
        for item in profile.get(field, []):
            item_id = int(item['id'])
            db.upsert('player_card', uid, dict(kind=kind, item_id=item_id, obtained=1), keys=('uid', 'kind', 'item_id'))
            asset_times[field][str(item_id)] = {key: int(item[key]) for key in ('lasted_time', 'obtain_time') if key in item}
    extra['profile_asset_times'] = asset_times
    for field, kind in (('all_sticker_list', 'sticker'), ('all_background_list', 'sticker_bg'), ('all_foreground_list', 'sticker_fg')):
        for item_id in profile.get(field, []):
            db.upsert('player_card', uid, dict(kind=kind, item_id=int(item_id), obtained=1), keys=('uid', 'kind', 'item_id'))
    for scene in profile.get('poster_background_list', []):
        db.upsert('user_scene', uid, dict(scene_id=int(scene['id']), lasted_time=int(scene.get('lasted_time', 0)),
            obtain_time=int(scene.get('obtain_time', 0)), update_ts=timestamp), keys=('uid', 'scene_id'))
    sub_backgrounds = (packets.get(32011) or [{}])[0].get('sub_poster_background_list')
    if sub_backgrounds is not None:
        extra['sub_poster_background_list'] = deepcopy(sub_backgrounds)
    db.execute('UPDATE users SET extra=?,sign=?,likes=?,portrait=?,icon_frame=? WHERE uid=?',
        (_json(extra), profile.get('sign', ''), int(profile.get('likes', 0)), int(profile.get('icon', 0)), int(profile.get('icon_frame', 0)), uid))
    for item_id in (packets.get(12039) or [{}])[0].get('unlocked_emoji_list', []):
        db.upsert('chat_sticker', uid, dict(emoji_id=int(item_id)), keys=('uid', 'emoji_id'))
    for kind in (packets.get(13057) or [{}])[0].get('type_list', []):
        db.upsert('ops_common', uid, dict(kind='auto_decompose', item_id=str(kind), value_json=_json(dict(sign=1))),
                  keys=('uid', 'kind', 'item_id'))
    if packets.get(21001):
        db.upsert('user_setting', uid, dict(packets[21001][0]['setting'], update_ts=timestamp))
    for packet in packets.get(14201, []):
        for row in packet.get('player_info_list', []):
            db.upsert('player_skin', uid, dict(player_id=int(row['id']), using_skin=int(row.get('using_skin', 0)), update_ts=timestamp))
            for skin in row.get('unlocked_skin', []):
                db.upsert('player_skin_unlocked', uid, dict(skin_id=int(skin['skin_id']), unlock_ts=int(skin.get('time', 0)), update_ts=timestamp),
                          keys=('uid', 'skin_id'))
    for row in (packets.get(14501) or [{}])[0].get('hero_oath', []):
        hero = int(row['hero_id'])
        db.upsert('hero_oath', uid, {key: row[key] for key in ('hero_id', 'oath', 'oath_level', 'nick', 'picture_link', 'oath_time') if key in row},
                  keys=('uid', 'hero_id'))
        for index, text_id in enumerate(row.get('oath_plot', {}).get('text_list', [])):
            db.upsert('hero_oath_plot', uid, dict(hero_id=hero, plot_idx=index, text_id=int(text_id)), keys=('uid', 'hero_id', 'plot_idx'))
        for index, stamp in enumerate(row.get('time_list', [])):
            db.upsert('hero_oath_time', uid, dict(hero_id=hero, time_idx=index, oath_time=int(stamp)), keys=('uid', 'hero_id', 'time_idx'))
    for row in (packets.get(14503) or [{}])[0].get('assignment_list', []):
        db.upsert('oath_assignment', uid, dict(assignment_id=int(row['id']), progress=int(row.get('progress', 0)),
            complete_flag=int(row.get('complete_flag', 0))), keys=('uid', 'assignment_id'))
    if packets.get(14503):
        db.upsert('oath_assignment_meta', uid, dict(send_type=int(packets[14503][0].get('send_type', 0))))


def _restore_collections(db, packets, uid, timestamp):
    from capture_import import _json

    for field, state in (('client_finished_red_dot', 0), ('red_dot', 1)):
        for item_id in (packets.get(56001) or [{}])[0].get(field, []):
            db.set_red_dot(uid, int(item_id), state)
    for story in (packets.get(12001) or [{}])[0].get('story_list', []):
        db.upsert('story_unlock', uid, dict(story_id=int(story), unlock_flag=1), keys=('uid', 'story_id'))
    for command, kind in ((12011, 'base'), (12111, 'weak')):
        for guide in (packets.get(command) or [{}])[0].get('mod_guide_list', []):
            if kind == 'weak' and db.get('guide', uid, 'AND guide_id=?', (int(guide),)):
                continue
            db.upsert('guide', uid, dict(guide_id=int(guide), kind=kind), keys=('uid', 'guide_id'))
    chips = (packets.get(50001) or [{}])[0]
    for field, category in (('unlock_kernel_chip', 'kernel'), ('unlock_secondary_chip', 'secondary'),
                            ('unlock_hero_chip', 'hero'), ('unlock_reviser_chip', 'reviser')):
        for chip_id in chips.get(field, []):
            from chip_service import ChipService, CHIP_UNLOCK_CFG
            cfg = CHIP_UNLOCK_CFG['chips'].get(str(chip_id))
            if cfg is None:
                raise ValueError(f'芯片 {chip_id} 缺少本地配置')
            ChipService(db)._store_unlocked_chip(db, uid, int(chip_id), cfg, category)
    for row in chips.get('hero_chip_state', []):
        db.execute('UPDATE hero SET chip_state=? WHERE uid=? AND id=?', (_json({str(index): value for index, value in enumerate(row['secondary'], 1)}), uid, int(row['hero_id'])))
    collection = (packets.get(52001) or [{}])[0]
    for field, kind, key in (('enemy_info', 'enemy', 'id'), ('servant_info', 'servant', 'id'),
        ('equip_info', 'equip', 'suit'), ('plot_info', 'plot', 'id'), ('inbetweening_info', 'inbetweening', 'id'), ('affix_info', 'affix', 'id')):
        for row in collection.get(field, []):
            values = dict(kind=kind, item_id=int(row[key]), complete_flag=1)
            values.update({name: int(row[name]) for name in ('times', 'is_view', 'is_receive', 'progress', 'complete_flag') if name in row})
            if 'pos_list' in row:
                values['pos_list_json'] = _json(row['pos_list'])
            db.upsert('illustrated', uid, values, keys=('uid', 'kind', 'item_id'))
    for row in (packets.get(53001) or [{}])[0].get('achievement_list', []):
        db.upsert('achievement', uid, dict(achievement_id=int(row['id']), progress=int(row['progress']),
            complete_flag=int(row['complete_flag']), achieve_time=int(row['achieve_time'])), keys=('uid', 'achievement_id'))
    extra = json.loads(db.get('users', uid).get('extra') or '{}')
    if packets.get(53001):
        extra['achievement_story_read'] = packets[53001][0].get('story_line', [])
    if packets.get(12111):
        extra['weak_guide_ids'] = packets[12111][0].get('mod_guide_list', [])
    db.execute('UPDATE users SET extra=? WHERE uid=?', (_json(extra), uid))
    if packets.get(52021):
        db.upsert('loading_set', uid, dict(id_list=_json(packets[52021][0].get('id_list', []))))
    for row in (packets.get(52025) or [{}])[0].get('hero_race_collect', []):
        db.upsert('hero_race_collect', uid, dict(race_type=int(row['race_type']), received_cnt_list=_json(row['cnt_list'])),
                  keys=('uid', 'race_type'))


def _restore_entitlements(db, packets, uid, timestamp):
    from capture_import import _json
    from lazy_timer import get_daily_5am_ts

    for command, table in ((34023, 'month_card'), (34101, 'big_month_card'), (34031, 'battlepass')):
        if packets.get(command):
            row = deepcopy(packets[command][0])
            for key, value in row.items():
                if isinstance(value, list):
                    row[key] = _json(value)
            db.upsert(table, uid, dict(row, update_ts=timestamp))
    if packets.get(34023) or packets.get(34101):
        from paid_entitlement_service import _save
        _save(db, uid, dict(initialized=True, small_claim_day=get_daily_5am_ts(timestamp) if
            (packets.get(34023) or [{}])[0].get('is_sign') else 0,
            big_claim_day=get_daily_5am_ts(timestamp) if (packets.get(34101) or [{}])[0].get('is_sign') else 0))
    if packets.get(34007):
        row = packets[34007][0]
        db.upsert('user_recharge', uid, dict(total_recharge_num=int(row['total_recharge_num']),
            time_limit_recharge_num=int(row['time_limit_recharge_num']), total_recharge_version=int(row['total_recharge_version']),
            time_limit_version=int(row['now_time_limit_version']), claimed_total_bonus=_json(row.get('receive_total_recharge_list', [])),
            claimed_limit_bonus=_json(row.get('receive_time_limit_recharge_list', [])), update_ts=timestamp))
    if packets.get(11013):
        row = packets[11013][0]
        db.upsert('sign', uid, dict(activity_id=3, year=row['year'], month=row['month'], day=row['day'],
            sign_list=_json(row.get('sign_list', [])), sign_count=len(row.get('sign_list', [])), last_sign_ts=timestamp), keys=('uid', 'activity_id'))
    for row in packets.get(11015, []):
        db.upsert('sign', uid, dict(activity_id=row['activity_id'], sign_count=row['sign_count'], last_sign_ts=row['last_sign_time']),
                  keys=('uid', 'activity_id'))
    if packets.get(17027):
        row = packets[17027][0]
        db.upsert('accumulate_sign', uid, dict(version=row['version'], open_sign=int(row['open_sign']), login_days=row['login_days']))
        for reward in row.get('award_ids', []):
            db.upsert('accumulate_sign_award', uid, dict(award_id=int(reward)), keys=('uid', 'award_id'))
    if packets.get(17033):
        row = packets[17033][0]
        db.upsert('accumulate_sign_discount', uid, dict(version=row['version'], cumulative_buy_card_num=row['cumulative_buy_card_num']))
        for bp_id in row.get('cumulative_buy_battlepass_list', []):
            db.upsert('accumulate_sign_bp', uid, dict(bp_id=int(bp_id)), keys=('uid', 'bp_id'))


def _restore_backhome(db, packets, uid, timestamp):
    from capture_import import _json

    row = (packets.get(58001) or [{}])[0]
    if not row:
        return
    for canteen in row.get('canteens', []):
        db.upsert('backhome_canteen_meta', uid, dict(canteen_id=canteen['id'], accruing_earnings=canteen['accruing_earnings'],
            last_receive_earnings_time=timestamp, update_ts=timestamp), keys=('uid', 'canteen_id'))
        for item in canteen.get('entrust', []):
            values = dict(pos=item['pos'], task_id=item['id'], hero_list=','.join(map(str, item.get('hero_list', []))), update_ts=timestamp)
            values.update({key: item[key] for key in ('num_max', 'refresh_times', 'start_time', 'duration') if key in item})
            db.upsert('backhome_canteen_entrust', uid, values, keys=('uid', 'pos'))
            db.upsert('ops_common', uid, dict(kind='canteen_entrust', item_id=str(item['pos']),
                value_json=_json(dict(task_id=item['id'], hero_list=item.get('hero_list', []), tags=item.get('tags', [])))),
                keys=('uid', 'kind', 'item_id'))
        for item in canteen.get('signature_dish', []):
            db.upsert('backhome_canteen_dish', uid, dict(item, update_ts=timestamp), keys=('uid', 'food_id'))
        for item in canteen.get('careers', []):
            db.upsert('backhome_canteen_career', uid, dict(ctype=item['type'], hero_id=item['hero_id'], update_ts=timestamp), keys=('uid', 'ctype'))
    for item in row.get('canteen_furnitures', []):
        db.upsert('backhome_canteen_furniture', uid, dict(entity_id=item['uid'], type_id=941000 + int(item['uid']), level=item['level'], update_ts=timestamp),
                  keys=('uid', 'entity_id'))
    skins = {int(item['hero_id']): int(item['skin_id']) for item in row.get('hero_setting', [])}
    for item in row.get('backhome_hero', []):
        db.upsert('backhome_hero', uid, dict(item, skin_id=skins.get(int(item['hero_id']), 0), update_ts=timestamp), keys=('uid', 'archives_id'))
    for item in row.get('dorm', []):
        values = {key: item[key] for key in ('pos_id', 'exp', 'liked_num') if key in item}
        db.upsert('backhome_dorm', uid, dict(values, dorm_id=item['id'], update_ts=timestamp), keys=('uid', 'dorm_id'))
        for hero_id in item.get('archives_id', []):
            db.upsert('backhome_dorm_hero', uid, dict(dorm_id=item['id'], hero_id=hero_id, update_ts=timestamp), keys=('uid', 'dorm_id', 'hero_id'))
        for gift in item.get('give_furnitures', []):
            db.upsert('backhome_dorm_gift', uid, dict(dorm_id=item['id'], hero_id=0, furniture_id=gift['id'], num=gift['num'], update_ts=timestamp),
                      keys=('uid', 'dorm_id', 'furniture_id'))
    for item in row.get('ingredients', []):
        db.upsert('backhome_ingredient', uid, dict(item_id=item['id'], num=item['num'], update_ts=timestamp), keys=('uid', 'item_id'))
    for item in row.get('furnitures', []):
        db.upsert('backhome_furniture', uid, dict(item, update_ts=timestamp), keys=('uid', 'furniture_id'))
    for suit_id in row.get('backhome_suit_id_list', []):
        db.upsert('backhome_suit', uid, dict(suit_id=suit_id, update_ts=timestamp), keys=('uid', 'suit_id'))
    db.upsert('backhome_meta', uid, {key: int(row[key]) for key in ('last_fatigue_update_time', 'exhibition_id', 'share_is_open', 'received_be_visited_gift_num') if key in row})
    extra = json.loads(db.get('users', uid).get('extra') or '{}')
    extra['backhome_daily_game_currency_num'] = int(row.get('daily_game_currency_num', 0))
    db.execute('UPDATE users SET extra=? WHERE uid=?', (_json(extra), uid))
    for item in (packets.get(58063) or [{}])[0].get('content_list', []):
        for index, param in enumerate(item.get('content_params', [])):
            db.upsert('dorm_information', uid, dict(info_id=item['id'], param_idx=index, param=param), keys=('uid', 'info_id', 'param_idx'))


def _restore_progress(db, packets, uid, timestamp):
    from capture_import import _json
    from stage_service import EQUIP_GROUP_FIRST_STAGE
    if 43001 in packets and not _equip_dungeon_gap(packets, timestamp):
        packet = packets[43001][0]
        first = EQUIP_GROUP_FIRST_STAGE[packet['stage_base_id']]
        for item in packet['insure_list']:
            db.upsert('battle_equip', uid, dict(stage_id=first + item['difficulty'] - 1,
                insure_times=item['insure_times'], suit_id=packet['equip_suit_id'],
                next_refresh_time=packet['next_refresh_time']), keys=('uid', 'stage_id'))
    for packet in packets.get(25009, []):
        for row in packet.get('daily_battle_list', []):
            db.upsert('chapter', uid, dict(id=row['id'], star_list=_json(row.get('star_list', [])), clear_times=row.get('clear_times', 0)), keys=('uid', 'id'))
    teaching = (packets.get(47001) or [{}])[0].get('base_stage_list', [])
    for hero in (packets.get(47003) or [{}])[0].get('hero_teaching_list', []):
        teaching = teaching + hero.get('stage_list', [])
    for row in teaching:
        db.upsert('chapter', uid, dict(id=row['id'], clear_times=row.get('clear_times', 0), star_list='[]'), keys=('uid', 'id'))


def _restore_games(db, packets, uid, timestamp):
    from capture_import import _json

    if packets.get(83026):
        from sphero_leisure_service import read, save
        from lazy_timer import get_daily_5am_ts
        row = packets[83026][0]
        state = read(db, uid)
        state.update(day=get_daily_5am_ts(timestamp), coins=int(row.get('reward_record', 0)),
                     tickets=int(row.get('ticket_record', 0)))
        save(db, uid, state)
    if packets.get(24051):
        row = packets[24051][0]
        db.upsert('skuld_progress', uid, dict(activity_id=row['activity_id'], client_opt_list=_json(row.get('client_opt', [])),
            mission_json=_json(row.get('mission_list', [])), reward_list=_json(row.get('reward_list', [])), point=row['point'], update_ts=timestamp),
            keys=('uid', 'activity_id'))
    for row in (packets.get(68171) or [{}])[0].get('pass_stages', []):
        db.upsert('osiris_stage_progress', uid, dict(stage_id=row['stage_id'], score=row['pass_time'], settle=row['point'], update_ts=timestamp),
            keys=('uid', 'stage_id'))
    for chapter_id in (packets.get(68171) or [{}])[0].get('pass_chapters', []):
        db.upsert('osiris_chapter_progress', uid, dict(chapter_no=chapter_id, value=chapter_id, update_ts=timestamp), keys=('uid', 'chapter_no'))
    for row in (packets.get(68181) or [{}])[0].get('pass_stages', []):
        db.upsert('ash_shoot_stage', uid, dict(stage_id=row['stage_id'], point=row['point'], update_ts=timestamp), keys=('uid', 'stage_id'))
    if packets.get(89401):
        row = packets[89401][0]
        from pinball_service import save
        save(db, dict(uid=uid, stage_count=row['hai_la_level'], cleared_stage_list=row.get('stage_list', []),
            unlock_skill_list=row.get('skills', []), equip_skill_list=row.get('select_active_skills', []), score=row['challenge_score']))
    if packets.get(84331):
        row = packets[84331][0]
        from kadas_race_service import save
        save(db, dict(uid=uid, tank_id=row['tank_id'], mission_list=row.get('mission_list', []), tank_info=row.get('tank_info', []),
            round=row.get('challenge_stage_info', {}).get('round', 0), max_score=row.get('challenge_stage_info', {}).get('max_score', -1)))
    if packets.get(89701):
        from vehicle_ball_service import save
        save(db, uid, packets[89701][0])
    if packets.get(89011):
        row = packets[89011][0]
        from summer_pub_service import save
        save(db, uid, dict(stage_list=row.get('stage_list', []), battle_stages=row.get('battle_stage_list', []), time_state=row['time_state'],
            cook_stages={str(item['stage_id']): item['state'] for item in row.get('cook_stage_list', [])},
            illustrated={str(item['illustrated_id']): item['view_state'] for item in row.get('illustrated', [])}))
    for row in (packets.get(61047) or [{}])[0].get('challenge_info', []):
        db.upsert('resident_music_record', uid, dict(music_id=row['id'], score=row['score'], sign=row['sign'], is_rewarded=None, update_ts=timestamp),
            keys=('uid', 'music_id'))
    for row in (packets.get(83124) or [{}])[0].get('rhythm_stage_list', []):
        db.upsert('rhythm_game_progress', uid, dict(stage_id=row['id'], star_id_list=_json(row.get('star_id_list', [])),
            use_seconds=row['use_seconds'], update_ts=timestamp), keys=('uid', 'stage_id'))
    for story in (packets.get(83124) or [{}])[0].get('story_id_list', []):
        db.upsert('rhythm_story_record', uid, dict(story_id=story, update_ts=timestamp), keys=('uid', 'story_id'))
    if packets.get(89601):
        row = packets[89601][0]; story = row['story']; challenge = row['challenge']
        record = {key: int(story.get(key, 0)) for key in ('thread_id', 'thread_state', 'battle_id')}
        record.update({key: _json(story.get(key, [])) for key in ('finish_thread_list', 'like_thread_list', 'post_thread_list', 'view_thread_list')})
        record.update({f'challenge_{key}': int(challenge.get(source, 0)) for key, source in
            (('deck', 'deck'), ('diff', 'diff'), ('state', 'state'), ('battle_id', 'battle_id'))})
        record['challenge_status_list'] = _json(challenge.get('status_list', []))
        record.update({key: _json(row.get(key, [])) for key in ('gather_card_list', 'gather_enhance_list', 'gather_weal_woe_list')})
        db.upsert('rogue_card_game_record', uid, dict(record, update_ts=timestamp))


def team_protocol_state(payload):
    """Read the actual team wire schema; the archived codec schema predates it."""
    from formation_codec import _iter_fields, _required_varint

    teams = []; formations = []
    for field, wire, multi in _iter_fields(payload):
        if field not in (1, 4) or wire != 2:
            raise ValueError('编队包含未审核的顶层字段')
        team_type = _required_varint(multi, 1, 'team_type')
        if field == 4:
            contents = {_required_varint(v, 1, 'cont_id'): v for k, w, v in _iter_fields(multi) if k == 2 and w == 2}
            names = {_required_varint(v, 1, 'cont_id'): v for k, w, v in _iter_fields(multi) if k == 3 and w == 2}
            if contents.keys() != names.keys():
                raise ValueError('编队方案与名称的关卡 ID 不一致')
            formations.extend(dict(team_type=team_type, cont_id=cid, cont_team=body.hex(), data_rec=names[cid].hex()) for cid, body in contents.items())
            continue
        for key, kind, content in _iter_fields(multi):
            if key != 2 or kind != 2:
                continue
            cont_id = _required_varint(content, 1, 'cont_id')
            for key2, kind2, body in _iter_fields(content):
                if key2 != 2 or kind2 != 2:
                    continue
                team = dict(team_type=team_type, cont_id=cont_id, team_index=_required_varint(body, 1, 'team_index'),
                    heroes=[], cooperate_skill=0, mimir_id=0, mimir_hero_id=0, chips=[], hero_chips=[])
                for number, w, value in _iter_fields(body):
                    if number == 2 and w == 2:
                        fields = {f: v for f, wt, v in _iter_fields(value) if wt == 0}
                        team['heroes'].append(dict(slot=len(team['heroes']) + 1, hero_id=fields.get(1, 0), owner_id=fields.get(2, 0), hero_type=fields.get(3, 1)))
                    elif number == 3 and w == 0:
                        team['cooperate_skill'] = value
                    elif number == 4 and w == 2:
                        for f, wt, v in _iter_fields(value):
                            if wt != 0:
                                raise ValueError('管理喵编队包含未审核的字段类型')
                            if f == 1: team['mimir_id'] = v
                            elif f == 2: team['chips'].append(v)
                            elif f == 3: team['mimir_hero_id'] = v
                            elif f == 4: team['hero_chips'].append(v)
                    elif number != 1:
                        raise ValueError('编队包含未审核的队伍字段')
                teams.append(team)
    return dict(teams=teams, formations=formations)


def _restore_exploration(db, packets, uid, timestamp):
    from capture_import import _json

    for archive_id in (packets.get(24043) or [{}])[0].get('plot_list', []):
        db.upsert('stage_archive_collect', uid, dict(archive_id=int(archive_id)), keys=('uid', 'archive_id'))
    if packets.get(24029):
        row = packets[24029][0]
        scans = set(); clues = {}; events = set(); days = []; map_clues = {}
        for item in row.get('map_info', []):
            scans.update(item.get('scan_location_list', [])); events.update(item.get('event_list', []))
            map_clues[str(item['map_id'])] = sorted(set(item.get('clue_list', [])))
            for clue in item.get('clue_location_list', []):
                clues[str(clue['location_id'])] = clue['clue_id']
        for day in row.get('detector_info', []):
            if day['status'] == 1: days.append(day['day'])
            elif day['status'] != 0: raise ValueError('未审核的第 19 章探测器状态')
        from chapter19_service import service
        detectors = [dict(chapter_id=int(item['chapter_id']), day=int(item['day']), status=int(item['status']))
                     for item in row.get('detector_info', [])]
        service._save(db, uid, dict(scans=sorted(scans), clues=clues, events=sorted(events), days=days,
                                    detectors=detectors, map_clues=map_clues))
        service._load(db, uid)
    if packets.get(24061):
        row = packets[24061][0]
        from chapter_v2_map_service import service
        reads = [i for i in row.get('event_list', []) if i in service.events and service.events[i]['type'] == 3]
        db.upsert('chapter_v2_map_state', uid, dict(now_location=row['now_location'], read_events_json=_json(reads)))
    for row in (packets.get(28801) or [{}])[0].get('quest_list', []):
        db.upsert('qworld_quest', uid, dict(main_quest_id=row['id'], status=row['status'], expired_ts=row.get('expired_timestamp', 0), update_ts=timestamp),
            keys=('uid', 'main_quest_id'))
        for task in row.get('task_list', []):
            db.upsert('qworld_quest_task', uid, dict(main_quest_id=row['id'], task_id=task['id'], status=task['status'], progress=task['progress'], update_ts=timestamp),
                keys=('uid', 'main_quest_id', 'task_id'))
    if packets.get(28837):
        from quanzhou_quest import KIND, ACTIVITY
        db.upsert('ops_common', uid, dict(kind=KIND, item_id=str(ACTIVITY), value_json=_json(packets[28837][0].get('sys_id_list', []))),
            keys=('uid', 'kind', 'item_id'))
    if packets.get(79601):
        from quanzhou_service import save
        positions = packets[79601][0].get('stage_list', [])
        if len(positions) > 1: raise ValueError('箱庭存在多个当前位置')
        save(db, uid, dict(version=1, position=positions[0] if positions else None, latest=None))
    if packets.get(86035):
        from quanzhou_collection import save
        row = packets[86035][0]['data']
        save(db, uid, dict(version=1, completed=row.get('stage_id_list', []), skills=row.get('affix', [])))
    for row in (packets.get(49001) or [{}])[0].get('chess_map_list', []):
        db.upsert('warchess_map', uid, dict(activity_id=row['activity_id'], current_chapter=row['chapter']), keys=('uid', 'activity_id'))
        for chapter in row.get('chapter_info', []):
            for box in chapter.get('box', []):
                db.upsert('warchess_box', uid, dict(chapter_id=chapter['chapter_id'], box_id=box['id'], num=box['num']),
                    keys=('uid', 'chapter_id', 'box_id'))


def _restore_communications(db, packets, uid, timestamp):
    from capture_import import _json

    for item in (packets.get(30017) or [{}])[0].get('letter_list', []):
        db.upsert('letter_special', uid, dict(letter_id=item['id'], is_viewed=int(item['is_viewed']), update_ts=timestamp), keys=('uid', 'letter_id'))
    for item in (packets.get(73001) or [{}])[0].get('info', {}).get('skill_list', []):
        db.upsert('combo_skill_state', uid, dict(skill_id=item['id'], level=item['level'],
            progress_json=_json({str(progress['id']): progress['times'] for progress in item.get('progress_list', [])}), update_ts=timestamp),
            keys=('uid', 'skill_id'))
    from trust_service import TrustService
    trust = TrustService.get_instance()
    for row in (packets.get(73005) or [{}])[0].get('limit_list', []):
        db.upsert('trust_displace_counter', uid, dict(item_id=int(row['item_id']),
            day_key=trust._displace_day_key(timestamp), use=int(row.get('use', 0))), keys=('uid', 'item_id', 'day_key'))
    for row in (packets.get(12023) or [{}])[0].get('reward', []):
        db.upsert('unclaimed', uid, dict(unclaimed_id=int(row['id']), stage=int(row.get('stage', 0)),
            update_ts=timestamp), keys=('uid', 'unclaimed_id'))
    for story_id in (packets.get(73007) or [{}])[0].get('got_reward_id_list', []):
        if story_id not in trust.current_relation_stories:
            raise ValueError(f'关系剧情奖励 {story_id} 缺少目录')
        db.execute("INSERT INTO claim_ledger(uid,kind,key_id,claim_ts) VALUES(?,'relation_story',?,?)", (uid, story_id, timestamp))
    for notice in (packets.get(12119) or [{}])[0].get('momotalk_list', []):
        db.execute("INSERT INTO claim_ledger(uid,kind,key_id,claim_ts) VALUES(?,'ash_momotalk_notice',?,?)", (uid, notice, timestamp))
    row = (packets.get(91001) or [{}])[0]
    if 'icon' in row:
        db.upsert('game_user', uid, dict(cur_momotalk_frame=row['icon']))
    for group in row.get('type_hero', []):
        if group['type'] != 1: raise ValueError('MomoTalk 对话分类尚未映射')
        for hero in group.get('hero_session', []):
            for session in hero.get('session_list', []):
                db.upsert('momotalk_session', uid, dict(session_id=session['id'], hero_id=hero['sender_id'],
                    send_time=session['send_time'], is_view=session.get('is_view', 0), current_content_id=session.get('current_content_id', 0),
                    save_list=_json(session.get('save_list', [])), update_ts=timestamp), keys=('uid', 'hero_id', 'session_id'))


def _restore_activities(db, packets, uid, timestamp):
    """Restore activity-owned snapshots that have direct existing consumers."""
    from capture_import import _json
    from new_player_service import enabled

    fresh_save = enabled(db, uid)

    for packet in packets.get(11001, []):
        for row in packet.get('activity_list', []):
            db.upsert('activity', uid, dict(
                activity_id=int(row['activity_id']),
                name=str(row.get('name', '')),
                start_time=int(row.get('start_time', 0)),
                stop_time=int(row.get('stop_time', 0)),
                state=int(row.get('state', 0)),
                theme=int(row.get('theme', 0)),
                template=int(row.get('template', 0)),
                sub_activity_id_list=_json(row.get('sub_activity_id_list', [])),
                update_ts=timestamp), keys=('uid', 'activity_id'))

    if packets.get(18001):
        row = packets[18001][0]
        activity_id = int(row['activity_id'])
        version_activity = db.get_system_config('capture.polyhedron_activity_id')
        if not version_activity:
            import res_version_manager
            version_activity = res_version_manager.get_version_config(
                db.get_system_config('capture.resource_version') or None
            )['polyhedron_activity_id']
        if activity_id != int(version_activity):
            raise ValueError('sc_18001 活动 ID 与当前资源版本不一致')
        game = row.get('game') or {}
        terminal = row.get('terminal') or {}
        decision = row.get('decision') or {}
        db.upsert('polyhedron_meta', uid, dict(
            activity_id=activity_id,
            game_state=int(game.get('state', 0)),
            reset_times=int(terminal.get('reset_times', 0)),
            already_challenge_times=int(row.get('already_challenge_times', 0)),
            is_new=int(row.get('is_new', 0)),
            update_ts=timestamp), keys=('uid', 'activity_id'))
        for terminal_id in terminal.get('upgrade_id_list', []):
            db.upsert('polyhedron_terminal', uid, dict(
                terminal_id=int(terminal_id), update_ts=timestamp),
                keys=('uid', 'terminal_id'))
        for beacon_id in row.get('beacon_id_list', []):
            db.upsert('polyhedron_beacon', uid, dict(
                beacon_id=int(beacon_id), update_ts=timestamp),
                keys=('uid', 'beacon_id'))
        for hero in row.get('unlocked_hero_list', []):
            astrolabes = [int(value) for value in hero.get('astrolabe_id_list', [])]
            if len(astrolabes) > 3:
                raise ValueError('sc_18001 星盘列表超过三个槽位')
            astrolabes += [0] * (3 - len(astrolabes))
            db.upsert('polyhedron_hero', uid, dict(
                hero_id=int(hero['hero_id']),
                astrolabe_1=astrolabes[0],
                astrolabe_2=astrolabes[1],
                astrolabe_3=astrolabes[2],
                update_ts=timestamp), keys=('uid', 'hero_id'))
        for difficulty_id in row.get('clear_difficulty_list', []):
            db.upsert('polyhedron_difficulty', uid, dict(
                difficulty_id=int(difficulty_id), update_ts=timestamp),
                keys=('uid', 'difficulty_id'))
        for sample in (row.get('manual') or {}).get('sample_list', []):
            db.upsert('polyhedron_artifact', uid, dict(
                artifact_id=int(sample['id']),
                state=int(sample.get('state', 0)),
                update_ts=timestamp), keys=('uid', 'artifact_id'))
        for level in decision.get('apply_id_list', []):
            db.upsert('polyhedron_policy_claimed', uid, dict(
                activity_id=activity_id, level=int(level), update_ts=timestamp),
                keys=('uid', 'activity_id', 'level'))

    if packets.get(35011):
        row = packets[35011][0]
        affix = row.get('affix_info') or {}
        db.upsert('equip_seizure_progress', uid, dict(
            stage_id=int(row['stage_id']),
            challenge_rate=float(row['challenge_rate']),
            affix_id_list=_json(affix.get('affix_id_list', [])),
            affix_refresh_ts=int(affix.get('refresh_timestamp', 0)),
            today_max_score=int(row.get('today_max_score', 0)),
            sum_score=int(row.get('sum_score', 0)),
            refresh_ts=int(row.get('refresh_timestamp', 0)),
            got_reward_id_list=_json(row.get('got_reward_id_list', [])),
            update_ts=timestamp))

    if not fresh_save and (
            packets.get(44007) or packets.get(44019) or packets.get(44023)):
        rotation = (packets.get(44007) or [{}])[0]
        public = (packets.get(44019) or [{}])[0]
        final = (packets.get(44023) or [{}])[0]
        difficulty = public.get('difficulty')
        if difficulty is None:
            difficulty = final.get('now_difficulty')
        if difficulty is None:
            difficulty = 0
        db.upsert('mythic_public', uid, dict(
            current_difficulty=int(difficulty),
            is_new_difficulty=int(bool(public.get(
                'is_new_difficulty', final.get('is_new_difficulty', False)))),
            next_refresh_ts=int(rotation.get('next_refresh_timestamp', 0)),
            recommend_team_1=int((rotation.get('recommend_team') or [0])[0]),
            recommend_team_2=int((rotation.get('recommend_team') or [0, 0])[1]),
            update_ts=timestamp))
        for difficulty_id in public.get('open_difficulty_list', []):
            db.upsert('mythic_difficulty', uid, dict(
                difficulty_id=int(difficulty_id), is_open=1, update_ts=timestamp),
                keys=('uid', 'difficulty_id'))
        for difficulty_row in rotation.get('difficulty_list', []):
            difficulty_id = int(difficulty_row['difficulty'])
            main = difficulty_row.get('main_partition') or {}
            if main:
                db.upsert('mythic_partition', uid, dict(
                    difficulty=difficulty_id,
                    partition_id=int(main['partition']),
                    stage_id=int(main['stage_id']),
                    kind='main', update_ts=timestamp),
                    keys=('uid', 'difficulty', 'partition_id'))
            for sub in difficulty_row.get('sub_partition_list', []):
                db.upsert('mythic_partition', uid, dict(
                    difficulty=difficulty_id,
                    partition_id=int(sub['partition']),
                    stage_id=int(sub['stage_id']),
                    kind='sub', update_ts=timestamp),
                    keys=('uid', 'difficulty', 'partition_id'))
        for source, kind in (('superiority_affix_list', 'advantage'),
                             ('inferiority_affix_list', 'inferiority'),
                             ('mythic_ultimate_affix_list', 'ultimate')):
            for affix in rotation.get(source, []):
                db.upsert('mythic_affix', uid, dict(
                    affix_kind=kind,
                    affix_id=int(affix['id']),
                    level=int(affix.get('level', 0)),
                    aff_type=int(affix.get('type', 0)),
                    update_ts=timestamp),
                    keys=('uid', 'affix_kind', 'affix_id'))
        if final:
            db.upsert('mythic_final_progress', uid, dict(
                now_difficulty=int(final.get('now_difficulty', 0)),
                can_choose_list=_json(final.get('difficulty_id_can_choose', [])),
                receive_reward_list=_json(final.get('receive_reward', [])),
                clear_list=_json(final.get('clear_list', [])),
                challenge_info_json=_json(final.get('challenge_info', [])),
                is_new_difficulty=int(bool(final.get('is_new_difficulty', False))),
                update_ts=timestamp))

    if not fresh_save and packets.get(45201):
        row = packets[45201][0]
        db.upsert('boss_challenge_progress', uid, dict(
            mode=int(row.get('mode', 0)),
            next_refresh_time=int(row.get('next_refresh_time', 0)),
            difficulty_list=_json(row.get('difficulty_list', [])),
            update_ts=timestamp))

    if not fresh_save and packets.get(48001):
        system = packets[48001][0].get('matrix_system') or {}
        heroes = system.get('ready_hero_list', [])
        db.upsert('matrix_system', uid, dict(
            ready_hero_ids=_json([int(row['hero_standard_id']) for row in heroes]),
            ready_hero_skins=_json([int(row.get('skin_id', 0)) for row in heroes]),
            ready_hero_json=_json(heroes),
            difficulty_json=_json(system.get('difficulty_list', [])),
            next_refresh_ts=int(system.get('next_refresh_timestamp', 0))))

    if not fresh_save and packets.get(48003):
        user = packets[48003][0].get('user_matrix') or {}
        terminal = user.get('terminal') or {}
        rewards = user.get('point_reward_list', [])
        db.upsert('matrix_user', uid, dict(
            game_state=int(user.get('game_state', 0)),
            current_progress_json=_json(user.get('current_progress', {})),
            terminal_json=_json(terminal),
            beacon_json=_json(user.get('unlocked_beacon_id_list', [])),
            point_reward_got=_json([
                int(row['rank']) for row in rewards
                if int(row.get('is_got_reward', 0))]),
            update_ts=timestamp))

    if not fresh_save and packets.get(55001):
        row = packets[55001][0]
        activity_id = int(row['activity_id'])
        db.upsert('abyss', uid, dict(
            activity_id=activity_id,
            is_back=int(bool(row.get('is_back', False))),
            history_max_layer=int(row.get('history_max_layer', 0)),
            layer_reset_time=int(row.get('layer_reset_time', 0)),
            stage_reset_time=int(row.get('stage_reset_time', 0)),
            last_version_max_unlock_layer=int(
                row.get('last_version_max_unlock_layer', 0)),
            refresh_timestamp=int(row.get('refresh_timestamp', 0)),
            update_ts=timestamp), keys=('uid', 'activity_id'))
        for layer in row.get('layer_info_list', []):
            layer_id = int(layer['layer_id'])
            for source in ('stage_info_list', 'boss_stage_info_list'):
                for stage in layer.get(source, []):
                    db.upsert('abyss_layer_stage', uid, dict(
                        layer_id=layer_id,
                        stage_id=int(stage['stage_id']),
                        is_completed=int(bool(stage.get('is_completed', False))),
                        update_ts=timestamp),
                        keys=('uid', 'layer_id', 'stage_id'))
        for reward_id in row.get('got_reward_id_list', []):
            db.upsert('abyss_reward', uid, dict(
                reward_id=int(reward_id), update_ts=timestamp),
                keys=('uid', 'reward_id'))

    if not fresh_save and packets.get(59001):
        row = packets[59001][0]
        sign = row.get('newbie_sign') or {}
        level_reward = row.get('newbie_level_reward') or {}
        recharge = row.get('newbie_recharge_reward') or {}
        first = recharge.get('first_recharge_reward') or {}
        monthly = recharge.get('first_monthly_card_reward') or {}
        battlepass = recharge.get('first_battlepass_reward') or {}
        completed = int(row.get('is_completed', 0))
        db.upsert('newbie_activity', uid, dict(
            completed_time=completed,
            now_sign_times=int(sign.get('now_sign_times', 0)),
            last_sign_ts=int(sign.get('last_sign_timestamp', 0)),
            fr_first_gear=int(first.get('first_gear_recharge_reward', 0)),
            fr_second_gear=int(bool(first.get('second_gear_recharge_flag', False))),
            fr_now_sign=int(first.get('now_sign_times', 0)),
            fr_last_sign_ts=int(first.get('last_sign_timestamp', 0)),
            fr_new6=int(bool(first.get('is_new_recharge_6', False))),
            fr_new18=int(bool(first.get('is_new_recharge_18', False))),
            mc_flag=int(bool(monthly.get('flag', False))),
            mc_role_flag=int(bool(monthly.get('role_reward_flag', False))),
            mc_sign_times=int(monthly.get('sign_times', 0)),
            mc_sign_reward=int(bool(monthly.get('sign_reward_flag', False))),
            mc_new_role=int(bool(monthly.get('is_new_tag_role_reward', False))),
            mc_new_sign=int(bool(monthly.get('is_new_tag_sign_reward', False))),
            bp_reward=int(battlepass.get('first_battlepass_reward', 0)),
            bp_new=int(bool(battlepass.get('is_new_battlepass_reward', False))),
            trigger_time=int(row.get('trigger_time', 0)),
            update_ts=timestamp))
        for level in level_reward.get('received_level_list', []):
            db.upsert('newbie_level_reward', uid, dict(
                level=int(level), update_ts=timestamp), keys=('uid', 'level'))

    if not fresh_save and packets.get(62019):
        row = packets[62019][0]
        db.upsert('regression', uid, dict(
            other_sign=int(bool(row.get('other_sign', False))),
            draw_over_sign=int(bool(row.get('draw_over_sign', False))),
            update_ts=timestamp))

    for packet in packets.get(64031, []):
        activity_id = int(packet['activity_id'])
        for refresh_time in packet.get('refresh_time', []):
            db.upsert('activity_refresh_time', uid, dict(
                activity_id=activity_id,
                refresh_time=int(refresh_time),
                update_ts=timestamp),
                keys=('uid', 'activity_id', 'refresh_time'))

    if packets.get(67001):
        from lazy_timer import get_weekly_mon_5am_ts
        row = packets[67001][0]
        db.save_admin_cat_explore_data(uid, dict(
            weekly_time=row.get('weekly_time', 0),
            daily_time=row.get('daily_time', 0),
            weekly_reward_state=row.get('weekly_reward_state', 0),
            weekly_scene_open=row.get('weekly_scene_open', 0),
            total_explore_c=row.get('total_explore_c', 0),
            last_weekly_reset_ts=get_weekly_mon_5am_ts(timestamp)))
        for cat in row.get('mimir', []):
            skills = cat.get('skill') or []
            if len(skills) != 1:
                raise ValueError('sc_67001 猫咪技能必须恰有一条')
            db.unlock_admin_cat(uid, int(cat['mimir_id']),
                                int(skills[0].get('skill_level', 1)))
        for queue in row.get('explore_queue', []):
            db.save_admin_cat_queue(
                uid, int(queue['area_id']), int(queue['mimir_id']),
                int(queue.get('start_time', 0)), int(queue.get('stop_time', 0)),
                int(queue.get('target_explore_hour', 0)),
                queue.get('explore_event', []))

    if packets.get(83021):
        stages = [int(stage) for stage in
                  packets[83021][0].get('stage_completed_list', [])]
        db.upsert('sp_hero_puzzle_progress', uid, dict(
            activity_id=242871, cleared_stage_list=_json(stages),
            update_ts=timestamp), keys=('uid', 'activity_id'))

    if packets.get(85101):
        for point_id in packets[85101][0].get('reward_list', []):
            db.upsert('summer_chess_point', uid, dict(
                point_id=int(point_id), update_ts=timestamp),
                keys=('uid', 'point_id'))

    for packet in packets.get(86037, []):
        activity_id = int(packet['activity_id'])
        db.upsert('activity_point', uid, dict(
            activity_id=activity_id, point=int(packet.get('point', 0)),
            update_ts=timestamp), keys=('uid', 'activity_id'))
        for reward_id in packet.get('reward_list', []):
            db.upsert('activity_point_reward', uid, dict(
                activity_id=activity_id, reward_id=int(reward_id),
                update_ts=timestamp),
                keys=('uid', 'activity_id', 'reward_id'))

    for badge in (packets.get(89021) or [{}])[0].get('illustrated', []):
        db.upsert('core_verification_cl_badge_unlocked', uid, dict(
            badge_id=int(badge['illustrated_id']),
            unlock_ts=int(badge.get('time', 0))),
            keys=('uid', 'badge_id'))


def _restore_idol(db, packets, uid, timestamp):
    from capture_import import _json

    overview = (packets.get(58169) or [{}])[0]
    if overview:
        attack = overview.get('attack_hero_id_list') or [0]
        defend = overview.get('defend_hero_id_list') or [0]
        if len(attack) != 1 or len(defend) != 1:
            raise ValueError('sc_58169 攻守阵容必须各有一个英雄')
        exercise = overview.get('exercise_times_info') or {}
        pvp = overview.get('pvp_stage_info') or {}
        db.upsert('idol_trainee', uid, dict(
            attack_hero_id=int(attack[0]),
            defend_hero_id=int(defend[0]),
            exercise_use_times=int(exercise.get('use_times', 0)),
            camp_list=','.join(str(int(value))
                               for value in exercise.get('camp_list', [])),
            pvp_stage_id=int(pvp.get('stage_id', 0)),
            pvp_refresh_ts=int(pvp.get('refresh_timestamp', 0)),
            update_ts=timestamp))
        for hero in overview.get('hero_list', []):
            attrs = [int(value) for value in hero.get('attribute_list', [])]
            if len(attrs) != 5:
                raise ValueError('sc_58169 角色属性必须恰有五个值')
            db.upsert('idol_trainee_hero', uid, dict(
                hero_id=int(hero['hero_id']),
                attr1=attrs[0], attr2=attrs[1], attr3=attrs[2],
                attr4=attrs[3], attr5=attrs[4], update_ts=timestamp),
                keys=('uid', 'hero_id'))
        for pos in overview.get('hero_pos_list', []):
            db.upsert('idol_trainee_pos', uid, dict(
                pos=int(pos['pos']), hero_id=int(pos['hero_id']),
                update_ts=timestamp), keys=('uid', 'pos'))

    pvp = ((packets.get(58173) or [{}])[0].get('pvp_stage_info') or {})
    if pvp:
        db.upsert('idol_pvp_stage', uid, dict(
            stage_id=int(pvp.get('stage_id', 0)),
            refresh_timestamp=int(pvp.get('refresh_timestamp', 0)),
            update_ts=timestamp))

    for chapter in (packets.get(58189) or [{}])[0].get('chapter_list', []):
        chapter_id = int(chapter['chapter_id'])
        for stage in chapter.get('stage_list', []):
            db.upsert('idol_trainee_pve', uid, dict(
                chapter_id=chapter_id, stage_id=int(stage['stage_id']),
                score=int(stage.get('score', 0)),
                is_clear=int(bool(stage.get('is_clear', False))),
                update_ts=timestamp),
                keys=('uid', 'chapter_id', 'stage_id'))

    rank = (packets.get(58191) or [{}])[0]
    if rank:
        db.upsert('idol_trainee_rank', uid, dict(
            weekly_point=int(rank.get('point', 0)), update_ts=timestamp))
        for rank_id in rank.get('get_id_list', []):
            db.upsert('idol_trainee_rank_got', uid, dict(
                rank_id=int(rank_id), update_ts=timestamp),
                keys=('uid', 'rank_id'))

    for sequence in (packets.get(58195) or [{}])[0].get('sequence_list', []):
        base = sequence.get('base_sequence') or {}
        actions = [int(value) for value in base.get('action_id_list', [])]
        db.upsert('dance_diy', uid, dict(
            pos=int(sequence['pos']),
            scene_id=int(base.get('scene_id', 0)),
            music_id=int(base.get('music_id', 0)),
            action_list=','.join(str(value) for value in actions),
            update_ts=timestamp), keys=('uid', 'pos'))

    for collection in (packets.get(58203) or [{}])[0].get('collection_list', []):
        viewed = [int(value) for value in collection.get('viewed_id_list', [])]
        db.upsert('idol_dance_collection', uid, dict(
            collect_type=int(collection['type']),
            viewed_id_list=','.join(str(value) for value in viewed),
            update_ts=timestamp), keys=('uid', 'collect_type'))


def _restore_rogueteam(db, packets, uid, timestamp):
    """Restore durable RogueTeam data and an active run only when evidence supports it."""
    from capture_import import _json

    fetters = (packets.get(88315) or [{}])[0]
    if fetters:
        fetters_state = dict(
            activity_id=int(fetters['activity_id']),
            next_timestamps=int(fetters['next_timestamps']),
            fetters_id=int(fetters['fetters_id']))
        db.upsert(
            'ops_common',
            uid,
            dict(kind='capture_rogueteam_fetters', item_id='100001',
                 value_json=_json(fetters_state)),
            keys=('uid', 'kind', 'item_id'))
    outside = (packets.get(88305) or [{}])[0]
    template_id = int(outside.get('template_id', 100001))
    expected_collections = []
    if outside:
        db.upsert('rogueteam_user', uid, dict(
            template_id=template_id,
            difficult=int(outside.get('difficult', 0)),
            max_difficult=max([int(row.get('key', 0))
                               for row in outside.get('his_difficult', [])] or [1]),
            last_score_id=int(outside.get('last_id', 0)),
            update_ts=timestamp), keys=('uid', 'template_id'))
        for node_id in outside.get('tree_list', []):
            db.upsert('rogueteam_tree', uid, dict(
                template_id=template_id, node_id=int(node_id),
                unlock_ts=timestamp),
                keys=('uid', 'template_id', 'node_id'))
        viewed = {int(value) for value in outside.get('view_collection', [])}
        for collection in outside.get('collection_list', []):
            item_type = int(collection['type'])
            expected_collections.append(dict(type=item_type,
                                             item_list=[int(value) for value in collection.get('item_list', [])]))
            for item_id in expected_collections[-1]['item_list']:
                db.upsert('rogueteam_illustrated', uid, dict(
                    template_id=template_id, item_id=int(item_id),
                    item_type=item_type,
                    is_viewed=int(int(item_id) in viewed),
                    unlock_ts=timestamp),
                    keys=('uid', 'template_id', 'item_id'))
        db.upsert('rogueteam_history', uid, dict(
            template_id=template_id,
            diff_clear_json=_json(outside.get('his_difficult', [])),
            ending_pass_json=_json(outside.get('his_avg', [])),
            update_ts=timestamp), keys=('uid', 'template_id'))

    points = (packets.get(88309) or [{}])[0]
    if points:
        point_template = int(points.get('template_id', template_id))
        db.upsert('rogueteam_user', uid, dict(
            template_id=point_template,
            point=int(points.get('point', 0)),
            rewarded_list_json=_json(points.get('reward_list', [])),
            update_ts=timestamp), keys=('uid', 'template_id'))

    session = (packets.get(88001) or [{}])[0]
    if session:
        session_template = int(session.get('template_id', template_id))
        attrs = (packets.get(88013) or [{}])[0].get('attr_list', [])
        heroes = (packets.get(88019) or [{}])[0].get('hero_list', [])
        db.upsert('rogueteam_session', uid, dict(
            template_id=session_template,
            difficult=int((outside or {}).get('difficult', 1)),
            floor_num=int(session.get('floor_num', 1)),
            floor_state=int(session.get('floor_state', 0)),
            select_node_id=int(session.get('select_node_id', 0)),
            map_info_json=_json(session.get('map_info', [])),
            treasure_list_json=_json(session.get('treasure_list', [])),
            other_item_list_json=_json(session.get('other_item_list', [])),
            effect_list_json=_json(session.get('effect_list', [])),
            hero_list_json=_json(heroes),
            attr_list_json=_json(attrs),
            affix_list_json=_json(session.get('affix_list', [])),
            other_info_json=_json(session.get('other_info', {})),
            shop_info_json=_json(session.get('shop_info', {})),
            in_game=1,
            update_ts=timestamp),
            keys=('uid', 'template_id'))
        db.upsert('ops_common', uid, dict(
            kind='capture_rogueteam_collection',
            item_id=str(session_template),
            value_json=_json(expected_collections)),
            keys=('uid', 'kind', 'item_id'))


def _restore_admin_cat(db, packets, uid, timestamp):
    """Restore Mimir exploration through the existing persistence API."""
    # The payload is handled together with the activities table so its main row,
    # cat skills and queues are committed through the same consumer methods.
    if packets.get(67001):
        from admin_cat_explore_service import AdminCatExploreService
        projected = AdminCatExploreService.get_instance().generate_sc_67001_dict(db, uid)
        if not projected.get('mimir') and not projected.get('explore_queue'):
            raise ValueError('管理员猫咪状态恢复后无法回读')


def _restore_autochess(db, packets, uid, timestamp):
    """Restore autochess collection, stages and the exact session snapshot."""
    from capture_import import _json

    for row in (packets.get(89201) or [{}])[0].get('stage_list', []):
        db.upsert('autochess_stage', uid, dict(
            stage_id=int(row['id']), clear_time=int(row.get('time', 0))),
            keys=('uid', 'stage_id'))
    for row in (packets.get(89201) or [{}])[0].get('medal', []):
        db.upsert('autochess_medal', uid, dict(
            medal_id=int(row['id']), level=int(row.get('level', 1)),
            unlock_time=int(row.get('unlock_time', 0)),
            upgrade_time=int(row.get('upgrade_time', 0))),
            keys=('uid', 'medal_id'))

    if packets.get(90051):
        row = packets[90051][0]
        for sequence, card in enumerate(row.get('card_list', [])):
            db.upsert('autochess_card', uid, dict(
                card_id=int(card['id']), num=int(card.get('num', 0)),
                seq=sequence, update_ts=timestamp), keys=('uid', 'card_id'))
        db.upsert('autochess_meta', uid, dict(
            rank_score=int(row.get('rank_score', 0)),
            energy=int(row.get('energy', 0)),
            sunglasses=int(row.get('sunglasses', 0)),
            update_ts=timestamp))

    board = (packets.get(89101) or [{}])[0]
    state = (packets.get(89125) or [{}])[0]
    if board and int(state.get('state', 0)) != 0:
        info = board.get('auto_chessboard_info') or {}
        base = {int(row['key']): row for row in info.get('base_info_list', [])}
        board_chess = []
        bench_chess = []
        for row in info.get('chess_list', []):
            attrs = {int(item['key']): int(item.get('value', 0))
                     for item in row.get('chess_attr_list', [])}
            piece = dict(
                unique_id=int(row['unique_id']), chess_id=int(row['chess_id']),
                index=int(row.get('index', 0)), atk=attrs.get(1, 0),
                hp=attrs.get(2, 0), exp=attrs.get(3, 0),
                buff_list=row.get('buff_list', []))
            (board_chess if piece['index'] > 0 else bench_chess).append(piece)
        db.upsert('autochess_session', uid, dict(
            game_type=int(board.get('game_type', 0)),
            state=int((state or {}).get('state', 0)),
            stage_id=int(base.get(5, {}).get('value', 0)),
            round=int(base.get(4, {}).get('value', 1)),
            gold=int(base.get(2, {}).get('value', 10)),
            hp=int(base.get(1, {}).get('value', 100)),
            win_count=int(base.get(3, {}).get('value', 0)),
            defeat_count=0,
            shop_level=int(base.get(9, {}).get('value', 1)),
            chess_board_json=_json(board_chess),
            bench_chess_json=_json(bench_chess),
            shop_items_json=_json(board.get('shop_items', [])),
            buff_list_json=_json(board.get('buff_list', [])),
            update_ts=timestamp))


def _restore_teams(db, payload, uid):
    from capture_import import _json
    from formation_codec import _pb_message, _pb_varint, save_formation

    state = team_protocol_state(payload)
    for formation in state['formations']:
        save_formation(db, uid, _pb_varint(1, formation['team_type']) +
            _pb_message(2, bytes.fromhex(formation['cont_team'])) + _pb_message(3, bytes.fromhex(formation['data_rec'])))
    for team in state['teams']:
        keys = {key: team[key] for key in ('team_type', 'cont_id', 'team_index')}
        chips = ','.join(map(str, team['chips'])); hero_chips = ','.join(map(str, team['hero_chips']))
        db.upsert('reserve_team', uid, dict(keys, cooperate_skill=team['cooperate_skill'], mimir_id=team['mimir_id'],
            chip_ids=chips, hero_chip_ids=hero_chips), keys=('uid', 'team_type', 'cont_id', 'team_index'))
        for hero in team['heroes']:
            db.upsert('reserve_team_hero', uid, dict(keys, **hero), keys=('uid', 'team_type', 'cont_id', 'team_index', 'slot'))
        db.upsert('stage_team', uid, dict(stage_type=team['team_type'], activity_id=team['cont_id'], team_index=team['team_index'],
            hero_json=_json([hero['hero_id'] for hero in team['heroes']]), cooperate_skill=team['cooperate_skill'], mimir_id=team['mimir_id'],
            mimir_chips=chips, hero_chips=hero_chips), keys=('uid', 'stage_type', 'activity_id', 'team_index'))
        db.upsert('ops_common', uid, dict(kind='stage_team_mimir', item_id=f"{team['team_type']}:{team['cont_id']}:{team['team_index']}",
            value_json=_json(dict(hero_id=team['mimir_hero_id']))), keys=('uid', 'kind', 'item_id'))


def account_protocol_state(command, packets):
    """Compare account-owned state, preserving source field presence."""
    from capture_import import _wire_state

    values = deepcopy(packets)
    set_fields = {'client_opt', 'battle_stage_list', 'stage_list', 'stages', 'skills', 'mission_list',
                  'pass_chapters', 'reward_list', 'finish_thread_list', 'view_thread_list',
                  'gather_card_list', 'gather_enhance_list', 'gather_weal_woe_list',
                  'momotalk_list', 'got_reward_id_list', 'sys_id_list', 'event_list',
                  'stage_id_list', 'affix', 'beacon_id_list', 'get_id_list',
                  'stage_completed_list', 'clear_difficulty_list', 'upgrade_id_list'}
    def order_sets(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in set_fields and isinstance(item, list) and all(isinstance(v, int) for v in item):
                    item.sort()
                else:
                    order_sets(item)
        elif isinstance(value, list):
            for item in value:
                order_sets(item)
    order_sets(values)
    if command == 13009:
        from enchant_slots_util import normalize_enchant_slots
        for row in values:
            for equip in row.get('equip_list', []):
                equip['enchant_slot_list'] = normalize_enchant_slots(equip.get('enchant_slot_list'))
    if command == 15009:
        for row in values:
            row.pop('last_fatigue_recover_time', None)
    if command == 12023:
        values = [dict(reward=row.get('reward', [])) for row in values]
    if command == 73005:
        values = [dict(limit_list=[item for item in row.get('limit_list', []) if item.get('use')]) for row in values]
    if command in (24043, 56001):
        for row in values:
            for field in ('plot_list', 'red_dot', 'client_finished_red_dot'):
                if field in row:
                    row[field].sort()
    if command == 24009:
        values = [dict(user_chapter_list=[item for row in values for item in row.get('user_chapter_list', [])
            if item.get('clear_times') or any(item.get('star_list', []))])]
    if command == 24017:
        values = [dict(claimed=[dict(chapter_id=row['id'], reward_order=reward['reward_order'])
            for packet in values for row in packet.get('gain_list', []) for reward in row.get('reward_list', []) if reward.get('is_received')])]
    if command == 20009:
        import res_version_manager
        excluded = set(res_version_manager.get_version_config().get('deprecated_shops', []))
        return _wire_state(dict(purchases=[dict(shop_id=shop['shop_id'], **goods) for packet in values
            for shop in packet.get('shop_item_list', []) if shop['shop_id'] not in excluded
            for goods in shop.get('goods_list', []) if goods.get('buy_times')],
            daily=[shop for packet in values for shop in packet.get('shop_item_list', []) if shop['shop_id'] == 2]))
    if command == 32009:
        for row in values:
            for field in ('all_sticker_list', 'all_background_list', 'all_foreground_list'):
                if field in row:
                    row[field].sort()
    if command == 34031:
        import res_version_manager
        from paid_entitlement_service import project_battlepass_claims
        target = res_version_manager.get_version_config()['battlepass_list_id']
        for row in values:
            row['receive_info'] = project_battlepass_claims(row.get('receive_info', []), row['battlepass_list_id'], target)
            row['battlepass_list_id'] = target
            for field in ('start_timestamp', 'end_timestamp', 'next_refresh_timestamp'):
                row.pop(field, None)
    if command == 52001:
        for row in values:
            row.pop('intelligence_reward', None)
            row['affix_info'] = [item for item in row.get('affix_info', []) if item.get('is_view')]
    if command == 58001:
        for row in values:
            row['backhome_suit_id_list'] = sorted(row.get('backhome_suit_id_list', []))
            for dorm in row.get('dorm', []):
                if not dorm.get('archives_id'):
                    dorm.pop('archives_id', None)
                if not dorm.get('give_furnitures'):
                    dorm.pop('give_furnitures', None)
                if 'archives_id' in dorm:
                    dorm['archives_id'].sort()
    if command == 25009:
        records = {}
        for row in values:
            for item in row.get('daily_battle_list', []):
                prior = records.get(item['id'])
                if prior is not None and prior != item:
                    raise ValueError('资源关卡重复快照冲突')
                records[item['id']] = item
        values = [dict(daily_battle_list=list(records.values()))]
    if command == 61047:
        for row in values:
            row['challenge_info'] = [item for item in row.get('challenge_info', []) if item.get('score') or item.get('sign')]
    if command == 47003:
        values = [dict(hero_teaching_list=[dict(row, stage_list=[stage for stage in row.get('stage_list', []) if stage.get('clear_times')])
            for packet in values for row in packet.get('hero_teaching_list', []) if any(stage.get('clear_times') for stage in row.get('stage_list', []))])]
    if command == 28801:
        for row in values:
            row['quest_list'] = [dict(quest, task_list=sorted(quest.get('task_list', []), key=lambda item: item['id']))
                                 for quest in sorted(row.get('quest_list', []), key=lambda item: item['id'])]
    if command == 24029:
        for row in values:
            for item in row.get('map_info', []):
                item['clue_list'] = sorted(item.get('clue_list', []))
    if command in (12001, 12011, 12111, 12039, 13057, 17027, 50001, 52021):
        for row in values:
            if command == 12039:
                row.pop('emoticon_id_list', None)
            for key, items in row.items():
                if isinstance(items, list) and all(isinstance(item, int) for item in items):
                    row[key] = sorted(items)
    if command == 11001:
        for row in values:
            row['activity_list'] = []
    if command in (44007, 44019, 44023, 55001, 59001):
        values = [{}]
    if command == 64031:
        for row in values:
            row['refresh_time'] = sorted(row.get('refresh_time', []))
    if command == 35011:
        # The live consumer rotates the daily stage and affix at capture time.
        # Keep those account values in the source payload and database evidence;
        # the replay compares only the persisted scores and reward state.
        values = [{}]
    if command == 88001:
        for row in values:
            row.pop('other_info', None)
            row.pop('shop_info', None)
            row.setdefault('second_map_info', [])
            row.setdefault('affix_list', [])
            row.setdefault('plot_id', 0)
            row.setdefault('template_id', 100001)
    if command == 88019:
        for row in values:
            row.pop('modify_type', None)
    if command == 88305:
        for row in values:
            row['collection_list'] = []
            row['tree_list'] = sorted(row.get('tree_list', []))
    return _wire_state(values)
