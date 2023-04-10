import collections

import novus
from novus.ext import client, database as db

from utils.message_queuer import MaxLenList


class MessageHandler(client.Plugin):

    message_cache: dict[int, MaxLenList[novus.Message]]
    message_cache = collections.defaultdict(lambda: MaxLenList(5_000))

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
        if not rows:
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
        )
        await log_channel.send(embeds=[embed])
