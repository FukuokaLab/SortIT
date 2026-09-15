import os

from django.contrib.auth.models import User
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        if User.objects.count() == 0:
            username = os.getenv("DJANGO_SUPERUSER_USERNAME")
            email = os.getenv("DJANGO_SUPERUSER_EMAIL")
            password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

            if not username or not email or not password:
                raise ValueError("Must set DJANGO_SUPERUSER_* env vars")

            admin = User.objects.create_superuser(
                email=email, username=username, password=password
            )
            admin.save()
        else:
            print("Admin accounts can only be initialized if no Accounts exist")
