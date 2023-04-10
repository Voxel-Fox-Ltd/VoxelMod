import novus
from novus.ext import client

from utils import delete_messages


class Clear(client.Plugin):

    @client.command(
        name="clear",
        options=[
            novus.ApplicationCommandOption(
                name="user",
                type=novus.ApplicationOptionType.user,
                description="The user who you want to clear messages from.",
                required=False
            ),
            novus.ApplicationCommandOption(
                name="num_messages",
                type=novus.ApplicationOptionType.number,
                description="The number of messages to clear",
                required=False,
            ),
            novus.ApplicationCommandOption(
                name="reason",
                type=novus.ApplicationOptionType.string,
                description="The reason for clearing these messages.",
                required=False,
            ),
        ],
        default_member_permissions=novus.Permissions(manage_messages=True),
        dm_permission=False,
    )
    async def clear(
            self,
            interaction: novus.types.CommandI,
            user: novus.GuildMember | None = None,
            num_messages: int = 100,
            reason: str | None = None) -> None:
        """
        Clears a number of messages from a user
        """

        await interaction.defer()

        # Create an action for the infraction
        assert interaction.guild

        await delete_messages(interaction.channel, user, num_messages, reason)

        content = "Cleared last %s messages".format(num_messages)
        if user:
            content += " from **%s**".format(user.mention)

        await interaction.send(
            content=content,
            ephemeral=True
        )
