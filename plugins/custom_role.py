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
from novus import types as t
from novus.ext import client, database as db


class CustomRole(client.Plugin):

    async def readd_custom_role(self, guild: n.BaseGuild, user: n.GuildMember, role_id: int) -> int:
        """
        Re-adds a custom role to a user if they lost it but are still allowed to have it.

        Parameters
        ----------
        guild : n.Guild
            The guild that the user and role are in.
        user_id : int
            The ID of the user to re-add the role to.
        role_id : int
            The ID of the role to re-add.

        Returns
        -------
        bool
            Whether the role was successfully re-added.
        """

        if role_id is None:
            raise ValueError("Role ID cannot be None.")
        if role_id in user.role_ids:
            # User already has the role
            return -1
        try:
            await guild.add_member_role(
                user.id,
                role_id,
                reason="User custom role.",
            )
        except n.NotFound:
            # Role doesn't exist
            return 1
        except n.Forbidden:
            # We can't manage roles
            return 2
        else:
            # Successfully re-added
            return 0

    @client.command(
        "custom-role create",
        dm_permission=False,
    )
    async def custom_role_create(self, ctx: t.CommandGI) -> None:
        """
        Creates a custom role for a user in the server.
        """

        # Get relevant db data
        await ctx.defer(ephemeral=True)
        async with db.Database.acquire() as conn:
            row: dict[str, int] | None = await conn.fetchrow(
                """
                SELECT
                    custom_role_allowed_role_id,
                    custom_role_beneath_role_id
                FROM
                    guild_settings
                WHERE
                    guild_id = $1
                """,
                ctx.guild.id,
            )
            existing_custom_role_id: int | None = await conn.fetchval(
                """
                SELECT
                    role_id
                FROM
                    custom_roles
                WHERE
                    guild_id = $1
                    AND user_id = $2
                """,
                ctx.guild.id,
                ctx.user.id,
            )
        assert isinstance(ctx.user, n.GuildMember), "User should be a GuildMember"

        # See if they have the required role to use this command
        if row is None or row["custom_role_allowed_role_id"] is None:
            await ctx.send(
                "Custom role settings have not been set up on this server.",
                ephemeral=True,
            )
            return
        if (req_role_id := row["custom_role_allowed_role_id"]) not in ctx.user.role_ids:
            await ctx.send(
                f"You need to have the <@&{req_role_id}> role to create a custom role.",
                ephemeral=True,
            )
            return

        # See if they already have a custom role and readd if they lost it
        if existing_custom_role_id is not None:
            status = await self.readd_custom_role(ctx.guild, ctx.user, existing_custom_role_id)
            if status == -1:
                await ctx.send(
                    "You already have a custom role!",
                    ephemeral=True,
                )
                return
            elif status == 0:
                await ctx.send(
                    "I've re-added your existing custom role to you!",
                    ephemeral=True,
                )
                return

        # Create role and move into place
        if (ben_role_id := row["custom_role_beneath_role_id"]) is None:
            await ctx.send(
                "Custom role settings have not been set up on this server.",
                ephemeral=True,
            )
            return
        created_role = await ctx.guild.create_role(
            name=f"User custom role @ {ctx.user.id}",
            reason="User custom role.",
            permissions=n.Permissions.none(),
        )
        guild_roles = await ctx.guild.fetch_roles()
        guild_roles = sorted(guild_roles, key=lambda r: (r.position, r.id))
        new_guild_roles = []
        added_new = False
        for idx, i in enumerate(guild_roles):
            if i.id == ben_role_id:
                new_guild_roles.append((created_role.id, idx))
                added_new = True
            new_guild_roles.append((i.id, idx + (1 if added_new else 0)))
        await ctx.guild.move_roles(new_guild_roles)

        # Save role ID in the database
        async with db.Database.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO
                    custom_roles
                    (
                        guild_id,
                        user_id,
                        role_id
                    )
                VALUES
                    ($1, $2, $3)
                ON CONFLICT
                    (guild_id, user_id)
                DO UPDATE
                SET
                    role_id = EXCLUDED.role_id
                """,
                ctx.guild.id,
                ctx.user.id,
                created_role.id,
            )

        # Assign the role to the user
        await ctx.guild.add_member_role(
            ctx.user.id,
            created_role.id,
            reason="User custom role.",
        )

        # And done
        await ctx.send(f"Created your custom role, {created_role.mention}!")

    @client.command(
        "custom-role delete",
        dm_permission=False,
    )
    async def custom_role_delete(self, ctx: t.CommandGI) -> None:
        """
        Deletes a user's custom role from the server.
        """

        async with db.Database.acquire() as conn:

            # See if they have a custom role to delete
            custom_role_id: int | None = await conn.fetchval(
                """
                SELECT
                    role_id
                FROM
                    custom_roles
                WHERE
                    guild_id = $1
                    AND user_id = $2
                """,
                ctx.guild.id,
                ctx.user.id,
            )
            if custom_role_id is None:
                await ctx.send(
                    "You don't have a custom role!",
                    ephemeral=True,
                )
                return

            # Delete the role and remove from database
            try:
                await ctx.guild.delete_role(
                    custom_role_id,
                    reason="User custom role deletion.",
                )
            except n.NotFound:
                pass
            except n.Forbidden:
                await ctx.send(
                    "I don't have permission to delete your custom role.",
                    ephemeral=True,
                )
                return
            await conn.execute(
                """
                DELETE FROM
                    custom_roles
                WHERE
                    guild_id = $1
                    AND user_id = $2
                """,
                ctx.guild.id,
                ctx.user.id,
            )

        # And done
        await ctx.send("Deleted your custom role.")

    @client.command(
        "custom-role edit name",
        options=[
            n.ApplicationCommandOption(
                name="name",
                description="The name that you want the custom role to have.",
                type=n.ApplicationOptionType.STRING,
            )
        ],
        dm_permission=False,
    )
    async def custom_role_edit_name(self, ctx: t.CommandGI, name: str) -> None:
        """
        Edits the name of a user's custom role.
        """

        await ctx.defer(ephemeral=True)
        async with db.Database.acquire() as conn:

            # See if they have a custom role
            custom_role_id: int | None = await conn.fetchval(
                """
                SELECT
                    role_id
                FROM
                    custom_roles
                WHERE
                    guild_id = $1
                    AND user_id = $2
                """,
                ctx.guild.id,
                ctx.user.id,
            )
            if custom_role_id is None:
                await ctx.send(
                    "You don't have a custom role!",
                    ephemeral=True,
                )
                return

        # Readd role if necessary
        assert isinstance(ctx.user, n.GuildMember), "User should be a GuildMember"
        if custom_role_id is not None:
            status = await self.readd_custom_role(ctx.guild, ctx.user, custom_role_id)
            if status == 1:
                await ctx.send(
                    "Your custom role seems to have been deleted.",
                    ephemeral=True,
                )
                return
            elif status == 2:
                await ctx.send(
                    "I don't have permission to manage your custom role.",
                    ephemeral=True,
                )
                return

        # Edit the role's name
        try:
            await ctx.guild.edit_role(
                custom_role_id,
                name=name,
                reason="User custom role name change.",
            )
        except n.NotFound:
            await ctx.send(
                "Your custom role seems to have been deleted.",
                ephemeral=True,
            )
            return
        except n.Forbidden:
            await ctx.send(
                "I don't have permission to manage your custom role.",
                ephemeral=True,
            )
            return

        # And done
        await ctx.send(
            f"Renamed your custom role to **{name}**!",
            ephemeral=True,
        )

    @client.command(
        "custom-role edit colour",
        options=[
            n.ApplicationCommandOption(
                name="colour",
                description="The name that you want the custom role to have.",
                type=n.ApplicationOptionType.STRING,
            )
        ],
        dm_permission=False,
    )
    async def custom_role_edit_colour(self, ctx: t.CommandGI, colour: str) -> None:
        """
        Edits the colour of a user's custom role.
        """

        await ctx.defer(ephemeral=True)

        async with db.Database.acquire() as conn:

            # See if they have a custom role
            custom_role_id: int | None = await conn.fetchval(
                """
                SELECT
                    role_id
                FROM
                    custom_roles
                WHERE
                    guild_id = $1
                    AND user_id = $2
                """,
                ctx.guild.id,
                ctx.user.id,
            )
            if custom_role_id is None:
                await ctx.send(
                    "You don't have a custom role!",
                    ephemeral=True,
                )
                return

        # Validate colour
        if colour.startswith("#"):
            colour = colour[1:]
        try:
            colour_int = int(colour, 16)
        except ValueError:
            await ctx.send(
                "Invalid colour! Please provide a hex code like `#FF0000`.",
                ephemeral=True,
            )
            return

        # Readd role if necessary
        assert isinstance(ctx.user, n.GuildMember), "User should be a GuildMember"
        if custom_role_id is not None:
            status = await self.readd_custom_role(ctx.guild, ctx.user, custom_role_id)
            if status == 1:
                await ctx.send(
                    "Your custom role seems to have been deleted.",
                    ephemeral=True,
                )
                return
            elif status == 2:
                await ctx.send(
                    "I don't have permission to manage your custom role.",
                    ephemeral=True,
                )
                return

        # Edit the role's colour
        try:
            await ctx.guild.edit_role(
                custom_role_id,
                color=colour_int,
                reason="User custom role colour change.",
            )
        except n.NotFound:
            await ctx.send(
                "Your custom role seems to have been deleted.",
                ephemeral=True,
            )
            return
        except n.Forbidden:
            await ctx.send(
                "I don't have permission to manage your custom role.",
                ephemeral=True,
            )
            return

        # And done
        await ctx.send(
            f"Changed your custom role's color to **#{colour_int:0>6X}**!",
            ephemeral=True,
        )

    @client.event.guild_member_update
    async def member_update_listener(self, before: n.GuildMember, after: n.GuildMember) -> None:
        """
        Listens for a user losing the required role to keep a custom role, deleting it if
        necessary.
        """

        # See if they had a custom role before and don't now
        pass

        # If so, delete role
        pass

    @client.event.guild_member_remove
    async def member_leave_listener(self, guild: n.BaseGuild, user: n.GuildMember | n.User) -> None:
        """
        Listens for a user leaving the server, deleting their custom role if they had one.
        """

        # See if they had a custom role
        pass

        # If so, delete role
        pass
