import asyncio
from functools import partial
import sqlite3
from textwrap import dedent
import traceback
from typing import Optional
import discord
from discord.ext import commands

"""
Bot runs, and loads cog without problem.
Tested in discord, works with setup, joining, creating.
"""


VOICE_DB = "voice.db"

# create new database if it doesn't exist
try:
    with open(VOICE_DB, "r") as f:
        f.close()
except FileNotFoundError:
    conn = sqlite3.connect('voice.db')
    with open('voice.db.sql', 'r') as sql_file:
        conn.executescript(sql_file.read())
    conn.close()


def check_if_setup_user(m: commands.Context, ctx: commands.Context) -> bool:
    """Check if message send, is from `.voice setup` user"""
    return m.author.id == ctx.author.id


def check_empty_voice(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> bool:
    print(f"check empty: {member}, {before}, {after}")
    return (len(before.channel.members) == 0)


class FromDatabase(object):
    @classmethod
    def get_voice_id_from_user(cls, member_id: int, c: sqlite3.Cursor) -> Optional[tuple[int]]:
        c.execute(
            "SELECT voiceID FROM voiceChannel WHERE userID = ?",
            (member_id,)
        )
        return c.fetchone()
    @classmethod
    def get_user_voice(cls, member: discord.Member, c: sqlite3.Cursor) -> Optional[tuple[int, int]]:
        c.execute(
                "SELECT * FROM voiceChannel WHERE userID = ?",
                (member.id,)
            )
        return c.fetchone()

    @classmethod
    def get_voice_category(cls, guild_id: int, c: sqlite3.Cursor) -> tuple[int]:
        c.execute(
                "SELECT voiceCategoryID FROM guild WHERE guildID = ?",
                (guild_id,)
            )
        return c.fetchone()

    @classmethod
    def get_settings(cls, member: discord.Member, c: sqlite3.Cursor) -> Optional[tuple[str, int]]:
        c.execute(
                "SELECT channelName, channelLimit FROM userSettings WHERE userID = ?",
                (member.id,),
            )
        return c.fetchone()

    @classmethod
    def get_guild_settings(cls, guild_id: int, c: sqlite3.Cursor) -> Optional[tuple[str, int]]:
        c.execute(
                "SELECT channelName, channelLimit FROM guildSettings WHERE guildID = ?",
                (guild_id,)
            )
        return c.fetchone()

    @classmethod
    def get_guild_voice_id(cls, guild_id: int, c: sqlite3.Cursor) -> Optional[tuple[int]]:
        c.execute(
                "SELECT voiceChannelID FROM guild WHERE guildID = ?",
                (guild_id,)
            )
        return c.fetchone()


class _Voice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            guild_id = member.guild.id
            voice_create = FromDatabase.get_guild_voice_id(guild_id, c)

            if voice_create is None:
                return

            voice_id = voice_create[0]

            if before.channel is not None and before.channel.id == voice_id:
                return

            if before.channel and FromDatabase.get_user_voice(member, c):
                await before.channel.delete(reason="removing empty voice")
                c.execute("DELETE FROM voiceChannel WHERE userID=?", (member.id,))
            if after.channel is not None and after.channel.id == voice_id:
                try:
                    return await self.create_custom_channel(member, after, conn, c, guild_id)
                except Exception as e:
                    print("OnVoiceUpdate:")
                    traceback.print_exception(e)
            conn.commit()


    async def create_custom_channel(
            self,
            member: discord.Member,
            after: discord.VoiceState,
            conn: sqlite3.Connection,
            c: sqlite3.Cursor,
            guild_id: int
        ) -> None:
        if after.channel is None:
            return
        user_channel = FromDatabase.get_user_voice(member, c)
        if user_channel is not None:
            await member.send(f"You already have a channel at {self.bot.get_channel(user_channel[1]).mention}")
            return
        
        voice = FromDatabase.get_voice_category(guild_id, c)
        setting = FromDatabase.get_settings(member, c)
        guild_setting = FromDatabase.get_guild_settings(guild_id, c)

        name, limit = self.transform_settings(member, setting, guild_setting)
        category_id = voice[0]
        member_id = member.id

        category = self.bot.get_channel(category_id)
        channel_2 = await member.guild.create_voice_channel(name, category=category)
        channel_id = channel_2.id
        await member.move_to(channel_2)
        await channel_2.set_permissions(
            self.bot.user, connect=True, read_messages=True
        )
        await channel_2.set_permissions(member, connect=True, read_messages=True)
        await channel_2.edit(name=name, user_limit=limit)
        c.execute("INSERT INTO voiceChannel VALUES (?, ?)", (member_id, channel_id))
        conn.commit()



    def transform_settings(
            self,
            member: discord.Member,
            setting: Optional[tuple[str, int]],
            guild_setting: Optional[tuple[str, int]]
        ) -> tuple[str, int]:
        print(f"transform settings: {member}, {setting=}, {guild_setting=}")
        name = f"{member.name}'s channel" if setting is None else setting[0]
        if (
            setting is None 
            or guild_setting is None 
            or setting[1] == 0
        ):
            limit = 0
        else:
            limit = setting[1]
        return name, limit


    @commands.command()
    async def help(self, ctx: commands.Context) -> None:
        embed = discord.Embed(title="Help", description="", color=7506394)
        embed.set_author(
            name=f"{ctx.guild.me.display_name}",
            url="https://discordbots.org/bot/472911936951156740",
            icon_url=f"{ctx.guild.me.display_avatar.url}",
        )
        commands_text = dedent("""
            **Lock your channel by using the following command:**
            `.voice lock`
            ------------
            **Unlock your channel by using the following command:**
            `.voice unlock`
            ------------
            **Change your channel name by using the following command:**
            `.voice name <name>`
            **Example:** `.voice name EU 5kd+`
            ------------
            **Change your channel limit by using the following command:**
            `.voice limit number`
            **Example:** `.voice limit 2`
            ------------
            **Give users permission to join by using the following command:**
            `.voice permit @person`
            **Example:** `.voice permit @Sam#9452`
            ------------
            **Claim ownership of channel once the owner has left:**
            `.voice claim`
            **Example:** `.voice claim`
            ------------
            **Remove permission and the user from your channel using the following command:**
            `.voice reject @person`
            **Example:** `.voice reject @Sam#9452`
            """
        )
        embed.add_field(
            name="**Commands**",
            value=commands_text,
            inline="false",
        )
        embed.set_footer(text="Bot developed by Sam#9452")
        await ctx.channel.send(embed=embed)


    @commands.group()
    async def voice(self, ctx: commands.Context) -> None:
        pass


    @voice.command()
    async def setup(self, ctx: commands.Context) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            author_id = ctx.author.id
            if ctx.author.id == ctx.guild.owner_id or ctx.author.id in self.bot.owner_ids:
                await ctx.channel.send(dedent("""
                    **You have 60 seconds to answer each question!**
                    **Enter the name of the category you wish to create the channels in:(e.g Voice Channels)**"""
                    ))
                guild_id = ctx.guild.id
                check_func = partial(check_if_setup_user, ctx=ctx)
                category, channel = await self.get_setup_answers(ctx, check_func)
                new_cat = await ctx.guild.create_category(category.content)
                try:
                    await self.create_cat_channel(ctx, c, author_id, guild_id, new_cat, channel)
                except Exception as e:
                    print(f"setup error {e}")
                    await ctx.channel.send("You didn't enter the names properly.\nUse `.voice setup` again!")
            else:
                await ctx.channel.send(f"{ctx.author.mention} only the owner of the server can setup the bot!")
            conn.commit()


    async def create_cat_channel(
            self,
            ctx: commands.Context,
            c: sqlite3.Cursor,
            author_id: int,
            guild_id: int,
            new_cat: discord.CategoryChannel,
            channel: discord.Message
        ) -> None:
        channel = await ctx.guild.create_voice_channel(channel.content, category=new_cat)
        c.execute("SELECT * FROM guild WHERE guildID = ? AND ownerID=?", (guild_id, author_id))
        voice = c.fetchone()
        if voice is None:
            c.execute(
                "INSERT INTO guild VALUES (?, ?, ?, ?)",
                (guild_id, author_id, channel.id, new_cat.id),
            )
        else:
            c.execute(
                "UPDATE guild SET guildID = ?, ownerID = ?, voiceChannelID = ?, voiceCategoryID = ? WHERE guildID = ?",
                (guild_id, author_id, channel.id, new_cat.id, guild_id),
            )
        await ctx.channel.send("**You are all setup and ready to go!**")


    async def get_setup_answers(self, ctx: commands.Context, check_func) -> tuple[discord.Message, discord.Message]:
        try:
            category = await self.bot.wait_for("message", check=check_func, timeout=60.0)
            await ctx.channel.send("**Enter the name of the voice channel: (e.g Join To Create)**")
            channel = await self.bot.wait_for("message", check=check_func, timeout=60.0)
        except asyncio.TimeoutError:
            await ctx.channel.send("Took too long to answer!")
        return category, channel


    @commands.command()
    async def set_limit(self, ctx: commands.Context, number: int) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            if ctx.author.id == ctx.guild.owner.id or ctx.author.id in self.bot.owner_ids:
                settings = FromDatabase.get_guild_settings(ctx.guild.id, c)
                if settings is None:
                    c.execute(
                        "INSERT INTO guildSettings VALUES (?, ?, ?)",
                        (ctx.guild.id, f"{ctx.author.name}'s channel", number),
                    )
                else:
                    c.execute(
                        "UPDATE guildSettings SET channelLimit = ? WHERE guildID = ?",
                        (number, ctx.guild.id),
                    )
                await ctx.send("You have changed the default channel limit for your server!")
            else:
                await ctx.channel.send(
                    f"{ctx.author.mention} only the owner of the server can setup the bot!"
                )
            conn.commit()


    @setup.error
    async def info_error(self, ctx: commands.Context, error: Exception) -> None:
        print(error)

    @voice.command()
    async def lock(self, ctx: commands.Context) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            author_id = ctx.author.id
            voice = FromDatabase.get_voice_id_from_user(author_id, c)
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channel_id = voice[0]
                role = ctx.guild.default_role
                channel = self.bot.get_channel(channel_id)
                await channel.set_permissions(role, connect=False)
                await ctx.channel.send(f"{ctx.author.mention} Voice chat locked! 🔒")
            conn.commit()

    @voice.command()
    async def unlock(self, ctx: commands.Context) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            author_id = ctx.author.id
            voice = FromDatabase.get_voice_id_from_user(author_id, c)
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channel_id = voice[0]
                role = ctx.guild.default_role
                channel = self.bot.get_channel(channel_id)
                await channel.set_permissions(role, connect=True)
                await ctx.channel.send(f"{ctx.author.mention} Voice chat unlocked! 🔓")
            conn.commit()

    @voice.command(aliases=["allow"])
    async def permit(self, ctx: commands.Context, member: discord.Member) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            author_id = ctx.author.id
            voice = FromDatabase.get_voice_id_from_user(author_id, c)
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channel_id = voice[0]
                channel = self.bot.get_channel(channel_id)
                await channel.set_permissions(member, connect=True)
                await ctx.channel.send(
                    f"{ctx.author.mention} You have permitted {member.name} to have access to the channel. ✅"
                )
            conn.commit()

    @voice.command(aliases=["deny"])
    async def reject(self, ctx: commands.Context, member: discord.Member) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            author_id = ctx.author.id
            guild_id = ctx.guild.id
            voice = FromDatabase.get_voice_id_from_user(author_id, c)
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channel_id = voice[0]
                channel = self.bot.get_channel(channel_id)
                for members in channel.members:
                    if members.id == member.id:
                        c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guild_id,))
                        voice = c.fetchone()
                        channel2 = self.bot.get_channel(voice[0])
                        await member.move_to(channel2)
                await channel.set_permissions(member, connect=False, read_messages=True)
                await ctx.channel.send(
                    f"{ctx.author.mention} You have rejected {member.name} from accessing the channel. ❌"
                )
            conn.commit()

    @voice.command()
    async def limit(self, ctx: commands.Context, limit: int) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            author_id = ctx.author.id
            voice = FromDatabase.get_voice_id_from_user(author_id, c)
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channel_id = voice[0]
                channel = self.bot.get_channel(channel_id)
                await channel.edit(user_limit=limit)
                await ctx.channel.send(f"{ctx.author.mention} You have set the channel limit to be {limit}!")
                c.execute("SELECT channelName FROM userSettings WHERE userID = ?", (author_id,))
                voice = c.fetchone()
                if voice is None:
                    c.execute(
                        "INSERT INTO userSettings VALUES (?, ?, ?)",
                        (author_id, f"{ctx.author.name}", limit),
                    )
                else:
                    c.execute(
                        "UPDATE userSettings SET channelLimit = ? WHERE userID = ?", (limit, author_id)
                    )
            conn.commit()

    @voice.command()
    async def name(self, ctx: commands.Context, *, name: str) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            author_id = ctx.author.id
            voice = FromDatabase.get_voice_id_from_user(author_id, c)
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channel_id = voice[0]
                channel = self.bot.get_channel(channel_id)
                await channel.edit(name=name)
                await ctx.channel.send(f"{ctx.author.mention} You have changed the channel name to {name}!")
                c.execute(
                    "SELECT channelName FROM userSettings WHERE userID = ?",
                    (author_id,)
                )
                voice = c.fetchone()
                if voice is None:
                    c.execute(
                        "INSERT INTO userSettings VALUES (?, ?, ?)",
                        (author_id, name, 0)
                    )
                else:
                    c.execute(
                        "UPDATE userSettings SET channelName = ? WHERE userID = ?",
                        (name, author_id)
                    )
            conn.commit()


    @voice.command()
    async def claim(self, ctx: commands.Context) -> None:
        x = False
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            channel = ctx.author.voice.channel
            if channel is None:
                await ctx.channel.send(f"{ctx.author.mention} you're not in a voice channel.")
                return
            author_id = ctx.author.id
            c.execute(
                "SELECT userID FROM voiceChannel WHERE voiceID = ?",
                (channel.id,)
            )
            voice = c.fetchone()
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You can't own that channel!")
            else:
                for data in channel.members:
                    if data.id == voice[0]:
                        owner = ctx.guild.get_member(voice[0])
                        await ctx.channel.send(f"{ctx.author.mention} This channel is already owned by {owner.mention}!")
                        x = True
                if x is False:
                    await ctx.channel.send(f"{ctx.author.mention} You are now the owner of the channel!")
                    c.execute(
                        "UPDATE voiceChannel SET userID = ? WHERE voiceID = ?",
                        (author_id, channel.id)
                    )
            conn.commit()
            conn.close()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(_Voice(bot))