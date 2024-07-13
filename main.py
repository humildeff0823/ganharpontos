import json
import yt_dlp
import os
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
import logging
from flask import Flask, request
import threading

# Configuração do logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar a lista de filmes e canais do arquivo JSON
with open('iptv.json', 'r') as file:
    movie_list = json.load(file)

TMDB_API_KEY = '253c1602a6d75af489edf2878636cc18'
YOUTUBE_API_KEY = 'AIzaSyDbc52S_vbNFQ3iqdQVdawOQQATWOMQU0A'
TELEGRAM_BOT_TOKEN = '7353949939:AAHeGCghEEfkcm8MEE0zCM5XzFExZn2loL4'

# Arquivo de banidos
banidos_arquivo = 'banidos.json'

# Função para registrar usuários banidos
def registrar_banido(user):
    with open(banidos_arquivo, 'a') as file:
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file.write(f"Usuário: @{user.username} | ID: {user.id} | Data e Hora: {agora}\n")

# Função para obter detalhes de filmes
def get_movie_details(title):
    try:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}&language=pt-BR"
        response = requests.get(url)
        data = response.json()
        if data['results']:
            movie = data['results'][0]
            poster_path = movie['poster_path']
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
            synopsis = movie.get('overview', 'Sinopse não disponível.')
            rating = movie.get('vote_average', 'Avaliação não disponível.')
            return poster_url, synopsis, rating
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do filme: {e}")
    return None, 'Sinopse não disponível.', 'Avaliação não disponível.'

# Handler para o comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("🎬 Baixar Filmes", callback_data="baixar_filmes"),
            InlineKeyboardButton("🎵 Baixar Músicas", callback_data="baixar_musicas")
        ],
        [
            InlineKeyboardButton("📺 Baixar Vídeos", callback_data="baixar_videos"),
        ],
        [
            InlineKeyboardButton("📞 Suporte", url="https://t.me/seu_telegram")
        ],
        [
            InlineKeyboardButton("🚫 Não concordo com esse bot", callback_data="nao_concordo")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    image_url = 'https://s10.gifyu.com/images/StcDr.png'  # Substitua pelo URL da sua imagem
    await update.message.reply_photo(photo=image_url, caption='😎Olá! Bem-vindo ao bot. Escolha uma opção abaixo:', reply_markup=reply_markup)

# Handler para o comando /filme
async def filme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    movie_name = ' '.join(context.args).lower()
    if not movie_name:
        await update.message.reply_text(f"🤔 Você precisa digitar o nome do filme! Use: /filme <nome do filme>")
        return

    for movie in movie_list:
        if movie_name in movie['title'].lower():
            title = movie['title']
            url = movie['url']
            poster_url, synopsis, rating = get_movie_details(title)
            movie_id = str(movie_list.index(movie))
            callback_data = f"send_link:{movie_id}"
            
            keyboard = [
                [
                    InlineKeyboardButton("🤔Sim, esse é o filme", callback_data=callback_data),
                    InlineKeyboardButton("Cancelar", callback_data="cancelar")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            caption = f"Você escolheu o filme: {title}\n\n👀Sinopse: {synopsis}\n\n🌟Avaliação: {rating}\n\n🤔Está correto?"
            if poster_url:
                await update.message.reply_photo(photo=poster_url, caption=caption, reply_markup=reply_markup)
            else:
                await update.message.reply_text(text=caption, reply_markup=reply_markup)
            return

    await update.message.reply_text(f"👀Filme '{movie_name}' não encontrado.")

# Handler para o comando /musica
async def musica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    music_name = ' '.join(context.args)
    if not music_name:
        await update.message.reply_text(f"🤔 Você precisa digitar o nome da música! Use: /musica <nome da música>")
        return

    try:
        # Pesquisa na API do YouTube
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={music_name}&type=video&key={YOUTUBE_API_KEY}"
        response = requests.get(url)
        data = response.json()

        if 'items' in data:
            video_id = data['items'][0]['id']['videoId']
            video_title = data['items'][0]['snippet']['title']
            video_thumbnail = data['items'][0]['snippet']['thumbnails']['high']['url']
            
            keyboard = [
                [
                    InlineKeyboardButton("Sim, essa é a música?🤔", callback_data=f"confirm_music:{video_id}"),
                    InlineKeyboardButton("Cancelar❌️", callback_data="cancelar")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            caption = f"Você escolheu a música: {video_title}\n\nEssa é a música correta?🤔"

            await update.message.reply_photo(photo=video_thumbnail, caption=caption, reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"Música '{music_name}' não encontrada.")

    except Exception as e:
        await update.message.reply_text(f"Erro ao buscar a música: {e}")

# Handler para o comando /video
async def video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video_name = ' '.join(context.args).lower()
    if not video_name:
        await update.message.reply_text(f"🤔 Você precisa digitar o nome do vídeo! Use: /video <nome do vídeo>")
        return

    try:
        # Pesquisa na API do YouTube
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={video_name}&type=video&key={YOUTUBE_API_KEY}"
        response = requests.get(url)
        data = response.json()

        if 'items' in data:
            video_id = data['items'][0]['id']['videoId']
            video_title = data['items'][0]['snippet']['title']
            video_thumbnail = data['items'][0]['snippet']['thumbnails']['high']['url']
            
            keyboard = [
                [
                    InlineKeyboardButton("Sim, esse é o vídeo?🤔", callback_data=f"confirm_video:{video_id}"),
                    InlineKeyboardButton("Cancelar❌️", callback_data="cancelar")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            caption = f"Você escolheu o vídeo: {video_title}\n\nEsse é o vídeo correto?🤔"

            await update.message.reply_photo(photo=video_thumbnail, caption=caption, reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"Vídeo '{video_name}' não encontrado.")

    except Exception as e:
        await update.message.reply_text(f"Erro ao buscar o vídeo: {e}")

# Handler para os botões de callback
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    logger.info(f"Botão clicado com callback_data: {data}")

    if data.startswith("send_link:"):
        movie_id = data.split(":")[1]
        movie = movie_list[int(movie_id)]
        url = movie['url']
        title = movie['title']
        poster_url, synopsis, rating = get_movie_details(title)

        if poster_url:
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=poster_url, caption=f"😘👀Aqui está o link do filme '{title}': {url}\nBom filme! 🎬")
        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"Aqui está o link do filme '{title}': {url}\nBom filme! 🎬")

    elif data.startswith("confirm_music:"):
        video_id = data.split(":")[1]
        music_name = query.message.caption.split(': ')[1].split('\n')[0]  # Obtém o nome da música da legenda
        
        await query.message.delete()  # Remove a mensagem original com a imagem e botões
        mensagem_espera = await context.bot.send_message(chat_id=query.message.chat_id, text="🎶 Em 3/5 segundos sua música será enviada! 🎶")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{music_name}.%(ext)s',
            'postprocessors': [{
            'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f'https://www.youtube.com/watch?v={video_id}'])

            file_path = f'{music_name}.mp3'
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=mensagem_espera.message_id)
            await context.bot.send_audio(chat_id=query.message.chat_id, audio=open(file_path, 'rb'))
            os.remove(file_path)
        except Exception as e:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"Erro ao baixar a música: {e}")

    elif data.startswith("confirm_video:"):
        video_id = data.split(":")[1]
        video_name = query.message.caption.split(': ')[1].split('\n')[0]  # Obtém o nome do vídeo da legenda
        
        await query.message.delete()  # Remove a mensagem original com a imagem e botões
        mensagem_espera = await context.bot.send_message(chat_id=query.message.chat_id, text="📺 Em 3/5 segundos seu vídeo será enviado! 📺")

        ydl_opts = {
            'format': 'best',
            'outtmpl': f'{video_name}.%(ext)s',
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f'https://www.youtube.com/watch?v={video_id}'])

            file_path = f'{video_name}.mp4'
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=mensagem_espera.message_id)
            await context.bot.send_video(chat_id=query.message.chat_id, video=open(file_path, 'rb'))
            os.remove(file_path)
        except Exception as e:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"Erro ao baixar o vídeo: {e}")

    elif data == "cancelar":
        await query.message.delete()  # Remove a mensagem original com a imagem e botões
        await context.bot.send_message(chat_id=query.message.chat_id, text="🤔 Quer escolher outra opção? Use /musica ou /video.")

    elif data == "baixar_filmes":
        await query.message.reply_text("🎬 Escolha o filme com o comando /filme <nome do filme>.")

    elif data == "baixar_musicas":
        await query.message.reply_text("🎵 Escolha a música com o comando /musica <nome da música>.")

    elif data == "baixar_videos":
        await query.message.reply_text("📺 Escolha o vídeo com o comando /video <nome do vídeo>.")

    elif data == "suporte":
        await query.message.reply_text("📞 Para suporte, entre em contato com @seu_telegram")

    elif data == "nao_concordo":
        user = query.from_user
        if update.effective_chat.type in ['group', 'supergroup']:
            await context.bot.send_message(chat_id=query.message.chat_id, text="🚫 Não aceitamos pessoas do seu tipo aqui em nossa comunidade. Segura o bloqueio!")
            await context.bot.ban_chat_member(chat_id=query.message.chat_id, user_id=user.id)
            registrar_banido(user)
        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text="🚫 Não aceitamos pessoas do seu tipo aqui em nossa comunidade.")
        await query.message.delete()

# Servidor Flask para manter o bot vivo
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('filme', filme))
    application.add_handler(CommandHandler('musica', musica))
    application.add_handler(CommandHandler('video', video))
    application.add_handler(CallbackQueryHandler(button))

    keep_alive()
    application.run_polling()

if __name__ == '__main__':
    main()