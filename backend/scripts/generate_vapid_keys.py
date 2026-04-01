#!/usr/bin/env python3
"""
generate_vapid_keys.py — Generate VAPID key pair for web push notifications.

Uses the `cryptography` library directly (already installed as a pywebpush
dependency) to avoid API breakage in newer versions of py_vapid.

Run from inside your virtualenv:
    python backend/scripts/generate_vapid_keys.py

Then paste the output into your .env file.
"""
import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

# Generate EC P-256 key pair (the only curve VAPID accepts)
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

# Private key: raw 32-byte big-endian integer, base64url encoded (no padding)
# This is the format pywebpush 2.x's Vapid.from_raw() expects.
private_int = private_key.private_numbers().private_value
private_b64 = base64.urlsafe_b64encode(private_int.to_bytes(32, "big")).rstrip(b"=").decode()

# Public key: uncompressed point (0x04 || x || y = 65 bytes), base64url encoded
# This is what the browser's pushManager.subscribe({ applicationServerKey }) expects.
public_raw = public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
public_b64 = base64.urlsafe_b64encode(public_raw).rstrip(b"=").decode()

print("# Add these lines to your .env file:")
print(f"VAPID_PRIVATE_KEY={private_b64}")
print(f"VAPID_PUBLIC_KEY={public_b64}")
