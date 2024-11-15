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

from datetime import datetime as dt, timedelta, timezone
import re

import novus
from novus.ext import client
from dateutil import tz


class Timestamp(client.Plugin):

    @staticmethod
    def get_timezone_from_string(timezone_name: str) -> timezone | None:
        """
        Try and work out a timezone from an input string, in given priority
        order:

        * TODO See if the string is a TZ name
        * See if the string is in form UTC+XX:YY
        * See if the string is one of our common locations
            * US states
            * European countries
        * See if the string is one of our common acronyms
        * Fallback to null
        """

        # UTC offsets
        match = re.search(
            r"^utc(?P<direction>[+-])(?P<hour>\d{1,2}(?::(?P<minute>\d{2}))?)$",
            timezone_name,
            re.IGNORECASE,
        )
        if match is not None:
            delta = timedelta(
                hours=int(match.group("hour")),
                minutes=int(match.group("minute") or 0)
            )
            if match.group("direction") == "-":
                delta = -delta
            return timezone(delta)

        # Common countries
        # TODO

        # Common acronyms
        acronyms = {
            "UTC": tz.UTC,

            # Australia
            "ACST": tz.gettz("Australia/Adelaide"),
            "ACST": tz.gettz("Australia/Adelaide"),
            "ACT": tz.gettz("Australia/Adelaide"),
            "AEST": tz.gettz("Australia/Melbourne"),
            "AEDT": tz.gettz("Australia/Melbourne"),
            "AET": tz.gettz("Australia/Melbourne"),
            "AWST": tz.gettz("Australia/Perth"),
            "AWDT": tz.gettz("Australia/Perth"),

            # America
            "ET": tz.gettz("America/New_York"),
            "EST": tz.gettz("America/New_York"),
            "EDT": tz.gettz("America/New_York"),
            "CT": tz.gettz("America/Chicago"),
            "CST": tz.gettz("America/Chicago"),
            "CDT": tz.gettz("America/Chicago"),
            "MT": tz.gettz("America/Phoenix"),
            "MST": tz.gettz("America/Phoenix"),
            "MDT": tz.gettz("America/Phoenix"),
            "PT": tz.gettz("America/Los_Angeles"),
            "PST": tz.gettz("America/Los_Angeles"),
            "PDT": tz.gettz("America/Los_Angeles"),

            # Europe
            "GMT": tz.gettz("Europe/London"),
            "BST": tz.gettz("Europe/London"),
            "CET": tz.gettz("Europe/Brussels"),
            "CEST": tz.gettz("Europe/Brussels"),

            # Africa
            # Asia
        }
        if timezone_name.upper() in acronyms:
            return acronyms[timezone_name.upper()]

        # Fallback
        return None

    @client.command(
        name="timestamp",
        options=[
            novus.ApplicationCommandOption(
                name="year",
                type=novus.ApplicationOptionType.INTEGER,
                description="The year of the given datetime.",
                min_value=1_970,
                max_value=3_000,
                required=False,
            ),
            novus.ApplicationCommandOption(
                name="month",
                type=novus.ApplicationOptionType.INTEGER,
                description="The month of the given datetime.",
                choices=[
                    novus.ApplicationCommandChoice("January", 1),
                    novus.ApplicationCommandChoice("February", 2),
                    novus.ApplicationCommandChoice("March", 3),
                    novus.ApplicationCommandChoice("April", 4),
                    novus.ApplicationCommandChoice("May", 5),
                    novus.ApplicationCommandChoice("June", 6),
                    novus.ApplicationCommandChoice("July", 7),
                    novus.ApplicationCommandChoice("August", 8),
                    novus.ApplicationCommandChoice("September", 9),
                    novus.ApplicationCommandChoice("October", 10),
                    novus.ApplicationCommandChoice("November", 11),
                    novus.ApplicationCommandChoice("December", 12),
                ],
                required=False,
            ),
            novus.ApplicationCommandOption(
                name="day",
                type=novus.ApplicationOptionType.INTEGER,
                description="The day of the given datetime.",
                min_value=1,
                max_value=31,
                required=False,
            ),
            novus.ApplicationCommandOption(
                name="hour",
                type=novus.ApplicationOptionType.INTEGER,
                description="The hour of the given datetime, in 24 hour (military) time.",
                min_value=0,
                max_value=23,
                required=False,
            ),
            novus.ApplicationCommandOption(
                name="minute",
                type=novus.ApplicationOptionType.INTEGER,
                description="The minute of the given datetime.",
                min_value=0,
                max_value=59,
                required=False,
            ),
            novus.ApplicationCommandOption(
                name="timezone",
                type=novus.ApplicationOptionType.STRING,
                description="The timezone of the provided timestamp",
                required=False,
            ),
        ],
    )
    async def timestamp(
            self,
            ctx: novus.types.CommandI,
            *,
            year: int | None = None,
            month: int | None = None,
            day: int | None = None,
            hour: int | None = None,
            minute: int | None = None,
            timezone: str | None = None) -> None:
        """
        Sends a well-formatted Discord timestamp message.
        """

        # Get timezone so we can say if the timezone is valid
        if timezone is None:
            tz_object = tz.UTC
        elif (tz_object := self.get_timezone_from_string(timezone)) is None:
            return await ctx.send(
                f"The timezone `{timezone}` is not valid.",
                ephemeral=True,
            )

        # The default values for each datetime attribute is the current time
        now = dt.utcnow().replace(tzinfo=tz.UTC).astimezone(tz_object)
        default = lambda a, b: a if a is not None else b
        created_time = dt(
            year=default(year, now.year),
            month=default(month, now.month),
            day=default(day, now.day),
            hour=default(hour, now.hour),
            minute=(
                minute if minute is not None
                else 0 if hour is not None
                else now.minute
            ),
            second=0,
            microsecond=0,
            tzinfo=tz_object,
        )
        timestamp: str = str(int(created_time.timestamp()))
        await ctx.send(f"<t:{timestamp}> (`<t:{timestamp}>`)")
