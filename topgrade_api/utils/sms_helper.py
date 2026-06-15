"""
Helper functions for sending SMS (OTP) via the apitxt.com gateway.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_otp_sms(phone_number, otp_code):
    """
    Send an OTP code to a phone number via the apitxt.com SMS gateway.

    The gateway only delivers the code; the OTP is generated and verified by
    our backend. The request is made synchronously so the caller gets
    immediate feedback on delivery success/failure.

    Args:
        phone_number (str): Phone number, with or without +91/+ prefix.
        otp_code (str): The 6-digit OTP to deliver.

    Returns:
        tuple: (success: bool, message: str)
    """
    # apitxt expects the bare 10-digit mobile number (no country code prefix).
    mobile = phone_number.replace('+91', '').replace('+', '').strip()

    authkey = getattr(settings, 'APITXT_AUTHKEY', '')
    if not authkey:
        logger.error("APITXT_AUTHKEY is not configured")
        return False, "SMS service is not configured"

    try:
        response = requests.get(
            settings.APITXT_SENDOTP_URL,
            params={
                'authkey': authkey,
                'mobile': mobile,
                'otp': otp_code,
            },
            timeout=10,
        )

        # apitxt returns HTTP 200 with a JSON body; the "status" field is the
        # real success signal (it can return 200 even on a logical failure).
        # Successful response example:
        # {"status": "success", "message": "Sms OTP Sent Successfully",
        #  "data": {"request_id": "SMS-OTP-...", "mobile": "918610360491"}}
        if response.status_code == 200:
            try:
                body = response.json()
            except ValueError:
                body = {}

            if str(body.get('status', '')).lower() == 'success':
                logger.info("OTP SMS sent to %s", mobile)
                return True, "OTP sent successfully"

            logger.error("apitxt logical failure for %s: %s", mobile, response.text)
            return False, body.get('message') or "Failed to send OTP. Please try again."

        logger.error(
            "apitxt returned status %s for %s: %s",
            response.status_code, mobile, response.text,
        )
        return False, "Failed to send OTP. Please try again."

    except requests.RequestException as e:
        logger.error("Error sending OTP SMS to %s: %s", mobile, str(e))
        return False, "Failed to send OTP. Please try again."
