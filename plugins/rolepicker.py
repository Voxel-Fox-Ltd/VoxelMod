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
from novus.ext import client
from novus import types as t


class Rolepicker(client.Plugin):
    """
    A plugin for rolepicker commands.
    """

    # client.CommandDescription

    @client.command(
        name="rolepicker create",
        options=[
            n.ApplicationCommandOption(
                name="name",
                description="The name of the role picker.",
                type=n.ApplicationOptionType.STRING,
            ),
        ],
        dm_permission=False,
    )
    async def create_rolepicker(self, ctx: t.CommandI, name: str):
        """
        Create a rolepicker group.
        """

        # Send an empty embed allowing the user to add/remove roles
        embed = n.Embed(title=f"Roles for the '{name}' group")
        components = [
            n.Container([
                n.TextDisplay("No roles added...")
            ]),
            n.Container([
                n.TextDisplay("Add a role"),
                n.RoleSelectMenu(
                    custom_id=f"ROLEPICKER_CREATE_ADD {name}",
                ),
            ]),
            n.Container([
                n.TextDisplay("Remove a role"),
                n.RoleSelectMenu(
                    custom_id=f"ROLEPICKER_CREATE_REMOVE {name}",
                ),
            ]),
        ]
        await ctx.send(componentsv2=components)

    @client.event.filtered_component(r"ROLEPICKER_CREATE_*")
    async def handle_create_rolepicker_dropdown(self, interaction: t.ComponentI):
        """
        Handle a rolepicker creation interaction for roles being added/removed.
        """

        action, group_name = interaction.custom_id.split(" ")[1:]
        selected_roles = interaction.values
        self.log.info(interaction.data)