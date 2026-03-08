#!/usr/bin/env python3
"""
Secure API Credential Manager for Operation Capital Forge
Architectural Purpose: Centralized, encrypted credential management with rotation support
Prevents credential leakage and enables automated API registration workflows
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import base64
from cryptography.fernet import Fernet
import requests
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceType(Enum):
    """Enumeration of supported API services"""
    RPC_PROVIDER = "rpc_provider"
    DEX_AGGREGATOR = "dex_aggregator"
    PRICE_FEED = "price_feed"
    BLOCK_EXPLORER = "block_explorer"
    CLOUD_INFRA = "cloud_infra"

@dataclass
class APICredential:
    """Data class for credential management with validation"""
    service_name: str
    service_type: ServiceType
    api_key: str
    api_secret: str = ""
    endpoint_url: str = ""
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    rate_limit: Optional[int] = None
    last_used: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if credential has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, handling datetime objects"""
        data = asdict(self)
        # Convert datetime to ISO format string
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

class CredentialManager:
    """
    Secure credential manager with encryption and validation
    Edge Cases: Missing encryption key, corrupted storage, expired credentials
    """
    
    def __init__(self, config_dir: Path = Path("./config")):
        self.config_dir = config_dir
        self.config_dir.mkdir(exist_ok=True, parents=True)
        self.credentials_file = config_dir / "encrypted_credentials.json"
        self.key_file = config_dir / ".encryption.key"
        self.fernet = None
        self.credentials: Dict[str, APICredential] = {}
        
        # Initialize encryption
        self._init_encryption()
        
        # Load existing credentials
        self._load_credentials()
    
    def _init_encryption(self) -> None:
        """Initialize Fernet encryption with key management"""
        try:
            if self.key_file.exists():
                with open(self.key_file, 'rb') as f:
                    key = f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                # Set restrictive permissions
                self.key_file.chmod(0o600)
                logger.info("Generated new encryption key")
            
            self.fernet = Fernet(key)
            
        except Exception as e:
            logger.error(f"Encryption initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize encryption: {e}")
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt string data"""
        if not self.fernet:
            raise RuntimeError("Encryption not initialized")
        return self.fernet.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        if not self.fernet:
            raise RuntimeError("Encryption not initialized")
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    def _load_credentials(self) -> None:
        """Load and decrypt credentials from file"""
        if not self.credentials_file.exists():
            logger.warning("No credentials file found, starting fresh")
            return
        
        try:
            with open(self.credentials_file, 'r') as f:
                encrypted_data = json.load(f)
            
            # Decrypt each credential
            for service_name, enc_cred in encrypted_data.items():
                try:
                    # Decrypt the credential data
                    decrypted_json = self._decrypt_data(enc_cred['encrypted_data'])
                    cred_dict = json.loads(decrypted_json)
                    
                    # Convert string dates back to datetime
                    for date_field in ['created_at', 'expires_at', 'last_used']:
                        if date_field in cred_dict and cred_dict[date_field]:
                            cred_dict[date_field] = datetime.fromisoformat(cred_dict[date_field])
                    
                    # Recreate ServiceType enum
                    cred_dict['service_type'] = ServiceType(cred_dict['service_type'])
                    
                    self.credentials[service_name] = APICredential(**cred_dict)
                    
                except Exception as e:
                    logger.error(f"Failed to decrypt credential for {service_name}: {e}")
            
            logger.info(f"Loaded {len(self.credentials)} credentials")
            
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted credentials file: {e}")
            # Backup corrupted file
            backup_name = self.credentials_file.with_suffix(f'.corrupted.{datetime.now().timestamp()}')
            self.credentials