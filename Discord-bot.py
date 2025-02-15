import nextcord
from nextcord.ext import commands
import os
import random
from keep_alive import keep_alive  # Webserver für 24/7 Hosting

intents = nextcord.Intents.default()
intents.members = True

bot = commands.Bot(intents=intents)

auto_role = None  
BEWERBUNGS_KANAL_ID = 1329941203705397299  # Bewerbungskanal-ID
MOD_ROLE_ID = 1333712189651025930  # ❗ Mod-Rolle anpassen!

# -----------------------------
# Fun Commands
# -----------------------------
@bot.slash_command(description="Wirft einen Würfel (1-6)")
async def dice(interaction: nextcord.Interaction):
    number = random.randint(1, 6)
    await interaction.response.send_message(f"🎲 Du hast eine **{number}** geworfen!")

@bot.slash_command(description="Zeigt die aktuelle Ping-Zeit des Bots")
async def ping(interaction: nextcord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Ping: **{latency}ms**")

@bot.slash_command(description="Zeigt Informationen über den Server")
async def serverinfo(interaction: nextcord.Interaction):
    guild = interaction.guild
    embed = nextcord.Embed(title=guild.name, color=0x00ff00)
    embed.add_field(name="👥 Mitglieder", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Erstellt am", value=guild.created_at.strftime("%d.%m.%Y"), inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await interaction.response.send_message(embed=embed)

# -----------------------------
# Moderation Commands
# -----------------------------
@bot.slash_command(description="Bannt ein Mitglied")
@commands.has_permissions(ban_members=True)
async def ban(interaction: nextcord.Interaction, member: nextcord.Member, reason: str = "Kein Grund angegeben"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"{member.mention} wurde gebannt. Grund: {reason}")

@bot.slash_command(description="Kickt ein Mitglied")
@commands.has_permissions(kick_members=True)
async def kick(interaction: nextcord.Interaction, member: nextcord.Member, reason: str = "Kein Grund angegeben"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"{member.mention} wurde gekickt. Grund: {reason}")

# -----------------------------
# Bewerbungssystem mit Annahme/Ablehnung
# -----------------------------
class BewerbungView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="Jetzt bewerben!", style=nextcord.ButtonStyle.green)
    async def bewerbung_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message("📩 Ich habe dir eine private Nachricht mit den Fragen gesendet!", ephemeral=True)

        try:
            user = interaction.user
            questions = [
                "Wie heißt du auf Twitch?",
                "Stell dich einmal vor (Name, Alter, Hobbys)?",
                "Was hat dich motiviert, dich als Mod zu bewerben?",
                "Auf welchem Gerät würdest du den Stream moderieren?",
                "Hast du bereits Erfahrung als Twitch Mod, wenn ja, wo?",
                "Was hebt dich von anderen Bewerbern ab?",
                "Wie erstellst du einen Command mit Nightbot mit Userping?",
                "Was würdest du machen, wenn ein Zuschauer wilde Sachen spammt?"
            ]

            answers = []
            await user.send("📝 **Bewerbung für Twitch-Mod**\nBitte beantworte die folgenden Fragen:")

            for question in questions:
                await user.send(question)
                response = await bot.wait_for("message", check=lambda m: m.author == user and isinstance(m.channel, nextcord.DMChannel))
                answers.append(f"**{question}**\n{response.content}")

            guild = interaction.guild
            bewerbungskanal = guild.get_channel(BEWERBUNGS_KANAL_ID)

            if bewerbungskanal:
                thread = await bewerbungskanal.create_thread(name=f"Bewerbung-{user.name}", type=nextcord.ChannelType.public_thread)

                embed = nextcord.Embed(
                    title=f"📄 Bewerbung von {user.name}",
                    color=0x3498db
                )
                for answer in answers:
                    embed.add_field(name="‎", value=answer, inline=False)

                await thread.send(embed=embed, view=AnnahmeView(user.id))
                await user.send("✅ Deine Bewerbung wurde erfolgreich eingereicht!")
            else:
                await user.send("❌ Fehler: Bewerbungs-Channel nicht gefunden!")

        except Exception as e:
            await interaction.user.send(f"❌ Es gab einen Fehler: {e}")

class AnnahmeView(nextcord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id  # Speichert die ID des Bewerbers

    @nextcord.ui.button(label="✅ Annehmen", style=nextcord.ButtonStyle.green)
    async def accept_application(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        guild = interaction.guild
        user = guild.get_member(self.user_id)

        if user:
            mod_role = guild.get_role(MOD_ROLE_ID)
            if mod_role:
                await user.add_roles(mod_role)
                await interaction.response.send_message(f"✅ {user.mention} wurde als Moderator angenommen!", ephemeral=True)
                await user.send("🎉 Glückwunsch! Du wurdest als **Twitch-Mod** angenommen!")
            else:
                await interaction.response.send_message("❌ Fehler: Mod-Rolle nicht gefunden!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Fehler: Bewerber nicht gefunden!", ephemeral=True)

    @nextcord.ui.button(label="❌ Ablehnen", style=nextcord.ButtonStyle.red)
    async def reject_application(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        user = interaction.guild.get_member(self.user_id)

        if user:
            await interaction.response.send_message(f"❌ {user.mention} wurde abgelehnt.", ephemeral=True)
            await user.send("📢 Deine Bewerbung als **Twitch-Mod** wurde leider abgelehnt.")
        else:
            await interaction.response.send_message("❌ Fehler: Bewerber nicht gefunden!", ephemeral=True)

# -----------------------------
# Befehl zum Senden der Bewerbungsnachricht
# -----------------------------
@bot.slash_command(description="Sendet eine Bewerbungsnachricht in den Bewerbungs-Channel (Admin)")
@commands.has_permissions(administrator=True)
async def bewerbung(interaction: nextcord.Interaction):
    embed = nextcord.Embed(
        title="🎉 Bewerbungen für Twitch-Mods!",
        description="Drücke auf den Button unten, um dich zu bewerben!",
        color=0x00ff00
    )
    await interaction.channel.send(embed=embed, view=BewerbungView())
    await interaction.response.send_message("✅ Nachricht gesendet!", ephemeral=True)

# -----------------------------
# Webserver für UptimeRobot
# -----------------------------
keep_alive()

# -----------------------------
# Bot starten
# -----------------------------
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("❌ Fehler: TOKEN nicht gefunden!")
    exit()

@bot.event
async def on_ready():
    print(f"✅ Bot ist eingeloggt als {bot.user}")

bot.run(TOKEN)
