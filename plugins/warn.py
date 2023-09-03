import novus
from novus.ext import client, database as db

from utils import Action, ActionType, create_chat_log


class Warn(client.Plugin):

    @client.command(
        name="warn",
        options=[
            novus.ApplicationCommandOption(
                name="user",
                type=novus.ApplicationOptionType.user,
                description="The user who you want to warn.",
            ),
            novus.ApplicationCommandOption(
                name="reason",
                type=novus.ApplicationOptionType.string,
                description="The reason for warning this user.",
                required=False,
            ),
        ],
        default_member_permissions=novus.Permissions(moderate_members=True),
        dm_permission=False,
    )
    async def warn(
            self,
            interaction: novus.types.CommandI,
            user: novus.GuildMember,
            reason: str | None = None) -> None:
        """
        Warns a member, adding an infraction to their history
        """

        await interaction.defer()
        async with db.Database.acquire() as conn:
            log_id = await create_chat_log(conn, interaction.channel)  # pyright: ignore

        # Create an action for the infraction
        assert interaction.guild
        async with db.Database.acquire() as conn:
            await Action.create(
                conn,
                guild_id=interaction.guild.id,
                user_id=user.id,
                action_type=ActionType.WARN,
                reason=reason,
                moderator_id=interaction.user.id,
                log_id=log_id
            )
        await interaction.send(f"A warning has been added to **{user.mention}**.")
