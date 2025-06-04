# Generated manually for adding image fields to LinkedinPostingContent

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_linkedinpostingcontent'),
    ]

    operations = [
        migrations.AddField(
            model_name='linkedinpostingcontent',
            name='image_urls',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='linkedinpostingcontent',
            name='images_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='linkedinpostingcontent',
            name='post_type',
            field=models.CharField(default='text', max_length=20),
        ),
    ] 