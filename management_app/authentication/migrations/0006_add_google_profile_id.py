# Generated manually for google_profile_id field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0005_add_jwt_token_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='google_profile_id',
            field=models.CharField(blank=True, help_text='Google profile ID', max_length=100, null=True),
        ),
    ] 