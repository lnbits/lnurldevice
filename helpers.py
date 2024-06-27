async def registerAtmPayment(device, p):
    lnurldevicepayment = await checkAtmPaymentExists(p)
    data = base64.urlsafe_b64decode(p)
    try:
        pin, amount_in_cent = xor_decrypt(device.key.encode(), data)
    except Exception as exc:
        return {"status": "ERROR", "reason": str(exc)}

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
        return lnurldevicepayment
    except Exception:
        return {"status": "ERROR", "reason": "Could not create ATM payment."}   

async def checkAtmPaymentExists(p):
    lnurldevicepayment = await get_lnurldevicepayment_by_p(p)
    if lnurldevicepayment:
        if lnurldevicepayment.payload == lnurldevicepayment.payhash:
            return {"status": "ERROR", "reason": "Payment already claimed"}
    return lnurldevicepayment