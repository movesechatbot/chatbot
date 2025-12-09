import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")

HIGH = float(os.getenv("HIGH", "0.83"))
MED  = float(os.getenv("MED",  "0.82"))
TOPK = int(os.getenv("TOPK", "3"))

TIMEZONE = os.getenv("TZ", "America/Sao_Paulo")
SOCIAL_IG_URL = os.getenv("SOCIAL_IG_URL", "")

PORT = int(os.getenv("PORT", "10000"))

MODEL_NAME = os.getenv("ST_MODEL", "intfloat/multilingual-e5-small")
FAQ_PATH   = os.getenv("FAQ_PATH", "base_faq.json")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "")
RESEND_TO_EMAIL = os.getenv("RESEND_TO_EMAIL", "")
RESEND_SUBJECT = os.getenv("RESEND_SUBJECT", "Novo documento recebido pelo WhatsApp")

# PARA PRODUÇÃO ABRA O CORS COM ESSA VARIAVEL:
# ALLOWED_ORIGINS=https://seu-app.com,https://app.seu-app.com,https://admin.seu-app.com
# O CORS SERVE PARA ENVIARMOS REQUISIÇOES HTTPS PELO NAVEGADOR, DE OUTROS DOMINIOS
# ANTES ELE ESTAVA COMO "*" MAS ISSO É MUITO INSEGURO PARA PRODUÇÃO.

# Configurações CORS seguras
def get_allowed_origins():
    """Carrega origens permitidas do .env"""
    origins_str = os.getenv("ALLOWED_ORIGINS", "")
    if not origins_str:
        return []
    
    # Formato no .env: https://site1.com,https://site2.com,http://localhost:3000
    return [origin.strip() for origin in origins_str.split(",") if origin.strip()]

# Cria a variável para importar
ALLOWED_ORIGINS = get_allowed_origins()

# Para desenvolvimento local, inclui automaticamente localhost
if os.environ.get("FLASK_ENV") == "development":
    dev_origins = ["http://localhost:5500", "http://127.0.0.1:5500"]
    ALLOWED_ORIGINS = list(set(ALLOWED_ORIGINS + dev_origins))