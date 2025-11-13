from app.core.db.firestore_db import FirestoreManager
from app.settings import ENV

__all__ = ["db"]

db = FirestoreManager(ENV.FIRE_STORE_DB_NAME, ENV.GOOGLE_CREDENTIAL_PATH)
