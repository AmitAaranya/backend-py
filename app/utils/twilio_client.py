from twilio.rest import Client
from app.settings import ENV, logger
from fastapi import HTTPException


class TwilioClient:
    def __init__(self):
        try:
            self.client = Client(ENV.TWILIO_ACCOUNT_SID, ENV.TWILIO_AUTH_TOKEN)
            self.verify_sid = ENV.TWILIO_VERIFY_SERVICE_SID
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            # Allow app to run even if Twilio is not configured
            self.client = None
            self.verify_sid = None

    def send_otp(self, mobile_number: str):
        if not self.client:
            raise HTTPException(status_code=500, detail="Twilio client not configured")
        try:
            self.client.verify.v2.services(self.verify_sid).verifications.create(to=mobile_number, channel="sms")
        except Exception as e:
            logger.error(f"Failed to send OTP to {mobile_number}: {e}")
            raise HTTPException(status_code=500, detail="Failed to send OTP")

    def verify_otp(self, mobile_number: str, otp: str) -> bool:
        if not self.client:
            raise HTTPException(status_code=500, detail="Twilio client not configured")
        try:
            verification_check = self.client.verify.v2.services(self.verify_sid).verification_checks.create(to=mobile_number, code=otp)
            return verification_check.status == "approved"
        except Exception as e:
            logger.error(f"Failed to verify OTP for {mobile_number}: {e}")
            return False

twilio_client = TwilioClient()
