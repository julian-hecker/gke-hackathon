import os

is_local = os.getenv("APP_ENVIRONMENT", "PROD") == "LOCAL"
