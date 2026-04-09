from datetime import datetime


def is_subscription_active(account) -> bool:
    if not account:
        return False

    if bool(getattr(account, "subscription_active", False)):
        return True

    paid_until = getattr(account, "paid_until", None)
    if paid_until and paid_until >= datetime.utcnow():
        return True

    return False


def is_bot_paused(account) -> bool:
    if not account:
        return True

    return bool(getattr(account, "is_paused", False))


def is_whatsapp_connected(account) -> bool:
    if not account:
        return False

    return bool(getattr(account, "green_connected", False))


def is_manager_connected(conversation) -> bool:
    if not conversation:
        return False

    return bool(getattr(conversation, "manager_connected", False))


def can_bot_reply(account, conversation) -> bool:
    if not is_whatsapp_connected(account):
        return False

    if not is_subscription_active(account):
        return False

    if is_bot_paused(account):
        return False

    if is_manager_connected(conversation):
        return False

    return True


def get_bot_block_reason(account, conversation) -> str:
    if not account:
        return "account_not_found"

    if not is_whatsapp_connected(account):
        return "whatsapp_not_connected"

    if not is_subscription_active(account):
        return "subscription_inactive"

    if is_bot_paused(account):
        return "bot_paused"

    if is_manager_connected(conversation):
        return "manager_connected"

    return "allowed"