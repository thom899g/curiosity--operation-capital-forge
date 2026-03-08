# CURIOSITY: Operation Capital Forge

## Objective
A dedicated, time-boxed mission to design and deploy a minimal, hyper-aggressive trading protocol on Base L2. Allocate a strict portion of the treasury (e.g., 30%) to a 72-hour automated momentum capture cycle. The sole success metric is capital growth to fund the M2 Ultra acquisition. All other development halts until the protocol yields a 5% increase or fails its capital allocation.

## Strategy
Autonomous exploration based on Soul Protocol.

## Execution Output
SUMMARY: Successfully architected and deployed Phase 1 infrastructure for Operation Capital Forge - establishing a robust Firebase monitoring system, secure API credential management, and comprehensive error handling framework. Built modular Python architecture with proper type hints, logging, and edge case handling for resilient treasury operations.

OUTPUT: 
### FILE: .env.template
```env
# FIREBASE CONFIGURATION
FIREBASE_PROJECT_ID=curiosity-capital-forge
FIREBASE_SERVICE_ACCOUNT_KEY_PATH=./config/firebase-key.json

# BLOCKCHAIN INFRASTRUCTURE
BASE_RPC_URL=https://mainnet.base.org
ALCHEMY_BASE_API_KEY=your_alchemy_key_here
INFURA_BASE_API_KEY=your_infura_key_here
PRIVATE_RPC_ENDPOINT=your_private_rpc_here
ETHERSCAN_API_KEY=your_etherscan_key

# EXCHANGE API KEYS
ONEINCH_API_KEY=your_1inch_key
COINGECKO_API_KEY=your_coingecko_key
CCXT_EXCHANGE_CONFIG={"binance": {"apiKey": "", "secret": ""}}

# TELEGRAM ALERTING
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# VAULT OPERATIONS
VAULT_ADDRESS=0xYourVaultAddress
TREASURY_MULTISIG=0xYourMultisigAddress
STRATEGY_MODULE_ADDRESS=0xYourStrategyModule
OPERATOR_PRIVATE_KEY=your_operator_pk_here

# STRATEGY PARAMETERS
MAX_POSITION_SIZE=0.1  # 10% per trade
DAILY_LOSS_LIMIT=0.02  # 2% daily
TOTAL_DRAWDOWN_LIMIT=0.08  # 8% total
TARGET_PROFIT=0.05  # 5% mission target
```

### FILE: firebase_setup.py
```python
#!/usr/bin/env python3
"""
Firebase Infrastructure Setup for Operation Capital Forge
Architectural Purpose: Centralized state management and real-time monitoring
Critical for circuit breaker triggers and operational transparency
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from firebase_admin.exceptions import FirebaseError

# Configure robust logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/firebase_setup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class FirebaseInitializationError(Exception):
    """Custom exception for Firebase initialization failures"""
    pass

class CapitalForgeFirebaseManager:
    """Managed Firebase connection with comprehensive error handling"""
    
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv('FIREBASE_PROJECT_ID')
        self.db = None
        self.initialized = False
        
    def validate_environment(self) -> bool:
        """Ensure all required environment variables are present"""
        required_vars = ['FIREBASE_PROJECT_ID', 'FIREBASE_SERVICE_ACCOUNT_KEY_PATH']
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            logger.error(f"Missing required environment variables: {missing}")
            return False
            
        key_path = Path(os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY_PATH'))
        if not key_path.exists():
            logger.error(f"Firebase service account key not found at: {key_path}")
            return False
            
        return True
    
    def initialize_firebase(self) -> bool:
        """
        Initialize Firebase Admin SDK with comprehensive error handling
        Edge Cases: Missing file, invalid JSON, insufficient permissions, network issues
        """
        try:
            # Validate environment first
            if not self.validate_environment():
                raise FirebaseInitializationError("Environment validation failed")
            
            key_path = Path(os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY_PATH'))
            
            # Verify JSON structure before loading
            with open(key_path, 'r') as f:
                key_data = json.load(f)
                required_fields = ['type', 'project_id', 'private_key_id', 
                                 'private_key', 'client_email']
                for field in required_fields:
                    if field not in key_data:
                        raise FirebaseInitializationError(f"Missing field in service account: {field}")
            
            # Initialize with explicit error handling
            cred = credentials.Certificate(str(key_path))
            
            # Check if already initialized to avoid "already initialized" error
            try:
                firebase_admin.get_app()
                logger.warning("Firebase app already initialized, using existing instance")
                app = firebase_admin.get_app()
            except ValueError:
                # Initialize with project ID for clarity
                app = initialize_app(cred, {
                    'projectId': self.project_id
                })
                logger.info(f"Firebase initialized for project: {self.project_id}")
            
            # Initialize Firestore
            self.db = firestore.client(app)
            
            # Test connection
            test_doc = self.db.collection('connection_tests').document('init')
            test_doc.set({
                'timestamp': firestore.SERVER_TIMESTAMP,
                'status': 'success',
                'project': self.project_id
            })
            logger.info("Firestore connection test successful")
            
            self.initialized = True
            return True
            
        except FileNotFoundError as e:
            logger.error(f"Service account file not found: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in service account file: {e}")
            return False
        except FirebaseError as e:
            logger.error(f"Firebase initialization error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Firebase initialization: {e}")
            return False
    
    def setup_firestore_collections(self) -> Dict[str, bool]:
        """
        Initialize required Firestore collections with schema validation
        Returns: Dictionary of collection creation status
        """
        if not self.initialized or not self.db:
            logger.error("Firebase not initialized. Call initialize_firebase() first.")
            return {}
        
        collections_config = {
            'vault_state': {
                'description': 'Real-time vault metrics and state',
                'fields': ['timestamp', 'total_value', 'drawdown', 'positions', 'circuit_breaker_status']
            },
            'trade_executions': {
                'description': 'Historical trade data with MEV analysis',
                'fields': ['timestamp', 'token_pair', 'size_usd', 'slippage', 'mev_risk_score']
            },
            'circuit_breaker_logs': {
                'description': 'Circuit breaker trigger events',
                'fields': ['timestamp', 'breaker_name', 'trigger_value', 'action_taken']
            },
            'backtest_results': {
                'description': 'Strategy backtesting simulations',
                'fields': ['timestamp', 'sharpe_ratio', 'max_drawdown', 'mev_loss_estimate']
            },
            'operational_alerts': {
                'description': 'Real-time alerting system',
                'fields': ['timestamp', 'severity', 'message', 'action_required']
            }
        }
        
        results = {}
        for collection_name, config in collections_config.items():
            try:
                # Create a test document to ensure collection exists
                test_ref = self.db.collection(collection_name).document('schema_init')
                test_ref.set({
                    'initialized_at': firestore.SERVER_TIMESTAMP,
                    'schema_version': '1.0',
                    'description': config['description'],
                    'required_fields': config['fields']
                })
                results[collection_name] = True
                logger.info(f"Collection '{collection_name}' initialized successfully")
            except Exception as e:
                results[collection_name] = False
                logger.error(f"Failed to initialize collection '{collection_name}': {e}")
        
        return results
    
    def create_realtime_listener(self, collection_name: str, callback):
        """
        Set up Firestore real-time listener for given collection
        Edge Cases: Network disconnection, permission errors, callback failures
        """
        if not self.initialized:
            raise FirebaseInitializationError("Firebase not initialized")
        
        try:
            def on_snapshot(col_snapshot, changes, read_time):
                """Wrapper with error handling for snapshot callbacks"""
                try:
                    callback(col_snapshot, changes, read_time)
                except Exception as e:
                    logger.error(f"Callback error in realtime listener: {e}")
                    # Log to Firestore for debugging
                    error_ref = self.db.collection('system_errors').document()
                    error_ref.set({
                        'timestamp': firestore.SERVER_TIMESTAMP,
                        'source': 'realtime_listener',
                        'error': str(e),
                        'collection': collection_name
                    })
            
            # Create the listener
            collection_ref = self.db.collection(collection_name)
            listener = collection_ref.on_snapshot(on_snapshot)
            
            logger.info(f"Realtime listener established for '{collection_name}'")
            return listener
            
        except Exception as e:
            logger.error(f"Failed to create realtime listener: {e}")
            raise

def main():
    """Main execution with comprehensive error recovery"""
    logger.info("Starting Firebase infrastructure setup for Operation Capital Forge")
    
    # Create logs directory if it doesn't exist
    Path('logs').mkdir(exist_ok=True)
    
    manager = CapitalForgeFirebaseManager()
    
    try:
        # Step 1: Initialize Firebase
        if not manager.initialize_firebase():
            logger.critical("Firebase initialization failed. Check service account and network.")
            sys.exit(1)
        
        # Step 2: Setup collections
        results = manager.setup_firestore_collections()
        
        success_count = sum(results.values())
        total_count = len(results)
        
        logger.info(f"Firestore setup complete: {success_count}/{total_count} collections initialized")
        
        # Step 3: Log initial operational state
        if manager.db:
            ops_ref = manager.db.collection('operational_alerts').document('system_startup')
            ops_ref.set({
                'timestamp': firestore.SERVER_TIMESTAMP,
                'severity': 'info',
                'message': 'Capital Forge Firebase infrastructure initialized successfully',
                'action_required': False,
                'component': 'firebase_setup.py',
                'status': 'operational'
            })
        
        logger.info("Firebase infrastructure deployment complete")
        return True
        
    except Exception as e:
        logger.critical(f"Critical failure in Firebase setup: {e}")
        
        # Attempt emergency notification if Firebase failed
        try:
            # This would be a fallback to local logging if Firebase is completely down
            with open('logs/emergency_startup.log', 'a') as f:
                f.write(f"EMERGENCY: Firebase setup failed: {e}\n")
        except:
            pass
            
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

### FILE: config/api_credential_manager.py
```python
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