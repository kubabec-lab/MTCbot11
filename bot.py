import discord
from discord import app_commands
from discord.ext import commands
import os
import sqlite3
import random
import math
import re

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
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, xp INTEGER DEFAULT 0, warns INTEGER DEFAULT 0)')
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
        print("✅ MILITARYBOT: Všechny systémy online.")

bot = MyBot()

# --- VERIFIKAČNÍ SYSTÉM (TLAČÍTKO) ---
class RoleView(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Vstoupit do armády", style=discord.ButtonStyle.green, custom_id="mtc_verify_v9")
    async def assign_rank(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_private = interaction.guild.get_role(RANKS[0]['id'])
        if role_private in interaction.user.roles: 
            return await interaction.response.send_message("⚠️ Už jsi v armádě!", ephemeral=True)
        
        await interaction.user.add_roles(role_private)
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (interaction.user.id,))
        db.commit()
        await interaction.response.send_message(f"✅ Vítej v MTC! Hodnost Private ti byla udělena.", ephemeral=True)

# --- TAKTICKÝ MOZEK ---
def calculate_artillery(message_text):
    numbers = re.findall(r'\d+', message_text)
    if len(numbers) >= 2:
        offset = float(numbers[0])
        distance = float(numbers[1])
        if distance > 0:
            radians = math.atan(offset / distance)
            degrees = math.degrees(radians)
            mrad = radians * 1000
            return (f"🎯 **MILITARYBOT BALISTICKÁ JEDNOTKA:**\n"
                    f"Korekce: **{offset}m** | Vzdálenost: **{distance}m**\n"
                    f"🔹 Úhel: **{degrees:.2f}°**\n"
                    f"🔹 Miliradiány: **{mrad:.1f} mrad**")
    return None

def get_tactical_advice(content):
    content = content.lower()
    if "cqb" in content:
        return "🏠 **TAKTIKA CQB:** Čistěte místnosti metodou 'Slicing the pie'. Pointman nikdy nezastavuje ve dveřích (Fatal Funnel)!"
    if "formace" in content:
        return "🛡️ **FORMACE:** Line pro útok, Column pro pochod, Diamond pro ochranu VIP/velitele."
    if "pruzkum" in content or "recon" in content:
        return "🔭 **PRŮZKUM:** Pozoruj, podej hlášení (SALUTE report), ale nepouštěj se do boje, pokud to není nezbytné."
    return None

# --- UDÁLOSTI ---
@bot.event
async def on_message(message):
    if message.author.bot: return

    # REAKCE NA MILITARYBOTA (Taktika a Výpočty)
    if bot.user.mentioned_in(message):
        async with message.channel.typing():
            art_calc = calculate_artillery(message.content)
            tac_advice = get_tactical_advice(message.content)
            
            if art_calc:
                await message.reply(art_calc)
            elif tac_advice:
                await message.reply(tac_advice)
            else:
                await message.reply("Vojáku, jsem připraven k výpočtům nebo taktické radě. Co potřebuješ? 🫡")

    # XP SYSTÉM
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.author.id,))
    cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (random.randint(1, 3), message.author.id))
    db.commit()
    await bot.process_commands(message)

# --- SLASH PŘÍKAZY ---

@bot.tree.command(name="profile", description="Tvoje vojenská karta")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    cursor.execute("SELECT xp, warns FROM users WHERE user_id = ?", (target.id,))
    data = cursor.fetchone()
    xp, warns = (data[0], data[1]) if data else (0, 0)
    
    current_rank = "Rekrut"
    for rank in RANKS:
        role = target.guild.get_role(rank['id'])
        if role and role in target.roles: current_rank = rank['name']

    embed = discord.Embed(title=f"🪖 Karta: {target.display_name}", color=discord.Color.dark_green())
    embed.add_field(name="Hodnost", value=f"🎖️ {current_rank}", inline=False)
    embed.add_field(name="Zkušenosti", value=f"⭐ {xp} XP", inline=True)
    embed.add_field(name="Warny", value=f"⚠️ {warns}", inline=True)
    embed.set_footer(text="Generováno systémem MILITARYBOT")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="warn", description="Udělit warn")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, member: discord.Member, duvod: str):
    cursor.execute("UPDATE users SET warns = warns + 1 WHERE user_id = ?", (member.id,))
    db.commit()
    channel = bot.get_channel(WARN_CHANNEL_ID)
    if channel: 
        await channel.send(embed=discord.Embed(title="⚠️ DISCIPLINÁRNÍ LOG", description=f"Voják: {member.mention}\nDůvod: {duvod}", color=discord.Color.red()))
    await interaction.response.send_message(f"✅ Warn pro {member.display_name} uložen.", ephemeral=True)

@bot.tree.command(name="setup_nabor", description="Vytvoří náborový panel")
@app_commands.checks.has_permissions(administrator=True)
async def setup_nabor(interaction: discord.Interaction):
    embed = discord.Embed(title="Nábor MTC", description="Vstupte do řad MTC kliknutím níže!", color=discord.Color.green())
    await interaction.channel.send(embed=embed, view=RoleView())
    await interaction.response.send_message("Panel nasazen.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'--- {bot.user.name} (MILITARYBOT) připraven k akci ---')

bot.run(TOKEN)
