from app.core.db.firestore_db import FirestoreManager
from app.core.storage import StorageManager
from app.settings import ENV

__all__ = ["db", "storage"]

db = FirestoreManager(ENV.FIRE_STORE_DB_NAME, ENV.GOOGLE_CREDENTIAL_PATH)
storage = StorageManager(credential_path=ENV.GOOGLE_CREDENTIAL_PATH)
