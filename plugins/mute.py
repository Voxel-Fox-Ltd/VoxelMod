from datetime import datetime as dt, timedelta
import asyncio

import novus
from novus.ext import client, database as db

from utils import Action, ActionType, create_chat_log, get_datetime_until, delete_messages as delete_messages_util


class Mute(client.Plugin):

    @client.command(
        name="mute",
        options=[
            novus.ApplicationCommandOption(
                name="user",
                type=novus.ApplicationOptionType.user,
                description="The user who you want to mute.",
            ),
            novus.ApplicationCommandOption(
                name="reason",
                type=novus.ApplicationOptionType.string,
                description="The reason for muting this user.",
                required=False,
            ),
            novus.ApplicationCommandOption(
                name="duration",
                type=novus.ApplicationOptionType.string,
                description="The amount of time to mute the member for.",
                required=False,
            ),
            novus.ApplicationCommandOption(
                name="delete_messages",
                type=novus.ApplicationOptionType.boolean,
                description="Whether or not you want to delete messages from the user on their mute.",
                required=False,
            ),
        ],
        default_member_permissions=novus.Permissions(moderate_members=True),
        dm_permission=False,
    )
    async def mute(
            self,
            interaction: novus.types.CommandI,
            user: novus.GuildMember,
            reason: str | None = None,
            duration: str = "",
            delete_messages: bool = False) -> None:
        """
        Mutes a member from chatting in the guild until a certain time.
        """

        await interaction.defer()
        async with db.Database.acquire() as conn:
            log_id = await create_chat_log(conn, interaction.channel)

        # Get duration
        future = dt.utcnow() + get_datetime_until(duration)
        try:
            await user.edit(timeout_until=future, reason=reason)
        except novus.Forbidden:
            await interaction.send(
                "I'm missing the relevant permissions to timeout that user."
            )
            return

        # Delete messages from the user
        if delete_messages and interaction.app_permissions.manage_messages:
            asyncio.create_task(
                delete_messages_util(
                    interaction.channel,
                    user,
                    reason="The user has been muted."
                    )
                )

        # Create an action for the infraction
        assert interaction.guild
        async with db.Database.acquire() as conn:
            await Action.create(
                conn,
                guild_id=interaction.guild.id,
                user_id=user.id,
                action_type=ActionType.MUTE,
                reason=reason,
                moderator_id=interaction.user.id,
                log_id=log_id
            )

        # Send a confirmation message
        relative = novus.utils.format_timestamp(future, "R")
        await interaction.send(
            "**{user}** has been muted - they will be unmuted {time}."
            .format(user=user.mention, time=relative)
        )

    @client.command(
        name="unmute",
        options=[
            novus.ApplicationCommandOption(
                name="user",
                type=novus.ApplicationOptionType.user,
                description="The user who you want to unmute.",
            ),
        ],
        default_member_permissions=novus.Permissions(moderate_members=True),
        dm_permission=False,
    )
    async def unmute(
            self,
            interaction: novus.types.CommandI,
            user: novus.GuildMember) -> None:
        """
        Unmutes a member from a guild.
        """

        await interaction.defer()

        # Create an action for the infraction
        assert interaction.guild
        async with db.Database.acquire() as conn:
            await Action.create(
                conn,
                guild_id=interaction.guild.id,
                user_id=user.id,
                action_type=ActionType.UNMUTE,
                moderator_id=interaction.user.id,
            )

        # Try unmuting the user
        try:
            await user.edit(timeout_until=None)
        except novus.Forbidden:
            await interaction.send(
                "I'm missing the relevant permissions to timeout that user."
            )
            return

        # Send a confirmation message
        await interaction.send(
            "**{user}** has been unmuted :3c"
            .format()
        )
