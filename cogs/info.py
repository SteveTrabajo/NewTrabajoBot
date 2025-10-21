"""
info.py
=======
A Cog that provides general informational slash commands about users and servers.
Logging included to track calls.

Now sets cog_description and cog_icon_url for use by the Help Cog.
"""


import logging
import discord
from discord.utils import format_dt
from discord.ext import commands
from discord import app_commands, Interaction
from discord.ui import Button, View

logger = logging.getLogger("TrabajoBot")

class InfoCog(commands.Cog):
    """
    Includes commands to show user info and server info.
    """
    cog_name = "Information"
    cog_description = "Commands for user/server info."
    cog_icon_url = "https://cdn-icons-png.flaticon.com/512/993/993535.png"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.debug("InfoCog initialized.")

    @app_commands.command(name="userinfo", description="Displays info about a user, or yourself if none specified.")
    @app_commands.describe(member="Which user to get info about (must be in this server).")
    async def userinfo(self, interaction: Interaction, member: discord.Member = None):
        """
        Slash command: /userinfo [user]
          - If no user is given, we show the invoking user's info.
          - If a user is provided but not in this server, we can't show presence/roles.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)

        logger.info(f"/userinfo invoked by {interaction.user} (target: {member or 'self'})")

        if member is None:
            member = interaction.user  
        
        member = interaction.guild.get_member(member.id)

        if member is None:
            await interaction.followup.send(
                f"**{member}** is not in this server (or I can't access them)."
            )
            return

        # Build presence string
        presence_map = {
            discord.Status.online: "🟢 Online",
            discord.Status.idle: "🌙 Idle",
            discord.Status.dnd:   "⛔ Do Not Disturb",
            discord.Status.offline: "🔴 Offline"
        }
        presence_str = presence_map.get(member.status, "Unknown")
        
        # Basic account info
        created_str = format_dt(member.created_at, style="R")  # "X time ago"
        joined_str = format_dt(member.joined_at, style="R") if member.joined_at else "N/A"

        # Roles (excluding @everyone)
        roles = [r.mention for r in member.roles if r != interaction.guild.default_role]
        if not roles:
            roles_display = "No roles"
        else:
            roles_display = " ".join(roles)

        # Build an embed
        embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(name=f"{member.name}",icon_url="https://cdn3.emoji.gg/emojis/2986-discord-username.png")
        # Avatar
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        embed.set_footer(text=f"ID: {member.id}", icon_url="https://cryptologos.cc/logos/space-id-id-logo.png")
        embed.add_field(name="Mention", value=member.mention, inline=True)
        embed.add_field(name="Bot?", value="Yes" if member.bot else "No", inline=True)
        embed.add_field(name="Status", value=presence_str, inline=True)
        embed.add_field(name="Account Created", value=created_str, inline=True)
        embed.add_field(name="Joined Server", value=joined_str, inline=True)
        embed.add_field(name="Roles", value=roles_display, inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="serverinfo", description="Displays info about the server.")
    @app_commands.describe(guild_id="The ID of the server to get info of")
    async def serverinfo(self, interaction: Interaction, guild_id: int = None):
        logger.info(f"/serverinfo invoked by {interaction.user} for guild {guild_id or interaction.guild.id}")
        await interaction.response.defer(thinking=True, ephemeral=False)
        try:
            if guild_id:
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    await interaction.followup.send(f"Server with ID {guild_id} not found.", ephemeral=True)
                    return
            else:
                guild = interaction.guild
                
            created = discord.utils.format_dt(guild.created_at, "R")
            embed = discord.Embed(
                title=f"Server Info - {guild.name}",
                color=discord.Color.green()
            )
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            embed.set_author(name=guild.name)
            embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
            embed.add_field(name="Member Count", value=guild.member_count, inline=True)
            embed.add_field(name="Role Count", value=len(guild.roles), inline=True)
            embed.add_field(name="Server Level", value=guild.premium_tier, inline=True)
            embed.add_field(name="Boost Count", value=f"{guild.premium_subscription_count}/14", inline=True)
            embed.add_field(name="Channel Count", value=len(guild.channels), inline=True)
            embed.add_field(name="Created", value=created, inline=True)
            embed.add_field(name="Description", value=guild.description, inline=False)
            
            embed.set_footer(text=guild.id, icon_url="https://cryptologos.cc/logos/space-id-id-logo.png")
            
            # Send the embed as a response to the interaction
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /serverinfo: {e}")
            await interaction.followup.send("An error occurred while fetching server info. Please try again later.", ephemeral=True)

    @app_commands.command(name="ping", description="Displays ping information")
    async def ping(self, interaction: Interaction):
        logger.info(f"/ping invoked by {interaction.user}")
        await interaction.response.defer(thinking=True, ephemeral=False)
        embed = discord.Embed(
            title=f"Pong! 🏓",
            color=discord.Color.green()
        )
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        await interaction.followup.send(embed=embed)

    
            
    @app_commands.command(name="invite", description="Sends the bot invite link")
    async def invite(self, interaction: Interaction):
        logger.info(f"/invite invoked by {interaction.user}")
        await interaction.response.defer(thinking=True, ephemeral=True)
        invite_link = "https://discord.com/oauth2/authorize?client_id=1000039115183640588"
        # Create the URL button
        link_button = Button(label="🤖 Invite TrabajoBot", url=invite_link)

        # Create a View and add the button
        view = View()
        view.add_item(link_button)
        
        await interaction.followup.send("## Click below to invite me!",view=view, ephemeral=True)
        
async def setup(bot: commands.Bot):
    logger.debug("Setting up InfoCog...")
    await bot.add_cog(InfoCog(bot))
