# Generated manually for linkedin_scopes field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_user_linkedin_access_token_user_linkedin_profile_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='linkedin_scopes',
            field=models.TextField(blank=True, help_text='LinkedIn OAuth granted scopes (space-separated)', null=True),
        ),
    ] 