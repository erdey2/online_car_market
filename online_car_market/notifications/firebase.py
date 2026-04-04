import os
import firebase_admin
from firebase_admin import credentials


def init_firebase():
    cred_env = os.getenv("FIREBASE_CREDENTIALS_PATH")

    if not cred_env:
        raise ValueError("FIREBASE_CREDENTIALS_PATH is not set!")

    cred_path = os.path.join(os.getcwd(), cred_env)

    if not os.path.exists(cred_path):
        raise FileNotFoundError(f"Firebase credentials not found at {cred_path}")

    cred = credentials.Certificate(cred_path)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
