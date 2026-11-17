"""Set the owner's login password (writes OWNER_PASSWORD_HASH into backend/.env)."""

import getpass
import re

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Set the single user's login password (stored hashed in backend/.env)."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Non-interactive; avoid on shared machines (shell history).")

    def handle(self, *args, **opts):
        password = opts.get("password")
        if not password:
            password = getpass.getpass("New password: ")
            if password != getpass.getpass("Repeat password: "):
                raise CommandError("Passwords do not match.")
        if len(password) < 8:
            raise CommandError("Use at least 8 characters.")

        hashed = make_password(password)
        env_file = settings.ENV_FILE
        text = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
        line = f"OWNER_PASSWORD_HASH='{hashed}'"
        if re.search(r"^OWNER_PASSWORD_HASH=.*$", text, flags=re.M):
            text = re.sub(r"^OWNER_PASSWORD_HASH=.*$", lambda _m: line, text, flags=re.M)
        else:
            text = (text.rstrip("\n") + "\n" if text else "") + line + "\n"
        env_file.write_text(text, encoding="utf-8")
        env_file.chmod(0o600)
        self.stdout.write(self.style.SUCCESS(f"Password updated in {env_file}. Restart the backend to apply it."))
