"""
Application configuration loaded from environment variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables from the local .env file when available.
load_dotenv()


class Config:
    """Application configuration."""

    # Flask configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() in {'1', 'true', 'yes', 'on'}
    HOST = os.getenv('FLASK_HOST', '127.0.0.1')
    PORT = int(os.getenv('FLASK_PORT', '5000'))

    # OpenAI configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')

    # Whisper configuration
    WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')

    # App defaults
    DEFAULT_UI_LANGUAGE = os.getenv('DEFAULT_UI_LANGUAGE', 'en')
    DEFAULT_AUDIO_LANGUAGE = os.getenv('DEFAULT_AUDIO_LANGUAGE', 'en')
    DEFAULT_ENGINE = os.getenv('DEFAULT_ENGINE', 'vosk')
    SUPPORTED_AUDIO_LANGUAGES = ('ru', 'en', 'es', 'fr', 'de', 'zh')
    SUPPORTED_ENGINES = ('vosk', 'whisper')

    # Upload configuration
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    RESULTS_FOLDER = os.getenv('RESULTS_FOLDER', 'results')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 104857600))

    # Allowed extensions
    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'opus', 'oga', 'm4a'}

    @staticmethod
    def init_app(app):
        """
        Initialize the Flask app with the configured directories.

        Args:
            app: Flask application instance
        """
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.RESULTS_FOLDER, exist_ok=True)

    @staticmethod
    def allowed_file(filename):
        """
        Check whether the uploaded file extension is allowed.

        Args:
            filename: Uploaded filename

        Returns:
            True when the file extension is supported
        """
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
