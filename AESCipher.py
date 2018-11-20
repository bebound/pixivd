import base64
import uuid

import pyaes

class AESCipher:
    def __init__(self, key=uuid.UUID(int=uuid.getnode()).hex):
        self.key = key.encode('utf-8')

    def encrypt(self, raw):
        cipher = pyaes.AESModeOfOperationCTR(self.key)
        return base64.b64encode(cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        cipher = pyaes.AESModeOfOperationCTR(self.key)
        return cipher.decrypt(enc).decode('utf-8')

