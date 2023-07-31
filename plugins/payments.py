from __future__ import annotations

import asyncpg
import novus
from novus.ext import client


class Payments(client.Plugin):

    async def get_connection(self) -> asyncpg.Connection:
        return await asyncpg.connect(self.bot.config.vfl_database_dsn)

    @client.command(
        name="purchases list",
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
    async def purchases_list(self, ctx: novus.types.CommandI, user: novus.User):
        """
        Get the purchases for a given user.
        """

        # Get the user from the database
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
            return await ctx.send(f"{user.mention} does not have a VFL account.")
        user_row = user_rows[0]
        user_embed = (
            novus.Embed(title="Voxel Fox account info")
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
        if not purchase_rows:
            return await ctx.send(embeds=[
                user_embed,
                novus.Embed(title="Purchases", description="None :(")
            ])
        purchases_embed = novus.Embed(title="Purchases")
        for r in purchase_rows:
            ts = novus.utils.parse_timestamp(r['timestamp'])
            identifier = r['identifier']
            if identifier.startswith("sub_"):
                identifier = f"[{identifier}](https://dashboard.stripe.com/subscriptions/{identifier})"
            lines = [
                f"* **ID**\n  {r['id']}",
                f"* **Timestamp**\n  {ts.format(novus.TimestampFormat.long_datetime)}",
                f"* **Identifier**\n  {identifier}",
            ]
            if r["discord_guild_id"]:
                lines.append(f"* **Guild ID**\n  {r['discord_guild_id']}",)
            if r["cancel_url"] or r["expiry_time"]:
                if r["expiry_time"]:
                    ts = novus.utils.parse_timestamp(r['expiry_time'])
                    lines.append(f"* **Subscription expiry**\n  {ts.format('R')}")
                else:
                    lines.append(f"* **Subscription expiry**\n  N/A")
            purchases_embed.add_field(r["product_name"], "\n".join(lines), inline=False)
        return await ctx.send(embeds=[
            user_embed,
            purchases_embed,
        ])

