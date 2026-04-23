import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime
import random
import os

# --- KONFIGURACE (ID vložená přímo) ---
TOKEN = os.getenv('TOKEN')
WELCOME_CHANNEL_ID = 1466784809316782110
WARN_CHANNEL_ID = 1483168781080592474
ROLE_PRIVATE_ID = 1467194169423433738
ROLE_DEPUTY_ID = 1466792881800085555

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Tlačítko bude fungovat i po restartu
        self.add_view(RoleView())
        # Synchronizace Slash příkazů (může trvat chvíli, než se objeví v Discordu)
        await self.tree.sync()
        print("✅ Slash commandy synchronizovány.")

bot = MyBot()

# --- VERIFIKAČNÍ SYSTÉM (Tlačítko na role) ---
class RoleView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Vstoupit do armády", style=discord.ButtonStyle.green, custom_id="mtc_verify_v2")
    async def assign_rank(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_private = interaction.guild.get_role(ROLE_PRIVATE_ID)
        role_deputy = interaction.guild.get_role(ROLE_DEPUTY_ID)

        if not role_private:
            return await interaction.response.send_message("❌ Chyba: Role 'Private' nebyla nalezena (ID je špatně).", ephemeral=True)

        # Kontrola, zda uživatel už roli nemá
        if role_private in interaction.user.roles:
            return await interaction.response.send_message("⚠️ Už jsi členem armády!", ephemeral=True)

        roles_to_add = [role_private]
        msg = f"✅ Vítej v MTC! Byla ti udělena hodnost **{role_private.name}**."

        # Šance 20 % na Deputy Corporal
        if random.random() < 0.20 and role_deputy:
            roles_to_add.append(role_deputy)
            msg += f"\n🎖️ Navíc jsi byl za zásluhy jmenován **{role_deputy.name}**!"

        try:
            await interaction.user.add_roles(*roles_to_add)
            await interaction.response.send_message(msg, ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Nemám práva na přidávání rolí! Přesuň roli bota v nastavení serveru úplně nahoru.", ephemeral=True)

# --- UDÁLOSTI ---
@bot.event
async def on_ready():
    print(f'--- {bot.user.name} je ONLINE a připraven ---')

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Nový voják na základně!",
            description=f"🎖️ Pozor! {member.mention} dorazil k jednotce MTC. Vítej!",
            color=discord.Color.blue()
        )
        await channel.send(embed=embed)

# --- SLASH PŘÍKAZY (Menu pod /) ---

@bot.tree.command(name="setup_nabor", description="Vytvoří náborovou zprávu s tlačítkem")
@app_commands.checks.has_permissions(administrator=True)
async def setup_nabor(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Nábor do Military Teamu",
        description="Kliknutím na tlačítko níže podepíšeš svůj kontrakt a vstoupíš do MTC.\n\n"
                    "🔹 Získáš základní vybavení a hodnost.\n"
                    "🔹 Špičkoví rekruti mohou být povýšeni rovnou po vstupu.",
        color=discord.Color.dark_green()
    )
    await interaction.response.send_message("Generuji náborový panel...", ephemeral=True)
    await interaction.channel.send(embed=embed, view=RoleView())

@bot.tree.command(name="warn", description="Udělá varování členovi")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, member: discord.Member, duvod: str):
    warn_channel = bot.get_channel(WARN_CHANNEL_ID)
    if not warn_channel:
        return await interaction.response.send_message("❌ Kanál pro varování nebyl nalezen!", ephemeral=True)

    embed = discord.Embed(title="⚠️ DISCIPLINÁRNÍ TREST", color=discord.Color.red())
    embed.add_field(name="Potrestaný:", value=member.mention, inline=False)
    embed.add_field(name="Důvod:", value=duvod, inline=False)
    embed.add_field(name="Udělil:", value=interaction.user.mention, inline=False)
    embed.set_timestamp()
    embed.set_footer(text="MTC Vojenská Policie")
    
    await warn_channel.send(embed=embed)
    await interaction.response.send_message(f"✅ Varování pro {member.mention} bylo zaznamenáno.", ephemeral=True)

@bot.tree.command(name="meeting", description="Svolá nástup všech jednotek")
@app_commands.checks.has_permissions(administrator=True)
async def meeting(interaction: discord.Interaction, cas: str):
    # Příkaz odpoví a zároveň pošle zprávu s @everyone
    await interaction.response.send_message(f"📢 **@everyone POZOR!** Nástup v **{cas}**! Všichni na značky!", allowed_mentions=discord.AllowedMentions(everyone=True))

# --- SPUŠTĚNÍ ---
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ CHYBA: Chybí TOKEN v Railway Variables!")
