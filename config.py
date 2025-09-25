import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")

HIGH = float(os.getenv("HIGH", "0.90"))
MED  = float(os.getenv("MED",  "0.89"))
TOPK = int(os.getenv("TOPK", "3"))

PORT = int(os.getenv("PORT", "10000"))

MODEL_NAME = os.getenv("ST_MODEL", "intfloat/multilingual-e5-small")
FAQ_PATH   = os.getenv("FAQ_PATH", "base_faq.json")