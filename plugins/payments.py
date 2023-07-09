from __future__ import annotations

import asyncpg
import novus
from novus.ext import client


class Payments(client.Plugin):

    @client.command(
        options=[
            novus.ApplicationCommandOption(
                name="user",
                description="The user who you want to check the purchases of.",
                type=novus.ApplicationOptionType.user,
            ),
        ],
        dm_permission=False,
        default_member_permissions=novus.Permissions(manage_channels=True),
        guild_ids=[208895639164026880,],
    )
    async def purchases(self, ctx: novus.types.CommandI, user: novus.User):
        """
        Get the purchases for a given user.
        """

        # Get the user from the database
        conn: asyncpg.Connection = await asyncpg.connect(self.bot.config.vfl_database_dsn)
        user_rows = await conn.fetch(
            """
            SELECT
                *
            FROM
                users
            WHERE
                discord_user_id = $1::TEXT
            """,
            user.id,
        )
        if not user_rows:
            return await ctx.send(f"{user.mention} does not have a VFL account.")
        user_row = user_rows[0]
        user_embed = (
            novus.Embed(title="Voxel Fox account info")
            .add_field("ID", (user_id := user_row["id"]))
            .add_field("Discord ID", user_row["discord_user_id"])
        )

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
        if not purchase_rows:
            return await ctx.send(embeds=[
                user_embed,
                novus.Embed(title="Purchases", description="None :(")
            ])
        purchases_embed = novus.Embed(title="Purchases")
        for r in purchase_rows:
            purchases_embed.add_field(r["product_name"], "\n".join([
                f"* **ID**: {r['id']}",
                f"* **Identifier**: {r['identifier']}",
                f"* **Guild ID**: {r['discord_guild_id']}",
                f"* **Cancel URL**: {r['cancel_url']}",
                f"* **Expiry**: {r['expiry_time']}",
                f"* **Timestamp**: {r['timestamp']}",
            ]))
        return await ctx.send(embeds=[
            user_embed,
            purchases_embed,
        ])


