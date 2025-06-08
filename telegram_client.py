from telethon import TelegramClient
import config

# Create the Telethon client (this creates a 'session_name.session' file)
client = TelegramClient(
    'session_name',
    config.TELETHON_API_ID,
    config.TELETHON_API_HASH
)

async def start_client():
    await client.start(phone=config.TELETHON_PHONE)
    print("✅ Telethon client logged in")

# Call this once at startup
with client:
    client.loop.run_until_complete(start_client())
