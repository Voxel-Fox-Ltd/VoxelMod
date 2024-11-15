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

import collections
from typing import Any

import novus
from novus.ext import client, database as db

from utils.message_queuer import MaxLenList


class MessageHandler(client.Plugin):

    message_cache: dict[int, MaxLenList[novus.Message]]
    message_cache = collections.defaultdict(lambda: MaxLenList(5_000))

    def try_get_message(
            self,
            channel_id: int,
            message_id: int) -> novus.Message | None:
        """
        Try and get a message from the cache.

        Parameters
        ----------
        channel_id : int
            The ID of the channel where the message lives.
        message_id : int
            The ID of the message you want to retrieve from cache.

        Returns
        -------
        novus.Message | None
            The retrieved message, if one could be found.
        """

        for i in self.message_cache[channel_id]:
            if i.id == message_id:
                return i
        return None

    @staticmethod
    def message_to_embed(
            message: novus.Message,
            *,
            channel: novus.abc.Snowflake | None = None,
            **kwargs: Any) -> novus.Embed:
        """
        Convert a message into an embed.

        Parameters
        ----------
        message : novus.Message
            The message that you want to convert.
        channel : novus.abc.Snowflake | None
            Whether or not a field should be added to show the channel the
            message originated from.
        **kwargs
            All passed into the embed initializer.

        Returns
        -------
        novus.Embed
            The created embed.
        """

        e = novus.Embed(
            description=message.content,
            **kwargs,
        ).set_author(
            name=str(message.author),
            icon_url=(
                str(message.author.avatar)
                if message.author.avatar
                else None
            ),
        )
        if message.attachments:
            e.add_field(
                "Attachments",
                "\n".join([f"[{i.filename}]({i.url})" for i in message.attachments]),
                inline=False,
            )
        if channel:
            e.add_field(
                "Channel",
                f"<#{channel.id}>",
            )
        return e

    @client.event.message
    async def on_message(self, message: novus.Message):
        """
        Handle a new message being created; adding it to the message queue.
        """

        if message.guild is None:
            return
        self.message_cache[message.channel.id].append(message)

    @client.event.message_delete
    async def on_message_delete(
            self,
            message: novus.Message):
        """
        Handle messages being deleted.
        """

        # Make sure the author is not a bot
        if message.author.bot:
            return

        # See if we have a message logs channel
        assert message.channel.guild
        async with db.Database.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    message_channel_id
                FROM
                    guild_settings
                WHERE
                    guild_id = $1
                LIMIT 1
                """,
                message.channel.guild.id,
            )
        if not rows or rows[0]["message_channel_id"] is None:
            return
        log_channel_id = rows[0]["message_channel_id"]

        # Make sure we have a valid message
        if not isinstance(message, novus.Message):
            cached_message = self.try_get_message(message.channel.id, message.id)
            if cached_message is None:
                self.log.info(
                    "Failed to get message %s-%s from cache",
                    message.channel.id, message.id,
                )
                return
            message = cached_message

        # Log message to channel
        log_channel = novus.Channel.partial(self.bot.state, log_channel_id)
        embed = self.message_to_embed(
            message,
            channel=message.channel,
            title="Message Deleted",
            color=0xee1111,
        )
        await log_channel.send(embeds=[embed])


    @client.event.message_edit
    async def on_message_update(
            self,
            before: novus.Message | None,
            message: novus.Message):
        """
        Handle messages being deleted.
        """

        # Make sure the author is not a bot
        if message.author.bot:
            return

        # See if we should even bother
        if before is None:
            cached_message = self.try_get_message(message.channel.id, message.id)
            if cached_message is None:
                self.log.info(
                    "Failed to get message %s-%s from cache",
                    message.channel.id, message.id,
                )
                return
            before = cached_message

        # See if we have a message logs channel
        channel = message.channel
        assert channel.guild
        async with db.Database.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    message_channel_id
                FROM
                    guild_settings
                WHERE
                    guild_id = $1
                LIMIT 1
                """,
                channel.guild.id,
            )
        if not rows or rows[0]["message_channel_id"] is None:
            return
        log_channel_id = rows[0]["message_channel_id"]

        # Make sure we have a valid message
        if not isinstance(message, novus.Message):
            for i in self.message_cache[channel.id]:
                if i.id == message.id:
                    message = i
                    break
            else:
                self.log.info(
                    "Failed to get message %s-%s from cache",
                    channel.id, message.id,
                )
                return

        # Log message to channel
        log_channel = novus.Channel.partial(self.bot.state, log_channel_id)
        embeds = [
            novus.Embed(
                title="Message Edited",
                color=0x666666,
            ).set_author(
                name=str(message.author),
                icon_url=(
                    str(message.author.avatar)
                    if message.author.avatar
                    else None
                ),
            ).add_field(
                "Channel",
                f"{channel.mention} ([jump to message]({message.jump_url}))",
            )
        ]
        if before:
            embeds.append(novus.Embed(
                color=0x11ee11,
                description=before.content,
            ))
        embeds.append(novus.Embed(
            color=0xee11ee,
            description=message.content,
        ))
        await log_channel.send(embeds=embeds)
