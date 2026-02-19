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
            try:
                # Ensure key is valid base64url-encoded 32-byte key
                # If the user provided a raw string passphrase, we might want to derive a key,
                # but for now we assume they followed the generate_key() instructions.
                key = master_key.encode() if isinstance(master_key, str) else master_key
                Fernet(key) # Validate key format
            except Exception as e:
                logger.error(f"Invalid MAYA_MASTER_KEY format: {e}. Falling back to temporary key.")
                key = Fernet.generate_key()
                
        self._cipher_suite = Fernet(key)
        
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
