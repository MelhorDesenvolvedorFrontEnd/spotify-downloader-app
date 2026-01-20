# main.py - Spotify Downloader com interface gráfica (Kivy) - versão mobile/PC
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp, sp  # para ajustes automáticos de tamanho
import threading
import os
import sys
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TPE1, TIT2, TALB, TDRC, TRCK
import subprocess

# Configurações
SPOTIFY_CLIENT_ID = "b6c3b5b84f214b82b823d2ca9b362d60"
SPOTIFY_CLIENT_SECRET = "385da508953d495ba43052130727b917"
CONFIG_FILE = "config.txt"

# Fundo verde escuro estilo Spotify
Window.clearcolor = (0.07, 0.6, 0.3, 1)  # Verde Spotify

# Tamanho fixo para teste no PC (simula celular médio)
Window.size = (400, 700)  # Isso faz abrir fixo no seu PC, mas no celular real ignora e ajusta automático

class SpotifyDownloaderApp(App):
    def __init__(self):
        super().__init__()
        self.download_dir = self.load_config()
        self.sp = None

    def build(self):
        # Ajuste automático baseado na resolução do dispositivo
        width = Window.width  # Pega largura atual (automático em celular)
        height = Window.height  # Pega altura atual

        # Fatores de escala básica para diferentes resoluções comuns
        if width < 400:  # Celulares pequenos (ex: 360x640)
            font_scale = 0.9
            padding = dp(10)
            spacing = dp(8)
            input_height = dp(40)
            log_height = dp(200)
        elif width < 600:  # Celulares médios (ex: 414x896, 393x873)
            font_scale = 1.0
            padding = dp(20)
            spacing = dp(10)
            input_height = dp(50)
            log_height = dp(300)
        elif width < 800:  # Celulares grandes ou tablets (ex: 412x915, 800x1280)
            font_scale = 1.2
            padding = dp(30)
            spacing = dp(15)
            input_height = dp(60)
            log_height = dp(400)
        else:  # PC ou resoluções maiores (ex: 1280x720 ou mais)
            font_scale = 1.5
            padding = dp(40)
            spacing = dp(20)
            input_height = dp(70)
            log_height = dp(500)

        layout = BoxLayout(orientation='vertical', padding=padding, spacing=spacing)

        # Título
        title = Label(
            text="Spotify Music Downloader",
            font_size=sp(28 * font_scale),
            bold=True,
            color=(1,1,1,1)
        )
        layout.add_widget(title)

        # Campo de link
        self.url_input = TextInput(
            hint_text="Cole o link do Spotify aqui",
            multiline=False,
            size_hint=(1, 0.1),
            height=input_height,
            background_color=(0.1,0.1,0.1,1),
            foreground_color=(1,1,1,1),
            font_size=sp(16 * font_scale)
        )
        layout.add_widget(self.url_input)

        # Botão Baixar
        download_btn = Button(
            text="Baixar",
            size_hint=(1, 0.15),
            height=input_height,
            background_color=(0, 0.8, 0, 1),
            color=(1,1,1,1),
            font_size=sp(20 * font_scale)
        )
        download_btn.bind(on_press=self.start_download)
        layout.add_widget(download_btn)

        # Área de log
        scroll = ScrollView()
        self.log_label = Label(
            text="Log aqui...\n\n",
            size_hint_y=None,
            height=log_height,
            valign='top',
            halign='left',
            text_size=(None, None),
            color=(1,1,1,1),
            font_size=sp(14 * font_scale)
        )
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        scroll.add_widget(self.log_label)
        layout.add_widget(scroll)

        # Botão de configurar pasta
        config_btn = Button(
            text="Mudar pasta de download",
            size_hint=(1, 0.1),
            height=input_height - dp(10),
            background_color=(0.2, 0.2, 0.2, 1),
            font_size=sp(16 * font_scale)
        )
        config_btn.bind(on_press=self.choose_folder_popup)
        layout.add_widget(config_btn)

        return layout

    def log(self, message):
        self.log_label.text += message + "\n"
        self.log_label.text_size = (self.log_label.width, None)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                path = f.read().strip()
                if os.path.exists(path):
                    return path
        return os.path.expanduser("~/storage/downloads/spotify" if 'storage' in os.path.expanduser("~") else os.path.expanduser("~/Downloads/spotify"))

    def save_config(self, path):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(path)
        self.download_dir = path
        self.log(f"Pasta de download alterada para: {path}")

    def choose_folder_popup(self, instance):
        content = BoxLayout(orientation='vertical', padding=10)
        label = Label(text="Digite o caminho completo da pasta desejada\n(ex: /storage/emulated/0/Music)", size_hint=(1, 0.4))
        input_field = TextInput(multiline=False, size_hint=(1, 0.2))
        btn_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)
        ok_btn = Button(text="Salvar", background_color=(0, 0.8, 0, 1))
        cancel_btn = Button(text="Cancelar", background_color=(0.8, 0, 0, 1))

        def save_path(*args):
            path = input_field.text.strip()
            if path:
                os.makedirs(path, exist_ok=True)
                self.save_config(path)
            popup.dismiss()

        ok_btn.bind(on_press=save_path)
        cancel_btn.bind(on_press=lambda x: popup.dismiss())

        btn_layout.add_widget(ok_btn)
        btn_layout.add_widget(cancel_btn)

        content.add_widget(label)
        content.add_widget(input_field)
        content.add_widget(btn_layout)

        popup = Popup(title="Escolher Pasta de Download", content=content, size_hint=(0.8, 0.6))
        popup.open()

    def get_spotify_client(self):
        if not self.sp:
            try:
                self.sp = spotipy.Spotify(
                    auth_manager=SpotifyClientCredentials(
                        client_id=SPOTIFY_CLIENT_ID,
                        client_secret=SPOTIFY_CLIENT_SECRET
                    )
                )
                self.log("Conectado ao Spotify com sucesso!")
            except Exception as e:
                self.log(f"Erro ao conectar ao Spotify: {e}")
        return self.sp

    def download_thread(self, url):
        sp = self.get_spotify_client()
        if not sp:
            return

        self.log("\nLendo informações do Spotify...")

        tracks = []
        album_name = "Vários"

        try:
            if "track" in url:
                track_id = url.split('/')[-1].split('?')[0]
                track = sp.track(track_id)
                tracks = [track]
                album_name = track["album"]["name"]

            elif "album" in url:
                album_id = url.split('/')[-1].split('?')[0]
                album = sp.album(album_id)
                album_name = album["name"]
                album_tracks = sp.album_tracks(album_id)
                tracks = album_tracks['items']

            elif "playlist" in url:
                playlist_id = url.split('/')[-1].split('?')[0]
                results = sp.playlist_tracks(playlist_id)
                tracks = [item['track'] for item in results['items'] if item['track']]
                album_name = "Playlist - " + sp.playlist(playlist_id)["name"]

            else:
                self.log("Link não reconhecido.")
                return

            album_dir = os.path.join(self.download_dir, album_name.replace("/", "-").replace("\\", "-"))
            os.makedirs(album_dir, exist_ok=True)

            self.log(f"Baixando {len(tracks)} faixas para: {album_dir}")

            for i, track in enumerate(tracks, 1):
                self.log(f"Faixa {i}/{len(tracks)}: {track['name']}")
                metadata = self.get_track_metadata(track)
                if not metadata:
                    continue

                search = f"{metadata['artist']} - {metadata['title']}"
                file_path = self.download_track(search, album_dir)

                if file_path and os.path.exists(file_path):
                    self.embed_tags(file_path, metadata)
                else:
                    self.log("Falhou nessa faixa.")

            self.log("\nTudo finalizado! Verifique a pasta: " + album_dir)

        except Exception as e:
            self.log(f"Erro geral: {e}")

    def start_download(self, instance):
        url = self.url_input.text.strip()
        if not url:
            self.log("Digite um link do Spotify!")
            return

        threading.Thread(target=self.download_thread, args=(url,)).start()

    def get_track_metadata(self, track):
        try:
            return {
                "artist": track["artists"][0]["name"],
                "title": track["name"],
                "album": track["album"]["name"],
                "year": track["album"]["release_date"][:4],
                "cover_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None
            }
        except:
            return None

    def embed_tags(self, file_path, metadata):
        try:
            audio = MP3(file_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()

            audio.tags.add(TPE1(encoding=3, text=metadata["artist"]))
            audio.tags.add(TIT2(encoding=3, text=metadata["title"]))
            audio.tags.add(TALB(encoding=3, text=metadata["album"]))
            audio.tags.add(TDRC(encoding=3, text=metadata["year"]))

            if metadata["cover_url"]:
                cover_data = requests.get(metadata["cover_url"]).content
                audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_data))

            audio.save()
            self.log("Tags e capa embutidas!")
        except Exception as e:
            self.log(f"Erro ao embutir tags: {e}")

    def download_track(self, search, output_dir):
        searches = [
            search,
            search + " áudio oficial",
            search + " letra oficial",
            search + " 320kbps"
        ]

        for query in searches:
            self.log(f"Tentando: {query}")
            cmd = [
                "yt-dlp",
                "-f", "bestaudio/best",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "--embed-thumbnail",
                "-o", os.path.join(output_dir, "%(title)s.%(ext)s"),
                f"ytsearch1:{query}"
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    for file in os.listdir(output_dir):
                        if file.endswith('.mp3'):
                            return os.path.join(output_dir, file)
                else:
                    self.log("Falhou. Tentando próxima...")
            except:
                pass

        self.log("Não encontrou áudio para essa faixa.")
        return None

if __name__ == '__main__':
    SpotifyDownloaderApp().run()