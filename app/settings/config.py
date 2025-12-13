import os


TITLE = "Farmer-App"
VERSION = "alpha"


class EnvInit:

    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
    GOOGLE_CREDENTIAL_PATH = os.getenv("GOOGLE_CREDENTIAL_PATH")
    FIRE_STORE_DB_NAME = os.environ["FIRE_STORE_DB_NAME"]
    GOOGLE_STORAGE_BUCKET = os.environ["GOOGLE_STORAGE_BUCKET"]
    SECRET_KEY = os.getenv("SECRET_KEY", "secret-farmer-app")
    REDIS_SERVER_ACCESS_TOKEN = os.environ["REDIS_SERVER_ACCESS_TOKEN"]
    REDIS_SERVER_URL = os.environ["REDIS_SERVER_URL"]
    REDIS_RESP_HOST = os.environ["REDIS_RESP_HOST"]
    REDIS_RESP_PORT = int(os.environ["REDIS_RESP_PORT"])
    REDIS_RESP_PASSWORD = os.environ["REDIS_RESP_PASSWORD"]
    REDIS_CHANNEL_CHAT = "chatMessage"

    RAZORPAY_KEY_ID = os.environ["RAZORPAY_KEY_ID"]
    RAZORPAY_KEY_SECRET = os.environ["RAZORPAY_KEY_SECRET"]

    TWILIO_ACCOUNT_SID =  os.environ["TWILIO_ACCOUNT_SID"]
    TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
    TWILIO_VERIFY_SERVICE_SID = os.environ["TWILIO_VERIFY_SERVICE_SID"]

    ...
