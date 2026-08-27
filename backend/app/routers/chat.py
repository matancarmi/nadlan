from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ChatMessage
from ..schemas import ChatMessageOut, ChatRequest
from ..security import require_session
from ..services.chat_advisor import generate_reply

router = APIRouter(prefix="/api/chat", tags=["chat"], dependencies=[Depends(require_session)])


@router.get("/messages", response_model=list[ChatMessageOut])
def get_messages(db: Session = Depends(get_db)):
    return db.query(ChatMessage).order_by(ChatMessage.created_at).all()


@router.post("/messages", response_model=ChatMessageOut)
def post_message(payload: ChatRequest, db: Session = Depends(get_db)):
    history = db.query(ChatMessage).order_by(ChatMessage.created_at).all()
    conversation = [{"role": m.role, "content": m.content} for m in history]

    user_msg = ChatMessage(role="user", content=payload.content)
    db.add(user_msg)
    db.commit()

    reply_text = generate_reply(db, conversation, payload.content)

    assistant_msg = ChatMessage(role="assistant", content=reply_text)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg
