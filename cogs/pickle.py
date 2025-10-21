"""
pickle.py
========
A Discord bot cog that handles the 'pickle size' game functionality.
Includes commands for checking pickle sizes, leaderboard, and growth tracking graphs.
"""

import nextcord
from nextcord.ext import commands, tasks
from nextcord import Embed
import matplotlib.pyplot as plt
import numpy as np
import datetime
import io
import os
from typing import Optional, Tuple, List, Dict
from db import Database
import logging

logger = logging.getLogger("TrabajoBot")

class PickleConfig:
    """Configuration settings for the Pickle module"""
    MIN_SIZE = 3
    MAX_SIZE = 32
    GRAPH_COLOR = 'white'
    HIGHLIGHT_COLOR = 'purple'
    EMBED_COLOR = nextcord.Color.purple()
    PICKLE_EMOJI = "🍆"
    
    # Special user IDs loaded from environment
    STEVE_ID = int(os.getenv('STEVEID', 0))
    LIOR_ID = int(os.getenv('LIORID', 0))
    SELF_ID = int(os.getenv('SELFID', 0))

class PickleData:
    """Handles all database operations for the Pickle module"""
    def __init__(self):
        self.db = Database()
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensures all required tables exist in the database"""
        creation_query = """
        CREATE TABLE IF NOT EXISTS pickle_sizes (
            user_id BIGINT PRIMARY KEY,
            current_size INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS pickle_history (
            user_id BIGINT,
            size INTEGER,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, recorded_at)
        );
        """
        self.db.execute(creation_query, commit=True)

    async def get_size(self, user_id: int) -> Optional[int]:
        """Get current pickle size for a user"""
        self.db.execute("SELECT current_size FROM pickle_sizes WHERE user_id = %s", (user_id,))
        result = self.db.fetchone()
        return result['current_size'] if result else None

    async def set_size(self, user_id: int, size: int):
        """Set pickle size for a user and record in history"""
        # Update current size
        self.db.execute("""
            INSERT INTO pickle_sizes (user_id, current_size)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE
            SET current_size = %s, last_updated = CURRENT_TIMESTAMP
        """, (user_id, size, size), commit=True)

        # Add to history
        self.db.execute("""
            INSERT INTO pickle_history (user_id, size)
            VALUES (%s, %s)
        """, (user_id, size), commit=True)

    async def get_leaderboard(self) -> List[Dict]:
        """Get the current pickle size leaderboard"""
        self.db.execute("""
            SELECT user_id, current_size 
            FROM pickle_sizes 
            ORDER BY current_size DESC
        """)
        return self.db.fetchall()

    async def get_history(self, user_id: int, months: int = 12) -> List[Tuple[datetime.date, int]]:
        """Get pickle size history for a user"""
        self.db.execute("""
            SELECT recorded_at::date as date, size
            FROM pickle_history
            WHERE user_id = %s
            AND recorded_at > NOW() - INTERVAL %s MONTH
            ORDER BY recorded_at ASC
        """, (user_id, months))
        return [(row['date'], row['size']) for row in self.db.fetchall()]

class PickleGraphs:
    """Handles all graph generation for the Pickle module"""
    @staticmethod
    async def create_history_graph(history: List[Tuple[datetime.date, int]], user: nextcord.Member) -> Tuple[io.BytesIO, dict]:
        """Creates a graph of pickle size history"""
        dates = [h[0] for h in history]
        sizes = [h[1] for h in history]

        plt.style.use('dark_background')
        plt.figure(figsize=(10, 6))
        plt.clf()

        # Create bars
        bars = plt.bar([d.strftime('%b') for d in dates], sizes)

        # Color all bars white except max
        max_idx = sizes.index(max(sizes))
        for i, bar in enumerate(bars):
            bar.set_color(PickleConfig.HIGHLIGHT_COLOR if i == max_idx else PickleConfig.GRAPH_COLOR)

        # Customize the graph
        plt.xlabel("Month")
        plt.ylabel("Length (cm)")
        plt.title(f"{user.display_name}'s Pickle Length - Last 12 Months")

        # Save to BytesIO
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        # Calculate stats
        stats = {
            'max_month': dates[max_idx].strftime('%b'),
            'max_size': sizes[max_idx],
            'average': round(np.mean(sizes), 2)
        }

        return buf, stats

class Pickle(commands.Cog):
    """A cog that handles the pickle size game functionality"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = PickleData()
        self._setup_monthly_reset()

    def _setup_monthly_reset(self):
        """Set up the monthly reset task"""
        @tasks.loop(hours=1)  # Check every hour
        async def check_monthly_reset():
            now = datetime.datetime.now()
            # If it's the first day of the month and between 00:00 and 01:00
            if now.day == 1 and now.hour == 0:
                logger.info("Performing monthly pickle size reset...")
                try:
                    # Archive current month's data
                    self.data.db.execute("""
                        INSERT INTO pickle_history (user_id, size)
                        SELECT user_id, current_size
                        FROM pickle_sizes
                        WHERE NOT EXISTS (
                            SELECT 1 FROM pickle_history
                            WHERE pickle_history.user_id = pickle_sizes.user_id
                            AND DATE_TRUNC('month', recorded_at) = DATE_TRUNC('month', CURRENT_TIMESTAMP)
                        )
                    """, commit=True)
                    
                    # Reset current sizes
                    self.data.db.execute("TRUNCATE TABLE pickle_sizes", commit=True)
                    
                    # Notify in all guilds where the bot is present
                    for guild in self.bot.guilds:
                        # Try to find a general or bot channel to send the message
                        channel = None
                        for ch in guild.text_channels:
                            if ch.name in ['general', 'bot', 'bot-commands', 'announcements']:
                                channel = ch
                                break
                        if channel:
                            try:
                                await channel.send(
                                    embed=nextcord.Embed(
                                        title=f"{PickleConfig.PICKLE_EMOJI} Monthly Pickle Reset {PickleConfig.PICKLE_EMOJI}",
                                        description="All pickle sizes have been reset for the new month! Use `/pickle` to get your new size!",
                                        color=PickleConfig.EMBED_COLOR
                                    )
                                )
                            except Exception as e:
                                logger.error(f"Failed to send reset notification in guild {guild.name}: {e}")
                    
                    logger.info("Monthly pickle size reset completed successfully")
                except Exception as e:
                    logger.error(f"Error during monthly pickle reset: {e}")

        # Start the task loop
        check_monthly_reset.start()
        
    def _get_size_message(self, user: nextcord.Member, size: int) -> str:
        """Generate appropriate message based on user and size"""
        if user.id == PickleConfig.STEVE_ID:
            return f"Master, your pickle size is **{size} cm**! {PickleConfig.PICKLE_EMOJI}"
        elif user.id == PickleConfig.LIOR_ID:
            return (f"**DAMN Lior! You got lucky this month.**\n"
                   f"Your pickle size is **{size} cm**! {PickleConfig.PICKLE_EMOJI}"
                   if size > 10 else
                   f"**HAH! Smol PP as always.**\n"
                   f"Those **{size} cm** couldn't even satisfy a fleshlight! {PickleConfig.PICKLE_EMOJI}")
        else:
            return f"**{user.display_name}**'s pickle size is **{size} cm**! {PickleConfig.PICKLE_EMOJI}"

    @nextcord.slash_command(description="Shows the size of your pickle")
    async def pickle(self, interaction: nextcord.Interaction, 
                    member: Optional[nextcord.Member] = nextcord.SlashOption(required=False)):
        """Check pickle size for yourself or another member"""
        target = member or interaction.user
        
        try:
            size = await self.data.get_size(target.id)
            
            if size is None:
                size = np.random.randint(PickleConfig.MIN_SIZE, PickleConfig.MAX_SIZE + 1)
                await self.data.set_size(target.id, size)
                
            message = self._get_size_message(target, size)
            embed = Embed(description=message, color=PickleConfig.EMBED_COLOR)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in pickle command: {e}")
            await interaction.response.send_message(
                "Sorry, something went wrong checking that pickle size!", 
                ephemeral=True
            )

    @nextcord.slash_command(description="Shows the pickle size leaderboard")
    async def pickleboard(self, interaction: nextcord.Interaction):
        """Display the pickle size leaderboard"""
        try:
            leaderboard = await self.data.get_leaderboard()
            
            if not leaderboard:
                await interaction.response.send_message("No pickle sizes recorded yet!")
                return

            # Build leaderboard text
            lb_text = ""
            for i, entry in enumerate(leaderboard, 1):
                member = await self.bot.fetch_user(entry['user_id'])
                if member:
                    lb_text += f"**{i}.** {member.name} - **{entry['current_size']}** cm\n"

            embed = nextcord.Embed(
                title=f"{PickleConfig.PICKLE_EMOJI} Pickle Leaderboard {PickleConfig.PICKLE_EMOJI}",
                description=lb_text,
                color=PickleConfig.EMBED_COLOR
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in pickleboard command: {e}")
            await interaction.response.send_message(
                "Sorry, something went wrong fetching the leaderboard!", 
                ephemeral=True
            )

    @nextcord.slash_command(description="Shows your pickle size history graph")
    async def picklegraph(self, interaction: nextcord.Interaction,
                         member: Optional[nextcord.Member] = nextcord.SlashOption(required=False)):
        """Display a graph of pickle size history"""
        target = member or interaction.user
        
        try:
            history = await self.data.get_history(target.id)
            
            if not history:
                embed = nextcord.Embed(
                    description=f"No pickle history found for **{target.display_name}**.\n"
                              f"Use `/pickle` first!",
                    color=nextcord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            # Generate graph
            graph_buf, stats = await PickleGraphs.create_history_graph(history, target)
            
            # Create embed
            embed = nextcord.Embed(
                title="Yearly Pickle Length History",
                color=PickleConfig.EMBED_COLOR,
                timestamp=datetime.datetime.now()
            )
            
            # Add stats
            embed.add_field(
                name="Best Month", 
                value=f"**{stats['max_month']}** - {stats['max_size']} cm", 
                inline=True
            )
            embed.add_field(
                name="Average", 
                value=f"{stats['average']} cm", 
                inline=True
            )
            
            # Set author and images
            embed.set_author(name=target.display_name, icon_url=target.display_avatar.url)
            embed.set_thumbnail(url='https://cdn3.emoji.gg/emojis/1774-hd-eggplant.png')
            
            # Send response
            file = nextcord.File(graph_buf, filename='pickle_history.png')
            embed.set_image(url='attachment://pickle_history.png')
            
            await interaction.response.send_message(
                content=f"||{target.mention}||",
                file=file,
                embed=embed
            )
            
        except Exception as e:
            logger.error(f"Error in picklegraph command: {e}")
            await interaction.response.send_message(
                "Sorry, something went wrong generating the graph!", 
                ephemeral=True
            )

    @commands.has_permissions(administrator=True)
    @nextcord.slash_command(
        name="resetpickles",
        description="Reset all pickle sizes (Admin only)",
        guild_ids=[1165008766345953351]
    )
    async def reset_pickles(self, interaction: nextcord.Interaction):
        """Reset all pickle sizes (Admin only)"""
        try:
            self.db.execute("TRUNCATE TABLE pickle_sizes, pickle_history", commit=True)
            await interaction.response.send_message(
                "All pickle sizes have been reset!", 
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in reset_pickles command: {e}")
            await interaction.response.send_message(
                "Sorry, something went wrong resetting the pickle sizes!", 
                ephemeral=True
            )

def setup(bot: commands.Bot):
    bot.add_cog(Pickle(bot))