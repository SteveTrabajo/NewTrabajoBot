"""
birthdays.py
============
A Cog for storing and retrieving user birthdays in CockroachDB using psycopg2.
"""

import logging
import datetime
from discord.ext import commands
from discord import app_commands, Interaction
from db import Database

logger = logging.getLogger("TrabajoBot")

class BirthdaysCog(commands.Cog):
    """
    Provides slash commands to set a birthday, view your birthday, and list all
    birthdays in the server.
    """
    cog_name = "Birthday"
    cog_description = "Birthday tracking commands."
    cog_icon_url = "https://cdn-icons-png.flaticon.com/512/2004/2004422.png"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()

        # Ensure the table exists
        creation_query = """
        CREATE TABLE IF NOT EXISTS birthdays (
            user_id BIGINT PRIMARY KEY,
            birthday_date DATE NOT NULL
        );
        """
        self.db.ensure_table_exists("birthdays", creation_query)
        logger.debug("BirthdaysCog initialized with database table check.")

    def __del__(self):
        self.db.conn.close()

    @app_commands.command(name="setbirthday", description="Set your birthday (YYYY-MM-DD).")
    @app_commands.describe(date="The date of your birthday (YYYY-MM-DD)")
    async def set_birthday(self, interaction: Interaction, date: str):
        logger.info(f"/setbirthday invoked by {interaction.user} with date {date}")
        
        # Defer the interaction immediately to prevent timeout
        await interaction.response.defer(thinking=True, ephemeral=False)
    
        try:
            # Parse the date string
            bday = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            logger.warning("Invalid date format provided.")
            # Send follow-up if the date is invalid
            return await interaction.followup.send("Invalid date format. Please use YYYY-MM-DD.")
    
        # Execute the database query
        query = """
            INSERT INTO birthdays (user_id, birthday_date)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE
              SET birthday_date = EXCLUDED.birthday_date
        """
        try:
            self.db.execute(query, (interaction.user.id, bday), commit=True)
            logger.debug(f"Birthday set for user {interaction.user.id} to {bday}")
            await interaction.followup.send(f"Birthday set to {bday} for {interaction.user.mention}")
        except Exception as e:
            logger.error(f"Database error when setting birthday: {e}")
            await interaction.followup.send("An error occurred while setting your birthday. Please try again later.")

    @app_commands.command(name="mybirthday", description="Check your stored birthday.")
    async def my_birthday(self, interaction: Interaction):
        logger.info(f"/mybirthday invoked by {interaction.user}")
        await interaction.response.defer(thinking=True, ephemeral=False)
        query = """
            SELECT birthday_date
            FROM birthdays
            WHERE user_id = %s
        """
        try:
            self.db.execute(query, (interaction.user.id,))
            row = self.db.fetchone()
            if row:
                logger.debug(f"User {interaction.user.id} birthday: {row['birthday_date']}")
                await interaction.followup.send(f"Your birthday is set to **{row['birthday_date']}**.")
            else:
                logger.debug(f"No birthday found for user {interaction.user.id}")
                await interaction.followup.send("No birthday set. Use /setbirthday to set it.")
        except Exception as e:
            logger.error(f"Database error when fetching birthday: {e}")
            await interaction.followup.send("An error occurred while fetching your birthday. Please try again later.")

    @app_commands.command(name="birthdaylist", description="List all birthdays in this server.")
    async def birthday_list(self, interaction: Interaction):
        logger.info(f"/birthdaylist invoked by {interaction.user}")
        await interaction.response.defer(thinking=True, ephemeral=False)
        query = """
            SELECT user_id, birthday_date
            FROM birthdays
            ORDER BY birthday_date
        """
        try:
            self.db.execute(query, ())
            rows = self.db.fetchall()
            if not rows:
                logger.debug("No birthdays found.")
                return await interaction.followup.send("No birthdays found.")

            lines = []
            for row in rows:
                user_id = row["user_id"]
                birthday = row["birthday_date"]
                # Check if the user is in the current server
                member = interaction.guild.get_member(user_id)
                if member is not None:
                    lines.append(f"{member.mention} - {birthday}")

            if not lines:
                return await interaction.followup.send("No birthdays found for members in this server.")

            await interaction.followup.send("\n".join(lines))
        except Exception as e:
            logger.error(f"Database error when fetching birthday list: {e}")
            await interaction.followup.send("An error occurred while fetching the birthday list. Please try again later.")

async def setup(bot: commands.Bot):
    logger.debug("Setting up BirthdaysCog...")
    await bot.add_cog(BirthdaysCog(bot))
