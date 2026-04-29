import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from discord.ext.commands import cooldown

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_TOKEN = os.getenv("GEMINI_TOKEN")

# Initialize client
client = genai.Client(api_key=GEMINI_TOKEN)

#Initialize bot
intents = discord.Intents.default()
intents.message_content = True # Allows bot to read messages
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None) #disable default help

memory= {} #Dictionary
MAX_HISTORY = 10
MAX_CHARS = 1800

@bot.event
async def on_ready():
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
async def chat(ctx, *, message):
    user_id = str(ctx.author.id)

    # Initialize memory if first time
    if user_id not in memory:
        memory[user_id] = []

    try:
        async with ctx.typing():

            # Add user message
            memory[user_id].append(f"User: {message}")
            memory[user_id] = memory[user_id][-MAX_HISTORY:]

            conversation = "\n".join(memory[user_id])

            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[conversation],
                config=types.GenerateContentConfig(
                    system_instruction="You are a cute cat. Keep responses concise and under 1800 characters."
                )
            )

            reply = response.text

            # Save bot reply
            memory[user_id].append(f"Bot: {reply}")

            # Trim if too long
            if len(reply) > MAX_CHARS:
                reply = reply[:MAX_CHARS] + "..."

            await ctx.send(reply)

    except Exception as e:
        await ctx.send("Something went wrong.")
        print("ERROR:", e)

@bot.command()
async def reset(ctx):
    user_id = str(ctx.author.id)
    if user_id in memory:
        memory[user_id]=[]
        await ctx.send("Memory cleared. Meow~ starting fresh! 🐾")
    else:
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

# Run bot
bot.run(DISCORD_TOKEN)




