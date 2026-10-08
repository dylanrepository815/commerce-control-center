"""Create local environment secrets without printing them or overwriting existing configuration."""

from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    raise SystemExit(".env already exists; leaving it unchanged")
text = (
    (root / ".env.example")
    .read_text()
    .replace("REPLACE_WITH_RANDOM_ADMIN_PASSWORD", secrets.token_hex(32))
    .replace("REPLACE_WITH_RANDOM_APP_PASSWORD", secrets.token_hex(32))
)
with target.open("x") as file:
    file.write(text)
target.chmod(0o600)
print(
    "Created .env with independent database passwords. No Owner account has been created."
)
