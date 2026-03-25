import discord
from discord.ext import commands
from discord import app_commands
from bytez import Bytez
import asyncio
import os
from collections import defaultdict

DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
BYTEZ_KEY = "MBOq/sU88vSQ/QdoMfEP6yMN26LV1BZbK8uPxyY25eFKV5MdCfifpcwqvzISF6WQZ0dEzX4j+oX6hkepIU4hNogmNRptE41oj06xKP4WB4gdYMxORsCfXD5sMAkzBXPer2Oz7y4="

sdk = Bytez(BYTEZ_KEY)
model = sdk.model("openai/gpt-oss-120b")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

memory = defaultdict(list)
modes = {
    "normal": "You're Batman. Chill, use slang. Short answers. Max 2 sentences.",
    "freaky": "You're Batman. Flirty and smooth. Short answers. Max 2 sentences.",
    "angry": "You're Batman. Roast them. Short answers. Max 2 sentences.",
    "batman": "You're Batman. Dark and serious. Short answers. Max 2 sentences."
}
user_mode = {}

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online")
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
            try:
                uid = message.author.id
                mode = user_mode.get(uid, "normal")
                
                msgs = [{"role": "system", "content": modes[mode]}]
                msgs.extend(memory[uid][-6:])
                msgs.append({"role": "user", "content": content})
                
                result = await asyncio.get_event_loop().run_in_executor(None, lambda: model.run(msgs))
                
                if result.error:
                    await message.channel.send("API error. Try again.")
                elif result.output:
                    if isinstance(result.output, list) and len(result.output) > 0:
                        reply = result.output[-1].get("content", str(result.output[-1]))
                    else:
                        reply = str(result.output)
                    reply = reply[:1900]
                    
                    memory[uid].append({"role": "user", "content": content})
                    memory[uid].append({"role": "assistant", "content": reply})
                    if len(memory[uid]) > 12:
                        memory[uid] = memory[uid][-12:]
                    
                    await message.channel.send(reply)
            except Exception as e:
                print(e)
                await message.channel.send("Error. Try again.")

@bot.tree.command(name="mode", description="Change personality")
@app_commands.choices(mode=[
    app_commands.Choice(name="Normal", value="normal"),
    app_commands.Choice(name="Freaky", value="freaky"),
    app_commands.Choice(name="Angry", value="angry"),
    app_commands.Choice(name="Batman", value="batman")
])
async def set_mode(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    user_mode[interaction.user.id] = mode.value
    await interaction.response.send_message(f"Mode: {mode.name}")

bot.run(DISCORD_TOKEN)
