from typing import Optional
import razorpay
from razorpay.errors import SignatureVerificationError

from app.settings import ENV


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
        return {"order_id": order["id"]}

    def get_order_details(self, order_id: str):
        """
        Docstring for get_order_details

        :param order_id: order id of razorpay
        :type order_id: str

        :return: Order details
        :rtype: dict

        Example:
        {
            "id": "order_RnBCcl9s9PoPzk",
            "entity": "order",
            "amount": 10000,
            "amount_paid": 0,
            "amount_due": 10000,
            "currency": "INR",
            "receipt": "string",
            "offer_id": null,
            "status": "created",
            "attempts": 0,
            "notes": [],
            "created_at": 1764773856,
            "description": null,
            "checkout": null
            }
        """
        try:
            order_details = self.client.order.fetch(order_id)
            return order_details
        except Exception as e:
            return {"error": str(e)}

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


razorpay_client = RazorPayClient(ENV.RAZORPAY_KEY_ID, ENV.RAZORPAY_KEY_SECRET)
