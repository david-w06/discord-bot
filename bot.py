import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from discord.ext.commands import cooldown
import io
from huggingface_hub import InferenceClient

import aiosqlite

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_TOKEN = os.getenv("GEMINI_API_KEY")
HF_TOKEN = os.getenv("HF_API_KEY")

# Initialize client
gemini_client = genai.Client(api_key=GEMINI_TOKEN)
gemini_async = gemini_client.aio
hf_client = InferenceClient(token=HF_TOKEN)

#Initialize bot
intents = discord.Intents.default()
intents.message_content = True # Allows bot to read messages
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None) #disable default help
#Initialize SD Model


MAX_HISTORY = 10
MAX_CHARS = 1800

async def init_db():
    db = await aiosqlite.connect("memory.db")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)

    await db.commit()
    return db

@bot.event
async def on_ready():
    if not hasattr(bot, "db"):
        bot.db = await init_db()

    print(f"Logged in as {bot.user}")
    #Consider adding send to a default channel on startup


@bot.event
async def on_command_error(ctx, error): #Error handling

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"⏳ Slow down! Try again in {error.retry_after:.1f}s"
        )

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❗ You need to provide a message. Example: `!chat hello`")

    elif isinstance(error, commands.CommandNotFound):
        return  # silently ignore unknown commands

    else:
        await ctx.send("⚠️ Something went wrong.")
        print(error)

#------------------------------------COMMANDS---------------------------------------------#

# Chat command
@bot.command()
@commands.cooldown(3, 30, commands.BucketType.user)
async def chat(ctx, *, message=""):
    user_id = str(ctx.author.id)

    try:
        async with ctx.typing():

            # Get recent conversation history
            cursor = await bot.db.execute("""
                SELECT role, content
                FROM messages
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (user_id, MAX_HISTORY))

            rows = await cursor.fetchall()
            rows.reverse()

            conversation = "\n".join(
                f"{role}: {content}" for role, content in rows
            )

            # Save user's text
            if message:
                await bot.db.execute("""
                    INSERT INTO messages (user_id, role, content)
                    VALUES (?, ?, ?)
                """, (user_id, "User", message))

            # Prepare Gemini input
            contents = [conversation, message]

            # Add image if one was attached
            for attachment in ctx.message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    image_bytes = await attachment.read()

                    contents.append(
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=attachment.content_type
                        )
                    )

                    break

            # Non-blocking Gemini request
            response = await gemini_async.models.generate_content(
                model="gemini-3-flash-preview",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "You are a cute cat. "
                        "Keep responses concise and under 1800 characters."
                    )
                )
            )

            reply = response.text

            if len(reply) > MAX_CHARS:
                reply = reply[:MAX_CHARS] + "..."

            # Save AI response
            await bot.db.execute("""
                INSERT INTO messages (user_id, role, content)
                VALUES (?, ?, ?)
            """, (user_id, "Bot", reply))

            await bot.db.commit()

            await ctx.send(reply)

    except Exception as e:
        await ctx.send("Something went wrong.")
        print("ERROR:", e)

@bot.command()
async def reset(ctx):
    user_id = str(ctx.author.id)

    await bot.db.execute(
        "DELETE FROM messages WHERE user_id = ?",
        (user_id,)
    )

    await bot.db.commit()

    await ctx.send("Memory cleared. Meow~ starting fresh! 🐾")

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🐱 Bot Commands",
    )
    embed.add_field(name="!chat", value="Talk to the AI", inline=False)
    embed.add_field(name="!reset", value="Clear your memory", inline=False)
    embed.add_field(name="!help", value="Show this menu", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def image(ctx, *, prompt: str):
    await ctx.send("🎨 Generating image...")

    try:
        # Call Hugging Face API
        image = hf_client.text_to_image(
            prompt,
            model="stabilityai/stable-diffusion-3.5-large"
        )

        # Convert to Discord file
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        await ctx.send(file=discord.File(buffer, "image.png"))

    except Exception as e:
        await ctx.send(f"❌ Error generating image: {str(e)}")




# Run bot
bot.run(DISCORD_TOKEN)




