import collections

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
            channel: novus.TextChannel,
            message: novus.Message):
        """
        Handle messages being deleted.
        """

        # Make sure the author is not a bot
        if message.author.bot:
            return

        # See if we have a message logs channel
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
            cached_message = self.try_get_message(channel.id, message.id)
            if cached_message is None:
                self.log.info(
                    "Failed to get message %s-%s from cache",
                    channel.id, message.id,
                )
                return
            message = cached_message

        # Log message to channel
        log_channel = novus.Channel.partial(self.bot.state, log_channel_id)
        embed = novus.Embed(
            title="Message Deleted",
            description=message.content,
            color=0xee1111,
        ).set_author(
            name=str(message.author),
            icon_url=(
                str(message.author.avatar)
                if message.author.avatar
                else None
            ),
        ).add_field(
            "Channel",
            channel.mention,
        )
        await log_channel.send(embeds=[embed])


    @client.event.message_update
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
        embed = novus.Embed(
            title="Message Edited",
            description=before.content,
            color=0x11ee11,
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
        await log_channel.send(embeds=[embed])
