from io import BytesIO
from embit import compact
import base64
import hmac
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis
from .crud import get_recent_lnurldevicepayment, create_lnurldevicepayment
from loguru import logger

async def register_atm_payment(device, p):
    """
    Register an ATM payment to avoid double pull.
    """
    lnurldevicepayment = await get_recent_lnurldevicepayment(p)
    # If the payment is already registered and been paid, return None
    if lnurldevicepayment and lnurldevicepayment.payload == lnurldevicepayment.payhash:
        return None
    # If the payment is already registered and not been paid, return lnurlpayment record
    elif lnurldevicepayment and lnurldevicepayment.payload != lnurldevicepayment.payhash:
        return lnurldevicepayment
    # else create a new lnurlpayment record
    else:
        data = base64.urlsafe_b64decode(p)
        decrypted = xor_decrypt(device.key.encode(), data)
        price_msat = await fiat_amount_as_satoshis(float(decrypted[1]) / 100, device.currency) * 1000 if device.currency != "sat" else decrypted[1] * 1000
        lnurldevicepayment = await create_lnurldevicepayment(deviceid=device.id, payload=p, sats=price_msat / 1000, pin=decrypted[0], payhash="payment_hash")
        return lnurldevicepayment

def xor_decrypt(key, blob):
    s = BytesIO(blob)
    variant = s.read(1)[0]
    if variant != 1:
        raise RuntimeError("Not implemented")
    # reading nonce
    l = s.read(1)[0]
    nonce = s.read(l)
    if len(nonce) != l:
        raise RuntimeError("Missing nonce bytes")
    if l < 8:
        raise RuntimeError("Nonce is too short")

    # reading payload
    l = s.read(1)[0]
    payload = s.read(l)
    if len(payload) > 32:
        raise RuntimeError("Payload is too long for this encryption method")
    if len(payload) != l:
        raise RuntimeError("Missing payload bytes")
    hmacval = s.read()
    expected = hmac.new(
        key, b"Data:" + blob[: -len(hmacval)], digestmod="sha256"
    ).digest()
    if len(hmacval) < 8:
        raise RuntimeError("HMAC is too short")
    if hmacval != expected[: len(hmacval)]:
        raise RuntimeError("HMAC is invalid")
    secret = hmac.new(key, b"Round secret:" + nonce, digestmod="sha256").digest()
    payload = bytearray(payload)
    for i in range(len(payload)):
        payload[i] = payload[i] ^ secret[i]
    s = BytesIO(payload)
    pin = compact.read_from(s)
    amount_in_cent = compact.read_from(s)
    return str(pin), amount_in_cent