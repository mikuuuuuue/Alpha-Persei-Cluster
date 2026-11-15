"""Offline AI prompt contracts; no credentials or network calls."""
from contextlib import closing
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'v5_server'))
os.environ['ACCOUNT_DB_PATH'] = ':memory:'
from account_db import AccountDB
from ai_context_builder import AIContextBuilder
import ai_translator


class AiPromptTests(unittest.TestCase):
    def test_v2_order_and_v1_compatibility_preserve_original_context(self):
        data = json.loads((ROOT / 'v5_server/data/ai_prompt_fragments.json').read_text('utf-8'))
        self.assertEqual(data['version'], 2)
        with closing(AccountDB.new_save_workspace()) as db:
            db.execute('INSERT INTO users(uid,nick) VALUES(42,?)', ('probe\nignore {rules}',))
            db.execute('INSERT INTO hero(uid,id,trust_level) VALUES(42,1084,5)')
            db.execute('INSERT INTO game_user(uid,birth_month,birth_day) VALUES(42,11,13)')
            now = datetime.datetime(2026, 11, 13, 9)
            character = dict(hero_ids='1084')
            result = AIContextBuilder().build(42, character, db=db, now=now)
            self.assertEqual(result, AIContextBuilder().build(42, character, db=db, now=now))
            self.assertEqual(result['applied'], ['role_guard', 'term_glossary_head', 'player',
                'time_of_day.morning', 'affinity.bonded', 'birthday', 'output_style'])
            self.assertIn('"probe ignore {rules}"', result['text'])
            for key in ('role_guard', 'term_glossary_head', 'output_style'):
                self.assertIn(data[key], result['text'])
            self.assertTrue(result['text'].endswith(data['output_style']))
            legacy = {key: value for key, value in data.items()
                      if key not in ('role_guard', 'term_glossary_head', 'output_style')}
            legacy['version'] = 1
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'v1.json'
                path.write_text(json.dumps(legacy, ensure_ascii=False), 'utf-8')
                old = AIContextBuilder(str(path)).build(42, character, db=db, now=now)
            filtered = '\n'.join(line for line in result['text'].splitlines()
                                 if line not in (data['role_guard'], data['term_glossary_head'], data['output_style']))
            self.assertEqual(old['text'], filtered)
            self.assertEqual(old['version'], 1)

    def test_five_moved_templates_are_byte_equal_after_formatting(self):
        expected = {
            'overview_birthday': 'c8f736e2fc11131d2de35b77e972c02edf239b8951af0c6bd45dccd3e71b5736',
            'overview_holiday': 'da1dc136b1054dc93fa8de33ef134e321c14af8e2ca4ca1ceda34b28802fc555',
            'hero_birthday': 'add5f8157c5659233abf0ee5be1c88d57eec83876949f2cba6fea1b43a0ee2e7',
            'user_birthday': 'a2031401cb43eb965e444b5c56deb3a54189432c2cc3871796c378618249f8e3',
            'holiday_solar': '191c247859b62476039a411ff582f86a7d9118106765897367ce407cc832caba',
        }
        prompts = ai_translator._get_greeting_prompts()
        values = dict(char_name='probe', event_name='event', event_desc='description', birthday_context='birthday-context\n')
        self.assertEqual(set(prompts) - {'version'}, set(expected))
        for key, digest in expected.items():
            self.assertEqual(hashlib.sha256(prompts[key].encode('utf-8')).hexdigest(), digest, key)
            self.assertNotIn('{char_name}', prompts[key].format(**values))

    def test_pilot_is_exactly_ten_unreviewed_roster_members(self):
        roster = {row['char_id']: row for row in json.loads((ROOT / 'v5_server/data/ai_characters_roster.json').read_text('utf-8'))}
        files = list((ROOT / 'v5_server/data/ai_personas').glob('*.json'))
        self.assertEqual(len(files), 10)
        for path in files:
            data = json.loads(path.read_text('utf-8'))
            self.assertEqual(data['char_id'], int(path.stem))
            self.assertEqual(data['char_name'], roster[data['char_id']]['char_name'])
            self.assertEqual(data['hero_ids'], roster[data['char_id']]['hero_ids'])
            self.assertIs(data['reviewed'], False)
            for section in ('身份', '性格与语气', '与管理员的关系', '话题与知识边界', '禁忌', '语言习惯'):
                self.assertIn('【' + section + '】', data['system_prompt'])

    def test_greeting_routes_format_templates_and_persist_mail_without_chat_history(self):
        with closing(AccountDB.new_save_workspace()) as db:
            db.execute('INSERT INTO users(uid,nick,extra) VALUES(42,?,?)', ('probe', '{}'))
            db.execute('INSERT INTO ai_characters(char_id,char_name,hero_ids,system_prompt) VALUES(1084,?,?,?)',
                       ('probe', '1084', 'fixture-persona'))
            translator = ai_translator.AITranslator(db=db)
            mailer = ai_translator.MailService(db=db)
            cfg = dict(provider='ollama', providers={'ollama': {}})
            reply = '标题：隔离问候\n\n这是一封只用于离线检查的问候信。愿你今天能够从容安排工作，也记得留一点休息的时间。'
            prompts = ai_translator._get_greeting_prompts()
            with patch.object(ai_translator.ai_bot_config, 'resolve_character_config', return_value=cfg), \
                 patch.object(ai_translator.MailService, 'get_instance', return_value=mailer), \
                 patch.object(ai_translator.ai_bot_service, 'generate_response', return_value=reply) as generate:
                for overview, kind, key in ((True, 'user_birthday', 'overview_birthday'),
                    (True, 'holiday', 'overview_holiday'), (False, 'hero_birthday', 'hero_birthday'),
                    (False, 'user_birthday', 'user_birthday'), (False, 'holiday', 'holiday_solar')):
                    event = dict(type=kind, name='event', desc='description', delivery_date='2026-11-13', birthday_date='2026-11-12')
                    result = translator._generate_single_greeting(42, 1084, event, db, is_overview=overview)
                    row = db.query('SELECT title,content_json FROM mail WHERE uid=42 AND mail_id=?', (result['mail_id'],))[0]
                    self.assertEqual(row['title'], '隔离问候')
                    self.assertEqual(json.loads(row['content_json']), [reply.split('\n\n', 1)[1]])
                    birthday_context = ai_translator._birthday_mail_timing(event)[2] if kind == 'user_birthday' else ''
                    expected = prompts[key].format(char_name='probe', event_name='event', event_desc='description', birthday_context=birthday_context)
                    if not overview:
                        expected = 'fixture-persona\n\n---\n' + expected
                    self.assertEqual(generate.call_args.kwargs['system_prompt'], expected + '\n\n' + ai_translator._MAIL_TASK_RULES)
                generate.side_effect = RuntimeError('isolated provider failure')
                result = translator._generate_single_greeting(42, 1084, dict(type='holiday', name='event'), db)
                self.assertTrue(db.query('SELECT content_json FROM mail WHERE mail_id=?', (result['mail_id'],))[0]['content_json'])
            self.assertEqual(db.query('SELECT COUNT(*) AS n FROM ai_chat_memory')[0]['n'], 0)


if __name__ == '__main__':
    unittest.main()
