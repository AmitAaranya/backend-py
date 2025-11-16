from app.core.db.firestore_db import FirestoreManager
from app.core.storage import StorageManager
from app.core.firebase import FirebaseManager
from app.settings import ENV

__all__ = ["db", "storage", "firebase"]

db = FirestoreManager(ENV.FIRE_STORE_DB_NAME, ENV.GOOGLE_CREDENTIAL_PATH)
storage = StorageManager(credential_path=ENV.GOOGLE_CREDENTIAL_PATH)
firebase = FirebaseManager(ENV.FIREBASE_CREDENTIAL_PATH)
