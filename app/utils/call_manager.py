from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from app.core import db
from app.model import TableConfig
from app.settings import logger


class CallStatus(str, Enum):
    requested = "requested"
    fulfilled = "fulfilled"
    cancelled = "cancelled"


class CallRequestModel(BaseModel):
    id: str
    paid: bool
    user_id: str
    user_name: str
    agent_id: Optional[str] = None
    message: str
    request_time: str
    fulfilled_time: Optional[str] = None
    status: CallStatus
    remarks: Optional[str] = None


class CallManager:
    def __init__(self):
        ...

    def initiate_call_request(self, id: str, user_id: str, user_name: str, paid: bool,  message: str, request_time: str, agent_id: Optional[str] = None):
        try:
            data = CallRequestModel(id=id, user_id=user_id, user_name=user_name, paid=paid,
                                    agent_id=agent_id, message=message, request_time=request_time,
                                    status=CallStatus.requested)

            db.add_data(TableConfig.CALL_REQUEST.value,
                        data.id, data.model_dump())
            logger.debug(f"Call request initiated successfully {data.id}")
            return True
        except Exception as e:
            logger.error(f"Error initiating call request: {e}")
            return False

    def fulfilled_call_request(self, id: str, remarks: Optional[str] = None):
        try:
            data_ref = db.get_doc_ref(TableConfig.CALL_REQUEST.value, id)
            data_ref.update(
                {"status": CallStatus.fulfilled, "remarks": remarks, "fulfilled_time": str(datetime.now())})
            logger.debug(f"Call request fulfilled successfully {id}")
            return True
        except Exception as e:
            logger.error(f"Error fulfilling call request: {e}")
            return False

    def cancel_call_request(self, id: str, remarks: Optional[str] = None):
        try:
            data_ref = db.get_doc_ref(TableConfig.CALL_REQUEST.value, id)
            data_ref.update(
                {"status": CallStatus.cancelled, remarks: remarks})
            logger.debug(f"Call request cancelled successfully {id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling call request: {e}")
            return False

    def get_call_request(self, id: str):
        try:
            data = db.read_data(TableConfig.CALL_REQUEST.value, id)
            logger.debug(f"Call request fetched successfully {id}")
            return data
        except Exception as e:
            logger.error(f"Error fetching call request: {e}")
            return {}

    def get_all_call_requests(self):
        try:
            data = db.read_all_documents(TableConfig.CALL_REQUEST.value)
            logger.debug(f"All call requests fetched successfully")
            return data
        except Exception as e:
            logger.error(f"Error fetching all call requests: {e}")
            return []
