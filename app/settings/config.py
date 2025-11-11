import os


TITLE = "Farmer App"
VERSION = "alpha"

class EnvInit:

    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
    GOOGLE_CREDENTIAL_PATH = os.getenv("GOOGLE_CREDENTIAL_PATH")
    FIRE_STORE_DB_NAME = os.environ["FIRE_STORE_DB_NAME"]
    SECRET_KEY = os.getenv("SECRET_KEY", "secret-farmer-app")

    ...