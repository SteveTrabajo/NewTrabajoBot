import discord
from discord.ext import commands
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger("TrabajoBot")

ADMIN_USER_ID = int(os.getenv("STEVEID"))  # Your Discord ID
TEST_GUILD_ID = int(os.getenv("TEST_GUILD_ID"))  # Your Test Guild ID

def is_owner(ctx):
    """Check if the command user is the bot owner (you)."""
    return ctx.author.id == ADMIN_USER_ID

class AdminCog(commands.Cog):
    """
    Provides admin commands like reloading cogs.
    Fully invisible from the slash command menu.
    """
    cog_name = "Admin"
    cog_description = "Commands for bot maintenance (Owner Only)."
    cog_icon_url = ""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="reload")
    async def reload(self, ctx, cog_name: str):
        """Reload a specific cog. Only executable by the bot owner."""
        if not is_owner(ctx):
            return  # Silently fail if not you

        logger.info(f"Reload command invoked by {ctx.author} for {cog_name}")
        await ctx.message.delete()  # Auto-delete command message for stealth

        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            logger.info(f"Reloaded cog: {cog_name}")
            await ctx.send(f"✅ Reloaded `{cog_name}` successfully!", delete_after=1)
        except Exception as e:
            logger.error(f"Failed to reload cog {cog_name}: {e}")
            if "has not been loaded" in str(e):
                await self.bot.load_extension(f"cogs.{cog_name}")
                logger.info(f"Loaded cog: {cog_name}")
                await ctx.send(f"✅ Loaded `{cog_name}` successfully!", delete_after=1)
            else:
                logger.error(f"Failed to reload cog {cog_name}: {e}")
                await ctx.send(f"❌ Error reloading `{cog_name}`: {e}", delete_after=5)

    @commands.command(name="reloadall")
    async def reload_all(self, ctx: commands.Context):
        """Reload all cogs in the bot."""
        if not is_owner(ctx):
            return  # Silently fail if not me

        logger.info(f"Reload all command invoked by {ctx.author}")
        await ctx.message.delete()  # Auto-delete command message for stealth
        errors = []
        for cog in list(self.bot.extensions):
            try:
                await self.bot.reload_extension(cog)
                logger.info(f"Reloaded {cog}")
            except Exception as e:
                if "has not been loaded" in str(e):
                    await self.bot.load_extension(f"cogs.{cog}")
                    logger.info(f"Cog: {cog} not loaded, loading...")
                else:
                    errors.append(f"❌ `{cog}`: {e}")
        if errors:
            await ctx.send("\n".join(errors), delete_after=5)
        else:
            synced = await self.bot.tree.sync()
            logger.info(f"Synced {len(synced)} commands globally.")
            await ctx.send("✅ Reloaded all cogs successfully!", delete_after=1)

    @commands.command(name="shutdown", help="Shuts down the bot (Owner only).")
    async def shutdown_command(self, ctx: commands.Context):
        if not is_owner(ctx):
            logger.warning(f"Unauthorized shutdown attempt by {ctx.author} (ID: {ctx.author.id})")
            return

        logger.warning(f"Shutdown invoked by owner: {ctx.author}")
        await ctx.send("Shutting down... Goodbye!", delete_after=0.5)
        await ctx.message.delete()

        # Close any resources here if needed (db connections, etc.)

        await self.bot.close() # Then close the bot

async def setup(bot: commands.Bot):
    logger.debug("Setting up AdminCog (Owner Only)...")
    await bot.add_cog(AdminCog(bot))
