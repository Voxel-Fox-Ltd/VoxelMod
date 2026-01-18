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

from datetime import datetime as dt, timedelta
from utils import get_datetime_until

import novus as n
from novus.ext import client, database as db
import asyncpg


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
    )
    async def create_reminder(self, ctx: n.types.CommandI, reminder: str, time: str) -> None:
        """
        Creates a reminder with the given name and time.
        """
        try:
            reminder_time = dt.utcnow() + get_datetime_until(time)
        except OverflowError:
            await ctx.send("Please enter a smaller period of time.", ephemeral=True)
            return
        channel_id = ctx.channel.id
        user_id = ctx.user.id
        async with db.Database.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO
                        reminders
                        (
                            reminder_name,
                            reminder_time,
                            user_id,
                            message_channel_id
                        )
                    VALUES
                        (
                            $1,
                            $2,
                            $3,
                            $4
                        )
                    """,
                    reminder,
                    reminder_time,
                    user_id,
                    channel_id
                )
            except asyncpg.UniqueViolationError:
                await ctx.send("Another reminder with the same name exists.", ephemeral=True)
                return

        await ctx.send(
            f"Reminder '{reminder}' successfully created for <t:{round(dt.timestamp(reminder_time))}>.",
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
            await ctx.send("Reminder successfully deleted.")
        else:
            await ctx.send("There is no reminder with that name.")

    


    async def get_user_reminders(self, user_id: int) -> list[str]:
        async with db.Database.acquire() as conn:
            reminder_names: list[dict[str, str]] = await conn.fetch(
                """
                SELECT
                    reminder_name
                FROM
                    reminders
                WHERE
                    user_id = $1
                """,
                user_id,
            )
        actual_reminder_names: list[str] = []
        for row in reminder_names:
            actual_reminder_names.append(row.get("reminder_name"))
        return actual_reminder_names

    @delete_reminder.autocomplete
    async def reminder_name_autocomplete(
            self,
            ctx: n.Interaction) -> list[n.ApplicationCommandChoice]:
        user_id = ctx.user.id
        reminders = await self.get_user_reminders(user_id)
        return [
            n.ApplicationCommandChoice(name) for name in reminders
        ]