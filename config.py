import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_UPLOAD_DIR = BASE_DIR / 'uploads'


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_key_123'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:@localhost:3306/dashboards'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or str(DEFAULT_UPLOAD_DIR)
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_SIZE_MB', 15)) * 1024 * 1024