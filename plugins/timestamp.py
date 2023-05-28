from datetime import datetime as dt, MINYEAR, MAXYEAR
import re

import novus
from novus.ext import client


class Timestamp(client.Plugin):

    @client.command(
        name="timestamp",
        options=[
            novus.ApplicationCommandOption(
                name="time",
                type=novus.ApplicationOptionType.string,
                description="The time to convert ((yy)yy/mm/dd) (hh:mm)",
                required=True,
            ),  
            # novus.ApplicationCommandOption(
            #     name="timezone",
            #     type=novus.ApplicationOptionType.string,
            #     description="The timezone of the provided timestamp",
            #     required=False,
            # ),
        ],
    )
    async def timestamp(
            self,
            interaction: novus.types.CommandI,
            time: str) -> None:
        """
        Sends a well-formatted Discord timestamp message.
        """

        """
        The time string is made up of two parts: y/m/d and h:m

        Year can either be 2 digits (20yy) or 4 ditits (yyyy)
        Month and Day can be up to 2 digts (mm dd)
        Hour and Minute are both 1 or 2 digits (hh:mm)

        If an attribute is invalid (month 13, for example), the current value 
        for that attribute is used.
        """
        await interaction.defer()

        # The default values for each datetime attribute is the current time
        curr_time = dt.utcnow()
        created_payload = {
            'year': curr_time.year,
            'month': curr_time.month,
            'day': curr_time.day,

            'hour': curr_time.hour,
            'minute': curr_time.minute
        }

        # TODO: This could be moved into a util if needed
        # Patterns for recognizing year-month-date and hour-minute
        ymd_pattern = r"^(?:(?P<year>(?:\d{2})?\d{2})/)?(?P<month>\d{1,2})/(?P<day>\d{1,2})"
        hm_pattern = r"(?P<hour>\d{1,2}):(?P<minute>\d{1,2})"

        # Search the time string with both patterns
        ymd_match = re.search(f"{ymd_pattern}", time)
        hm_match = re.search(f"{hm_pattern}", time)

        # If a year-month-date match is found
        if ymd_match:
            year, month, day = map(int, ymd_match.groups())

            # Constrain and update the year
            if year and MINYEAR <= year <= MAXYEAR:
                
                # If a two-digit year is provided
                if year < 100:
                    year += 2000 # Will have to update this to 3000 eventually

                created_payload['year'] = year
            
            # Constrain and update the month
            if month and 1 <= month <= 12:
                created_payload['month'] = month
            
            # Constrain and update the day
            # If there's an easy way to calculate how many days are in a month,
            # feel free to change `31`
            if day and 1 <= day <= 31:
                created_payload['day'] = day
            
        # If a hour-minute match is found
        if hm_match:
            hour, minute = map(int, hm_match.groups())

            # Constrain and update the hour
            if hour and 0 <= hour < 24:
                created_payload['hour'] = hour
            
            # Constrain and update the minute
            if minute and 0 <= minute < 60:
                created_payload['minute'] = minute
        
        # TODO: No idea how I would do timezones lol

        try:
            created = dt(**created_payload)
            await interaction.send(f"<t:{int(created.timestamp())}>")
        except:
            # Send a confirmation message
            await interaction.send(
                "Something went wrong creating that timestamp :c"
            )





