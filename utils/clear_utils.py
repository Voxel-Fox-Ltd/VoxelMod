from __future__ import annotations

from typing import TYPE_CHECKING

from .message_queuer import MaxLenList

if TYPE_CHECKING:
    import novus

__all__ = (
    "delete_messages",
)


async def delete_messages(
            channel: novus.abc.StateSnowflake,
            user: novus.abc.Snowflake | None,
            num_messages: int = 100,
            reason: str | None = None) -> None:
        """
        Delete messages from a user in the interaction channel.

        Parameters
        ----------
        channel : novus.abc.StateSnowflake
            The channel that you want to delete messages in.
        user : novus.abc.Snowflake
            The user whose messages you want to delete.
            If no one is provided, the bot will ignore author checks
        num_messages : int
            The number of messages to delete.
        reason : str
            The reason for deleting these messages
        """

        # Get messages
        messages = await novus.Channel.fetch_messages(channel)  # pyright: ignore

        # Filter to only ones sent by the user
        delete_ids: MaxLenList[int] = MaxLenList(num_messages)
        last_message: novus.Message | None = None
        for last_message in messages:
            if user and last_message.author.id != user.id:
                continue
            delete_ids.append(last_message.id)

        # Delete appropriately
        if not delete_ids:
            return  # No messages to delete
        elif len(delete_ids) == 1:
            assert last_message
            await last_message.delete(reason=reason)
        else:
            await novus.Channel.bulk_delete_messages(
                channel,
                delete_ids,
                reason=reason,
            )
