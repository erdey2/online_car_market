import os
import firebase_admin
from firebase_admin import credentials

def init_firebase():
    if not firebase_admin._apps:
        cred_path = os.path.join(os.getcwd(), os.getenv("FIREBASE_CREDENTIALS_PATH"))
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
