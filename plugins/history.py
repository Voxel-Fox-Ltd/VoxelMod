from typing import cast

import novus
from novus.ext import client, database as db

from utils import create_chat_log

class History(client.Plugin):

    @client.event.filtered_component(r"P_HIST \d+ \d+")
    async def history_paginator(self, interaction: novus.types.ComponentI):
        """
        Handle a paginator button being clicked.
        """

        user_id = int(interaction.data.custom_id.split(" ")[1])
        offset = int(interaction.data.custom_id.split(" ")[2])
        await self.get_user_history(interaction, user_id, offset)

    @client.command(
        name="history",
        options=[
            novus.ApplicationCommandOption(
                name="user",
                description="The user that you want to see the history of.",
                type=novus.ApplicationOptionType.user,
            ),
        ],
    )
    async def history(
            self,
            interaction: novus.types.CommandI | novus.Interaction[novus.MessageComponentData],
            user: novus.GuildMember) -> None:
        """
        Views the full infraction history of a user.
        """

        await self.get_user_history(interaction, user.id)

    async def get_user_history(
            self,
            interaction: novus.types.CommandI | novus.Interaction[novus.MessageComponentData],
            user_id: int,
            offset: int = 0) -> None:
        """
        Get the history for the user.
        """

        await interaction.defer_update()

        # Get the actions
        assert interaction.guild
        async with db.Database.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    id,
                    action_type,
                    reason,
                    moderator_id,
                    timestamp
                FROM
                    actions
                WHERE
                    user_id = $1
                    AND guild_id = $2
                ORDER BY
                    timestamp DESC
                LIMIT 6
                OFFSET $3
                """,
                user_id,
                interaction.guild.id,
                offset,
            )
        if not rows:
            return await interaction.send(
                (
                    "**{user}** has no infractions."
                ).format(
                    user=f"<@{user_id}>",
                ),
                allowed_mentions=novus.AllowedMentions.none(),
            )

        # Make into an embed
        embed = novus.Embed()
        for r in rows:
            timestamp = r["timestamp"]
            relative = novus.utils.format_timestamp(timestamp, "R")
            embed.add_field(
                str(r["id"]),
                f"`{r['action_type']}` | {relative}\n{r['reason']}",
                inline=False,
            )

        # Decide what buttons we want
        buttons = [
            novus.Button(
                label="\N{LEFTWARDS ARROW}",
                custom_id=f"P_HIST {user_id} {offset - 5}",
            ),
            novus.Button(
                label="\N{RIGHTWARDS ARROW}",
                custom_id=f"P_HIST {user_id} {offset + 5}"
            ),
        ]
        if offset == 0:
            buttons[0].disabled = True
        if len(rows) <= 5:
            buttons[-1].disabled = True

        # Send message
        components = []
        if buttons:
            components = [novus.ActionRow(buttons)]
        await interaction.send(
            embeds=[embed],
            components=components,
        )

    @client.command(name="logs")
    async def logs(self, interaction: novus.types.CommandI) -> None:
        """
        Create and store a chat log.
        """

        await interaction.defer()
        async with db.Database.acquire() as conn:
            log_code = await create_chat_log(conn, interaction.channel)

        # TODO website stuff

        await interaction.send(
            "Created a chat log with code {0}"
            .format(log_code)
        )

        ...
