import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Backend.runtime.contracts import AgentRequest


_pending_module = importlib.import_module("Backend.runtime.skills.skill_send_email.pending_confirmation")
_router_module = importlib.import_module("Backend.runtime.router")
_skill_module = importlib.import_module("Backend.runtime.skills.skill_send_email.skill")
SendEmailSkill = _skill_module.SendEmailSkill


class SendEmailConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_pending_root = _pending_module._PENDING_ROOT
        self.original_shared_space_dir = _skill_module._SHARED_SPACE_DIR
        _pending_module._PENDING_ROOT = Path(self.temp_dir.name) / "pending_email_confirmation"
        _skill_module._SHARED_SPACE_DIR = Path(self.temp_dir.name) / "shared_space"
        _skill_module._SHARED_SPACE_DIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        _pending_module._PENDING_ROOT = self.original_pending_root
        _skill_module._SHARED_SPACE_DIR = self.original_shared_space_dir
        self.temp_dir.cleanup()

    def _expected_all_contact_receivers(self) -> list[str]:
        return [item["email"] for item in _skill_module._load_contacts()]

    def test_initial_request_requires_receiver_confirmation(self):
        skill = SendEmailSkill()
        request = AgentRequest(
            user_input="user: 帮我发邮件",
            session_id="session_confirm_1",
            metadata={
                "email": {
                    "receiver": "xiexin1.gd@ccb.com, longjiang.gd@ccb.com",
                    "subject": "测试主题",
                    "body": "这是可以直接发送的测试正文，请两位查收并按需处理。",
                }
            },
        )

        response = skill.run_once(request)

        self.assertIn("我编好内容了，帮我确认一下收件人，我怕打扰到大家~", response.content)
        self.assertIn("收件人：已收录的各位领导同事", response.content)
        self.assertEqual(response.metrics["send_email"]["reason"], "confirmation_pending")
        self.assertTrue(_pending_module.has_pending_email_confirmation("session_confirm_1"))

    def test_confirmation_yes_sends_email_and_clears_pending_state(self):
        skill = SendEmailSkill()
        _pending_module.save_pending_email_confirmation(
            "session_confirm_2",
            {
                "receivers": ["xiexin1.gd@ccb.com", "longjiang.gd@ccb.com"],
                "subject": "测试主题",
                "body": "这是可以直接发送的测试正文，请两位查收并按需处理。",
                "attachments": [],
                "base_metrics": {"llm_adapter_used": False},
            },
        )

        with patch.object(_skill_module.EmailSender, "send_text", return_value={
            "ok": True,
            "receiver": "xiexin1.gd@ccb.com, longjiang.gd@ccb.com",
            "receivers": ["xiexin1.gd@ccb.com", "longjiang.gd@ccb.com"],
            "attachments": [],
            "subject": "测试主题",
            "transport": "ssl",
            "smtp_host": "smtp.qq.com",
            "smtp_port": 465,
        }) as mocked_send:
            response = skill.run_once(AgentRequest(user_input="user: 是", session_id="session_confirm_2"))

        mocked_send.assert_called_once_with(
            subject="测试主题",
            body="这是可以直接发送的测试正文，请两位查收并按需处理。",
            receiver=["xiexin1.gd@ccb.com", "longjiang.gd@ccb.com"],
            attachments=[],
        )
        self.assertIn("邮件已发送。", response.content)
        self.assertFalse(_pending_module.has_pending_email_confirmation("session_confirm_2"))

    def test_confirmation_no_cancels_email_and_clears_pending_state(self):
        skill = SendEmailSkill()
        _pending_module.save_pending_email_confirmation(
            "session_confirm_3",
            {
                "receivers": ["xiexin1.gd@ccb.com"],
                "subject": "测试主题",
                "body": "这是可以直接发送的测试正文，请查收并按需处理。",
                "attachments": [],
                "base_metrics": {"llm_adapter_used": False},
            },
        )

        response = skill.run_once(AgentRequest(user_input="user: 否", session_id="session_confirm_3"))

        self.assertEqual(response.content, "好，这封邮件先不发了，已取消。")
        self.assertEqual(response.metrics["send_email"]["reason"], "user_cancelled")
        self.assertFalse(_pending_module.has_pending_email_confirmation("session_confirm_3"))

    def test_router_treats_pending_confirmation_as_send_email_intent(self):
        _pending_module.save_pending_email_confirmation(
            "session_confirm_4",
            {
                "receivers": ["xiexin1.gd@ccb.com"],
                "subject": "测试主题",
                "body": "这是可以直接发送的测试正文，请查收并按需处理。",
                "attachments": [],
                "base_metrics": {},
            },
        )

        result = _router_module._is_send_email_intent(
            AgentRequest(user_input="user: 是", session_id="session_confirm_4")
        )

        self.assertTrue(result)

    def test_confirmation_shows_shared_space_physical_exam_attachment_name(self):
        attachment_path = _skill_module._SHARED_SPACE_DIR / "uploads" / "session-a" / "20260413" / "abc123_广州直营中心体检单.pdf"
        attachment_path.parent.mkdir(parents=True, exist_ok=True)
        attachment_path.write_bytes(b"pdf")
        skill = SendEmailSkill()
        request = AgentRequest(
            user_input="user: 发邮件，体检单一起发给大家",
            session_id="session_confirm_attachment_1",
            metadata={
                "email": {
                    "receiver": "xiexin1.gd@ccb.com, longjiang.gd@ccb.com",
                    "subject": "体检资料",
                    "body": "这是本次体检资料，请查收。",
                }
            },
        )

        response = skill.run_once(request)

        self.assertIn("收件人：已收录的各位领导同事", response.content)
        self.assertIn("附件：广州直营中心体检单.pdf", response.content)
        pending = _pending_module.load_pending_email_confirmation("session_confirm_attachment_1")
        self.assertEqual(pending["attachments"], [str(attachment_path.resolve())])

    def test_request_metadata_attachments_are_carried_into_email_confirmation(self):
        uploaded_attachment = _skill_module._SHARED_SPACE_DIR / "uploads" / "session-b" / "20260413" / "upload123_广州直营中心体检单.pdf"
        uploaded_attachment.parent.mkdir(parents=True, exist_ok=True)
        uploaded_attachment.write_bytes(b"pdf")
        skill = SendEmailSkill()

        response = skill.run_once(
            AgentRequest(
                user_input="user: 帮我把体检单发给谢鑫",
                session_id="session_confirm_attachment_3",
                metadata={
                    "attachments": [
                        {
                            "name": "广州直营中心体检单.pdf",
                            "original_name": "广州直营中心体检单.pdf",
                            "path": str(uploaded_attachment.resolve()),
                            "storage_scope": "shared_space",
                        }
                    ],
                    "email": {
                        "receiver": "谢鑫",
                        "subject": "体检单",
                        "body": "这是体检单，请查收。",
                    },
                },
            )
        )

        self.assertIn("附件：广州直营中心体检单.pdf", response.content)
        pending = _pending_module.load_pending_email_confirmation("session_confirm_attachment_3")
        self.assertEqual(pending["attachments"], [str(uploaded_attachment.resolve())])

    def test_physical_exam_email_uses_fixed_body_template(self):
        attachment_path = _skill_module._SHARED_SPACE_DIR / "uploads" / "session-c" / "20260413" / "upload456_广州直营中心体检单.pdf"
        attachment_path.parent.mkdir(parents=True, exist_ok=True)
        attachment_path.write_bytes(b"pdf")
        skill = SendEmailSkill()

        response = skill.run_once(
            AgentRequest(
                user_input="user: 帮我把体检单发给谢鑫",
                session_id="session_confirm_attachment_4",
                metadata={
                    "attachments": [
                        {
                            "name": "广州直营中心体检单.pdf",
                            "original_name": "广州直营中心体检单.pdf",
                            "path": str(attachment_path.resolve()),
                            "storage_scope": "shared_space",
                        }
                    ],
                    "email": {
                        "receiver": "谢鑫",
                        "subject": "体检单",
                        "body": "随便写的旧正文",
                    },
                },
            )
        )

        self.assertIn("附件：广州直营中心体检单.pdf", response.content)
        pending = _pending_module.load_pending_email_confirmation("session_confirm_attachment_4")
        self.assertEqual(pending["subject"], _skill_module._PHYSICAL_EXAM_FIXED_SUBJECT)
        self.assertEqual(pending["body"], _skill_module._PHYSICAL_EXAM_FIXED_BODY)

    def test_generic_audience_confirmation_sends_to_all_contacts(self):
        attachment_path = _skill_module._SHARED_SPACE_DIR / "uploads" / "session-d" / "20260413" / "upload789_广州直营中心体检单.pdf"
        attachment_path.parent.mkdir(parents=True, exist_ok=True)
        attachment_path.write_bytes(b"pdf")
        skill = SendEmailSkill()

        first_response = skill.run_once(
            AgentRequest(
                user_input="user: 把体检单发给与会人员",
                session_id="session_confirm_attachment_5",
                metadata={
                    "attachments": [
                        {
                            "name": "广州直营中心体检单.pdf",
                            "original_name": "广州直营中心体检单.pdf",
                            "path": str(attachment_path.resolve()),
                            "storage_scope": "shared_space",
                        }
                    ],
                    "email": {
                        "receiver": "与会人员",
                        "subject": "体检单",
                        "body": "旧正文",
                    },
                },
            )
        )

        self.assertIn("收件人：已收录的各位领导同事", first_response.content)
        pending = _pending_module.load_pending_email_confirmation("session_confirm_attachment_5")
        self.assertEqual(pending["receivers"], self._expected_all_contact_receivers())

        with patch.object(_skill_module.EmailSender, "send_text", return_value={
            "ok": True,
            "receiver": ", ".join(self._expected_all_contact_receivers()),
            "receivers": self._expected_all_contact_receivers(),
            "attachments": [str(attachment_path.resolve())],
            "subject": "体检单",
            "transport": "ssl",
            "smtp_host": "smtp.qq.com",
            "smtp_port": 465,
        }) as mocked_send:
            response = skill.run_once(AgentRequest(user_input="user: 是", session_id="session_confirm_attachment_5"))

        mocked_send.assert_called_once_with(
            subject=_skill_module._PHYSICAL_EXAM_FIXED_SUBJECT,
            body=_skill_module._PHYSICAL_EXAM_FIXED_BODY,
            receiver=self._expected_all_contact_receivers(),
            attachments=[str(attachment_path.resolve())],
        )
        self.assertIn("邮件已发送。", response.content)

    def test_all_generic_audience_aliases_expand_to_all_contacts(self):
        skill = SendEmailSkill()
        expected_receivers = self._expected_all_contact_receivers()
        attachment_path = _skill_module._SHARED_SPACE_DIR / "uploads" / "session-e" / "20260413" / "upload999_广州直营中心体检单.pdf"
        attachment_path.parent.mkdir(parents=True, exist_ok=True)
        attachment_path.write_bytes(b"pdf")

        for index, alias in enumerate(["与会人员", "所有人", "全部联系人"], start=1):
            response = skill.run_once(
                AgentRequest(
                    user_input=f"user: 把体检单发给{alias}",
                    session_id=f"session_confirm_alias_{index}",
                    metadata={
                        "attachments": [
                            {
                                "name": "广州直营中心体检单.pdf",
                                "original_name": "广州直营中心体检单.pdf",
                                "path": str(attachment_path.resolve()),
                                "storage_scope": "shared_space",
                            }
                        ],
                        "email": {
                            "receiver": alias,
                            "subject": "体检单",
                            "body": "旧正文",
                        }
                    },
                )
            )

            self.assertIn("收件人：已收录的各位领导同事", response.content)
            pending = _pending_module.load_pending_email_confirmation(f"session_confirm_alias_{index}")
            self.assertEqual(pending["receivers"], expected_receivers)

    def test_attachment_resolution_failure_blocks_confirmation(self):
        skill = SendEmailSkill()

        response = skill.run_once(
            AgentRequest(
                user_input="user: 把体检单发给大家",
                session_id="session_confirm_attachment_2",
                metadata={
                    "email": {
                        "receiver": "xiexin1.gd@ccb.com",
                        "subject": "体检资料",
                        "body": "这是本次体检资料，请查收。",
                    }
                },
            )
        )

        self.assertEqual(response.metrics["send_email"]["reason"], "attachment_resolution_failed")
        self.assertIn("shared_space 里没有找到名称包含“体检单”的文件", response.content)


if __name__ == "__main__":
    unittest.main()