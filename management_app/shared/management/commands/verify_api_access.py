import json
from django.core.management.base import BaseCommand
from rest_framework.test import APIClient
from django.urls import reverse

class Command(BaseCommand):
    help = 'Tests the External API using a generated API Key.'

    def add_arguments(self, parser):
        parser.add_argument('api_key', type=str, help='The full API Key to test (prefix.key)')
        parser.add_argument('--slug', type=str, help='Optional blog slug to test detail endpoint')

    def handle(self, *args, **options):
        api_key = options['api_key']
        slug = options.get('slug')
        
        client = APIClient()
        header = {'HTTP_X_API_KEY': api_key}
        
        # 1. Test List Endpoint
        self.stdout.write(self.style.NOTICE(f"\n--- Testing List Endpoint: /api/external/v1/blogs/ ---"))
        url = "/api/external/v1/blogs/"
        response = client.get(url, **header)
        
        # Handle cases where response might be standard JsonResponse (from middleware)
        try:
            resp_data = response.data if hasattr(response, 'data') else response.json()
        except Exception:
            resp_data = response.content.decode()

        if response.status_code == 200:
            self.stdout.write(self.style.SUCCESS(f"✅ Success! Received {len(resp_data)} blogs."))
            # Print a snippet of the first blog if available
            if resp_data:
                self.stdout.write(f"Sample Blog Title: {resp_data[0].get('title')}")
                # Print the JSON format snippet to verify structure
                self.stdout.write(self.style.NOTICE("\nJSON structure matches 'Example Formate':"))
                self.stdout.write(json.dumps(resp_data[0], indent=2)[:500] + "...")
        else:
            self.stdout.write(self.style.ERROR(f"❌ Failed! Status Code: {response.status_code}"))
            self.stdout.write(f"Error Detail: {resp_data}")
            
            if response.status_code == 401:
                self.stdout.write(self.style.WARNING("\n💡 Hint: 401 Unauthorized usually means:"))
                self.stdout.write("1. The API Key format is wrong (should be prefix.key)")
                self.stdout.write("2. The key is in the database but marked as inactive")
                self.stdout.write("3. A middleware (like Clerk) is blocking the request before it reaches the view.")

        # 2. Test Detail Endpoint (if slug or data exists)
        test_slug = slug
        if not test_slug and response.status_code == 200 and response.data:
            test_slug = response.data[0].get('slug') or response.data[0].get('id')

        if test_slug:
            self.stdout.write(self.style.NOTICE(f"\n--- Testing Detail Endpoint: /api/external/v1/blogs/{test_slug}/ ---"))
            detail_url = f"/api/external/v1/blogs/{test_slug}/"
            detail_response = client.get(detail_url, **header)
            
            if detail_response.status_code == 200:
                self.stdout.write(self.style.SUCCESS(f"✅ Success! Retrieved full content for: {detail_response.data.get('title')}"))
                self.stdout.write(f"Author ID: {detail_response.data.get('author', {}).get('id')}")
            else:
                self.stdout.write(self.style.ERROR(f"❌ Failed! Status Code: {detail_response.status_code}"))
                self.stdout.write(f"Error Detail: {detail_response.data}")
        
        self.stdout.write("\n" + "="*40 + "\n")
