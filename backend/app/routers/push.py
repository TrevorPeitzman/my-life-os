from fastapi import APIRouter

from app.models import PushSubscription
from app.services import push_service

router = APIRouter(prefix="/push", tags=["push"])


@router.post("/subscribe")
def subscribe(sub: PushSubscription) -> dict:
    push_service.subscribe(sub.endpoint, sub.keys)
    return {"subscribed": True}


@router.post("/unsubscribe")
def unsubscribe(sub: PushSubscription) -> dict:
    push_service.unsubscribe(sub.endpoint)
    return {"unsubscribed": True}
