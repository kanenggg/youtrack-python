import os
from dotenv import load_dotenv

load_dotenv()

YOUTRACK_BASE_URL = os.getenv("YOUTRACK_URL").rstrip("/")
YOUTRACK_TOKEN = os.getenv("YOUTRACK_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {YOUTRACK_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}