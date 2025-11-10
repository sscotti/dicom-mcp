#!/usr/bin/env python3
"""
Centralized configuration for DICOM MWL-MPPS services
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = os.getenv('DB_HOST', 'mysql_db')
    user: str = os.getenv('DB_USER', 'root')
    password: str = os.getenv('DB_PASSWORD', 'root')
    name: str = os.getenv('DB_NAME', 'orthanc_ris')
    port: int = int(os.getenv('DB_PORT', '3306'))
    
    @property
    def connection_string(self) -> str:
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass
class DicomConfig:
    """DICOM service configuration"""
    ae_title: str = os.getenv('DICOM_AE_TITLE', 'MWL-MPPS-SCP')
    port: int = int(os.getenv('DICOM_PORT', '104'))
    bind_address: str = os.getenv('DICOM_BIND_ADDRESS', '0.0.0.0')
    max_associations: int = int(os.getenv('DICOM_MAX_ASSOC', '10'))
    

@dataclass
class ApiConfig:
    """REST API configuration"""
    host: str = os.getenv('API_HOST', '0.0.0.0')
    port: int = int(os.getenv('API_PORT', '8000'))
    debug: bool = os.getenv('API_DEBUG', 'false').lower() == 'true'
    cors_origins: list = os.getenv('API_CORS_ORIGINS', '*').split(',')


@dataclass
class WorklistConfig:
    """Worklist configuration"""
    directory: str = os.getenv('WORKLIST_DIR', '/worklist')
    file_extension: str = '.wl'
    max_age_days: int = int(os.getenv('WORKLIST_MAX_AGE_DAYS', '30'))


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = os.getenv('LOG_LEVEL', 'INFO')
    format: str = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_path: Optional[str] = os.getenv('LOG_FILE_PATH')


@dataclass
class Config:
    """Main configuration class"""
    database: DatabaseConfig = DatabaseConfig()
    dicom: DicomConfig = DicomConfig()
    api: ApiConfig = ApiConfig()
    worklist: WorklistConfig = WorklistConfig()
    logging: LoggingConfig = LoggingConfig()
    
    # Global settings
    environment: str = os.getenv('ENVIRONMENT', 'development')
    version: str = os.getenv('VERSION', '1.0.0')
    
    @classmethod
    def load(cls) -> 'Config':
        """Load configuration from environment"""
        return cls()
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() == 'development'


# Global config instance
config = Config.load() 