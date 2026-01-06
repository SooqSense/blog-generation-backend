from django.core.management.base import BaseCommand
from management_app.shared.services.authentication.api_key_auth import generate_api_key

class Command(BaseCommand):
    help = 'Generates a new secure API Key for testing and production integrations.'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Human readable name for the key')
        parser.add_argument('organization_name', type=str, help='Organization name to tie the key to')

    def handle(self, *args, **options):
        name = options['name']
        org = options['organization_name']

        raw_key, key_obj = generate_api_key(name=name, organization_name=org)

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🚀 API KEY GENERATED SUCCESSFULLY'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f" KEY NAME:       {key_obj.name}")
        self.stdout.write(f" ORGANIZATION:   {key_obj.organization_name}")
        self.stdout.write(f" PREFIX:         {key_obj.prefix}")
        self.stdout.write('-' * 60)
        self.stdout.write(f" FULL API KEY:   {raw_key}")
        self.stdout.write('-' * 60)
        self.stdout.write(self.style.WARNING(" ⚠️  WARNING: Keep this key secret! It is hashed in the database."))
        self.stdout.write(self.style.WARNING(" ⚠️  You will NOT be able to see this full key again."))
        self.stdout.write(self.style.SUCCESS('=' * 60))
