from io import BytesIO
from embit import compact
import base64
import hmac
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis
from .crud import get_lnurldevicepayment_by_p, create_lnurldevicepayment
from loguru import logger
async def registerAtmPayment(device, p):
    lnurldevicepayment = await checkAtmPaymentExists(p)
    logger.debug(lnurldevicepayment)
    if lnurldevicepayment:
        return lnurldevicepayment
    data = base64.urlsafe_b64decode(p)
    try:
        pin, amount_in_cent = xor_decrypt(device.key.encode(), data)
    except Exception as exc:
        return {"status": "ERROR", "reason": str(exc)}
    logger.debug(data)
    price_msat = (
        await fiat_amount_as_satoshis(float(amount_in_cent) / 100, device.currency)
        if device.currency != "sat"
        else amount_in_cent
    ) * 1000

    try:
        lnurldevicepayment = await create_lnurldevicepayment(
            deviceid=device.id,
            payload=p,
            sats=price_msat * 1000,
            pin=pin,
            payhash="payment_hash",
        )
        logger.debug(lnurldevicepayment)
        return lnurldevicepayment
    except Exception:
        return {"status": "ERROR", "reason": "Could not create ATM payment."}


async def checkAtmPaymentExists(p):
    lnurldevicepayment = await get_lnurldevicepayment_by_p(p)
    if lnurldevicepayment:
        if lnurldevicepayment.payload == lnurldevicepayment.payhash:
            return {"status": "ERROR", "reason": "Payment already claimed"}
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