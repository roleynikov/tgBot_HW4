import os
from dotenv import load_dotenv

load_dotenv()
TOKEN=os.getenv("BOT_TOKEN")
API_KEY=os.getenv("API_KEY")

if not TOKEN or not API_KEY:
    raise ValueError("Отсутствует токен бота или апи для погоды")