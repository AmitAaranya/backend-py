from google.cloud import firestore
from google.oauth2 import service_account
from app.settings import logger


class FirestoreManager:
    def __init__(self, database_name, credential_path=None):
        # service_account.Credentials.from_service_account_info()
        try:
            if credential_path:
                credentials = service_account.Credentials.from_service_account_file(
                    credential_path)
                # Initialize Firestore client
                self.db = firestore.Client(
                    credentials=credentials, database=database_name)
            else:
                self.db = firestore.Client(database=database_name)
            logger.info("Firestore client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            raise

    def add_data(self, collection_name, doc_id, data):
        """Add or update a document in Firestore."""
        try:
            doc_ref = self.db.collection(collection_name).document(doc_id)
            doc_ref.set(data)
            logger.info(
                f"Document '{doc_id}' added/updated in collection '{collection_name}'.")
        except Exception as e:
            logger.error(f"Failed to add data to Firestore: {e}")
            raise

    def get_user_ref(self, collection_name, doc_id):
        """Get a reference to a Firestore document."""
        return self.db.collection(collection_name).document(doc_id)

    def read_data(self, collection_name, doc_id):
        """Read a document from Firestore."""
        try:
            doc_ref = self.db.collection(collection_name).document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                logger.info(
                    f"Document '{doc_id}' fetched successfully from '{collection_name}'.")
                return doc.to_dict()
            else:
                logger.warning(
                    f"Document '{doc_id}' does not exist in '{collection_name}'.")
                return None
        except Exception as e:
            logger.error(f"Failed to read data from Firestore: {e}")
            raise

    def read_data_by_mobile(self, collection_name, mobile_number):
        """Read a document from Firestore by mobile number."""
        try:
            query = self.db.collection(collection_name).where(
                "mobile_number", "==", mobile_number)
            results = query.stream()
            documents = [doc.to_dict() for doc in results]

            if documents:
                logger.debug(
                    f"Document with mobile number '{mobile_number}' fetched successfully from '{collection_name}'.")
                return documents[0]  # Return the single matching document
            else:
                logger.debug(
                    f"No document found with mobile number '{mobile_number}' in '{collection_name}'.")
                return None
        except Exception as e:
            logger.error(
                f"Failed to read data by mobile number from Firestore: {e}")
            raise

    def delete_data(self, collection_name, doc_id):
        """Delete a document from Firestore."""
        try:
            doc_ref = self.db.collection(collection_name).document(doc_id)
            doc_ref.delete()
            logger.info(
                f"Document '{doc_id}' deleted from collection '{collection_name}'.")
        except Exception as e:
            logger.error(f"Failed to delete data from Firestore: {e}")
            raise

    def append_data(self, collection_name: str, doc_id: str, data: dict):
        try:
            doc_ref = self.db.collection(collection_name).document(doc_id)
            doc_ref.set({"messages": firestore.ArrayUnion([data])}, merge=True)
            logger.debug(
                f"Append data into Document '{doc_id}' in collection '{collection_name}'.")
        except Exception as e:
            logger.error(f"Failed to update data in Firestore: {e}")
            raise

    def update_data(self, collection_name, doc_id, data):
        """Update specific fields in a Firestore document."""
        try:
            doc_ref = self.db.collection(collection_name).document(doc_id)
            doc_ref.update(data)
            logger.info(
                f"Document '{doc_id}' updated in collection '{collection_name}'.")
        except Exception as e:
            logger.error(f"Failed to update data in Firestore: {e}")
            raise

    def read_all_documents(self, collection_name):
        """Read all documents from a collection."""
        try:
            docs = self.db.collection(collection_name).stream()
            all_docs = [doc.to_dict() for doc in docs]
            logger.info(
                f"Fetched all documents from collection '{collection_name}'.")
            return all_docs
        except Exception as e:
            logger.error(
                f"Failed to fetch all documents from '{collection_name}': {e}")
            raise

    def read_raw_all_documents(self, collection_name):
        """Read all documents from a collection."""
        try:
            docs = self.db.collection(collection_name).stream()
            all_docs = [doc for doc in docs]
            logger.info(
                f"Fetched all documents from collection '{collection_name}'.")
            return all_docs
        except Exception as e:
            logger.error(
                f"Failed to fetch all documents from '{collection_name}': {e}")
            raise

    def create_collection(self, collection_name, doc_id=None, data=None):
        """Ensure a collection exists by creating a document in it.

        If doc_id is provided the document will be created/overwritten with
        `data` (or an empty dict). If doc_id is None, an auto-id document is
        created. Returns the created document id.
        """
        try:
            col_ref = self.db.collection(collection_name)
            if doc_id:
                doc_ref = col_ref.document(doc_id)
                doc_ref.set(data or {})
                created_id = doc_ref.id
            else:
                doc_ref = col_ref.add(data or {})
                # add() returns (document_reference, write_result)
                created_id = doc_ref[0].id

            logger.info(
                f"Collection '{collection_name}' ensured (doc id: {created_id}).")
            return created_id
        except Exception as e:
            logger.error(
                f"Failed to create collection '{collection_name}': {e}")
            raise

    def _delete_collection_recursive(self, collection_ref, batch_size=100):
        """Recursively delete all documents in a collection and its subcollections.

        This deletes documents in batches. For each document, any subcollections
        are deleted recursively before the document itself is removed.
        """
        try:
            docs = list(collection_ref.list_documents())
            # Process in batches
            for i in range(0, len(docs), batch_size):
                batch = self.db.batch()
                batch_docs = docs[i: i + batch_size]

                for doc_ref in batch_docs:
                    # Recursively delete any subcollections under this document
                    try:
                        for subcol in doc_ref.collections():
                            self._delete_collection_recursive(
                                subcol, batch_size=batch_size)
                    except Exception:
                        # If listing collections fails, continue with deletion of doc
                        logger.warning(
                            f"Failed to list subcollections for doc '{doc_ref.id}' in '{collection_ref.id}'.")

                    batch.delete(doc_ref)

                batch.commit()

            # If there were documents but they were deleted, check again in case
            # new documents appeared while deleting (eventual consistency safety).
            remaining = list(collection_ref.list_documents())
            if remaining:
                # recurse until empty
                self._delete_collection_recursive(
                    collection_ref, batch_size=batch_size)
        except Exception as e:
            logger.error(
                f"Failed to delete collection '{collection_ref.id}': {e}")
            raise

    def delete_collection(self, collection_name, batch_size=100):
        """Delete all documents in a collection (recursively deletes subcollections).

        Firestore has no server-side 'drop collection' operation; removing a
        collection requires deleting its documents (and nested subcollections).
        """
        try:
            collection_ref = self.db.collection(collection_name)
            # start recursive deletion
            self._delete_collection_recursive(
                collection_ref, batch_size=batch_size)
            logger.info(
                f"Collection '{collection_name}' deleted (all documents removed).")
        except Exception as e:
            logger.error(
                f"Failed to delete collection '{collection_name}': {e}")
            raise
