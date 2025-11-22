from app.core.db.firestore_db import FirestoreManager
from app.core.google_docs import GoogleDocsManager
from app.core.storage import StorageManager
from app.core.firebase import FirebaseManager
from app.core.upstash_redis import UnifiedRedisManager
from app.settings import ENV

__all__ = ["db", "storage", "firebase", "docs", "redis"]

db = FirestoreManager(ENV.FIRE_STORE_DB_NAME, ENV.GOOGLE_CREDENTIAL_PATH)

storage = StorageManager(credential_path=ENV.GOOGLE_CREDENTIAL_PATH)

firebase = FirebaseManager(ENV.GOOGLE_CREDENTIAL_PATH)

docs = GoogleDocsManager(ENV.GOOGLE_CREDENTIAL_PATH)

redis = UnifiedRedisManager(http_url=ENV.REDIS_SERVER_URL,
                            http_token=ENV.REDIS_SERVER_ACCESS_TOKEN,
                            resp_host=ENV.REDIS_RESP_HOST,
                            resp_port=ENV.REDIS_RESP_PORT,
                            resp_password=ENV.REDIS_RESP_PASSWORD)
