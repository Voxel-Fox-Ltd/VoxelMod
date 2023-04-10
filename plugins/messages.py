import collections

import novus
from novus.ext import client

from utils.message_queuer import MaxLenList


class MessageHandler(client.Plugin):

    message_cache: dict[int, MaxLenList[novus.Message]]
    message_cache = collections.defaultdict(lambda: MaxLenList(2_000))

    @client.event.message
    async def on_message(self, message: novus.Message):
        """
        Handle a new message being created; adding it to the message queue.
        """

        if message.guild is None:
            return
        self.message_cache[message.channel.id].append(message)
