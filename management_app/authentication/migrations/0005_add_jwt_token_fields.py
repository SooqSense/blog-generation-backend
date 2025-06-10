# Generated manually for JWT token fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0004_user_linkedin_scopes'),
    ]

    operations = [
        # Simple login JWT tokens
        migrations.AddField(
            model_name='user',
            name='simple_login_access_token',
            field=models.TextField(blank=True, help_text='JWT access token for simple login', null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='simple_login_refresh_token',
            field=models.TextField(blank=True, help_text='JWT refresh token for simple login', null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='simple_login_token_expires_at',
            field=models.DateTimeField(blank=True, help_text='When simple login access token expires', null=True),
        ),
        
        # Google login JWT tokens
        migrations.AddField(
            model_name='user',
            name='google_login_access_token',
            field=models.TextField(blank=True, help_text='JWT access token for Google login', null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='google_login_refresh_token',
            field=models.TextField(blank=True, help_text='JWT refresh token for Google login', null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='google_login_token_expires_at',
            field=models.DateTimeField(blank=True, help_text='When Google login JWT token expires', null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='google_profile_id',
            field=models.CharField(blank=True, help_text='Google profile ID', max_length=100, null=True),
        ),
    ] 