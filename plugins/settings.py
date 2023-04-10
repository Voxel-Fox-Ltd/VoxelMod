import novus
from novus.ext import client, database as db


class Settings(client.Plugin):

    @client.command(
        name="settings channel report",
        options=[
            novus.ApplicationCommandOption(
                name="channel",
                type=novus.ApplicationOptionType.channel,
                description="The channel that you want to set reports to funnel to.",
                channel_types=[novus.ChannelType.guild_text],
            ),
        ],
        default_member_permissions=novus.Permissions(manage_guild=True),
    )
    async def report_channel(
            self,
            interaction: novus.types.CommandI,
            channel: novus.GuildTextChannel) -> None:
        """
        Set the report channel.
        """

        await interaction.defer(ephemeral=True)
        assert interaction.guild
        async with db.Database.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO
                    guild_settings
                    (
                        guild_id,
                        report_channel_id
                    )
                VALUES
                    (
                        $1,
                        $2
                    )
                ON CONFLICT (guild_id)
                DO UPDATE
                SET
                    report_channel_id = excluded.report_channel_id
                """,
                interaction.guild.id,
                channel.id,
            )
        await interaction.send(
            f"The report channel has been set to **{channel.mention}**.",
            ephemeral=True,
        )
