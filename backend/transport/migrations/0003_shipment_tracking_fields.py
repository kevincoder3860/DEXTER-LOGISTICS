from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("transport", "0002_transportenquiry_email_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="transportenquiry",
            name="current_checkpoint",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="transportenquiry",
            name="driver_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="transportenquiry",
            name="driver_phone",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="transportenquiry",
            name="estimated_arrival",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="transportenquiry",
            name="mpesa_receipt",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="transportenquiry",
            name="truck_registration",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
    ]
