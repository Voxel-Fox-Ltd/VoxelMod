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

from datetime import datetime as dt, timedelta

import novus
from novus.ext import client, database as db

from utils import Action, ActionType, create_chat_log


class Report(client.Plugin):

    @client.command(
        name="Report this message.",
        type=novus.ApplicationCommandType.MESSAGE,
    )
    async def report_context_command(
            self,
            interaction: novus.types.CommandI,
            message: novus.Message):
        """
        Report a message to the moderators of the guild.
        """

        async with db.Database.acquire() as conn:
            log_id = await create_chat_log(conn, message.channel)
        await interaction.send_modal(
            title="Message Report",
            custom_id=(
                f"MESSAGE_REPORT "
                f"{log_id} "
                f"{message.author.id} "
                f"{message.channel.id}"
            ),
            components=[
                novus.ActionRow([
                    novus.TextInput(
                        "Why are you reporting this message?",
                        custom_id="...",
                        style=novus.TextInputStyle.SHORT,
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

        _, log_id, user_id, channel_id = (
            interaction.data.custom_id.split(" ")
        )
        component: novus.TextInput = interaction.data[0][0]  # pyright: ignore
        reason: str = component.value  # pyright: ignore
        await self.handle_report(
            interaction,
            int(user_id),
            int(channel_id),
            log_id,
            reason,
        )

    @client.command(
        name="report",
        options=[
            novus.ApplicationCommandOption(
                name="user",
                type=novus.ApplicationOptionType.USER,
                description="The user that you want to report.",
            ),
            novus.ApplicationCommandOption(
                name="reason",
                type=novus.ApplicationOptionType.STRING,
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
            log_id = await create_chat_log(conn, interaction.channel)
        await self.handle_report(
            interaction,
            user.id,
            interaction.channel.id,
            log_id,
            reason,
        )

    async def handle_report(
            self,
            interaction: novus.Interaction,
            user_id: int,
            channel_id: int,
            log_id: str | None,
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
                log_id=log_id
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
            .add_field("Possible Rulebreaker", f"<@{user_id}>")
            .add_field("Channel", f"<#{channel_id}>")
            .add_field("Reason", reason or ":kaeShrug:", inline=False)
            .add_field("Log Code", log_id or ":kaeShrug:", inline=False)
        )
        content_kwargs = {}
        if rows[0]["staff_role_id"]:
            role_id = rows[0]["staff_role_id"]
            content_kwargs = {"content": f"<@&{role_id}>"}

        # Get buttons
        components = [
            novus.ActionRow([
                novus.Button("Handle report", custom_id="HANDLE_REPORT"),
            ]),
            novus.ActionRow([
                novus.Button("Quick mute (10m)", custom_id=f"HANDLE_REPORT_MUTE {user_id} 600"),
                novus.Button("Quick mute (1h)", custom_id=f"HANDLE_REPORT_MUTE {user_id} 3600"),
                novus.Button("Quick ban", custom_id=f"HANDLE_REPORT_BAN {user_id}"),
            ])
        ]

        # Send report message
        report_channel_id = rows[0]["report_channel_id"]
        channel = novus.Channel.partial(self.bot.state, report_channel_id)
        try:
            await channel.send(
                **content_kwargs,
                embeds=[embed,],
                components=components,
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

        await self.handle_report_message_edit(interaction)

    async def handle_report_message_edit(self, interaction: novus.Interaction[novus.MessageComponentData]):
        """
        Handle editing a report message after it has been interacted with.
        """

        assert interaction.message
        current_embed = interaction.message.embeds[0]
        current_embed.color = 0xe621
        _time = novus.utils.utcnow()
        time = _time.mention
        relative = _time.format("R")
        current_embed.insert_field_at(
            -1,
            "Handled by",
            f"{interaction.user.mention}\n{time} ({relative})",
            inline=False,
        )
        if interaction._responded:
            await interaction.edit_original(
                content=None,
                embeds=[current_embed],
                components=None,
            )
        else:
            await interaction.update(
                content=None,
                embeds=[current_embed],
                components=None,
            )

    @client.event.filtered_component(r"HANDLE_REPORT_MUTE \d+ \d+")
    async def handle_quick_mute_report(self, ctx: novus.types.ComponentI):
        """
        Handle a quick mute button being pressed.
        """

        _, ban_user_id, seconds_str = ctx.data.custom_id.split(" ")
        seconds = int(seconds_str)
        assert ctx.guild
        fake_user = novus.Object(
            ban_user_id,
            state=self.bot.state,
            guild_id=ctx.guild.id,
        )

        # Get reason from embed
        assert ctx.message
        embed = ctx.message.embeds[0]
        reason: str | None = None
        for field in embed.fields:
            if field.name.casefold() == "reason":
                reason = field.value
                break
        if reason is None:
            reason = "Muted via report"

        # Get duration
        future = dt.utcnow() + timedelta(seconds=seconds)
        try:
            await novus.GuildMember.edit(  # pyright: ignore
                fake_user,
                timeout_until=future,
                reason=reason,
            )
        except novus.Forbidden:
            await ctx.send(
                "I'm missing the relevant permissions to timeout that user."
            )
            return

    @client.event.filtered_component(r"HANDLE_REPORT_BAN \d+")
    async def handle_quick_ban_report(self, ctx: novus.types.ComponentI):
        """
        Handle a quick ban button being pressed.
        """

        _, ban_user_id = ctx.data.custom_id.split(" ")
        assert ctx.guild
        fake_user = novus.Object(
            ban_user_id,
            state=self.bot.state,
            guild_id=ctx.guild.id,
        )

        # Get reason from embed
        assert ctx.message
        embed = ctx.message.embeds[0]
        reason: str | None = None
        for field in embed.fields:
            if field.name.casefold() == "reason":
                reason = field.value
                break
        if reason is None:
            reason = "Ban via report"

        # Ban the user
        try:
            await novus.GuildMember.ban(  # pyright: ignore
                fake_user,
                reason=reason,
            )
        except novus.Forbidden:
            await ctx.send(
                "I'm missing the relevant permissions to ban that user."
            )
            return
