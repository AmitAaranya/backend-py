import re


def extract_google_docs_id(url: str) -> str:
    """
    Extract the Google Docs document ID from a given URL.

    Raises:
        ValueError: If no document ID is found.
    """
    # Regex to match /d/<id>/ in the URL
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    if not match:
        raise ValueError("Invalid Google Docs URL: Document ID not found.")
    return match.group(1)
