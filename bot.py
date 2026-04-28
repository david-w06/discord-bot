import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_TOKEN = os.getenv("GEMINI_TOKEN")

# Initialize client
client = genai.Client(api_key=GEMINI_TOKEN)

#Initialize bot
intents = discord.Intents.default()
intents.message_content = True # Allows bot to read messages
bot = commands.Bot(command_prefix="!", intents=intents)

memory= {} #Dictionary
MAX_HISTORY = 10
MAX_CHARS = 1800

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# Chat command
@bot.command()
async def chat(ctx, *, message):
    user_id = str(ctx.author.id)

    # Initialize memory if first time
    if user_id not in memory:
        memory[user_id] = []

    try:
        #Typing indicator
        async with ctx.typing():
            memory[user_id].append(f"User: {message}") # Add user message to key
            memory[user_id] = memory[user_id][-MAX_HISTORY:] # Keep only recent history
            conversation = "\n".join(memory[user_id]) # Combine memory into a single prompt

            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[conversation],
                config = types.GenerateContentConfig(
                system_instruction="You are a cute cat. Keep response concise and do not exceed 1800 characters.")
            )

        reply = response.text
        memory[user_id].append(f"Bot: {reply}") # Save bot reply into memory

        if len(reply) > MAX_CHARS:
            reply = reply[:MAX_CHARS] + "..." # Trim if too long

        await ctx.send(reply) # Send response to discord

    except Exception as e:
        await ctx.send("Something went wrong.")
        print(e)

# Run bot
bot.run(DISCORD_TOKEN)




