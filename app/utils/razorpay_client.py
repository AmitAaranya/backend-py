from typing import Optional
import razorpay
from razorpay.errors import SignatureVerificationError


class RazorPayClient:
    def __init__(self, key_id: str, key_secret: str):
        self.client = razorpay.Client(auth=(key_id, key_secret))

    def create_order(self, amount: int, currency: str = "INR", receipt: Optional[str] = None):
        order = self.client.order.create({
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1
        })
        return {"order_id": order["id"], "amount": amount, "currency": currency}

    def verify_payment(self, order_id: str, payment_id: str, signature: str):
        try:
            self.client.utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature
            })
            return {"status": "success", "payment_id": payment_id}
        except SignatureVerificationError:
            return {"status": "error", "message": "Signature verification failed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
