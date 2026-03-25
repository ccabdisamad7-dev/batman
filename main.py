DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
import discord
from discord.ext import commands
from discord import app_commands
from bytez import Bytez
import asyncio
from collections import defaultdict
import json
import os
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import traceback

# Get tokens from environment
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
BYTEZ_KEY = os.environ.get('BYTEZ_KEY', "f4cc6d4dbf0c693ed79841d709bc5455")

if not DISCORD_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN not set!")
    print("Please add it in Railway: Dashboard → Variables")
    exit(1)

print("🦇 Batman Bot Starting...")

# Setup AI
try:
    sdk = Bytez(BYTEZ_KEY)
    model = sdk.model("Qwen/Qwen3-0.6B")
    print("✓ Bytez AI Model Loaded Successfully")
except Exception as e:
    print(f"❌ Failed to load AI: {e}")
    exit(1)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Memory system
class Memory:
    def __init__(self):
        self.convos = defaultdict(list)
        self.notes = defaultdict(dict)
        self.load()
    
    def save(self):
        try:
            data = {
                "convos": {str(k): v for k, v in self.convos.items()}, 
                "notes": {str(k): v for k, v in self.notes.items()}
            }
            with open("memory.json", "w") as f:
                json.dump(data, f)
            print(f"💾 Memory saved: {len(self.convos)} users")
        except Exception as e:
            print(f"Error saving memory: {e}")
    
    def load(self):
        if os.path.exists("memory.json"):
            try:
                with open("memory.json", "r") as f:
                    data = json.load(f)
                    self.convos = defaultdict(list, {int(k): v for k, v in data.get("convos", {}).items()})
                    self.notes = defaultdict(dict, {int(k): v for k, v in data.get("notes", {}).items()})
                print(f"✓ Memory loaded: {len(self.convos)} users")
            except Exception as e:
                print(f"Error loading memory: {e}")

memory = Memory()

# Modes
MODES = {
    "normal": {
        "prompt": "You're Batman but chill. Use TikTok/Gen Z slang naturally. Be cool and friendly. Keep responses short and conversational. You're approachable but still Batman.",
        "color": 0x3498db,
        "emoji": "😎"
    },
    "freaky": {
        "prompt": "You're Batman but flirty and seductive. Be charming, use pet names (cutie, babe, gorgeous), make them blush. Keep it Discord-safe. Be smooth and magnetic.",
        "color": 0x9b59b6,
        "emoji": "🔥"
    },
    "angry": {
        "prompt": "You're Batman and PISSED. Roast them brutally, judge everything they say, use funny harmless threats. Maximum sarcasm. Make them angry but laughing.",
        "color": 0xe74c3c,
        "emoji": "🤬"
    },
    "mysterious": {
        "prompt": "You're Batman - creature of night. Speak in riddles, metaphors, never direct answers. Be cryptic and philosophical. Drop wisdom that makes people think.",
        "color": 0x34495e,
        "emoji": "🌙"
    },
    "hilarious": {
        "prompt": "You're Batman but a comedian. Make jokes, puns, witty observations. Be genuinely funny. Dad jokes, clever comebacks, make people laugh.",
        "color": 0xf1c40f,
        "emoji": "😂"
    }
}

user_modes = defaultdict(lambda: "normal")

@bot.event
async def on_ready():
    print(f"\n{'='*50}")
    print(f"🦇 BATMAN AI BOT IS ONLINE! 🦇")
    print(f"{'='*50}")
    print(f"📡 Logged in as: {bot.user.name}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"🎭 Modes: Normal, Freaky, Angry, Mysterious, Hilarious")
    print(f"💾 Memory: {len(memory.convos)} users remembered")
    print(f"{'='*50}\n")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Gotham's streets | /mode"
        )
    )
    
    try:
        synced = await bot.tree.sync()
        print(f"✓ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"✗ Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    await bot.process_commands(message)
    
    # Check if bot should respond
    should_respond = False
    if isinstance(message.channel, discord.DMChannel):
        should_respond = True
    elif bot.user in message.mentions:
        should_respond = True
    elif message.reference and message.reference.resolved:
        if message.reference.resolved.author == bot.user:
            should_respond = True
    
    if should_respond:
        content = message.content
        if bot.user in message.mentions:
            content = content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        
        if not content:
            return
        
        async with message.channel.typing():
            try:
                mode = user_modes[message.author.id]
                prompt = MODES[mode]["prompt"]
                
                # Add user notes to context
                if message.author.id in memory.notes and memory.notes[message.author.id]:
                    notes_text = "\n\nRemembered info about this user:\n"
                    for key, value in memory.notes[message.author.id].items():
                        notes_text += f"- {key}: {value}\n"
                    prompt += notes_text
                
                # Build messages
                msgs = [{"role": "system", "content": prompt}]
                for m in memory.convos[message.author.id][-10:]:
                    msgs.append(m)
                msgs.append({"role": "user", "content": content})
                
                # Get AI response
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: model.run(msgs))
                
                if result.error:
                    reply = "🦇 Batcomputer is glitching. Try again in a moment!"
                else:
                    if isinstance(result.output, list) and result.output:
                        last = result.output[-1]
                        if isinstance(last, dict) and "content" in last:
                            reply = last["content"]
                        else:
                            reply = str(last)
                    elif isinstance(result.output, dict) and "content" in result.output:
                        reply = result.output["content"]
                    else:
                        reply = str(result.output)[:1900]
                
                # Clean up reply
                reply = reply.strip()[:1900]
                
                # Store memory
                memory.convos[message.author.id].append({"role": "user", "content": content})
                memory.convos[message.author.id].append({"role": "assistant", "content": reply})
                if len(memory.convos[message.author.id]) > 20:
                    memory.convos[message.author.id] = memory.convos[message.author.id][-20:]
                memory.save()
                
                await message.channel.send(reply)
                
            except Exception as e:
                print(f"Error: {e}")
                traceback.print_exc()
                await message.channel.send("🦇 Something went wrong! Try again in a moment.")

# Slash commands
@bot.tree.command(name="mode", description="Change Batman's personality")
@app_commands.choices(mode=[
    app_commands.Choice(name="😎 Normal - Chill with slang", value="normal"),
    app_commands.Choice(name="🔥 Freaky - Flirty and spicy", value="freaky"),
    app_commands.Choice(name="🤬 Angry - Savage roasts", value="angry"),
    app_commands.Choice(name="🌙 Mysterious - Riddles and wisdom", value="mysterious"),
    app_commands.Choice(name="😂 Hilarious - Comedy Batman", value="hilarious")
])
async def set_mode(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    user_modes[interaction.user.id] = mode.value
    
    mode_descriptions = {
        "normal": "I'll keep it chill and use modern slang. No cap, we vibing 🦇",
        "freaky": "Getting spicy now~ Ready to charm your socks off 😏",
        "angry": "You asked for it. I'm about to roast you into next week 🔥",
        "mysterious": "The shadows speak... listen closely to my riddles 🌙",
        "hilarious": "Time to be the funniest vigilante in Gotham 😂"
    }
    
    style = MODES[mode.value]
    embed = discord.Embed(
        title=f"{style['emoji']} {mode.name} Mode Activated!",
        description=mode_descriptions[mode.value],
        color=style['color']
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="status", description="Check your status with Batman")
async def status(interaction: discord.Interaction):
    mode = user_modes[interaction.user.id]
    style = MODES[mode]
    msgs = len(memory.convos[interaction.user.id]) // 2
    notes = len(memory.notes.get(interaction.user.id, {}))
    
    embed = discord.Embed(
        title=f"{style['emoji']} Batman Status",
        color=style['color']
    )
    embed.add_field(name="Current Mode", value=mode.upper(), inline=True)
    embed.add_field(name="Messages Remembered", value=f"{msgs} exchanges", inline=True)
    embed.add_field(name="Things I Know", value=f"{notes} facts", inline=True)
    embed.add_field(name="How to Use", value="• Mention @Batman\n• DM me\n• Reply to my messages", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="reset", description="Reset your conversation with Batman")
async def reset(interaction: discord.Interaction):
    memory.convos[interaction.user.id] = []
    memory.save()
    embed = discord.Embed(
        title="🦇 Memory Reset",
        description="Your conversation history has been wiped clean.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="remember", description="Make Batman remember something about you")
async def remember(interaction: discord.Interaction, key: str, value: str):
    memory.notes[interaction.user.id][key] = value
    memory.save()
    embed = discord.Embed(
        title="🦇 Memory Stored",
        description=f"I'll remember that your **{key}** is **{value}**",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="forget", description="Make Batman forget something")
async def forget(interaction: discord.Interaction, key: str):
    if key in memory.notes.get(interaction.user.id, {}):
        del memory.notes[interaction.user.id][key]
        memory.save()
        await interaction.response.send_message(f"🦇 I've forgotten your **{key}**")
    else:
        await interaction.response.send_message(f"I don't remember anything about **{key}**", ephemeral=True)

@bot.tree.command(name="help", description="Get help with Batman bot")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🦇 Batman AI Bot - Help Guide",
        description="Your personal AI-powered Batman for Discord!",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="🎭 **Modes**",
        value="• `/mode` - Change personality\n• **5 unique personalities!**",
        inline=False
    )
    
    embed.add_field(
        name="💾 **Memory**",
        value="• `/remember` - Teach me about you\n• `/forget` - Make me forget\n• `/reset` - Clear conversation\n• `/status` - Check what I remember",
        inline=False
    )
    
    embed.add_field(
        name="💬 **How to Chat**",
        value="• **Mention me**: @Batman hello\n• **DM me**: Send direct messages\n• **Reply to me**: Continue conversations",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# Keep alive for Railway
app = Flask('')

@app.route('/')
def home():
    uptime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""
    <html>
        <head><title>Batman AI Bot</title></head>
        <body style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; padding: 50px;">
            <h1>🦇 BATMAN AI BOT</h1>
            <h2>✅ Bot is ONLINE</h2>
            <p>Started: {uptime}</p>
            <p>Users: {len(memory.convos)}</p>
        </body>
    </html>
    """

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run, daemon=True).start()
print("✓ Web server started on port 8080")

# Run bot
if __name__ == "__main__":
    print("🦇 Starting Batman Bot...")
    bot.run(DISCORD_TOKEN)
