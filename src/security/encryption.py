"""
Encryption utilities for securing sensitive data.

Uses Fernet (symmetric encryption) from the cryptography library.
"""
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from ..config.logging_config import get_logger

logger = get_logger(__name__)

class EncryptionManager:
    """
    Manages encryption and decryption of sensitive data.
    
    Uses a master key from environment or generates a temporary one.
    """
    
    _instance = None
    _cipher_suite: Optional[Fernet] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EncryptionManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the Fernet cipher suite."""
        master_key = os.getenv("MAYA_MASTER_KEY")
        
        if not master_key:
            logger.warning(
                "MAYA_MASTER_KEY not found in environment. "
                "Generating a temporary key for this session. "
                "Encrypted data will be lost upon restart."
            )
            key = Fernet.generate_key()
        else:
            # Try using the key directly if it's a valid Fernet key
            try:
                key_bytes = master_key.encode() if isinstance(master_key, str) else master_key
                # Validate if it's already a valid 32-byte base64-encoded key
                decoded = base64.urlsafe_b64decode(key_bytes)
                if len(decoded) == 32:
                    key = key_bytes
                else:
                    key = self._derive_key(master_key)
            except Exception:
                # If not a valid Fernet key, treat as passphrase and derive
                key = self._derive_key(master_key)
                
        self._cipher_suite = Fernet(key)

    def _derive_key(self, passphrase: str) -> bytes:
        """Derive a 32-byte Fernet key from a passphrase."""
        # Generate and persist a unique salt per installation
        salt_file = os.getenv("MAYA_SALT_FILE", ".maya_salt")
        try:
            if os.path.exists(salt_file):
                with open(salt_file, "rb") as f:
                    salt = f.read()
            else:
                salt = os.urandom(16)
                with open(salt_file, "wb") as f:
                    f.write(salt)
                # Secure the salt file
                os.chmod(salt_file, 0o600)
        except Exception as e:
            logger.warning(f"Failed to persist salt file, falling back to default: {e}")
            salt = b'mayamcp_default_salt_2026'
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key_raw = kdf.derive(passphrase.encode())
        return base64.urlsafe_b64encode(key_raw)
        
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string.
        
        Args:
            data: The plaintext string to encrypt.
            
        Returns:
            The encrypted string (base64 encoded).
        """
        if not data:
            return ""
        if not self._cipher_suite:
            self._initialize() # Should happen in __new__ but just in case
             
        try:
            encrypted_bytes = self._cipher_suite.encrypt(data.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
            
    def decrypt(self, token: str) -> str:
        """
        Decrypt a string.
        
        Args:
            token: The encrypted string (base64 encoded).
            
        Returns:
            The decrypted plaintext string.
        """
        if not token:
            return ""
        if not self._cipher_suite:
            self._initialize()

        try:
            decrypted_bytes = self._cipher_suite.decrypt(token.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
            
def get_encryption_manager() -> EncryptionManager:
    """Factory function to get the singleton manager."""
    return EncryptionManager()
