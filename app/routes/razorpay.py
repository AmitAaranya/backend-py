from fastapi import APIRouter, HTTPException, Request
from app.model import CreateOrder, VerifyPayment
from app.utils.razorpay_client import RazorPayClient
from app.settings import ENV, logger


rpay_rt = APIRouter(prefix="/razorpay", tags=["Razorpay"])


client = RazorPayClient(ENV.RAZORPAY_KEY_ID, ENV.RAZORPAY_KEY_SECRET)


@rpay_rt.post("/create-order/")
def create_order(data: CreateOrder):
    try:
        order_amount = data.amount_rupees * 100   # convert to paise
        return client.create_order(order_amount, data.currency, data.receipt)

    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@rpay_rt.post("/verify-payment/")
def verify_payment(data: VerifyPayment):
    return client.verify_payment(data.razorpay_order_id, data.razorpay_payment_id, data.razorpay_signature)
