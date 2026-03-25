import discord
from discord.ext import commands
from discord import app_commands
from bytez import Bytez
import asyncio
import os
from collections import defaultdict

# Config
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
BYTEZ_KEY = "f4cc6d4dbf0c693ed79841d709bc5455"

# AI Setup with GPT-4o
sdk = Bytez(BYTEZ_KEY)
model = sdk.model("openai/gpt-4o")

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Memory & Modes
memory = defaultdict(list)
modes = {
    "normal": "You're Batman but chill. Use slang. Be fun. Short answers. Max 1-2 sentences.",
    "freaky": "You're Batman but flirty. Be smooth and spicy. Short answers. Max 1-2 sentences.",
    "angry": "You're Batman but pissed. Roast them. Be savage but funny. Short answers. Max 1-2 sentences.",
    "batman": "You're Batman. Dark, serious, brooding. Use 'I'm Batman' sometimes. Short answers. Max 1-2 sentences."
}
user_mode = {}

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online with GPT-4o")
    await bot.tree.sync()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if bot.user in message.mentions or isinstance(message.channel, discord.DMChannel):
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not content:
            return
            
        async with message.channel.typing():
            uid = message.author.id
            mode = user_mode.get(uid, "normal")
            
            # Build messages with memory
            msgs = [{"role": "system", "content": modes[mode]}]
            msgs.extend(memory[uid][-6:])
            msgs.append({"role": "user", "content": content})
            
            # Get AI response
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: model.run(msgs))
            
            if result.error:
                await message.channel.send("Error. Try again.")
            elif result.output:
                reply = result.output[-1]["content"] if isinstance(result.output, list) else str(result.output)
                reply = reply[:1900]
                
                # Store memory
                memory[uid].append({"role": "user", "content": content})
                memory[uid].append({"role": "assistant", "content": reply})
                if len(memory[uid]) > 12:
                    memory[uid] = memory[uid][-12:]
                
                await message.channel.send(reply)

@bot.tree.command(name="mode", description="Change my personality")
@app_commands.choices(mode=[
    app_commands.Choice(name="Normal - Chill & fun", value="normal"),
    app_Commands.Choice(name="Freaky - Flirty & spicy", value="freaky"),
    app_commands.Choice(name="Angry - Savage roasts", value="angry"),
    app_commands.Choice(name="Batman - Dark & serious", value="batman")
])
async def set_mode(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    user_mode[interaction.user.id] = mode.value
    
    responses = {
        "normal": "Bet. I'm chill now 🦇",
        "freaky": "Ayo? Bet 😏",
        "angry": "Tf you want? 🤬",
        "batman": "I'm Batman. 🦇"
    }
    
    await interaction.response.send_message(responses[mode.value])

bot.run(DISCORD_TOKEN)
