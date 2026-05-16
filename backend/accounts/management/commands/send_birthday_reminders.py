"""Gửi email nhắc sinh nhật (trước 1 ngày). Đặt cron: 0 0,7,14,21,23 * * * cd ... && python manage.py send_birthday_reminders"""

from django.core.management.base import BaseCommand

from accounts.birthday_reminder import send_birthday_reminder_emails


class Command(BaseCommand):
    help = "Gửi email nhắc sinh nhật cho khách có sinh nhật vào ngày mai (theo TIME_ZONE)."

    def handle(self, *args, **options):
        explain: list[str] = []
        sent, skipped = send_birthday_reminder_emails(explain=explain)
        # ASCII-only: tránh UnicodeEncodeError trên Windows (cp1252) khi in ra console
        msg = f"Birthday reminders: sent={sent}, skipped_or_errors={skipped}."
        self.stdout.write(self.style.SUCCESS(msg))
        for line in explain:
            self.stdout.write(line)
