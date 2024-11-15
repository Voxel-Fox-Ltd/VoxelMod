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
from novus.ext import client

from utils import delete_messages


class Clear(client.Plugin):

    @client.command(
        name="clear",
        options=[
            novus.ApplicationCommandOption(
                name="user",
                type=novus.ApplicationOptionType.USER,
                description="The user who you want to clear messages from.",
                required=False
            ),
            novus.ApplicationCommandOption(
                name="num_messages",
                type=novus.ApplicationOptionType.NUMBER,
                description="The number of messages to clear",
                required=False,
            ),
            novus.ApplicationCommandOption(
                name="reason",
                type=novus.ApplicationOptionType.STRING,
                description="The reason for clearing these messages.",
                required=False,
            ),
        ],
        default_member_permissions=novus.Permissions(manage_messages=True),
        dm_permission=False,
    )
    async def clear(
            self,
            ctx: novus.types.CommandGI,
            user: novus.GuildMember | None = None,
            num_messages: int = 100,
            reason: str | None = None) -> None:
        """
        Clears a number of messages from a user
        """

        await ctx.defer(ephemeral=True)
        await delete_messages(ctx.channel, user, num_messages, reason)
        content = "Cleared last {} messages".format(num_messages)
        if user:
            content += " from **{}**".format(user.mention)
        content += "."
        await ctx.send(content, ephemeral=True)
