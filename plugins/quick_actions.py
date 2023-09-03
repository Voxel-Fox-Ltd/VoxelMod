import novus
from novus.ext import client, database as db


class QuickActions(client.Plugin):
    """
    Actions for moderators associated with a user context command.
    """

    @client.command(
        "Quick moderation actions",
        type=novus.ApplicationCommandType.user,
    )
    async def quick_mod_actions(
            self,
            ctx: novus.types.CommandI,
            user: novus.User | novus.GuildMember):
        """
        Get a set of commonly-used moderation actions for the given user.
        """

        # Make a list of quick action buttons to let the user see
        components = [
            novus.ActionRow(
                novus.Button()
            )
        ]
