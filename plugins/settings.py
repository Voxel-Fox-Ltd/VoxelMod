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

from typing import Any

import novus as n
from novus import types as t
from novus.ext import client, database as db


class Settings(client.Plugin):

    @staticmethod
    async def set_guild_item(column: str, guild_id: int, value: Any) -> None:
        """
        Set an item in the database.

        Parameters
        ----------
        column : str
            The name of the column that you want to set the given value to.
        guild_id : int
            The ID of the guild that you want to set the data for.
        value : Any
            The value that you want to set.
        """

        async with db.Database.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO
                    guild_settings
                    (
                        guild_id,
                        {0}
                    )
                VALUES
                    (
                        $1,
                        $2
                    )
                ON CONFLICT (guild_id)
                DO UPDATE
                SET
                    {0} = excluded.{0}
                """.format(column),
                guild_id,
                value,
            )

    @client.command(
        name="settings channel report",
        options=[
            n.ApplicationCommandOption(
                name="channel",
                type=n.ApplicationOptionType.CHANNEL,
                description="The channel where you want reports to funnel to.",
                channel_types=[n.ChannelType.GUILD_TEXT],
            ),
        ],
        default_member_permissions=n.Permissions(manage_guild=True),
    )
    async def report_channel_settings(
            self,
            interaction: t.CommandI,
            channel: n.Channel) -> None:
        """
        Set the report channel.
        """

        await interaction.defer(ephemeral=True)
        assert interaction.guild
        await self.set_guild_item(
            "report_channel_id",
            interaction.guild.id,
            channel.id,
        )
        await interaction.send(
            f"The report channel has been set to **{channel.mention}**.",
            ephemeral=True,
        )

    @client.command(
        name="settings channel message_logs",
        options=[
            n.ApplicationCommandOption(
                name="channel",
                type=n.ApplicationOptionType.CHANNEL,
                description="The channel where you want message logs to funnel to.",
                channel_types=[n.ChannelType.GUILD_TEXT],
            ),
        ],
        default_member_permissions=n.Permissions(manage_guild=True),
    )
    async def message_logs_channel_settings(
            self,
            interaction: t.CommandI,
            channel: n.Channel) -> None:
        """
        Set the message logs channel.
        """

        await interaction.defer(ephemeral=True)
        assert interaction.guild
        await self.set_guild_item(
            "message_channel_id",
            interaction.guild.id,
            channel.id,
        )
        await interaction.send(
            f"The message logs channel has been set to **{channel.mention}**.",
            ephemeral=True,
        )

    @client.command(
        name="settings role staff",
        options=[
            n.ApplicationCommandOption(
                name="role",
                type=n.ApplicationOptionType.ROLE,
                description="The role that all of staff members have.",
            ),
        ],
        default_member_permissions=n.Permissions(manage_guild=True),
    )
    async def staff_role_settings(
            self,
            interaction: t.CommandI,
            role: n.Role) -> None:
        """
        Set the staff role.
        """

        await interaction.defer(ephemeral=True)
        assert interaction.guild
        await self.set_guild_item(
            "staff_role_id",
            interaction.guild.id,
            role.id,
        )
        await interaction.send(
            f"The report channel has been set to **{role.mention}**.",
            allowed_mentions=n.AllowedMentions.none(),
            ephemeral=True,
        )

    @client.command(
        name="settings custom-role allowed",
        options=[
            n.ApplicationCommandOption(
                name="role",
                type=n.ApplicationOptionType.ROLE,
                description="Users with this role can create custom roles.",
            ),
        ],
        default_member_permissions=n.Permissions(manage_guild=True),
    )
    async def allowed_custom_role_settings(
            self,
            ctx: t.CommandI,
            role: n.Role) -> None:
        """
        Set the custom role allowed role.
        """

        await ctx.defer(ephemeral=True)
        assert ctx.guild
        await self.set_guild_item("custom_role_allowed_role_id", ctx.guild.id, role.id)
        await ctx.send(
            f"The custom role allowed role has been set to **{role.mention}**.",
            allowed_mentions=n.AllowedMentions.none(),
            ephemeral=True,
        )

    @client.command(
        name="settings custom-role beneath",
        options=[
            n.ApplicationCommandOption(
                name="role",
                type=n.ApplicationOptionType.ROLE,
                description="Created custom roles will be moved beneath this role.",
            ),
        ],
        default_member_permissions=n.Permissions(manage_guild=True),
    )
    async def beneath_custom_role_settings(
            self,
            ctx: t.CommandI,
            role: n.Role) -> None:
        """
        Set the custom role beneath role.
        """

        await ctx.defer(ephemeral=True)
        assert ctx.guild
        await self.set_guild_item("custom_role_beneath_role_id", ctx.guild.id, role.id)
        await ctx.send(
            f"The custom role beneath role has been set to **{role.mention}**.",
            allowed_mentions=n.AllowedMentions.none(),
            ephemeral=True,
        )
