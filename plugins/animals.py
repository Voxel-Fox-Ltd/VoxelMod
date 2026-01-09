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

import random

import aiohttp
import novus as n
from novus import types as t
from novus.ext import client


class Animals(client.Plugin):
    """
    A plugin for animal-related commands.
    """

    @client.command(
        name="cat",
        dm_permission=True,
    )
    async def cat(self, ctx: n.types.CommandI):
        """
        Post a random cat image.
        """

        headers = {
            "User-Agent": self.bot.config.api_keys._user_agent,
            "x-api-key": self.bot.config.api_keys.cat_api_key,
        }
        params = {
            "limit": 1
        }

        async with aiohttp.ClientSession() as session:
            r = await session.get(
                "https://api.thecatapi.com/v1/images/search",
                params=params,
                headers=headers,
            )
            data = await r.json()
        if not data:
            return await ctx.send("I couldn't find that breed of cat.")
        embed = (
            n.Embed(color=random.randint(1, 0xFFFFFF))
            .set_image(data[0]["url"])
        )
        await ctx.send(embeds=[embed])