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

import novus as n
from novus.ext import client, database as db
from novus import types as t


class RolePicker(client.Plugin):
    """
    A plugin for role picker commands.
    """

    def format_role_picker(self, name: str, role_ids: list[int], type_: str) -> dict:
        """
        Return a kwargs for sending a role picker edit menu.
        """

        return {
            "content": None,
            "embeds": [
                n.Embed(
                    title="Roles",
                    description="\n".join(
                        f"* <@&{role_id}>" for role_id in role_ids
                    ),
                )
            ],
            "components": [
                n.ActionRow([
                    n.RoleSelectMenu(
                        custom_id=f"ROLE_PICKER_CREATE_SELECT {name} 1",
                        max_values=25,
                        default_values=role_ids,
                    )
                ]),
                n.ActionRow([
                    n.Button(
                        "Users can pick multiple",
                        custom_id=f"ROLE_PICKER_TYPE {name} MULTIPLE",
                        style=n.ButtonStyle.GREEN if type_ == "MULTIPLE" else n.ButtonStyle.GRAY,
                        disabled=len(role_ids) <= 1 or type_ == "MULTIPLE"
                    ),
                    n.Button(
                        "Users can only pick one",
                        custom_id=f"ROLE_PICKER_TYPE {name} SINGLE",
                        style=n.ButtonStyle.GREEN if type_ == "SINGLE" else n.ButtonStyle.GRAY,
                        disabled=len(role_ids) <= 1 or type_ == "SINGLE"
                    ),
                ]),
            ],
        }

    async def get_user_role_picker(
            self,
            guild: n.Guild,
            name: str,
            role_ids: list[int],
            multiple: bool) -> n.StringSelectMenu:
        """
        Return a select menu for users to pick roles from.
        """

        guild_roles = await guild.fetch_roles()
        return n.StringSelectMenu(
            custom_id=f"ROLE_PICKER_SELECT {name}",
            options=[
                n.SelectOption(
                    label=next((r.name for r in guild_roles if r.id == role_id), "Unknown Role"),
                    value=str(role_id),
                )
                for role_id in role_ids
            ],
            max_values=1,
            # placeholder="Select your roles..."
        )

    @client.command(
        name="role-picker create",
        options=[
            n.ApplicationCommandOption(
                name="name",
                description="The name of the role picker.",
                type=n.ApplicationOptionType.STRING,
            ),
        ],
        dm_permission=False,
    )
    async def create_role_picker(self, ctx: t.CommandI, name: str):
        """
        Create a role picker group.
        """

        # Send an empty embed allowing the user to add/remove roles
        await ctx.send(
            "Select the roles that you want to include in this role picker.",
            components=[
                n.ActionRow([
                    n.RoleSelectMenu(
                        custom_id=f"ROLE_PICKER_CREATE_SELECT {name} 0",
                        max_values=25,
                    )
                ]),
            ],
        )

    @client.event.filtered_component(r"ROLE_PICKER_CREATE_SELECT")
    async def handle_create_role_picker_dropdown(self, interaction: t.ComponentGI):
        """
        Handle a role picker creation interaction for roles being added/removed.
        """

        # Get the name from the custom ID
        _, name, ignore_conflicts = interaction.data.custom_id.split(" ")
        selected_roles = [int(i.value) for i in interaction.data.values]

        # Make sure that the name they're trying to use doesn't already exist
        if ignore_conflicts == "0":
            async with db.Database.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT 1 FROM role_pickers WHERE guild_id=$1 AND name=$2",
                    interaction.guild.id, name,
                )
                if row:
                    await interaction.send(
                        f"A role picker with the name `{name}` already exists.",
                        ephemeral=True,
                    )
                    return

        # Make sure that all of the roles the user has selected are below the user's maximum role
        member_role_ids = interaction.user.role_ids  # pyright: ignore
        guild_roles: list[n.Role] = await interaction.guild.fetch_roles()
        member_highest_role_position = max(
            (role.position for role in guild_roles if role.id in member_role_ids),
            default=-1,
        )
        for role_id in selected_roles:
            role = next((r for r in guild_roles if r.id == role_id), None)
            if role is None:
                continue
            if role.position >= member_highest_role_position:
                await interaction.send(
                    (
                        f"You cannot include the role <@&{role_id}> as it is higher than or equal "
                        "to your highest role."
                    ),
                    ephemeral=True,
                )
                return

        # Save everything to database
        type_ = "MULTIPLE"
        async with db.Database.acquire() as conn:
            type_ = await conn.fetchval(
                """
                INSERT INTO
                    role_pickers
                    (
                        guild_id,
                        name,
                        role_ids,
                        type
                    )
                VALUES
                    ($1, $2, $3, $4)
                ON CONFLICT (guild_id, name) DO UPDATE SET
                    role_ids=$3
                RETURNING
                    type
                """,
                interaction.guild.id,
                name,
                selected_roles,
                type_,
            )

        # Update the message to show the selected roles
        await interaction.update(
            **self.format_role_picker(name, selected_roles, type_ or "MULTIPLE"),
        )

    @client.event.filtered_component(r"ROLE_PICKER_TYPE")
    async def handle_edit_role_picker_selection_type(self, interaction: t.ComponentGI):
        """
        Handle role picker type being updated
        """

        # Get the name from the custom ID
        _, name, type_ = interaction.data.custom_id.split(" ")

        # Update the database
        async with db.Database.acquire() as conn:
            role_ids = await conn.fetchval(
                """
                UPDATE
                    role_pickers
                SET
                    type=$1
                WHERE
                    guild_id=$2
                    AND name=$3
                RETURNING
                    role_ids
                """,
                type_,
                interaction.guild.id,
                name,
            )

        # Update the message to show the selected roles
        await interaction.update(
            **self.format_role_picker(name, role_ids or [], type_),
        )

    @client.command(
        name="role-picker delete",
        options=[
            n.ApplicationCommandOption(
                name="name",
                description="The name of the role picker to delete.",
                type=n.ApplicationOptionType.STRING,
                autocomplete=True,
            ),
        ],
        dm_permission=False,
    )
    async def delete_role_picker(self, ctx: t.CommandGI, name: str):
        """
        Delete a role picker group.
        """

        # Delete the role picker from the database
        async with db.Database.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM
                    role_pickers
                WHERE
                    guild_id=$1
                    AND name=$2
                """,
                ctx.guild.id,
                name,
            )

        # Check if anything was deleted
        if result.endswith("0"):
            await ctx.send(
                f"No role picker with the name `{name}` exists.",
                ephemeral=True,
            )
            return

        await ctx.send(
            f"The role picker `{name}` has been deleted.",
            allowed_mentions=n.AllowedMentions.none(),
        )

    @client.command(
        name="role-picker edit",
        options=[
            n.ApplicationCommandOption(
                name="name",
                description="The name of the role picker to edit.",
                type=n.ApplicationOptionType.STRING,
                autocomplete=True,
            ),
        ],
        dm_permission=False,
    )
    async def edit_role_picker(self, ctx: t.CommandGI, name: str):
        """
        Edit a role picker group.
        """

        # Fetch the role picker from the database
        async with db.Database.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    role_ids,
                    type
                FROM
                    role_pickers
                WHERE
                    guild_id=$1
                    AND name=$2
                """,
                ctx.guild.id,
                name,
            )

        # Check if the role picker exists
        if not row:
            await ctx.send(
                f"No role picker with the name `{name}` exists.",
                ephemeral=True,
            )
            return

        # Send the message to allow editing
        await ctx.send(
            **self.format_role_picker(name, row["role_ids"], row["type"])
        )

    @client.command(
        name="role-picker post",
        options=[
            n.ApplicationCommandOption(
                name="name",
                description="The name of the role picker to post.",
                type=n.ApplicationOptionType.STRING,
                autocomplete=True,
            ),
            n.ApplicationCommandOption(
                name="content",
                description="The content to post in addition to the dropdown.",
                type=n.ApplicationOptionType.STRING,
                required=False,
            ),
        ],
        dm_permission=False,
    )
    async def post_role_picker(self, ctx: t.CommandGI, name: str, content: str | None = None):
        """
        Post a role picker group.
        """

        # Fetch the role picker from the database
        async with db.Database.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    role_ids,
                    type
                FROM
                    role_pickers
                WHERE
                    guild_id=$1
                    AND name=$2
                """,
                ctx.guild.id,
                name,
            )

        # Check if the role picker exists
        if not row:
            await ctx.send(
                f"No role picker with the name `{name}` exists.",
                ephemeral=True,
            )
            return

        # Send the role picker message
        await ctx.send("Posting role picker...", ephemeral=True)
        await ctx.channel.send(
            content or "",
            components=[
                n.ActionRow([
                    await self.get_user_role_picker(
                        ctx.guild,  # pyright: ignore
                        name,
                        row["role_ids"],
                        row["type"] == "MULTIPLE",
                    )
                ]),
            ],
        )

    @client.event.filtered_component(r"ROLE_PICKER_SELECT")
    async def handle_role_picker_selection(self, interaction: t.ComponentGI):
        """
        Handle a user selecting roles from a role picker.
        """

        # Get the name from the custom ID
        _, name = interaction.data.custom_id.split(" ")

        # Fetch the role picker from the database
        async with db.Database.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    role_ids,
                    type
                FROM
                    role_pickers
                WHERE
                    guild_id=$1
                    AND name=$2
                """,
                interaction.guild.id,
                name,
            )

        # Check if the role picker exists
        if not row:
            await interaction.send(
                f"No role picker with the name `{name}` exists.",
                ephemeral=True,
            )
            return

        # Determine which roles to add/remove
        message: str = "I don't know what I did but it was sure something."
        selected_role_id = [int(i.value) for i in interaction.data.values][0]
        current_role_ids = interaction.user.role_ids  # pyright: ignore
        new_role_ids = set(current_role_ids)
        if selected_role_id in current_role_ids:
            new_role_ids.remove(selected_role_id)
            message = f"Removed <@&{selected_role_id}> from you."
        else:
            removed = []
            if row["type"] == "SINGLE":
                for role_id in row["role_ids"]:
                    if role_id in new_role_ids:
                        new_role_ids.discard(role_id)
                        removed.append(role_id)
            new_role_ids.add(selected_role_id)
            if removed:
                if len(removed) == 1:
                    message = (
                        f"I've added <@&{selected_role_id}> to you, and removed <@&{removed[0]}>."
                    )
                else:
                    removed_mentions = ", ".join(f"<@&{role_id}>" for role_id in removed)
                    message = (
                        f"I've added <@&{selected_role_id}> to you, and removed {removed_mentions}."
                    )
            else:
                message = f"I've added <@&{selected_role_id}> to you."

        # Update the user's roles
        await interaction.user.edit(  # pyright: ignore
            roles=list(new_role_ids),
            reason="Role picker selection"
        )
        await interaction.send(message, ephemeral=True)

    @delete_role_picker.autocomplete
    @edit_role_picker.autocomplete
    @post_role_picker.autocomplete
    async def role_picker_name_autocomplete(
            self,
            ctx: n.Interaction) -> list[n.ApplicationCommandChoice]:
        """
        Autocomplete for role picker names.
        """

        current = ctx.data.options[0].options[0].value
        async with db.Database.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    name
                FROM
                    role_pickers
                WHERE
                    guild_id=$1
                    AND name ILIKE $2
                ORDER BY
                    name ASC
                LIMIT 25
                """,
                ctx.guild.id,
                f"%{current}%",
            )

        return [
            n.ApplicationCommandChoice(name=row["name"], value=row["name"])
            for row in rows
        ]
