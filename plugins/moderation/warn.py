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

import novus
from novus.ext import client, database as db

from utils import Action, ActionType, create_chat_log


class Warn(client.Plugin):

    @client.command(
        name="warn",
        options=[
            novus.ApplicationCommandOption(
                name="user",
                type=novus.ApplicationOptionType.USER,
                description="The user who you want to warn.",
            ),
            novus.ApplicationCommandOption(
                name="reason",
                type=novus.ApplicationOptionType.STRING,
                description="The reason for warning this user.",
                required=False,
            ),
        ],
        default_member_permissions=novus.Permissions(moderate_members=True),
        dm_permission=False,
    )
    async def warn(
            self,
            interaction: novus.types.CommandI,
            user: novus.GuildMember,
            reason: str | None = None) -> None:
        """
        Warns a member, adding an infraction to their history
        """

        await interaction.defer()
        async with db.Database.acquire() as conn:
            log_id = await create_chat_log(conn, interaction.channel)  # pyright: ignore

        # Create an action for the infraction
        assert interaction.guild
        async with db.Database.acquire() as conn:
            await Action.create(
                conn,
                guild_id=interaction.guild.id,
                user_id=user.id,
                action_type=ActionType.WARN,
                reason=reason,
                moderator_id=interaction.user.id,
                log_id=log_id
            )
        await interaction.send(f"A warning has been added to **{user.mention}**.")
