"""
help.py
=======
A custom Help Cog that provides a single-parameter `/help` command:
 - "item": can be either a category or a command.
Behavior:
  - No item => show all categories.
  - If item matches a category => show that category's commands.
  - If item matches a command => show the category that command belongs to.
Case-insensitive matching, with merged autocomplete suggestions.
"""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
import logging

logger = logging.getLogger("TrabajoBot")

class HelpCog(commands.Cog):
    """
    A slash-based help system with a single "item" parameter that merges cogs + commands.
    """
    cog_name = "Help"
    cog_description = "Get help on categories or commands"
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.debug("HelpCog initialized.")
        # Remove default non-slash help
        bot.remove_command("help")

    # ----------------------------------------------------------------
    #  AUTOCOMPLETE
    # ----------------------------------------------------------------
    @app_commands.autocomplete()
    async def help_autocomplete(self, interaction: Interaction, current: str):
        """
        Return up to 25 combined suggestions (categories + commands), ignoring case.
        - Category suggestions come from cog_name
        - Command suggestions from cmd.qualified_name
        """
        suggestions = []
        current_lower = current.lower()

        # 1) Gather all categories (cogs)
        for cog_key, cog_obj in self.bot.cogs.items():
            friendly_name = getattr(cog_obj, "cog_name", cog_key)
            if current_lower in friendly_name.lower():
                suggestions.append(
                    app_commands.Choice(name=friendly_name, value=friendly_name)
                )

        # # 2) Gather all command names
        # for cmd_obj in self.bot.tree.walk_commands():
        #     qname_lower = cmd_obj.qualified_name.lower()
        #     if current_lower in qname_lower:
        #         # The suggestion label is just the command name (e.g. "play" or "music play")
        #         suggestions.append(
        #             app_commands.Choice(name=cmd_obj.qualified_name, value=cmd_obj.qualified_name)
        #         )

        # Return up to 25
        return suggestions[:25]

    # ----------------------------------------------------------------
    #  MAIN SLASH COMMAND
    # ----------------------------------------------------------------
    @app_commands.command(name="help", description="Show help for a category or command")
    @app_commands.describe(item="Type a category or command.")
    @app_commands.autocomplete(item=help_autocomplete)
    async def help_command(self, interaction: Interaction, item: str = None):
        """
        /help [item]
          - No item => show all categories
          - item is a category => show that category
          - item is a command => show the category that command belongs to
        Case-insensitive matching.
        """
        logger.info(f"/help invoked by {interaction.user} with item={item}")
        await interaction.response.defer(ephemeral=True, thinking=True)

        # CASE 1: No item => show all categories
        if not item:
            embed = self.build_all_categories_embed()
            return await interaction.followup.send(embed=embed)

        # Convert 'item' to case-insensitive
        item_lower = item.lower()
        
        # Special cases for short
        if item_lower == "info":
            item_lower = "information"
            
        if item_lower == "mod":
            item_lower = "moderation"

        # CASE 2: If item matches a category => show that category
        found_cog = self.match_cog_by_name(item_lower)
        if found_cog:
            embed = self.build_cog_commands_embed(found_cog)
            return await interaction.followup.send(embed=embed)

        # CASE 3: If item matches a command => find which category owns that command
        found_cog_for_cmd = self.match_cog_by_command(item_lower)
        if found_cog_for_cmd:
            embed = self.build_cog_commands_embed(found_cog_for_cmd)
            return await interaction.followup.send(embed=embed)

        # If neither category nor command matched
        return await interaction.followup.send(f"No category or command found for: **{item}**.")

    # ----------------------------------------------------------------
    #  MATCHERS
    # ----------------------------------------------------------------
    def match_cog_by_name(self, name_lower: str) -> commands.Cog | None:
        """
        Return the Cog whose user-friendly name (cog_name) 
        matches 'name_lower' (case-insensitive).
        """
        for cog_key, cog_obj in self.bot.cogs.items():
            friendly_name = getattr(cog_obj, "cog_name", cog_key).lower()
            if friendly_name == name_lower:
                return cog_obj
        return None

    def match_cog_by_command(self, command_lower: str) -> commands.Cog | None:
        """
        Return the Cog that has a command matching command_lower.
        If found, return that Cog.
        """
        for cmd_obj in self.bot.tree.walk_commands():
            if cmd_obj.qualified_name.lower() == command_lower:
                # Return the cog (binding) that command belongs to
                return cmd_obj.binding  # This is the Cog object
        return None

    # ----------------------------------------------------------------
    #  EMBED BUILDERS
    # ----------------------------------------------------------------
    def build_all_categories_embed(self) -> discord.Embed:
        """
        Show all cogs (categories).
        """
        embed = discord.Embed(
            title="Help - All Categories",
            description="``Pick a category or command``",
            color=discord.Color.blurple()
        )

        # Sort cogs by friendly name
        cogs_sorted = sorted(
            self.bot.cogs.items(),
            key=lambda x: getattr(x[1], "cog_name", x[0]).lower()
        )

        for cog_key, cog_obj in cogs_sorted:
            friendly_name = getattr(cog_obj, "cog_name", cog_key)
            desc = getattr(cog_obj, "cog_description", "No description.")
            embed.add_field(
                name=friendly_name,
                value=desc,
                inline=False
            )
        return embed

    def build_cog_commands_embed(self, cog: commands.Cog) -> discord.Embed:
        """
        Show all slash commands for a given cog.
        """
        friendly_name = getattr(cog, "cog_name", cog.__cog_name__)
        desc = getattr(cog, "cog_description", "No description.")
        embed = discord.Embed(
            title=f"{friendly_name} Commands",
            description=desc,
            color=discord.Color.green()
        )

        cmd_list = [
            cmd for cmd in self.bot.tree.walk_commands()
            if cmd.binding is cog
        ]
        if not cmd_list:
            embed.add_field(name="No commands found", value="(This category has no slash commands.)")
            return embed

        # Sort by command name
        for cmd_obj in sorted(cmd_list, key=lambda c: c.qualified_name):
            embed.add_field(
                name=f"/{cmd_obj.qualified_name}",
                value=cmd_obj.description or "No description.",
                inline=False
            )
        return embed

async def setup(bot: commands.Bot):
    logger.debug("Setting up HelpCog...")
    await bot.add_cog(HelpCog(bot))
