"""
Copyright (c) Daniel Meadows ♥

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

import novus as n
from novus.ext import client, database as db

from utils import get_datetime_until


class Reminders(client.Plugin):

    @client.command(
        name="reminder create",
        options=[
            n.ApplicationCommandOption(
                name="reminder",
                description="The content of the reminder being created.",
                type=n.ApplicationOptionType.STRING,
            ),
            n.ApplicationCommandOption(
                name="time",
                description="How far in the future your reminder will be triggered (eg 5h, 20m, etc).",
                type=n.ApplicationOptionType.STRING,
            ),
        ],
        dm_permission=False,
    )
    async def create_reminder(self, ctx: n.types.CommandGI, reminder: str, time: str) -> None:
        """
        Creates a reminder with the given name and time.
        """

        try:
            reminder_time = n.utils.utcnow() + get_datetime_until(time)
        except OverflowError:
            await ctx.send("Please enter a smaller period of time.", ephemeral=True)
            return
        async with db.Database.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO
                    reminders
                    (
                        reminder_name,
                        reminder_time,
                        user_id,
                        message_channel_id,
                        guild_id
                    )
                VALUES
                    (
                        $1,
                        $2,
                        $3,
                        $4,
                        $5
                    )
                """,
                reminder,
                reminder_time.naive,
                ctx.user.id,
                ctx.channel.id,
                ctx.guild.id
            )

        await ctx.send(
            f"Reminder '{reminder}' successfully created for {reminder_time.mention}.",
            allowed_mentions=n.AllowedMentions.none()
        )

    @client.command(
        name="reminder delete",
        options=[
            n.ApplicationCommandOption(
                name="reminder",
                description="The name of the reminder to be deleted.",
                type=n.ApplicationOptionType.STRING,
                autocomplete=True,
            ),
        ],
        dm_permission=False,
    )
    async def delete_reminder(self, ctx: n.types.CommandI, reminder: str) -> None:
        """
        Deletes a reminder with given name.
        """

        user_id = ctx.user.id
        async with db.Database.acquire() as conn:
            deleted_row = await conn.fetch(
                """
                DELETE FROM
                    reminders
                WHERE
                    reminder_name = $1
                    AND user_id = $2
                RETURNING
                    *
                """,
                reminder,
                user_id
            )
        if len(deleted_row) > 0:
            await ctx.send(
                "Reminder successfully deleted.",
                ephemeral=True
                )
        else:
            await ctx.send("There is no reminder with that name.")

    @client.loop(15)
    async def reminder_loop(self) -> None:
        """
        Loop through all reminders, unbanning them if the reminder time has elapsed.
        """

        # Get all reminders where the reminder time has been passed
        async with db.Database.acquire() as conn:
            rows = await conn.fetch(
                """
                DELETE FROM
                    reminders
                WHERE
                    reminder_time <= TIMEZONE('UTC', NOW())
                RETURNING
                    *
                """
            )

        # Send expired reminders out to the user
        for row in rows:

            # Make a fake guild so that we can get the user and channel
            reminder = row["reminder_name"]
            channel = n.Channel.partial(self.state, row["message_channel_id"])
            fake_guild = n.Object(row["guild_id"], state=self.state)

            # Make sure the user is in the server
            try:
                member = await n.Guild.fetch_member(fake_guild, row["user_id"])
            except n.NotFound:
                continue
            
            # Try and send the reminder
            try:
                await channel.send(f"Reminder for <@{member.id}>: '{reminder}'")
            except n.Forbidden:
                self.log.info("Could not send reminder in channel %s", channel.id)
            except Exception as e:
                self.log.info("Could not send reminder in channel %s (%s)", channel.id, e)

    @delete_reminder.autocomplete
    async def reminder_name_autocomplete(
            self,
            ctx: n.Interaction) -> list[n.ApplicationCommandChoice]:
        """
        Provides the autocomplete for a user's list of reminders.
        """

        assert ctx.guild is not None
        async with db.Database.acquire() as conn:
            reminder_names: list[dict[str, str]] = await conn.fetch(
                """
                SELECT
                    reminder_name
                FROM
                    reminders
                WHERE
                    user_id = $1
                    AND guild_id = $2
                """,
                ctx.user.id,
                ctx.guild.id,
            )
        choices = []
        for row in reminder_names:
            choice = n.ApplicationCommandChoice(row["reminder_name"])
            choices.append(choice)
        return choices
