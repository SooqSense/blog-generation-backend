# Generated manually for adding image_urls field to BlogGeneral model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_imageediting_blogainews_sources_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bloggeneral',
            name='image_urls',
            field=models.JSONField(blank=True, default=list, help_text='Store S3 bucket URLs for section-specific images'),
        ),
    ]
