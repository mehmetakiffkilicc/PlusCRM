from decimal import Decimal
from ...models import AISession, AIMessage

def create_session(user, title="Yeni Sohbet", model_name="gemini-2.0-flash"):
    return AISession.objects.create(user=user, title=title, model_name=model_name)

def get_session(user, session_id):
    try:
        return AISession.objects.get(id=session_id, user=user)
    except AISession.DoesNotExist:
        return None

def add_message(session, role, content, tool_calls=None, input_tokens=0, output_tokens=0):
    return AIMessage.objects.create(
        session=session,
        role=role,
        content=content,
        tool_calls=tool_calls or [],
        input_tokens=input_tokens,
        output_tokens=output_tokens
    )

def get_session_history(session):
    return AIMessage.objects.filter(session=session).order_by('created_at')

def update_session_usage(session, input_tokens, output_tokens, cost=Decimal('0')):
    session.total_tokens += input_tokens + output_tokens
    session.total_cost += Decimal(str(cost)) if not isinstance(cost, Decimal) else cost
    session.save()
