"""
fun.py
======
A Cog with simple slash commands for entertainment or fun interactions
"""

import os
import logging
import random
import requests
import discord  # Ensure discord is imported
from discord.ext import commands
from discord import app_commands, Interaction
from dotenv import load_dotenv

logger = logging.getLogger("TrabajoBot")

load_dotenv()
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")

class FunCog(commands.Cog):
    """
    Simple, fun slash commands (e.g., 8-ball).
    """
    cog_name = "Fun"
    cog_description = "Fun and random commands"
    cog_icon = "🎉"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.debug("FunCog initialized.")

    def get_random_gif(self, tag="pew pew"):
        """
        Fetches a random GIF URL from Giphy based on the provided tag.
        """
        if not GIPHY_API_KEY:
            logger.warning("GIPHY_API_KEY not found in environment. Using default GIFs.")
            return None

        url = f"https://api.giphy.com/v1/gifs/random?api_key={GIPHY_API_KEY}&tag={tag}&rating=pg-13"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            gif_url = data["data"]["images"]["original"]["url"]
            logger.debug(f"Fetched GIF from Giphy: {gif_url}")
            return gif_url
        except Exception as e:
            logger.error(f"Failed to fetch GIF from Giphy: {e}")
            return None

    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question.")
    @app_commands.describe(question="Your question for the 8-ball")
    async def eight_ball(self, interaction: Interaction, question: str):
        logger.info(f"/8ball invoked by {interaction.user} with question: {question}")
        await interaction.response.defer(thinking=True, ephemeral=False)
        responses = [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes – definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "No.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Don't count on it."
        ]
        answer = random.choice(responses)
        logger.debug(f"8-ball answer: {answer}")
        await interaction.followup.send(f"**Question**: {question}\n**Answer**: {answer}")
        
    @app_commands.command(name="pew", description="Pew pew a member!")
    @app_commands.describe(member="The member to pew pew")
    @commands.cooldown(1, 120, commands.BucketType.user)
    async def pew(self, interaction: Interaction, member: discord.Member):
        logger.info(f"/pew invoked by {interaction.user} on {member}")
        try:
            author_name = interaction.user.mention
            if interaction.guild.get_member(member.id) is None:
                await interaction.response.send_message("Member does not exist", ephemeral=True)
            else:
                embed = discord.Embed(title="Pew pew!", color=discord.Color.red())
                embed.description = f"User {author_name} shot {member.mention}!"
                
                # List of default shooting GIFs
                shooting_gifs = [
                    "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExamR1bXp5c3R5bjA4d2VreDFqc29pNzRnd3kzN2F5ejc4dXYxeG8wOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/9umH7yTO8gLYY/giphy.gif",
                    "https://media.giphy.com/media/4cz3D8Yhyzcg8/giphy.gif?cid=ecf05e47c1u0qjbwcb44dn7exdoq6cv39xl73f86hjqwta2y&ep=v1_gifs_related&rid=giphy.gif&ct=g",
                    "https://media.giphy.com/media/OgRsVkXWDLbXi/giphy.gif?cid=ecf05e47c1u0qjbwcb44dn7exdoq6cv39xl73f86hjqwta2y&ep=v1_gifs_related&rid=giphy.gif&ct=g",
                    "https://media.giphy.com/media/2jVc9KbzWWVgc/giphy.gif?cid=ecf05e477n2hwrutiqwrj5ra5426qbz5skgxmd9kikon30l7&ep=v1_gifs_related&rid=giphy.gif&ct=g",
                    "https://media.giphy.com/media/12MgUpnxEq3ypy/giphy.gif?cid=ecf05e47ycmjuh1sg9rf829pepx6s0mmf2ickv1543prxgkm&ep=v1_gifs_related&rid=giphy.gif&ct=g",
                    "https://media.giphy.com/media/hbtN4wlbTyEla/giphy.gif?cid=ecf05e47ycmjuh1sg9rf829pepx6s0mmf2ickv1543prxgkm&ep=v1_gifs_related&rid=giphy.gif&ct=g",
                    "https://media.giphy.com/media/PnhOSPReBR4F5NT5so/giphy.gif?cid=ecf05e47ycmjuh1sg9rf829pepx6s0mmf2ickv1543prxgkm&ep=v1_gifs_related&rid=giphy.gif&ct=g",
                    "https://media.giphy.com/media/QX26hw37ZXORAWNxyC/giphy.gif?cid=ecf05e47ycmjuh1sg9rf829pepx6s0mmf2ickv1543prxgkm&ep=v1_gifs_related&rid=giphy.gif&ct=g",
                    "https://media.giphy.com/media/FQOuwKQ46f9K7Vi5JR/giphy.gif?cid=ecf05e47ycmjuh1sg9rf829pepx6s0mmf2ickv1543prxgkm&ep=v1_gifs_related&rid=giphy.gif&ct=g"
                ]
                
                # Try to fetch a random GIF from Giphy
                gif_url = self.get_random_gif()
                if not gif_url:
                    gif_url = random.choice(shooting_gifs)
                logger.debug(f"Using GIF: {gif_url}")
                embed.set_image(url=gif_url)
                
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Problem: {e}")
            await interaction.response.send_message(f'Oops something went wrong, please try again or contact support.', ephemeral=True)

    @app_commands.command(name="coin", description="Flip a coin with another member.")
    @app_commands.describe(member="The member to flip a coin with")
    @commands.cooldown(1, 120, commands.BucketType.user)
    async def coin(self, interaction: Interaction, member: discord.Member = None):
        logger.info(f"/coin invoked by {interaction.user} with {member}")
        try:
            author_name = interaction.user.mention
            if member is None:
                # No member chosen, randomly choose heads or tails
                result = random.choice(["Heads", "Tails"])
                embed = discord.Embed(title="Coin Flip!", color=discord.Color.gold())
                embed.description = f"{author_name} flipped a coin and got **{result}**!"
                await interaction.response.send_message(embed=embed)
            else:
                # Member chosen, randomly choose one of the members to win
                winner = random.choice([author_name, member.mention])
                embed = discord.Embed(title="Coin Flip!", color=discord.Color.gold())
                embed.description = f"{author_name} flipped a coin with {member.mention} and **{winner}** won!"
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Problem: {e}")
            await interaction.response.send_message(f'Oops something went wrong, please try again or contact support.', ephemeral=True)

async def setup(bot: commands.Bot):
    logger.debug("Setting up FunCog...")
    await bot.add_cog(FunCog(bot))
