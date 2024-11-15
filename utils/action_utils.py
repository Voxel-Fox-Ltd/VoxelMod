from __future__ import annotations

from enum import Enum
from datetime import datetime as dt
from typing import TYPE_CHECKING, Any
from typing_extensions import Self
import uuid

import novus

from plugins.moderation.messages import MessageHandler

if TYPE_CHECKING:
    import asyncpg

__all__ = (
    "ActionType",
    "Action",
    "create_chat_log",
)


# cat/Dora wus here :3c(and hero/george) kae was also here briefly. we coded this actually
# Kae just got the credit and my comments got deleted ;-; this is catism
# I believe in you kae!! -Dowo :3


class ActionType(Enum):
    """
    The type of action that was applied.

    Attributes
    ----------
    REPORT: int
        An enum representing a 'report' action.
    WARN: int
        An enum representing a 'warn' action.
    MUTE: int
        An enum representing a 'mute' action.
    BAN: int
        An enum representing a 'ban' action.
    """

    REPORT = 0
    WARN = 1

    MUTE = 2
    UNMUTE = 3

    BAN = 4
    UNBAN = 5


class Action:
    """
    An action that was applied.

    Attributes
    ----------
    guild_id: int
    user_id: int
    action_type: ActionType
    reason: str | None
    moderator_id: int
    timestamp: dt | None
    """

    guild_id: int
    user_id: int
    action_type: ActionType
    reason: str | None
    moderator_id: int
    timestamp: dt | None

    def __init__(
            self,
            guild_id: int,
            user_id: int,
            action_type: ActionType,
            reason: str | None,
            moderator_id: int,
            timestamp: dt | None):
        self.guild_id = guild_id
        self.user_id = user_id
        self.action_type = action_type
        self.reason = reason
        self.moderator_id = moderator_id
        self.timestamp = timestamp

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Self:
        return cls(
            guild_id=row["guild_id"],
            user_id=row["user_id"],
            action_type=ActionType[row["action_type"]],
            reason=row["reason"],
            moderator_id=row["moderator_id"],
            timestamp=row["timestamp"],
        )

    @classmethod
    async def create(
            cls,
            db: asyncpg.Connection,
            *,
            guild_id: int,
            user_id: int,
            action_type: ActionType,
            moderator_id: int,
            log_id: str | None = None,
            reason: str | None = None,
            timestamp: novus.utils.DiscordDatetime | None = None) -> Action:
        """
        Create and store a new action, returning the created action.

        Parameters
        ----------
        db
            An open database connection.
        guild_id: int
            The ID of the guild where the action took place.
        user_id: int
            The ID of the user who the action was performed on.
        action_type: ActionType
            The action that was applied.
        reason: str
            The reason that the action happened.
        moderator_id: int
            The moderator who performed the action.
        timestamp: dt | None
            The timestamp that the action occured.

        Returns
        -------
        Action
            The action that was created.
        """

        rows = await db.fetch(
            """
            INSERT INTO
                actions
                (  
                    guild_id,
                    user_id,
                    action_type,
                    moderator_id,
                    log_id,
                    reason,
                    timestamp
                )
            VALUES
                (
                    $1,
                    $2,
                    $3,
                    $4,
                    $5,
                    $6,
                    $7
                )
            RETURNING
                *
            """,
            guild_id,
            user_id,
            action_type.name,
            moderator_id,
            log_id or None,
            reason or None,
            timestamp.naive if timestamp else novus.utils.utcnow().naive,
        )

        return cls.from_row(rows[0])


async def create_chat_log(
        db: asyncpg.Connection,
        channel: novus.Channel,
        num_messages: int = 100) -> str:
    """
    Create a log from the text channel.

    Parameters
    ----------
    channel: novus.GuildTextChannel
        The channel that you want to make a chat log from.
    num_messages: int
        The number of messages that you want to log.

    Returns
    -------
    str
        A code assocaited with the chat log.
    """

    messages_found: list[novus.Message] = MessageHandler.message_cache[channel.id][:-num_messages]

    message_log_id = str(uuid.uuid4())
    message_args: list[tuple] = []
    for message in messages_found:
        message_args.append((
            message_log_id,
            message.id,
            message.author.id,
            message.author.username,
            message.content,
        ))

    await db.executemany(
        """
        INSERT INTO
            message_logs
            (
                log_id,
                message_id,
                author_id,
                author_name,
                message_content
            )
        VALUES
            (
                $1,
                $2,
                $3,
                $4,
                $5
            )
        """,
        message_args,
    )

    return message_log_id
