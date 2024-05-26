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
