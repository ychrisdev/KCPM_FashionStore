from django.apps import AppConfig
import os
import sys

class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        import accounts.signals

        # Khi chạy 'manage.py runserver', Django tạo 2 log (1 process watcher, 1 worker).
        # Đoạn này bảo vệ: chỉ cho phép bật đồng hồ ở process Worker (RUN_MAIN='true').
        # Bỏ qua nếu đang chạy lệnh shell / migrate.
        if 'runserver' not in sys.argv:
            pass # Vẫn cho phép chạy (vd trên Gunicorn production), nhưng ở runserver thì xét kỹ dưới đây
        elif os.environ.get('RUN_MAIN', None) != 'true':
            return

        from apscheduler.schedulers.background import BackgroundScheduler
        from accounts.birthday_reminder import send_birthday_reminder_emails

        # Khởi tạo đồng hồ ngầm, ép chạy theo múi giờ chuẩn VN (Tuyệt đối không bị trôi giờ theo Server/UTC)
        scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")

        # Lập lịch chạy cho hàm gửi quà sinh nhật (0:00, 7:00, 14:00, 21:00, 23:00)
        scheduler.add_job(
            send_birthday_reminder_emails,
            trigger='cron',
            hour='0,7,14,21,23',
            id='birthday_email_cron',
            max_instances=1,
            replace_existing=True
        )

        scheduler.start()
