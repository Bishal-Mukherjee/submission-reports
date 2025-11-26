import os

class Config:
    """Base configuration"""
    UPLOAD_FOLDER = 'temp'
    OUTPUT_FOLDER = 'output'
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default
    MAX_OBSERVATIONS = int(os.getenv('MAX_OBSERVATIONS', 10000))
    
    # Security
    JSON_SORT_KEYS = False
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
