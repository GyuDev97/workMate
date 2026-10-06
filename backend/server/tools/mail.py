from datetime import datetime, timedelta, timezone

from server.models.schemas import MailSummary


class MailTool:
    name = "mail"
    description = "Search and summarize mail. V0.1 uses mock Bizmeka data."

    def important_mail(self) -> list[MailSummary]:
        now = datetime.now(timezone.utc)
        return [
            MailSummary(id="mail-kim", sender="김대리", subject="RAG 테스트 결과 검토 부탁드립니다", received_at=now - timedelta(hours=2), needs_reply=True, preview="검토 의견을 오늘 오후까지 공유해 주실 수 있을까요?"),
            MailSummary(id="mail-ops", sender="인프라운영팀", subject="금일 서버 점검 안내", received_at=now - timedelta(hours=4), needs_reply=False, preview="13:30부터 예정된 정기 점검 범위를 확인해 주세요."),
        ]

    def execute(self, **kwargs: object) -> list[MailSummary]:
        return self.important_mail()

    def unread_mail(self) -> list[MailSummary]:
        return [mail for mail in self.important_mail() if mail.is_unread]

    def search_mail(self, query: str) -> list[MailSummary]:
        needle = query.lower().strip()
        return [mail for mail in self.important_mail() if not needle or needle in f"{mail.sender} {mail.subject} {mail.preview}".lower()]

    def get_mail(self, identifier: str) -> MailSummary | dict[str, str]:
        for mail in self.important_mail():
            if identifier in (mail.id, mail.sender) or identifier.lower() in mail.subject.lower(): return mail
        return {"error": "Mail not found"}
