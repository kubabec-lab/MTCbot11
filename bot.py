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

# --- TABULKA HODNOSTÍ (ID zůstávají stejná) ---
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

bot = MyBot()

# --- VERIFIKAČNÍ SYSTÉM ---
class RoleView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Vstoupit do armády", style=discord.ButtonStyle.green, custom_id="mtc_verify_v8")
    async def assign_rank(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_private = interaction.guild.get_role(RANKS[0]['id'])
        if role_private in interaction.user.roles: return await interaction.response.send_message("⚠️ Už jsi v armádě!", ephemeral=True)
        await interaction.user.add_roles(role_private)
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (interaction.user.id,))
        db.commit()
        await interaction.response.send_message(f"✅ Vítej v MTC!", ephemeral=True)

# --- TAKTICKÝ MOZEK A VÝPOČTY ---
def calculate_artillery(message_text):
    # Hledáme čísla v textu (např. "posun o 20 metrů na 1000 metrů")
    numbers = re.findall(r'\d+', message_text)
    if len(numbers) >= 2:
        offset = float(numbers[0])   # Kolik metrů mimo (např. 20)
        distance = float(numbers[1]) # Vzdálenost k cíli (např. 1000)
        
        if distance > 0:
            # Výpočet úhlu v radiánech: tan(alpha) = protilehlá / přilehlá
            radians = math.atan(offset / distance)
            degrees = math.degrees(radians)
            # Často se v armádě používají miliradiány (mrad)
            mrad = radians * 1000
            
            return (f"🎯 **BALISTICKÝ VÝPOČET:**\n"
                    f"Pro korekci o **{offset}m** na vzdálenost **{distance}m**:\n"
                    f"🔹 Posunout dělo o: **{degrees:.2f}°**\n"
                    f"🔹 Korekce v miliradiánech: **{mrad:.1f} mrad**")
    return None

def get_tactical_advice(content):
    content = content.lower()
    if "cqb" in content or "budov" in content:
        return "🏠 **TACTICAL ADVICE (CQB):** Vždy pracujte ve dvojicích. První (Pointman) čistí rohy, druhý kryje záda. Než vstoupíte, použijte flashbang. Pamatujte: 'Slow is smooth, smooth is fast'."
    if "formace" in content or "formation" in content:
        return "🛡️ **TACTICAL ADVICE (FORMACE):** \n- **Line:** Max palebná síla dopředu.\n- **Column:** Rychlý přesun, slabé boky.\n- **Vee:** Dobrá ochrana boků a silný úder."
    if "recon" in content or "pruzkum" in content:
        return "🔭 **TACTICAL ADVICE (RECON):** Buď neviditelný. Používej vyvýšený terén, nekřižuj otevřená pole. Tvým úkolem je hlásit pozice, ne vyvolat přestřelku."
    if "artylerie" in content or "delo" in content:
        return "💥 **DĚLOSTŘELECTVO:** Pro přesný výpočet mi napiš: 'posun [metry] na vzdálenost [metry]'. Vždy počítej s větrem a nadmořskou výškou!"
    return None

# --- ON MESSAGE (LOGIKA AI A XP) ---
@bot.event
async def on_message(message):
    if message.author.bot: return

    # REAKCE NA TAKTIKU NEBO VÝPOČET
    if bot.user.mentioned_in(message):
        async with message.channel.typing():
            # 1. Zkusíme dělostřelecký výpočet
            art_calc = calculate_artillery(message.content)
            # 2. Zkusíme taktickou radu
            tac_advice = get_tactical_advice(message.content)
            
            if art_calc:
                await message.reply(art_calc)
            elif tac_advice:
                await message.reply(tac_advice)
            else:
                await message.reply("Zdravím, vojáku! Pokud chceš taktickou radu (CQB, formace, recon) nebo balistický výpočet, zeptej se mě přímo. 🫡")

    # XP SYSTÉM (zůstává stejný)
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.author.id,))
    cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (random.randint(1, 3), message.author.id))
    db.commit()
    await bot.process_commands(message)

# --- SLASH COMMANDS (Profile, Warn, Meeting...) ---
@bot.tree.command(name="profile", description="Vojenská karta")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    cursor.execute("SELECT xp, warns FROM users WHERE user_id = ?", (target.id,))
    data = cursor.fetchone()
    xp, warns = (data[0], data[1]) if data else (0, 0)
    
    current_rank = "Rekrut"
    for rank in RANKS:
        role = target.guild.get_role(rank['id'])
        if role and role in target.roles: current_rank = rank['name']

    embed = discord.Embed(title=f"🪖 Profil: {target.display_name}", color=discord.Color.dark_green())
    embed.add_field(name="Hodnost", value=f"🎖️ {current_rank}", inline=False)
    embed.add_field(name="Zkušenosti", value=f"⭐ {xp} XP", inline=True)
    embed.add_field(name="Warny", value=f"⚠️ {warns}", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="warn")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, member: discord.Member, duvod: str):
    cursor.execute("UPDATE users SET warns = warns + 1 WHERE user_id = ?", (member.id,))
    db.commit()
    channel = bot.get_channel(WARN_CHANNEL_ID)
    if channel: await channel.send(embed=discord.Embed(title="⚠️ WARN", description=f"{member.mention} - {duvod}", color=discord.Color.red()))
    await interaction.response.send_message("✅ Warn uložen.", ephemeral=True)

@bot.tree.command(name="meeting")
@app_commands.checks.has_permissions(administrator=True)
async def meeting(interaction: discord.Interaction, cas: str):
    await interaction.response.send_message(f"📢 **@everyone POZOR!** Nástup v **{cas}**!", allowed_mentions=discord.AllowedMentions(everyone=True))

@bot.tree.command(name="setup_nabor")
@app_commands.checks.has_permissions(administrator=True)
async def setup_nabor(interaction: discord.Interaction):
    await interaction.channel.send(embed=discord.Embed(title="Nábor MTC", description="Klikni pro vstup!", color=discord.Color.green()), view=RoleView())
    await interaction.response.send_message("Panel vytvořen.", ephemeral=True)

@bot.event
async def on_ready(): print(f'--- {bot.user.name} READY ---')

bot.run(TOKEN)
