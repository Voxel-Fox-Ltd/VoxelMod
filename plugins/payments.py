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

import os

import asyncpg
import dotenv
import novus as n
from novus import types as t
from novus.ext import client


dotenv.load_dotenv()


class Payments(client.Plugin):
    """
    For handling Voxel Fox website payment processing.
    """

    async def get_connection(self) -> asyncpg.Connection:
        return await asyncpg.connect(self.bot.config.vfl_database_dsn)

    @client.command(
        name="purchases list user",
        options=[
            n.ApplicationCommandOption(
                name="user",
                description="The user who you want to check the purchases of.",
                type=n.ApplicationOptionType.USER,
            ),
        ],
        dm_permission=False,
        default_member_permissions=n.Permissions(manage_channels=True),
        guild_ids=[int(os.getenv("MAIN_GUILD_ID", 0))],
    )
    async def purchases_list_user(self, ctx: n.types.CommandI, user: n.User):
        """
        Get the purchases for a given user.
        """

        conn = await self.get_connection()
        user_rows = await conn.fetch(
            """
            SELECT
                *
            FROM
                users
            WHERE
                discord_user_id = $1
            """,
            str(user.id),
        )
        if not user_rows:
            await conn.close()
            return await ctx.send(f"{user.mention} does not have a VFL account.")
        return await self.purchases_list_generic(ctx, conn, user_rows)

    @client.command(
        name="purchases list id",
        options=[
            n.ApplicationCommandOption(
                name="id",
                description="The VFL ID that you want to check the purchases of.",
                type=n.ApplicationOptionType.STRING,
            ),
        ],
        dm_permission=False,
        default_member_permissions=n.Permissions(manage_channels=True),
        guild_ids=[int(os.getenv("MAIN_GUILD_ID", 0))],
    )
    async def purchases_list_id(self, ctx: n.types.CommandI, id: str):
        """
        Get the purchases for a given VFL user ID.
        """

        conn = await self.get_connection()
        user_rows = await conn.fetch(
            """
            SELECT
                *
            FROM
                users
            WHERE
                id = $1
            """,
            id,
        )
        if not user_rows:
            await conn.close()
            return await ctx.send(
                f"There is no VFL account with the ID `{id}`.", 
                allowed_mentions=n.AllowedMentions.none(),
            )
        return await self.purchases_list_generic(ctx, conn, user_rows)

    async def purchases_list_generic(
            self, 
            ctx: t.CommandI, 
            conn: asyncpg.Connection, 
            user_rows: list[dict]) -> None:
        """
        Generic purchase list handling when given rows.
        """

        # Sort out initial data
        user_row = user_rows[0]
        user_embed = (
            n.Embed(title="Voxel Fox account info")
            .add_field("ID", str(user_id := user_row["id"]))
            .add_field("Discord ID", str(user_row["discord_user_id"]))
        )
        if (suid := user_row["stripe_customer_id"]):
            url = f"https://dashboard.stripe.com/customers/{suid}"
            user_embed.add_field("Stripe ID", f"[{suid}]({url})")

        # Get their purchases
        purchase_rows = await conn.fetch(
            """
            SELECT
                checkout_items.product_name,
                purchases.id,
                purchases.identifier,
                purchases.discord_guild_id,
                purchases.cancel_url,
                purchases.expiry_time,
                purchases.timestamp
            FROM
                purchases
            LEFT JOIN
                checkout_items
            ON
                purchases.product_id = checkout_items.id
            WHERE
                user_id = $1
            ORDER BY
                purchases.timestamp DESC
            """,
            user_id,
        )
        await conn.close()

        # Default for no rows
        if not purchase_rows:
            return await ctx.send(embeds=[
                user_embed,
                n.Embed(title="Purchases", description="None :(")
            ])

        # Create embed for purchases
        purchases_embed = n.Embed(title="Purchases")
        for r in purchase_rows:
            ts = n.utils.parse_timestamp(r['timestamp'])
            identifier = r['identifier']
            if identifier.startswith("sub_"):
                identifier = f"[{identifier}](https://dashboard.stripe.com/subscriptions/{identifier})"
            elif identifier.startswith("in_"):
                identifier = f"[{identifier}](https://dashboard.stripe.com/invoices/{identifier})"
            lines = [
                f"* **ID**\n  {r['id']}",
                f"* **Timestamp**\n\u200b  {ts.format(n.TimestampFormat.LONG_DATETIME)}",
                f"* **Identifier**\n\u200b  {identifier}",
            ]
            if r["discord_guild_id"]:
                lines.append(f"* **Guild ID**\n  {r['discord_guild_id']}",)
            if r["cancel_url"] or r["expiry_time"]:
                if r["expiry_time"]:
                    ts = n.utils.parse_timestamp(r['expiry_time'])
                    lines.append(f"* **Subscription expiry**\n\u200b  {ts.format('R')}")
                else:
                    lines.append(f"* **Subscription expiry**\n  N/A")
            purchases_embed.add_field(r["product_name"], "\n".join(lines), inline=False)

        # Send created embeds
        return await ctx.send(embeds=[
            user_embed,
            purchases_embed,
        ])

