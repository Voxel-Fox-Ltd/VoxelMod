import novus
from novus.ext import client


class Tag(client.Plugin):

    @client.command()
    async def tag(self, ctx: novus.types.CommandI) -> None:
        """
        Play tag with your server mates :)
        """

        await ctx.send(
            embeds=[
                novus.Embed(
                    title="Tag!",
                    description=(
                        "Join a game of tag! "
                    ),
                )
            ]
        )
