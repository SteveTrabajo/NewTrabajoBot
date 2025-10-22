import logging
from typing import cast
import asyncio
import discord
from discord.ext import commands
from discord import app_commands, Interaction

import wavelink

logger = logging.getLogger("TrabajoBot")

class MusicCog(commands.Cog):

    cog_name = "Music"
    cog_description = "Play music with the bot"
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    class ResetFiltersButton(discord.ui.Button):
        def __init__(self, interaction: Interaction, player: wavelink.Player, parent_cog):
            super().__init__(label="Reset Filters", style=discord.ButtonStyle.danger)
            self.interaction = interaction
            self.player = player
            self.parent_cog = parent_cog

        async def callback(self, interaction: Interaction):
            await self.parent_cog.reset_player_filters(interaction, self.player)
            self.disabled = True
            await self.interaction.edit_original_response(content="Player filters reset.", view=None)
            await asyncio.sleep(5)
            await self.interaction.delete_original_response()

    async def reset_player_filters(self, interaction: Interaction, player: wavelink.Player):
        filters = player.filters
        filters.reset()
        await player.set_filters(filters)

    # ---------------------------------------------------------
    # Events from snippet
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        logger.info("Wavelink Node connected: %r | Resumed: %s", payload.node, payload.resumed)
    
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        """
        Sends a 'Now Playing' embed to the player's home channel if set.
        """
        player: wavelink.Player | None = payload.player
        if not player:
            # Edge case
            return

        original: wavelink.Playable | None = payload.original
        track: wavelink.Playable = payload.track

        embed = discord.Embed(title="Now Playing")
        embed.description = f"**{track.title}** by `{track.author}`"

        if track.artwork:
            embed.set_image(url=track.artwork)

        if original and original.recommended:
            embed.description += f"\n\n`This track was recommended via {track.source}`"

        if track.album.name:
            embed.add_field(name="Album", value=track.album.name)

        # From snippet: "await player.home.send(embed=embed)"
        if hasattr(player, "home") and player.home:
            await player.home.send(embed=embed)

    # ---------------------------------------------------------
    # Utility: Check voice
    # ---------------------------------------------------------
    async def ensure_voice(self, interaction: Interaction) -> bool:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "Please join a voice channel first before using this command.",
                ephemeral=True
            )
            return False
        return True

    # ---------------------------------------------------------
    # /play from snippet
    # ---------------------------------------------------------
    @app_commands.command(name="play", description="Play a song with the given query (autoplay enabled).")
    @app_commands.describe(query="Search terms or link.")
    async def slash_play(self, interaction: Interaction, query: str):
        """
        The snippet's 'play' logic but as a slash command:
         - Connect if needed
         - Autoplay = enabled
         - If not player.playing: player.play(...)
        """
        if not await self.ensure_voice(interaction):
            return

        await interaction.response.defer()

        # Wavelink Player from voice_client
        player: wavelink.Player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            # connect
            try:
                channel = interaction.user.voice.channel
                player = await channel.connect(cls=wavelink.Player)
            except discord.ClientException:
                return await interaction.followup.send("I was unable to join that voice channel. Try again.")
        
        # Autoplay
        player.autoplay = wavelink.AutoPlayMode.partial

        # If snippet: "Lock the player to this channel"
        if not hasattr(player, "home"):
            player.home = interaction.channel
        elif player.home != interaction.channel:
            return await interaction.followup.send(
                f"You can only play songs in {player.home.mention}, since the player has already started there."
            )

        # Doc snippet: "tracks: wavelink.Search = await wavelink.Playable.search(query)"
        tracks: wavelink.Search = await wavelink.Playable.search(query)
        if not tracks:
            return await interaction.followup.send(
                f"Could not find any tracks with that query. Please try again."
            )

        if isinstance(tracks, wavelink.Playlist):
            # It's a playlist
            added = await player.queue.put_wait(tracks)
            await interaction.followup.send(f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue.")
        else:
            track_obj = tracks[0]
            await player.queue.put_wait(track_obj)
            await interaction.followup.send(f"Added **`{track_obj.title}`** to the queue.")

        # The snippet: "if not player.playing: ...  # Play now"
        if not player.playing:
            # "await player.play(player.queue.get(), volume=30)"
            next_t = player.queue.get()
            await player.play(next_t, volume=30)
            # optionally send a "Now playing" message
            # await interaction.followup.send(f"Now playing: **{next_t.title}**")

    # ---------------------------------------------------------
    # /skip
    # ---------------------------------------------------------
    @app_commands.command(name="skip", description="Skip the current song.")
    async def slash_skip(self, interaction: Interaction):
        """Skip song"""
        player: wavelink.Player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("No player to skip.", ephemeral=True)

        await interaction.response.defer()
        await player.skip(force=True)
        await interaction.followup.send("Skipped track.")

    # ---------------------------------------------------------
    # /nightcore
    # ---------------------------------------------------------
    @app_commands.command(name="nightcore", description="Set the filter to a nightcore style.")
    async def slash_nightcore(self, interaction: Interaction):
        """Snippets 'nightcore' command sets pitch=1.2, speed=1.2, rate=1"""
        player: wavelink.Player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("No player to apply nightcore to.", ephemeral=True)

        await interaction.response.defer()
        filters = player.filters
        filters.timescale.set(pitch=1.2, speed=1.2, rate=1)
        await player.set_filters(filters)

        view = discord.ui.View()
        view.add_item(self.ResetFiltersButton(interaction, player, self))

        await interaction.followup.send("Nightcore filter applied (pitch=1.2, speed=1.2).", view=view)

    # ---------------------------------------------------------
    # /resetfilters
    # ---------------------------------------------------------
    @app_commands.command(name="resetfilters", description="Resets all player filters")
    async def slash_resetfilters(self, interaction: Interaction):
        """Resets filters"""
        player: wavelink.Player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("No player to reset filters.", ephemeral=True)

        await interaction.response.defer()
        await self.reset_player_filters(interaction, player)
        await interaction.followup.send("Player filters reset.", delete_after=5)

    # ---------------------------------------------------------
    # /toggle = snippet's pause/resume
    # ---------------------------------------------------------
    @app_commands.command(name="toggle", description="Pause or Resume the player depending on its current state.")
    async def slash_toggle(self, interaction: Interaction):
        player: wavelink.Player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("No player found to toggle.", ephemeral=True)

        await interaction.response.defer()
        await player.pause(not player.paused)
        await interaction.followup.send("Toggled pause/resume.")

    # ---------------------------------------------------------
    # /volume
    # ---------------------------------------------------------
    @app_commands.command(name="volume", description="Change the volume of the player.")
    @app_commands.describe(value="Volume to set.")
    async def slash_volume(self, interaction: Interaction, value: int):
        """
        snippet: "await player.set_volume(value)"
        """
        player: wavelink.Player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("No player to set volume for.", ephemeral=True)

        await interaction.response.defer()
        await player.set_volume(value)
        await interaction.followup.send(f"Volume set to {value}.")

    # ---------------------------------------------------------
    # /disconnect (alias=dc)
    # ---------------------------------------------------------
    @app_commands.command(name="disconnect", description="Disconnect the Player.")
    async def slash_disconnect(self, interaction: Interaction):
        """Matches snippet's 'disconnect' logic: 'await player.disconnect()'"""
        player: wavelink.Player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)

        await interaction.response.defer()
        await player.disconnect()
        await interaction.followup.send("Disconnected.")

async def setup(bot: commands.Bot):
    """
    Standard async cog setup function for loading the MusicCog.
    """
    await bot.add_cog(MusicCog(bot))
