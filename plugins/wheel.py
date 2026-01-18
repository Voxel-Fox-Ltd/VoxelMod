"""
Copyright (c) Daniel Bartlett

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

import random

import novus as n
from novus.ext import client, database as db
import asyncpg


class Wheel(client.Plugin):

    @client.command(
        name="wheel create",
        options=[
            n.ApplicationCommandOption(
                name="name",
                description="The name of the wheel being created.",
                type=n.ApplicationOptionType.STRING,
            ),
        ],
    )
    async def create_wheel(self, ctx: n.types.CommandI, name: str) -> None:
        """
        Creates a wheel with the given name.
        """
        user_id = ctx.user.id
        async with db.Database.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO
                        wheels
                        (
                            name,
                            user_id
                        )
                    VALUES
                        (
                            $1,
                            $2
                        )
                    """,
                    name,
                    user_id
                )
            except asyncpg.UniqueViolationError:
                await ctx.send("Another wheel with the same name exists.", ephemeral=True)
                return

        await ctx.send("Wheel successfully created.")

    @client.command(
        name="wheel delete",
        options=[
            n.ApplicationCommandOption(
                name="name",
                description="The name of the wheel to be deleted.",
                type=n.ApplicationOptionType.STRING,
                autocomplete=True,
            ),
        ],
    )
    async def delete_wheel(self, ctx: n.types.CommandI, name: str) -> None:
        """
        Deletes a wheel with given name.
        """
        user_id = ctx.user.id
        async with db.Database.acquire() as conn:
            deleted_row = await conn.fetch(
                """
                DELETE FROM
                    wheels
                WHERE
                    name = $1
                    AND user_id = $2
                RETURNING
                    *
                """,
                name,
                user_id
            )

        if len(deleted_row) > 0:
            await ctx.send("Wheel successfully deleted.")
        else:
            await ctx.send("There is no wheel with that name.")

    @client.command(
        name="entry add",
        options=[
            n.ApplicationCommandOption(
                name="name",
                description="The name of the wheel to add the entry to.",
                type=n.ApplicationOptionType.STRING,
                autocomplete=True
            ),
            n.ApplicationCommandOption(
                name="entry",
                description="The name of the entry to be added to the wheel.",
                type=n.ApplicationOptionType.STRING,
            ),
        ],
    )
    async def add_entry(self, ctx: n.types.CommandI, name: str, entry: str) -> None:
        """
        Adds an entry to a given wheel.
        """
        user_id = ctx.user.id
        async with db.Database.acquire() as conn:
            updated_row = await conn.fetch(
                """
                UPDATE
                    wheels
                SET
                    entries = ARRAY_APPEND(entries, $1)
                WHERE
                    name = $2
                    AND user_id = $3
                RETURNING
                    *
                """,
                entry,
                name,
                user_id,
            )

        if len(updated_row) > 0:
            await ctx.send("Entry successfully added to wheel.")
        else:
            await ctx.send("You have no wheel with that name.")

    @client.command(
        name="entry delete",
        options=[
            n.ApplicationCommandOption(
                name="name",
                description="The name of the wheel to remove the entry from.",
                type=n.ApplicationOptionType.STRING,
                autocomplete=True
            ),
            n.ApplicationCommandOption(
                name="entry",
                description="The name of the entry to be removed from the wheel.",
                type=n.ApplicationOptionType.STRING,
                autocomplete=True
            ),
        ]
    )
    async def remove_entry(self, ctx: n.types.CommandI, name: str, entry: str) -> None:
        """
        Removes an entry from a given wheel.
        """
        user_id = ctx.user.id
        async with db.Database.acquire() as conn:
            updated_row = await conn.fetch(
                """
                UPDATE
                    wheels
                SET
                    entries = ARRAY_REMOVE(entries, $1)
                WHERE
                    $1 = ANY(entries)
                    AND name = $2
                    AND user_id = $3
                RETURNING
                    *
                """,
                entry,
                name,
                user_id,
            )

        if not updated_row:
            return await ctx.send(
                (
                    "You have no wheel with that name, or there is no entry with that name "
                    "within the wheel."
                ),
            )

        await ctx.send("Entry successfully removed from wheel.")

    @client.command(
        name="wheel spin",
        options=[
            n.ApplicationCommandOption(
                name="name",
                description="The name of the wheel to spin.",
                type=n.ApplicationOptionType.STRING,
                autocomplete=True
            ),
        ]
    )
    async def wheel_spin(self, ctx: n.types.CommandI, name: str) -> None:
        """
        Gets a random result from a given wheel.
        """
        user_id = ctx.user.id
        async with db.Database.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    entries
                FROM
                    wheels
                WHERE
                    name = $1
                    AND user_id = $2
                """,
                name,
                user_id,
            )

        if not rows:
            return await ctx.send("There is no wheel with that name.", ephemeral=True)

        wheel_entries = rows[0]["entries"]

        if not wheel_entries:
            return await ctx.send("There are no entries in this wheel.", ephemeral=True)

        chosen_entry = random.choice(wheel_entries)
        await ctx.send(
            f"**{chosen_entry}** is the winner.",
            allowed_mentions=n.AllowedMentions.none(),
            components=[
                n.ActionRow([
                    n.Button("Spin again", custom_id=f"WHEEL SPIN {name}")
                ])
            ],
        )

    @client.event.filtered_component("WHEEL SPIN ")
    async def on_wheel_button_press(self, ctx: n.types.ComponentI) -> None:
        """
        Handles wheel spin button presses.
        """

        await self.wheel_spin(ctx, ctx.data.custom_id[len("WHEEL SPIN "):])

    @client.command(
            name="wheel list",
    )
    async def wheel_list(self, ctx: n.types.CommandI) -> None:
        """
        Lists all of your wheels.
        """

        wheels = await self.get_user_wheels(ctx.user.id)
        await ctx.send(
            self.prettify_list_uwu(wheels),
            allowed_mentions=n.AllowedMentions.none(),
        )

    def prettify_list_uwu(self, stuff: list) -> str:
        output = ""
        if len(stuff) <= 5:
            for i in stuff:
                output += f"* {i}\n"
        else:
            for i in stuff:
                output += i + ", "
        return output

    @client.command(
        name="wheel entries",
        options=[
            n.ApplicationCommandOption(
                name="name",
                description="The name of the wheel to list entries from.??",
                type=n.ApplicationOptionType.STRING,
                autocomplete=True
            )
        ]
    )
    async def wheel_entries(self, ctx: n.types.CommandI, name: str) -> None:
        """
        List all of the entries within a wheel.
        """

        entries = await self.get_wheel_entries(ctx.user.id, name)
        await ctx.send(
            self.prettify_list_uwu(entries),
            allowed_mentions=n.AllowedMentions.none(),
        )

    async def get_user_wheels(self, user_id: int) -> list[str]:
        async with db.Database.acquire() as conn:
            wheel_names: list[dict[str, str]] = await conn.fetch(
                """
                SELECT
                    name
                FROM
                    wheels
                WHERE
                    user_id = $1
                """,
                user_id,
            )
        actual_wheel_names: list[str] = []
        for row in wheel_names:
            actual_wheel_names.append(row.get("name"))
        return actual_wheel_names

    async def get_wheel_entries(self, user_id: int, name: str) -> list[str]:
        async with db.Database.acquire() as conn:
            wheel_entries: list[dict[str, list[str]]] = await conn.fetch(
                """
                SELECT
                    entries
                FROM
                    wheels
                WHERE
                    user_id = $1
                    AND name = $2
                """,
                user_id,
                name,
            )
        if wheel_entries:
            actual_wheel_entries = wheel_entries[0].get("entries")
            self.log.info(actual_wheel_entries)
            return actual_wheel_entries
        else:
            return []

    @delete_wheel.autocomplete
    @wheel_spin.autocomplete
    @wheel_list.autocomplete
    @wheel_entries.autocomplete
    async def wheel_name_autocomplete(
            self,
            ctx: n.Interaction) -> list[n.ApplicationCommandChoice]:
        user_id = ctx.user.id
        wheels = await self.get_user_wheels(user_id)
        return [
            n.ApplicationCommandChoice(name) for name in wheels
        ]

    @add_entry.autocomplete
    @remove_entry.autocomplete
    async def wheel_entries_autocomplete(
            self,
            ctx: n.Interaction[n.ApplicationCommandData]) -> list[n.ApplicationCommandChoice]:
        self.log.info(ctx.data.options)
        focused = [i for i in ctx.data.options[0].options if i.focused][0]
        name_of_focused_option = focused.name
        if name_of_focused_option == "name":
            return await self.wheel_name_autocomplete(ctx)
        elif name_of_focused_option == "entry":
            user_id = ctx.user.id
            entries = await self.get_wheel_entries(user_id, ctx.data.options[0].options[0].value)
            return [
                n.ApplicationCommandChoice(entry) for entry in entries
            ]
