from telethon import TelegramClient
import config

client = TelegramClient("session_name",
                        config.TELETHON_API_ID,
                        config.TELETHON_API_HASH)

# Login once interactively then keep the session file
client.start(phone=config.TELETHON_PHONE)
print("✅ Telethon client logged in")
