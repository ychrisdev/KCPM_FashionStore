# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_profile_birth_date_reminder'),
        ('orders', '0014_order_updated_at_alter_order_inventory_deducted_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BirthdayEmailTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'email_subject',
                    models.CharField(
                        default='[FashionStore] Sinh nhật của bạn — quà tri ân từ cửa hàng',
                        max_length=200,
                    ),
                ),
                (
                    'intro_text',
                    models.TextField(
                        default=(
                            'Ngày mai là sinh nhật của bạn — FashionStore xin gửi lời chúc '
                            'sức khỏe và niềm vui!'
                        ),
                    ),
                ),
                ('cta_button_label', models.CharField(default='Vào FashionStore', max_length=80)),
                (
                    'footer_text',
                    models.TextField(
                        blank=True,
                        default='Thư tự động — vui lòng không trả lời trực tiếp email này.',
                    ),
                ),
                (
                    'discount_code',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='+',
                        to='orders.discountcode',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Mẫu email sinh nhật',
            },
        ),
    ]
