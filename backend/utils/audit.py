from typing import Any, Dict, Optional

from backend.database.connection import get_connection


async def log_audit(
    user_id: Optional[int],
    action: str,
    entity_name: str,
    record_id: Optional[int] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None
) -> None:
    """
    Log an audit entry to the AUDIT_LOG table.
    
    Args:
        user_id: ID of the user performing the action (None for system actions)
        action: Action performed (CREATE, UPDATE, DELETE, DEACTIVATE, LOGIN, etc.)
        entity_name: Name of the entity/table affected
        record_id: ID of the record affected
        old_value: Previous value (JSON string or description)
        new_value: New value (JSON string or description)
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO AUDIT_LOG (
                        AUDIT_ID, USER_ID, ACTION, ENTITY_NAME, RECORD_ID,
                        OLD_VALUE, NEW_VALUE, ACTION_TIMESTAMP
                    ) VALUES (
                        SEQ_AUDIT_LOG.NEXTVAL, :user_id, :action, :entity_name, :record_id,
                        :old_value, :new_value, CURRENT_TIMESTAMP
                    )
                    """,
                    {
                        "user_id": user_id,
                        "action": action,
                        "entity_name": entity_name,
                        "record_id": record_id,
                        "old_value": old_value,
                        "new_value": new_value
                    }
                )
                conn.commit()
    except Exception as e:
        # Log audit failures but don't break the main operation
        import logging
        logging.warning(f"Audit logging failed: {e}")


async def log_create(user_id: int, entity_name: str, record_id: int, new_value: str) -> None:
    """Log a CREATE action."""
    await log_audit(user_id, "INSERT", entity_name, record_id, None, new_value)


async def log_update(user_id: int, entity_name: str, record_id: int, old_value: str, new_value: str) -> None:
    """Log an UPDATE action."""
    await log_audit(user_id, "UPDATE", entity_name, record_id, old_value, new_value)


async def log_delete(user_id: int, entity_name: str, record_id: int, old_value: str) -> None:
    """Log a DELETE action."""
    await log_audit(user_id, "DELETE", entity_name, record_id, old_value, None)


async def log_deactivate(user_id: int, entity_name: str, record_id: int, old_value: str) -> None:
    """Log a DEACTIVATE action (soft delete)."""
    await log_audit(user_id, "UPDATE", entity_name, record_id, old_value, "STATUS=INACTIVE")


async def log_user_management(user_id: int, action: str, target_user_id: int, details: str) -> None:
    """Log user management actions."""
    # Map action to valid audit actions
    action_map = {
        "CREATE": "INSERT",
        "UPDATE": "UPDATE",
        "DELETE": "DELETE",
        "DEACTIVATE": "UPDATE",
    }
    audit_action = action_map.get(action, "INSERT")
    await log_audit(user_id, audit_action, "APP_USER", target_user_id, None, details)