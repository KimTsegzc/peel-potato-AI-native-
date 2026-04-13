import unittest
from pathlib import Path

from Backend.integrations import email_sender


class EmailSenderFooterTests(unittest.TestCase):
    def test_append_agent_footer_adds_footer_with_spacing(self):
        body = "测试正文"

        result = email_sender._append_agent_footer(body)

        self.assertEqual(
            result,
            "测试正文\n\n——本邮件为AI agent发出（来源xiexin1.gd）",
        )

    def test_normalize_receiver_input_supports_multiple_receivers(self):
        result = email_sender._normalize_receiver_input("a@example.com, b@example.com；c@example.com")

        self.assertEqual(
            result,
            ["a@example.com", "b@example.com", "c@example.com"],
        )

    def test_append_agent_footer_does_not_duplicate_existing_footer(self):
        body = "测试正文\n\n——本邮件为AI agent发出（来源xiexin1.gd）\n"

        result = email_sender._append_agent_footer(body)

        self.assertEqual(
            result,
            "测试正文\n\n——本邮件为AI agent发出（来源xiexin1.gd）",
        )

    def test_build_message_attaches_file_with_original_filename(self):
        temp_file = Path(__file__).resolve().parent / "_temp_体检单.txt"
        temp_file.write_text("hello", encoding="utf-8")
        try:
            message = email_sender._build_message(
                sender="sender@example.com",
                receiver="a@example.com",
                subject="测试",
                body="正文",
                attachments=[str(temp_file)],
            )

            serialized = message.as_string()

            self.assertIn("multipart/mixed", serialized)
            self.assertIn("Content-Disposition: attachment;", serialized)
        finally:
            temp_file.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()