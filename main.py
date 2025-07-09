# main.py

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp
from config import DISCORD_TOKEN  # Importa o token do seu arquivo de configuração

# --- CONFIGURAÇÕES DE MÚSICA ---
# Opções para o yt-dlp para garantir que ele pegue o melhor áudio e não um vídeo
YDL_OPTS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'auto',
    'quiet': True,
    'no_warnings': True,
}

# Opções para o FFmpeg para estabilizar a conexão
FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True # Necessário para algumas interações
bot = commands.Bot(command_prefix="!", intents=intents)

# Dicionário para guardar a fila de músicas de cada servidor
queues = {}

# --- FUNÇÃO AUXILIAR PARA TOCAR A PRÓXIMA MÚSICA ---
def play_next(interaction):
    # Checa se ainda existe uma fila para este servidor
    if interaction.guild.id in queues and queues[interaction.guild.id]:
        # Pega a próxima música da fila
        song = queues[interaction.guild.id].pop(0)
        source = discord.FFmpegPCMAudio(song['url'], **FFMPEG_OPTS)
        
        # Toca a música e, quando ela acabar, chama esta mesma função novamente
        interaction.guild.voice_client.play(source, after=lambda e: play_next(interaction))
    else:
        # Se a fila estiver vazia, apenas informa no console.
        print(f"Fila de músicas do servidor {interaction.guild.name} terminou.")

# --- EVENTO ON_READY (QUANDO O BOT LIGA) ---
@bot.event
async def on_ready():
    print(f'Bot conectado como: {bot.user}')
    print('Sincronizando comandos...')
    try:
        synced = await bot.tree.sync()
        print(f'Sincronizados {len(synced)} comandos.')
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")
    print('------')

# --- COMANDOS DE MÚSICA ---

@bot.tree.command(name="play", description="Toca uma música do YouTube ou faz uma busca.")
@app_commands.describe(busca="O nome ou o link da música do YouTube.")
async def play(interaction: discord.Interaction, busca: str):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Você precisa estar em um canal de voz para usar este comando.", ephemeral=True)
        return

    voice_client = interaction.guild.voice_client
    if not voice_client:
        voice_client = await interaction.user.voice.channel.connect()

    await interaction.response.send_message(f"🔎 Procurando por `{busca}`...", ephemeral=True)
    
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{busca}", download=False)['entries'][0]
        except Exception as e:
            await interaction.followup.send("❌ Não foi possível encontrar a música. Tente um nome diferente ou um link direto.", ephemeral=True)
            print(e)
            return

    song = {'url': info['url'], 'title': info.get('title', 'Título desconhecido')}
    
    if interaction.guild.id not in queues:
        queues[interaction.guild.id] = []
    queues[interaction.guild.id].append(song)
    
    if not voice_client.is_playing():
        await interaction.followup.send(f"▶️ Tocando agora: **{song['title']}**")
        play_next(interaction)
    else:
        await interaction.followup.send(f"✅ Adicionado à fila: **{song['title']}**")

@bot.tree.command(name="leave", description="Faz o bot sair do canal de voz.")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_connected():
        queues.pop(interaction.guild.id, None) # Limpa a fila do servidor
        await voice_client.disconnect()
        await interaction.response.send_message("👋 Desconectado do canal de voz.")
    else:
        await interaction.response.send_message("Eu não estou em um canal de voz.", ephemeral=True)

@bot.tree.command(name="skip", description="Pula para a próxima música da fila.")
async def skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop() # A função 'after' do play_next será chamada, tocando a próxima
        await interaction.response.send_message("⏭️ Música pulada.")
    else:
        await interaction.response.send_message("Não há música tocando para pular.", ephemeral=True)

@bot.tree.command(name="queue", description="Mostra a fila de músicas.")
async def queue(interaction: discord.Interaction):
    if interaction.guild.id in queues and queues[interaction.guild.id]:
        # Formata a lista para exibição
        queue_list = "\n".join([f"{i+1}. {song['title']}" for i, song in enumerate(queues[interaction.guild.id])])
        await interaction.response.send_message(f"**Fila de Músicas:**\n{queue_list}")
    else:
        await interaction.response.send_message("A fila de músicas está vazia.", ephemeral=True)

# --- RODA O BOT ---
if __name__ == '__main__':
    # Certifique-se de que as bibliotecas necessárias estão instaladas
    # pip install discord.py yt-dlp PyNaCl
    bot.run(DISCORD_TOKEN)