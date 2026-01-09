"""
Copyright (c) Kae Bartlett

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

from datetime import datetime as dt
import itertools
from typing import cast

import novus
from novus.ext import client, database as db

from utils import Action, ActionType, create_chat_log,  get_datetime_until


class Ban(client.Plugin):

    @client.command(
        name="ban",
        options=[
            novus.ApplicationCommandOption(
                name="user",
                type=novus.ApplicationOptionType.USER,
                description="The user who you want to ban.",
            ),
            novus.ApplicationCommandOption(
                name="reason",
                type=novus.ApplicationOptionType.STRING,
                description="The reason for banning this user.",
                required=False,
            ),
            novus.ApplicationCommandOption(
                name="delete_days",
                type=novus.ApplicationOptionType.NUMBER,
                description="The number of days of messages that you want to delete.",
                required=False,
            ),
            novus.ApplicationCommandOption(
                name="duration",
                type=novus.ApplicationOptionType.STRING,
                description="The amount of time to ban the user for.",
                required=False,
            ),
        ],
        default_member_permissions=novus.Permissions(ban_members=True),
        dm_permission=False,
    )
    async def ban(
            self,
            interaction: novus.types.CommandI,
            user: novus.GuildMember,
            *,
            reason: str | None = None,
            delete_days: float = 1.0,
            duration: str | None = None) -> None:
        """
        Ban a member from the guild.
        """

        await interaction.defer()
        async with db.Database.acquire() as conn:
            log_id = await create_chat_log(conn, interaction.channel)

        # Get duration
        future: dt | None = None
        if duration:
            future = dt.utcnow() + get_datetime_until(duration)
        try:
            await interaction.guild.ban(
                user,
                delete_message_seconds=int(delete_days * (24 * 60 * 60)),
                reason=reason,
            )
        except novus.Unauthorized:
            await interaction.send(
                "I'm missing the relevant permissions to ban that user.",
            )
            return

        # Create an action for the infraction
        assert interaction.guild
        async with db.Database.acquire() as conn:
            await Action.create(
                conn,
                guild_id=interaction.guild.id,
                user_id=user.id,
                action_type=ActionType.BAN,
                reason=reason,
                moderator_id=interaction.user.id,
                log_id=log_id
            )
            if future is not None:
                await conn.execute(
                    """
                    INSERT INTO
                        temporary_bans
                        (
                            guild_id,
                            user_id,
                            expiry_time
                        )
                    VALUES
                        (
                            $1,
                            $2,
                            $3
                        )
                    ON CONFLICT (guild_id, user_id)
                    DO UPDATE
                    SET
                        expiry_time = excluded.expiry_time
                    """,
                    interaction.guild.id,
                    user.id,
                    future,
                )
        await interaction.send(f"**{user.mention}** has been banned.")

    @client.command(
        name="unban",
        options=[
            novus.ApplicationCommandOption(
                name="user_id",
                type=novus.ApplicationOptionType.STRING,
                description="The ID of the user that you want to unban.",
            ),
        ],
        default_member_permissions=novus.Permissions(ban_members=True),
        dm_permission=False,
    )
    async def unban(
            self,
            interaction: novus.types.CommandI,
            user_id: str) -> None:
        """
        Unban a member from a guild.
        """

        if not user_id.isdigit():
            return await interaction.send("That is not a valid user ID.")
        user_id_int: int = int(user_id)

        await interaction.defer()

        assert interaction.guild
        async with db.Database.acquire() as conn:
            await Action.create(
                conn,
                guild_id=interaction.guild.id,
                user_id=user_id_int,
                action_type=ActionType.UNBAN,
                moderator_id=interaction.user.id,
            )

        fake_guild = novus.Object(interaction.guild.id, state=self.bot.state)
        success = await self.try_unban(fake_guild, user_id_int)
        if not success:
            return await interaction.send("I was unable to unban that user.")
        async with db.Database.acquire() as conn:
            await conn.fetch(
                """
                DELETE FROM
                    temporary_bans
                WHERE
                    user_id = $1
                    AND guild_id = $2
                """,
                user_id_int,
                interaction.guild.id,
            )
        await interaction.send(f"**<@{user_id_int}>** has been unbanned.")

    @client.loop(60)
    async def unban_loop(self):
        """
        Loop through any banned users, unbanning them by user ID.
        """

        # Get all users whose ban expiry time has passed
        async with db.Database.acquire() as conn:
            rows = await conn.fetch(
                """
                DELETE FROM
                    temporary_bans
                WHERE
                    expiry_time <= TIMEZONE('UTC', NOW())
                RETURNING
                    *
                """
            )
        for row in rows:
            row = cast(dict[str, int], row)
            guild_id = row["guild_id"]
            fake_guild = novus.Object(guild_id, state=self.bot.state)
            user_id = row["user_id"]
            if not await self.try_unban(fake_guild, user_id):
                break

    async def try_unban(
            self,
            guild: novus.abc.StateSnowflake,
            user_id: int) -> bool:
        """
        Try and unban a given user from the guild

        hellu~ -Dora :3

        Parameters
        ----------
        guild : novus.abc.StateSnowflake
            The guild object that you want to unban the user from.
        user_id : int
            The ID of the user to be unbanned.

        Returns
        -------
        bool
            Whether or not the bot can unban in the provided guild.
        """

        try:
            await novus.Guild.unban(
                guild,
                user_id,
                reason="Temporary ban has expired.",
            )
        except novus.Forbidden:
            self.log.info(
                "Missing permissions to unban users in guild %s",
                guild.id,
            )
            return False  # Don't try and unban in guilds where we can't unban
        except novus.NotFound:
            self.log.info(
                "User %s in guild %s is already unbanned",
                user_id, guild.id,
            )
        except Exception as e:
            self.log.info(
                "Failed to unban user %s in guild %s (%s)",
                user_id, guild.id, e,
            )
        else:
            self.log.info(
                "Unbanned user %s in guild %s",
                user_id, guild.id,
            )
        return True
