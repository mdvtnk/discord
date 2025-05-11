import discord
import random
import os
import aiohttp
import requests
import asyncio
import json
from discord import app_commands
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from flask import Flask
import threading
from os import getenv
from discord import ChannelType

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

# Создаём бота
bot = commands.Bot(command_prefix="!", intents=intents)

# Flask для Replit
app = Flask(__name__)


@app.route('/')
def home():
    return "Бот работает!"


def run_flask():
    app.run(host='0.0.0.0', port=8080)


threading.Thread(target=run_flask).start()

# Список всех агентов Valorant
AGENTS = [
    "Clove", "Iso", "Deadlock", "Gekko", "Harbor", "Fade", "Neon", "Chamber",
    "KAY/O", "Astra", "Yoru", "Skye", "Breach", "Raze", "Reyna", "Jett",
    "Phoenix", "Sage", "Sova", "Cypher", "Killjoy", "Omen", "Viper",
    "Brimstone"
]

SFW_CATEGORIES = ["waifu", "neko", "shinobu", "megumin"]
NSFW_CATEGORIES = ["waifu", "neko", "blowjob"]

# Глобальные переменные
welcome_channel_id = None
clown_role_id = None
voice_creator_channel_id = None


# Функции для работы с настройками
def load_settings():
    global welcome_channel_id, clown_role_id
    try:
        with open("settings.json", "r") as f:
            data = json.load(f)
            welcome_channel_id = data.get("welcome_channel_id")
            clown_role_id = data.get("clown_role_id")
    except FileNotFoundError:
        pass  # Если файла нет, оставляем None


def save_settings():
    data = {
        "welcome_channel_id": welcome_channel_id,
        "clown_role_id": clown_role_id
    }
    with open("settings.json", "w") as f:
        json.dump(data, f)


# Загружаем настройки при запуске
load_settings()


# Событие: бот запущен
@bot.event
async def on_ready():
    print(f"Бот {bot.user} запущен!")
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано {len(synced)} команд.")
    except Exception as e:
        print(f"Ошибка синхронизации команд: {e}")


# Обработчик события "участник зашел на сервер"
@bot.event
async def on_member_join(member: discord.Member):
    if welcome_channel_id is None:
        return

    channel = member.guild.get_channel(welcome_channel_id)
    if not channel:
        return

    welcome_image = create_welcome_image(member)
    with BytesIO() as image_binary:
        welcome_image.save(image_binary, "PNG")
        image_binary.seek(0)
        await channel.send(
            file=discord.File(fp=image_binary, filename="welcome.png"))


def create_welcome_image(member: discord.Member) -> Image:
    """Создает приветственное изображение для нового участника"""
    bg_path = "welcome_bg.png"
    if not os.path.exists(bg_path):
        img = Image.new("RGB", (800, 400), (30, 30, 30))
    else:
        img = Image.open(bg_path).resize((800, 400))

    draw = ImageDraw.Draw(img)

    avatar_asset = member.avatar.url if member.avatar else member.default_avatar.url
    avatar_bytes = BytesIO(requests.get(avatar_asset).content)
    avatar_image = Image.open(avatar_bytes).resize((150, 150)).convert("RGBA")

    mask = Image.new("L", (150, 150), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, 150, 150), fill=255)

    img.paste(avatar_image, (325, 100), mask)

    font_path = "arial.ttf"
    font = ImageFont.truetype(font_path, 40)
    small_font = ImageFont.truetype(font_path, 30)

    text = f"Добро пожаловать, {member.name}!"
    server_text = f"на сервер {member.guild.name}"
    draw.text((200, 270), text, (255, 255, 255), font=font)
    draw.text((250, 320), server_text, (200, 200, 200), font=small_font)

    return img


# Slash-команды
@bot.tree.command(name="welcome-set",
                  description="Устанавливает канал для приветствий")
@app_commands.describe(channel="Выберите канал")
async def welcome_set(interaction: discord.Interaction,
                      channel: discord.TextChannel):
    global welcome_channel_id
    welcome_channel_id = channel.id
    save_settings()
    await interaction.response.send_message(
        f"✅ Канал приветствий установлен: {channel.mention}")


@bot.tree.command(name="ping", description="Проверка ответа бота")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")


@bot.tree.command(name="say", description="Повторяет ваш текст")
@app_commands.describe(message="Введите текст, который скажет бот")
async def say(interaction: discord.Interaction, message: str):
    await interaction.response.send_message(message)


@bot.tree.command(name="roll",
                  description="Случайно выбирает одно из переданных слов")
@app_commands.describe(options="Введите несколько слов через пробел")
async def roll(interaction: discord.Interaction, options: str):
    choices = options.split()
    if not choices:
        await interaction.response.send_message(
            "⚠ Ошибка! Введите хотя бы одно слово.", ephemeral=True)
        return
    result = random.choice(choices)
    await interaction.response.send_message(f"🎲 Случайный выбор: **{result}**")


@bot.tree.command(
    name="randompickvalorant",
    description=
    "Случайно выбирает уникального агента Valorant для каждого имени")
@app_commands.describe(names="Введите до 5 имён через пробел")
async def randompickvalorant(interaction: discord.Interaction, names: str):
    player_names = names.split()
    if len(player_names) > 5:
        await interaction.response.send_message(
            "⚠ Можно указать максимум 5 имён!", ephemeral=True)
        return

    available_agents = AGENTS.copy()
    random.shuffle(available_agents)

    assigned_agents = {}
    for name in player_names:
        if available_agents:
            assigned_agents[name] = available_agents.pop(0)

    result = "\n".join(
        [f"**{name}** → {agent}" for name, agent in assigned_agents.items()])
    await interaction.response.send_message(
        f"🎲 **Случайный выбор агентов Valorant:**\n{result}")


@bot.tree.command(name="avatar", description="Показывает аватар пользователя")
@app_commands.describe(user="Выберите пользователя")
async def avatar(interaction: discord.Interaction, user: discord.Member):
    avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
    embed = discord.Embed(title=f"Аватар {user.display_name}",
                          color=discord.Color.blue())
    embed.set_image(url=avatar_url)
    embed.set_footer(text="Нажмите на изображение, чтобы скачать")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="anime",
                  description="Отправляет случайную аниме-картинку")
async def anime(interaction: discord.Interaction):
    category = random.choice(SFW_CATEGORIES)
    url = f"https://api.waifu.pics/sfw/{category}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                image_url = data["url"]
            else:
                await interaction.response.send_message(
                    "❌ Ошибка загрузки картинки.", ephemeral=True)
                return

    embed = discord.Embed(title=f"🎴 Случайное аниме ({category})",
                          color=discord.Color.purple())
    embed.set_image(url=image_url)
    embed.set_footer(text="Источник: waifu.pics")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="nsfw-anime",
    description="Отправляет NSFW аниме-картинку (только NSFW-каналы)")
async def nsfw_anime(interaction: discord.Interaction):
    if not interaction.channel.is_nsfw():
        await interaction.response.send_message(
            "❌ Эту команду можно использовать только в NSFW-каналах!",
            ephemeral=True)
        return

    category = random.choice(NSFW_CATEGORIES)
    url = f"https://api.waifu.pics/nsfw/{category}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                image_url = data["url"]
            else:
                await interaction.response.send_message(
                    "❌ Ошибка загрузки картинки.", ephemeral=True)
                return

    embed = discord.Embed(title=f"🔞 NSFW-аниме ({category})",
                          color=discord.Color.red())
    embed.set_image(url=image_url)
    embed.set_footer(text="Источник: waifu.pics")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="check-activity",
    description="Показывает активность всех участников сервера (кроме ботов)")
async def check_activity(interaction: discord.Interaction):
    guild = interaction.guild
    active_members = []

    for member in guild.members:
        if member.bot:
            continue

        if member.activities:
            for activity in member.activities:
                if isinstance(activity, discord.Game):
                    active_members.append(
                        f"🎮 **{member.display_name}** играет в **{activity.name}**"
                    )
                elif isinstance(activity, discord.Streaming):
                    active_members.append(
                        f"🔴 **{member.display_name}** стримит **{activity.game}** на [{activity.platform}]({activity.url})"
                    )
                elif isinstance(activity, discord.Spotify):
                    active_members.append(
                        f"🎵 **{member.display_name}** слушает **{activity.title}** от **{', '.join(activity.artists)}**"
                    )
                elif isinstance(activity, discord.Activity):
                    active_members.append(
                        f"🎭 **{member.display_name}** {activity.name}")

    if not active_members:
        await interaction.response.send_message(
            "🚫 Сейчас никто из людей не активен на сервере.", ephemeral=True)
        return

    embed = discord.Embed(title="📊 Активность участников",
                          color=discord.Color.blue())
    embed.description = "\n".join(active_members)
    embed.set_footer(text=f"Запрос от {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="clown_set_role",
                  description="Устанавливает роль для клоуна")
@app_commands.describe(role="Роль для клоуна")
async def clown_set_role(interaction: discord.Interaction, role: discord.Role):
    global clown_role_id
    clown_role_id = role.id
    save_settings()
    await interaction.response.send_message(
        f'Роль {role.name} установлена как клоунская!', ephemeral=True)


@bot.tree.command(name="clown",
                  description="Назначает клоунскую роль участнику")
@app_commands.describe(member="Участник, которому назначается роль")
async def clown(interaction: discord.Interaction, member: discord.Member):
    global clown_role_id
    if not clown_role_id:
        await interaction.response.send_message("Роль клоуна не установлена!",
                                                ephemeral=True)
        return

    role = interaction.guild.get_role(clown_role_id)
    if not role:
        await interaction.response.send_message("Роль не найдена!",
                                                ephemeral=True)
        return

    await member.add_roles(role)
    await interaction.response.send_message(
        f'🤡 {member.mention} теперь клоун на 10 минут!')
    await interaction.channel.send(
        f'@everyone, у нас на сервере новый клоун - {member.mention}! 🤡')

    await asyncio.sleep(600)
    await member.remove_roles(role)
    await interaction.channel.send(f'{member.mention} больше не клоун.')


# Настройки голосовых комнат
voice_settings = {
    "category_id": None,  # ID категории для создания комнат
    "default_name": "Новая комната {owner}",
    "default_limit": 0,  # 0 - без лимита
    "auto_delete_empty": True,  # Автоматически удалять пустые комнаты
    "bitrate": 64000  # Битрейт по умолчанию
}

# Словарь для хранения созданных комнат {channel_id: owner_id}
voice_rooms = {}


# Функции для работы с настройками
def load_settings():
    global welcome_channel_id, clown_role_id, voice_creator_channel_id, voice_settings
    try:
        with open("settings.json", "r") as f:
            data = json.load(f)
            welcome_channel_id = data.get("welcome_channel_id")
            clown_role_id = data.get("clown_role_id")
            voice_creator_channel_id = data.get("voice_creator_channel_id")
            if "voice_settings" in data:
                voice_settings.update(data["voice_settings"])
    except FileNotFoundError:
        pass


def save_settings():
    data = {
        "welcome_channel_id": welcome_channel_id,
        "clown_role_id": clown_role_id,
        "voice_creator_channel_id": voice_creator_channel_id,
        "voice_settings": voice_settings
    }
    with open("settings.json", "w") as f:
        json.dump(data, f)


# ... (предыдущий код до события on_voice_state_update)


# Событие: изменение голосового состояния участника
@bot.event
async def on_voice_state_update(member, before, after):
    # Создание комнаты при входе в специальный канал
    if (after.channel and after.channel.id == voice_creator_channel_id
            and not member.bot):
        await create_voice_room(member)

    # Удаление пустых комнат
    if (before.channel and before.channel.id in voice_rooms
            and len(before.channel.members) == 0
            and voice_settings["auto_delete_empty"]):
        try:
            await before.channel.delete()
            del voice_rooms[before.channel.id]
        except:
            pass


async def create_voice_room(owner):
    """Создает новую голосовую комнату для пользователя"""
    guild = owner.guild
    category = guild.get_channel(voice_settings["category_id"]
                                 ) if voice_settings["category_id"] else None

    channel_name = voice_settings["default_name"].format(
        owner=owner.display_name)

    try:
        new_channel = await guild.create_voice_channel(
            name=channel_name,
            category=category,
            bitrate=voice_settings["bitrate"],
            user_limit=voice_settings["default_limit"])

        voice_rooms[new_channel.id] = owner.id

        # Перемещаем пользователя в новую комнату
        await owner.move_to(new_channel)

        # Отправляем сообщение с инструкциями
        try:
            await owner.send(
                f"🎤 Вы создали голосовую комнату! Используйте команды:\n"
                f"`/voice name [название]` - изменить название комнаты\n"
                f"`/voice limit [число]` - установить лимит участников (0 - без лимита) \n"
                f"`/voice private` - сделать комнату приватной (только для владельца) \n"
                f"`/voice public` - сделать комнату публичной \n"
                f"`/voice close` - закрыть комнату \n"
                f"`/voice allow @user` - разрешить доступ пользователю (для приватных комнат) \n"
                f"`/voice kick @user` - выгнать пользователя из комнаты)")
        except:
            pass  # Если нельзя отправить ЛС

    except Exception as e:
        print(f"Ошибка создания голосовой комнаты: {e}")


# Команды для управления голосовыми комнатами
@bot.tree.command(name="voice_setup",
                  description="Настройка системы голосовых комнат")
@app_commands.describe(
    creator_channel="Канал, при входе в который создается комната",
    category="Категория для создания комнат (опционально)",
    default_name="Шаблон названия (используйте {owner})",
    default_limit="Лимит участников по умолчанию (0 - без лимита)",
    auto_delete="Автоматически удалять пустые комнаты")
async def voice_setup(interaction: discord.Interaction,
                      creator_channel: discord.VoiceChannel,
                      category: discord.CategoryChannel = None,
                      default_name: str = "Новая комната {owner}",
                      default_limit: int = 0,
                      auto_delete: bool = True):
    """Настраивает систему голосовых комнат"""
    global voice_creator_channel_id, voice_settings

    voice_creator_channel_id = creator_channel.id
    voice_settings["category_id"] = category.id if category else None
    voice_settings["default_name"] = default_name
    voice_settings["default_limit"] = max(0, min(default_limit, 99))
    voice_settings["auto_delete_empty"] = auto_delete

    save_settings()

    await interaction.response.send_message(
        "✅ Система голосовых комнат настроена!\n"
        f"Канал-триггер: {creator_channel.mention}\n"
        f"Категория: {category.name if category else 'не указана'}\n"
        f"Название по умолчанию: `{default_name}`\n"
        f"Лимит участников: `{default_limit if default_limit else 'нет'}`\n"
        f"Автоудаление: `{'включено' if auto_delete else 'выключено'}`",
        ephemeral=True)


@bot.tree.command(name="voice",
                  description="Управление вашей голосовой комнатой")
@app_commands.describe(action="Действие", value="Значение (для name и limit)")
@app_commands.choices(action=[
    app_commands.Choice(name="name", value="name"),
    app_commands.Choice(name="limit", value="limit"),
    app_commands.Choice(name="private", value="private"),
    app_commands.Choice(name="public", value="public"),
    app_commands.Choice(name="close", value="close"),
    app_commands.Choice(name="bitrate", value="bitrate")
])
async def voice_control(interaction: discord.Interaction,
                        action: str,
                        value: str = None):
    """Управление голосовой комнатой"""
    # Проверяем, есть ли у пользователя комната
    user_room = None
    for channel_id, owner_id in voice_rooms.items():
        if owner_id == interaction.user.id:
            user_room = interaction.guild.get_channel(channel_id)
            break

    if not user_room:
        await interaction.response.send_message(
            "❌ У вас нет активной голосовой комнаты!", ephemeral=True)
        return

    try:
        if action == "name" and value:
            # Изменение названия
            new_name = value[:100]  # Ограничение длины названия
            await user_room.edit(name=new_name)
            await interaction.response.send_message(
                f"✅ Название комнаты изменено на `{new_name}`", ephemeral=True)

        elif action == "limit":
            # Установка лимита участников
            try:
                limit = int(value) if value else 0
                limit = max(0, min(limit, 99))
                await user_room.edit(user_limit=limit)
                await interaction.response.send_message(
                    f"✅ Лимит участников {'установлен' if limit else 'удалён'}: `{limit if limit else 'нет'}`",
                    ephemeral=True)
            except:
                await interaction.response.send_message(
                    "❌ Неверное значение лимита! Используйте число от 0 до 99.",
                    ephemeral=True)

        elif action == "private":
            # Сделать комнату приватной
            overwrites = user_room.overwrites
            overwrites[
                interaction.guild.default_role] = discord.PermissionOverwrite(
                    connect=False)
            overwrites[interaction.user] = discord.PermissionOverwrite(
                connect=True)

            await user_room.edit(overwrites=overwrites)
            await interaction.response.send_message(
                "🔒 Комната теперь приватная! Разрешите доступ другим участникам с помощью `/voice allow @user`",
                ephemeral=True)

        elif action == "public":
            # Сделать комнату публичной
            overwrites = user_room.overwrites
            overwrites[
                interaction.guild.default_role] = discord.PermissionOverwrite(
                    connect=True)

            await user_room.edit(overwrites=overwrites)
            await interaction.response.send_message(
                "🔓 Комната теперь публичная!", ephemeral=True)

        elif action == "close":
            # Закрыть комнату
            await user_room.delete()
            del voice_rooms[user_room.id]
            await interaction.response.send_message("🚪 Комната закрыта!",
                                                    ephemeral=True)

        elif action == "bitrate" and value:
            # Изменение битрейта
            try:
                bitrate = min(max(int(value), 8000), 384000)
                await user_room.edit(bitrate=bitrate)
                await interaction.response.send_message(
                    f"✅ Битрейт изменён на {bitrate//1000}kbps",
                    ephemeral=True)
            except:
                await interaction.response.send_message(
                    "❌ Неверное значение битрейта! Используйте число от 8000 до 384000.",
                    ephemeral=True)

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ У меня нет прав для изменения этой комнаты!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Произошла ошибка: {e}",
                                                ephemeral=True)


@bot.tree.command(
    name="voice_allow",
    description="Разрешить пользователю доступ к вашей приватной комнате")
@app_commands.describe(user="Пользователь, которому нужно разрешить доступ")
async def voice_allow(interaction: discord.Interaction, user: discord.Member):
    """Разрешает пользователю доступ к приватной комнате"""
    # Проверяем, есть ли у пользователя комната
    user_room = None
    for channel_id, owner_id in voice_rooms.items():
        if owner_id == interaction.user.id:
            user_room = interaction.guild.get_channel(channel_id)
            break

    if not user_room:
        await interaction.response.send_message(
            "❌ У вас нет активной голосовой комнаты!", ephemeral=True)
        return

    try:
        overwrites = user_room.overwrites
        overwrites[user] = discord.PermissionOverwrite(connect=True)

        await user_room.edit(overwrites=overwrites)
        await interaction.response.send_message(
            f"✅ {user.mention} теперь может заходить в вашу комнату!",
            ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Не удалось предоставить доступ: {e}", ephemeral=True)


@bot.tree.command(name="voice_kick",
                  description="Выгнать пользователя из вашей комнаты")
@app_commands.describe(user="Пользователь, которого нужно выгнать")
async def voice_kick(interaction: discord.Interaction, user: discord.Member):
    """Выгоняет пользователя из голосовой комнаты"""
    # Проверяем, есть ли у пользователя комната
    user_room = None
    for channel_id, owner_id in voice_rooms.items():
        if owner_id == interaction.user.id:
            user_room = interaction.guild.get_channel(channel_id)
            break

    if not user_room:
        await interaction.response.send_message(
            "❌ У вас нет активной голосовой комнаты!", ephemeral=True)
        return

    if user not in user_room.members:
        await interaction.response.send_message(
            f"❌ {user.mention} не находится в вашей комнате!", ephemeral=True)
        return

    try:
        await user.move_to(None)
        await interaction.response.send_message(
            f"✅ {user.mention} был выгнан из комнаты!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Не удалось выгнать пользователя: {e}", ephemeral=True)


# Запуск бота
bot.run(
    "MTM0MDM3MTMzNzY0MTg1Mjk5Mg.Gkl_a8.otyydowaMTBOOTUT8EJwJ2X7jQ37yUGV-i7oxE")
