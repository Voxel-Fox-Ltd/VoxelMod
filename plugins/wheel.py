"""
Copyright (c) Daniel Meadows

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
from novus import types as t
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
    async def create_wheel(self, ctx: t.CommandI, name: str) -> None:
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
    async def delete_wheel(self, ctx: t.CommandI, name: str) -> None:
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
        name="wheel entries",
        options=[
            n.ApplicationCommandOption(
                name="name",
                description="The name of the wheel to add the entry to.",
                type=n.ApplicationOptionType.STRING,
                autocomplete=True
            ),
        ],
    )
    async def wheel_entries(self, ctx: t.CommandI, name: str) -> None:
        """
        Let you show and edit your wheel entriess.
        """

        entries = await self.get_wheel_entries(ctx.user.id, name)
        await ctx.send_modal(
            title=f"Entries for {name}",
            custom_id=f"WHEEL ENTRIES {name}",
            components=[
                n.ActionRow([
                    n.TextInput(
                        label="Set wheel entries",
                        custom_id="entry",
                        style=n.TextInputStyle.PARAGRAPH,
                        placeholder="Your wheel entries.",
                        value="\n".join(entries) + "\n"
                    )
                ]),
            ],
        )

    @client.event.filtered_component("WHEEL ENTRIES ")
    async def update_wheel_entries(self, ctx: n.Interaction[n.ModalSubmitData]) -> None:
        """
        Update the wheel entries based on the modal submission.
        """

        user_id = ctx.user.id
        wheel_name = ctx.data.custom_id.split(" ", 2)[2]
        value = ctx.data.components[0].components[0].value
        async with db.Database.acquire() as conn:
            updated_row = await conn.fetch(
                """
                UPDATE
                    wheels
                SET
                    entries = $1
                WHERE
                    name = $2
                    AND user_id = $3
                RETURNING
                    *
                """,
                value.strip().split("\n"),
                wheel_name,
                user_id,
            )
        await ctx.send("Entries successfully updated.")

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
    async def wheel_spin(self, ctx: t.CommandI, name: str) -> None:
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
    async def on_wheel_button_press(self, ctx: t.ComponentI) -> None:
        """
        Handles wheel spin button presses.
        """

        await self.wheel_spin(ctx, ctx.data.custom_id[len("WHEEL SPIN "):])

    @client.command(
            name="wheel list",
    )
    async def wheel_list(self, ctx: t.CommandI) -> None:
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
