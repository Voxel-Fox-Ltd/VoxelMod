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

import asyncio
import re

from novus.ext import client
import novus as n
from novus import types as t, utils as nu

import utils as u


class MeowChat(client.Plugin):

    MEOW_CHATS: set[int] = set()
    MEOW_KEYWORDS: set[str | re.Pattern] = {
        "meow",
        "mrow",
        "mreow",
        "mew",
        "miw",
        "maw",
        "wi",
        "nya",
        "x3",
        ":3",
        "=3",
        ";3",
        "^w^",
        ":<",
        "uwu",
        "owo",
        "ono",
        "rawr",
        "yip",
        "mlem",
        re.compile(r"\bmrr+p\b", re.IGNORECASE),
        # emotes!
        "🐱",
        "😿",
        "😻",
        "😹",
        "😽",
        "😾",
        "🙀",
        "😸",
        "😺",
        "😼",
        # VFL custom emotes :3
        ":catgun_cato:",
        ":catlipbite:",
        ":catpolice_cato:",
        ":catshrug_cato:",
        ":catsip_cato:",
        ":catsob:",
        ":catsparkle_cato:",
        ":catthinking_cato:",
        ":catunamused_cato:",
        ":catwhat:",
        ":crycat:",
        ":dadcat:",
        ":finnnyah:",
        ":hiss:",
        ":meowo:",
        ":nyah:",
        ":sadcat:",
        ":sadcatcowboy:",
        ":sadcatccream:",
        ":sadcatthumbsup:",
        ":blobsatstab:",
        ":blobsatsransseart:",
        ":cathyperhug:",
        ":catjam:",
        ":catpat:",
        ":catpop:",
        ":catvibe:",
        ":kittycatch:",
        ":myaa:",
        ":nodcat:",
        ":paws:",
        ":tigervibe:",
    }
    MEOW_TIMEOUT_TASKS: dict[int, asyncio.Task] = {}
    LAST_MEOW_POINTER: dict[int, nu.DiscordDatetime] = {}

    @staticmethod
    def match(pattern: str | re.Pattern, string: str) -> bool:
        if isinstance(pattern, str):
            return pattern in string.lower()
        return bool(pattern.search(string))

    @client.event.message
    async def on_message(self, message: n.Message) -> None:
        """
        Force the user to speak like a cat if they have meow chat enabled.
        """

        if message.author.bot:
            return  # ignore bots

        if message.guild is None:
            return  # ignore DMs

        # assert isinstance(message.author, n.GuildMember)
        # assert message.author.permissions is not None

        # if message.author.permissions.manage_messages:
        #     return  # ignore mods

        if message.channel.id not in self.MEOW_CHATS:
            return  # ignore channels that don't have meow chat enabled

        if not any(self.match(pattern, message.content) for pattern in self.MEOW_KEYWORDS):
            try:
                await message.delete(reason="Meow chat enabled; invalid message.")
                should_give_pointer = False
                now = n.utils.utcnow()
                last_pointer_time = self.LAST_MEOW_POINTER.get(message.channel.id)
                if last_pointer_time is None or (now - last_pointer_time).total_seconds() > 60:
                    should_give_pointer = True
                    self.LAST_MEOW_POINTER[message.channel.id] = now
                if should_give_pointer:
                    m = await message.channel.send(
                        f"Hey {message.author.mention} meow chat is turned on for this channel! "
                        f"Meowing is mandatory :3"
                    )
                    await asyncio.sleep(5)
                    try:
                        await m.delete()
                    except Exception:
                        pass
            except (n.Forbidden, n.NotFound):
                pass
            except Exception as e:
                self.log.exception(
                    "Failed to delete message in meow chat channel %d: %s",
                    message.channel.id, e,
                )

    @client.command(
        "meow-chat enable",
        options=[
            n.ApplicationCommandOption(
                name="time",
                description="Duration to enable meow chat for (e.g. '10m' for 10 minutes).",
                type=n.ApplicationOptionType.STRING,
                required=False,
            ),
        ],
        dm_permission=False,
    )
    async def enable_meowchat(self, ctx: t.CommandGI, time: str | None = None) -> None:
        """
        Enable meow chat in the current channel.
        """

        delta = None
        if time:
            try:
                delta = u.get_datetime_until(time, default_days=None)
            except ValueError:
                await ctx.send(
                    (
                        "Invalid time provided; please provide a valid time "
                        "(e.g. '10m' for 10 minutes)."
                    ),
                    ephemeral=True,
                )
                return
        self.MEOW_CHATS.add(ctx.channel.id)

        if delta:
            future = n.utils.utcnow() + delta
            await ctx.send(
                f"Meow chat has been enabled! It will be automatically "
                f"disabled {future.format('R')} nya :3"
            )
            if ctx.channel.id in self.MEOW_TIMEOUT_TASKS:
                self.MEOW_TIMEOUT_TASKS[ctx.channel.id].cancel()
            task = asyncio.create_task(
                self.disable_meowchat_after_timeout(ctx.channel, future)
            )
            self.MEOW_TIMEOUT_TASKS[ctx.channel.id] = task
        else:
            await ctx.send("Meow chat has been enabled nya :3")

    async def disable_meowchat_after_timeout(
            self,
            channel: n.Channel,
            time: n.utils.DiscordDatetime) -> None:
        """
        Wait until the given timestamp and then disable meow chat in the given channel.
        """

        duration = time - n.utils.utcnow()
        if duration.total_seconds() > 30:
            await asyncio.sleep(duration.total_seconds() - 30)
        while n.utils.utcnow() < time:
            await asyncio.sleep(0.5)
        self.MEOW_CHATS.discard(channel.id)
        await channel.send("Meow chat has been automatically disabled :3")
        self.MEOW_TIMEOUT_TASKS.pop(channel.id, None)

    @client.command(
        "meow-chat disable",
        dm_permission=False,
    )
    async def disable_meowchat(self, ctx: t.CommandGI) -> None:
        """
        Disable meow chat in the current channel.
        """

        if ctx.channel.id not in self.MEOW_CHATS:
            await ctx.send("Meow chat is not enabled in this channel.", ephemeral=True)
            return

        self.MEOW_CHATS.discard(ctx.channel.id)
        if ctx.channel.id in self.MEOW_TIMEOUT_TASKS:
            self.MEOW_TIMEOUT_TASKS[ctx.channel.id].cancel()
            self.MEOW_TIMEOUT_TASKS.pop(ctx.channel.id, None)
        await ctx.send("Meow chat has been disabled uwu :3")
