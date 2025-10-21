"""
moderation.py
=============
A Cog with slash commands for server moderation tasks such as kick, ban, and unban.
Logging of moderation actions included.
"""

import logging
import discord
from discord.ext import commands
from discord import app_commands, Interaction

logger = logging.getLogger("TrabajoBot")

class ModerationCog(commands.Cog):
    """
    Moderation Cog. Offers commands like kick, ban, unban.
    """
    cog_name = "Moderation"
    cog_description = "Server moderation commands (kick, ban, unban)."
    cog_icon_url = "https://cdn-icons-png.flaticon.com/512/1828/1828395.png"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.debug("ModerationCog initialized.")

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(member="The member to kick", reason="Reason for kicking")
    @app_commands.default_permissions(kick_members=True)
    async def kick_member(self, interaction: Interaction, member: discord.Member, reason: str = None):
        logger.info(f"/kick invoked by {interaction.user} on {member} with reason: {reason}")
        await interaction.response.defer(thinking=True, ephemeral=False)
        try:
            await member.kick(reason=reason)
            logger.info(f"Kicked {member} from the server.")
            await interaction.followup.send(f"Kicked {member.mention} (reason: {reason})")
        except discord.Forbidden:
            logger.warning("Kick failed due to missing permissions.")
            await interaction.followup.send("I do not have permission to kick this user.")
        except discord.HTTPException:
            logger.error("Kick failed (HTTPException).")
            await interaction.followup.send("Kick failed. Please try again.")

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(member="The member to ban", reason="Reason for banning")
    @app_commands.default_permissions(ban_members=True)
    async def ban_member(self, interaction: Interaction, member: discord.Member, reason: str = None):
        logger.info(f"/ban invoked by {interaction.user} on {member} with reason: {reason}")
        await interaction.response.defer(thinking=True, ephemeral=False)
        try:
            await member.ban(reason=reason)
            logger.info(f"Banned {member} from the server.")
            await interaction.followup.send(f"Banned {member.mention} (reason: {reason})")
        except discord.Forbidden:
            logger.warning("Ban failed due to missing permissions.")
            await interaction.followup.send("I do not have permission to ban this user.")
        except discord.HTTPException:
            logger.error("Ban failed (HTTPException).")
            await interaction.followup.send("Ban failed. Please try again.")

    @app_commands.command(name="unban", description="Unban a user by username.")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(username="The username of the user to unban")
    async def unban_member(self, interaction: Interaction, username: str):
        logger.info(f"/unban invoked by {interaction.user} for {username}")
        await interaction.response.defer(thinking=True, ephemeral=False)
        banned_users = await interaction.guild.bans()

        for ban_entry in banned_users:
            if ban_entry.user.name.lower() == username.lower():
                await interaction.guild.unban(ban_entry.user)
                logger.info(f"Unbanned {ban_entry.user}.")
                return await interaction.followup.send(f"Unbanned {ban_entry.user.mention}")

        logger.warning(f"User {username} not found in ban list.")
        await interaction.followup.send(f"User {username} not found among bans.")


async def setup(bot: commands.Bot):
    logger.debug("Setting up ModerationCog...")
    await bot.add_cog(ModerationCog(bot))
