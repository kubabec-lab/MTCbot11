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
        print("✅ MTC Systém kompletní a synchronizován.")

bot = MyBot()

# --- VERIFIKAČNÍ SYSTÉM (Tlačítko) ---
class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Vstoupit do armády", style=discord.ButtonStyle.green, custom_id="mtc_verify_v5")
    async def assign_rank(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_private = interaction.guild.get_role(RANKS[0]['id'])
        if role_private in interaction.user.roles:
            return await interaction.response.send_message("⚠️ Už jsi v armádě!", ephemeral=True)
        
        await interaction.user.add_roles(role_private)
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (interaction.user.id,))
        db.commit()
        await interaction.response.send_message(f"✅ Vítej v MTC, vojáku! Byla ti udělena hodnost Private.", ephemeral=True)

# --- POMOCNÉ FUNKCE ---
def add_xp(user_id, amount):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (amount, user_id))
    db.commit()
    cursor.execute("SELECT xp FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()[0]

async def check_rank_up(member, current_xp):
    for rank in reversed(RANKS):
        if current_xp >= rank['xp']:
            role = member.guild.get_role(rank['id'])
            if not role or role in member.roles: break
            
            if len(role.members) < rank['limit']:
                await member.add_roles(role)
                channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
                if channel:
                    await channel.send(f"🎖️ **POVÝŠENÍ!** {member.mention} získal hodnost **{rank['name']}**!")
                break

# --- SLASH PŘÍKAZY ---

@bot.tree.command(name="profile", description="Zobrazí tvůj profil")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    cursor.execute("SELECT xp, warns FROM users WHERE user_id = ?", (target.id,))
    data = cursor.fetchone()
    xp = data[0] if data else 0
    warns = data[1] if data else 0
    
    embed = discord.Embed(title=f"🪖 Profil: {target.display_name}", color=discord.Color.dark_green())
    embed.add_field(name="XP", value=f"⭐ {xp}", inline=True)
    embed.add_field(name="Warny", value=f"⚠️ {warns}", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="warn", description="Udělit varování")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, member: discord.Member, duvod: str):
    cursor.execute("UPDATE users SET warns = warns + 1 WHERE user_id = ?", (member.id,))
    db.commit()
    
    warn_channel = bot.get_channel(WARN_CHANNEL_ID)
    embed = discord.Embed(title="⚠️ DISCIPLINÁRNÍ TREST", color=discord.Color.red())
    embed.add_field(name="Voják", value=member.mention, inline=True)
    embed.add_field(name="Důvod", value=duvod, inline=True)
    embed.set_footer(text=f"Udělil: {interaction.user.display_name}")
    
    if warn_channel: await warn_channel.send(embed=embed)
    await interaction.response.send_message(f"✅ Varování pro {member.mention} uloženo.", ephemeral=True)

@bot.tree.command(name="meeting", description="Svolat nástup")
@app_commands.checks.has_permissions(administrator=True)
async def meeting(interaction: discord.Interaction, cas: str):
    await interaction.response.send_message(f"📢 **@everyone POZOR!** Nástup v **{cas}**!", allowed_mentions=discord.AllowedMentions(everyone=True))

@bot.tree.command(name="setup_nabor", description="Vytvořit náborový panel")
@app_commands.checks.has_permissions(administrator=True)
async def setup_nabor(interaction: discord.Interaction):
    embed = discord.Embed(title="Nábor do MTC", description="Klikni na tlačítko pro vstup!", color=discord.Color.green())
    await interaction.channel.send(embed=embed, view=RoleView())
    await interaction.response.send_message("Panel odeslán.", ephemeral=True)

@bot.tree.command(name="positions", description="Obsazenost hodností")
async def positions(interaction: discord.Interaction):
    embed = discord.Embed(title="📊 Obsazenost pozic", color=discord.Color.blue())
    for rank in RANKS[1:]:
        role = interaction.guild.get_role(rank['id'])
        count = len(role.members) if role else 0
        embed.add_field(name=rank['name'], value=f"`{count}/{rank['limit']}`", inline=True)
    await interaction.response.send_message(embed=embed)

# --- UDÁLOSTI ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    new_xp = add_xp(message.author.id, random.randint(1, 3))
    if new_xp % 10 == 0: await check_rank_up(message.author, new_xp)
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel: await channel.send(f"🎖️ Nováček {member.mention} dorazil na základnu!")

bot.run(TOKEN)
