from datetime import datetime as dt

import novus
from novus.ext import client, database as db

from utils import Action, ActionType, create_chat_log


class Report(client.Plugin):

    @client.command(
        name="Report this message.",
        type=novus.ApplicationCommandType.message,
    )
    async def report_context_command(
            self,
            interaction: novus.types.CommandI,
            message: novus.Message):
        """
        Report a message to the moderators of the guild.
        """

        async with db.Database.acquire() as conn:
            log_code = await create_chat_log(conn, message.channel)
        await interaction.send_modal(
            title="Message Report",
            custom_id=(
                f"MESSAGE_REPORT "
                f"{log_code} "
                f"{message.author.id} "
                f"{message.channel.id}"
            ),
            components=[
                novus.ActionRow([
                    novus.TextInput(
                        "Why are you reporting this message?",
                        custom_id="...",
                        style=novus.TextInputStyle.short,
                        max_length=200,
                    ),
                ]),
            ],
        )

    @client.event.filtered_component(r"^MESSAGE_REPORT [\w-]+ \d+ \d+$")
    async def handle_modal_submit(
            self,
            interaction: novus.Interaction[novus.ModalSubmitData]):
        """
        Listen for message report modals being submitted.
        """

        _, log_code, user_id, channel_id = (
            interaction.data.custom_id.split(" ")
        )
        component: novus.TextInput = interaction.data[0][0]  # pyright: ignore
        reason: str = component.value  # pyright: ignore
        await self.handle_report(
            interaction,
            int(user_id),
            int(channel_id),
            log_code,
            reason,
        )

    @client.command(
        name="report",
        options=[
            novus.ApplicationCommandOption(
                name="user",
                type=novus.ApplicationOptionType.user,
                description="The user that you want to report.",
            ),
            novus.ApplicationCommandOption(
                name="reason",
                type=novus.ApplicationOptionType.string,
                description="The reason you are reporting the user.",
            ),
        ]
    )
    async def report(
            self,
            interaction: novus.types.CommandI,
            user: novus.GuildMember,
            reason: str | None = None) -> None:
        """
        Reports a user, saving a chat log, so it can be reviewed by a
        moderator.
        """

        await interaction.defer(ephemeral=True)

        async with db.Database.acquire() as conn:
            log_code = await create_chat_log(conn, interaction.channel)

        await self.handle_report(
            interaction,
            user.id,
            interaction.channel.id,
            log_code,
            reason,
        )

    async def handle_report(
            self,
            interaction: novus.Interaction,
            user_id: int,
            channel_id: int,
            log_code: str | None,
            reason: str | None):
        """
        Handle a report submission from any given input.
        """

        # Create an action for the infraction
        assert interaction.guild
        async with db.Database.acquire() as conn:
            await Action.create(
                conn,
                guild_id=interaction.guild.id,
                user_id=user_id,
                action_type=ActionType.REPORT,
                reason=reason,
                moderator_id=interaction.user.id,
            )

            # Get the report channel ID
            rows = await conn.fetch(
                """
                SELECT
                    report_channel_id,
                    staff_role_id
                FROM
                    guild_settings
                WHERE
                    guild_id = $1
                LIMIT 1
                """,
                interaction.guild.id,
            )

        # Get channel ID
        if not rows or rows[0]["report_channel_id"] is None:
            await interaction.send(
                (
                    "Your report has been logged, but there is no report "
                    "channel set. Please inform a moderator for them to fix "
                    "this."
                ),
                ephemeral=True,
            )
            return

        # Create message content
        fake_message_id = interaction.id
        message_jump_url = f"https://discord.com/channels/{interaction.guild.id}/{channel_id}/{fake_message_id}"
        embed = (
            novus.Embed(color=0xe621_00, description=f"[Jump to a nearby message]({message_jump_url})")
            .add_field("Reporter", interaction.user.mention)
            .add_field("Reportee", f"<@{user_id}>")
            .add_field("Channel", f"<#{channel_id}>")
            .add_field("Reason", reason or ":kaeShrug:", inline=False)
            .add_field("Log Code", log_code or ":kaeShrug:")
        )
        content_kwargs = {}
        if rows[0]["staff_role_id"]:
            role_id = rows[0]["staff_role_id"]
            content_kwargs = {"content": f"<@&{role_id}>"}

        # Send report message
        report_channel_id = rows[0]["report_channel_id"]
        channel = novus.Channel.partial(self.bot.state, report_channel_id)
        button = novus.Button("Handle this report", custom_id="HANDLE_REPORT")
        try:
            await channel.send(
                **content_kwargs,
                embeds=[embed,],
                components=[novus.ActionRow([button]),]
            )
        except novus.Forbidden:
            return await interaction.send(
                (
                    "Your report has been logged, but I'm unable to send "
                    "messages into the guild's report channel. Please inform a "
                    "moderator for them to fix this."
                ),
                ephemeral=True,
            )
        except novus.NotFound:
            return await interaction.send(
                (
                    "Your report has been logged, but the guild's report "
                    "channel has been deleted. Please inform a moderator for "
                    "them to fix this."
                ),
                ephemeral=True,
            )
        await interaction.send("Your report has been sent :)", ephemeral=True)

    @client.event.filtered_component("HANDLE_REPORT")
    async def handle_report_button(self, interaction: novus.Interaction[novus.MessageComponentData]):
        """
        Handle the "handle report" button being clicked.
        """

        assert interaction.message
        current_embed = interaction.message.embeds[0]
        current_embed.color = 0xe621
        current_embed.add_field("Handled by", interaction.user.mention)
        await interaction.update(
            embeds=[current_embed],
            components=None,
        )
