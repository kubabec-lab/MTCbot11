import discord
from discord import app_commands
from discord.ext import commands
import os
import sqlite3
import random
from datetime import datetime

# --- KONFIGURACE ---
TOKEN = os.getenv('TOKEN')
WELCOME_CHANNEL_ID = 1466784809316782110
WARN_CHANNEL_ID = 1483168781080592474

# --- TABULKA HODNOSTÍ S LIMITAMY ---
RANKS = [
    {"name": "Private", "id": 1467194169423433738, "xp": 0, "limit": 999},
    {"name": "Deputy Corporal", "id": 1466792881800085555, "xp": 100, "limit": 10},
    {"name": "Corporal", "id": 1466792838527193243, "xp": 200, "limit": 7},
    {"name": "⭐Deputy Sergeant", "id": 1466792645014720602, "xp": 300, "limit": 4},
    {"name": "⭐Sergeant⭐", "id": 1466792531734958080, "xp": 400, "limit": 1},
    {"name": "⭐⭐Deputy commander⭐⭐", "id": 1466791815943557180, "xp": 500, "limit": 2},
    {"name": "⭐⭐Commander⭐⭐", "id": 1466791510451421244, "xp": 600, "limit": 2},
    {"name": "⭐⭐⭐ Deputy General⭐⭐⭐", "id": 1466788653203460146, "xp": 700, "limit": 1}
]

# --- DATABÁZE ---
db = sqlite3.connect('military_data.db')
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, xp INTEGER DEFAULT 0, warns INTEGER DEFAULT 0)''')
db.commit()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(RoleView())
        await self.tree.sync()
        print("✅ MTC Systém s limity pozic aktivován.")

bot = MyBot()

# --- VERIFIKAČNÍ SYSTÉM ---
class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Vstoupit do armády", style=discord.ButtonStyle.green, custom_id="mtc_verify_v4")
    async def assign_rank(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_private = interaction.guild.get_role(RANKS[0]['id'])
        if role_private in interaction.user.roles:
            return await interaction.response.send_message("⚠️ Už jsi v armádě!", ephemeral=True)
        
        await interaction.user.add_roles(role_private)
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (interaction.user.id,))
        db.commit()
        await interaction.response.send_message(f"✅ Vítej v MTC, vojáku!", ephemeral=True)

# --- XP A POVÝŠENÍ S KONTROLOU KAPACITY ---
async def check_rank_up(member, current_xp):
    # Procházíme od nejvyšší hodnosti
    for rank in reversed(RANKS):
        if current_xp >= rank['xp']:
            role = member.guild.get_role(rank['id'])
            if not role: continue
            
            # Pokud už roli má, končíme (má nejvyšší možnou)
            if role in member.roles:
                break
                
            # Kontrola kapacity (kolik lidí už má tuto roli)
            current_occupancy = len(role.members)
            
            if current_occupancy < rank['limit']:
                # Máme volné místo!
                await member.add_roles(role)
                channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
                if channel:
                    await channel.send(f"🎖️ **POVÝŠENÍ!** {member.mention} obsadil volnou pozici **{rank['name']}**!")
                break # Povýšen, končíme
            else:
                # Místo je plné, zkusíme nižší hodnost v dalším kole cyklu
                continue

# --- SLASH PŘÍKAZY ---

@bot.tree.command(name="positions", description="Zobrazí obsazenost hodností")
async def positions(interaction: discord.Interaction):
    embed = discord.Embed(title="📊 Obsazenost armádních pozic", color=discord.Color.blue())
    for rank in RANKS[1:]: # Přeskočíme Private
        role = interaction.guild.get_role(rank['id'])
        count = len(role.members) if role else 0
        status = "🔴 PLNO" if count >= rank['limit'] else "🟢 VOLNO"
        embed.add_field(
            name=rank['name'], 
            value=f"Obsazeno: `{count}/{rank['limit']}` | Stav: {status}", 
            inline=False
        )
    await interaction.response.send_message(embed=embed)

# --- ZBYTEK KÓDU (on_message, promote, atd.) ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.author.id,))
    cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (random.randint(1, 3), message.author.id))
    db.commit()
    cursor.execute("SELECT xp FROM users WHERE user_id = ?", (message.author.id,))
    new_xp = cursor.fetchone()[0]
    if new_xp % 20 == 0: await check_rank_up(message.author, new_xp)
    await bot.process_commands(message)

@bot.tree.command(name="profile")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    cursor.execute("SELECT xp FROM users WHERE user_id = ?", (target.id,))
    data = cursor.fetchone()
    xp = data[0] if data else 0
    await interaction.response.send_message(f"🪖 **{target.display_name}** má `{xp}` XP.")

bot.run(TOKEN)
