from fastapi import APIRouter, HTTPException, Request
from app.model.model import CreateOrder, VerifyPayment, UpdateOrder
from app.utils.razorpay_client import razorpay_client
from app.settings import ENV, logger


rpay_rt = APIRouter(prefix="/razorpay", tags=["Razorpay"])


@rpay_rt.post("/create-order/")
def create_order(data: CreateOrder):
    try:
        return razorpay_client.create_order(
            data.amount_rupees_paisa, data.currency, data.receipt
        )

    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@rpay_rt.post("/verify-payment/")
def verify_payment(data: VerifyPayment):
    return razorpay_client.verify_payment(
        data.razorpay_order_id, data.razorpay_payment_id, data.razorpay_signature
    )
