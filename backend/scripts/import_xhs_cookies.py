"""将 XHS_ALL_IN_ONE 的 Cookie 导入 data_hunter"""
import hashlib
import base64
import json
import sqlite3
from cryptography.fernet import Fernet

# Derive Fernet key
secret = b'dev-only-change-me'
key_bytes = hashlib.sha256(secret).digest()
fernet_key = base64.urlsafe_b64encode(key_bytes)
f = Fernet(fernet_key)

# Read from XHS db
xhs_db = sqlite3.connect('/Users/l./xhs_all_in_one_v2/data/spider_xhs.db')
row = xhs_db.execute(
    'SELECT encrypted_cookies FROM account_cookie_versions ORDER BY id DESC LIMIT 1'
).fetchone()
xhs_db.close()

encrypted = row[0]
decrypted = f.decrypt(encrypted.encode() if isinstance(encrypted, str) else encrypted)
cookies = json.loads(decrypted)

print(f"Decrypted {len(cookies)} cookies")

# Save to data_hunter db
dh_db = sqlite3.connect('/Users/l./data_hunter/backend/data_hunter.db')
dh_db.execute(
    "INSERT OR REPLACE INTO platform_accounts (id, platform, account_name, cookies, status, updated_at) "
    "VALUES (1, 'xiaohongshu', '源ヾ', ?, 'active', datetime('now'))",
    (json.dumps(cookies),)
)
dh_db.commit()

# Verify
r = dh_db.execute("SELECT id, platform, account_name, status FROM platform_accounts").fetchall()
print("Accounts:", r)

# Show cookie names
print("\nCookie names:")
for c in cookies:
    if isinstance(c, dict):
        print(f"  {c.get('name'):30s} | domain={c.get('domain', '?')}")
dh_db.close()

print("\n✅ Import complete!")
