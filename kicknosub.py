import os
import sys
import platform
import shutil
import subprocess
from datetime import datetime
from kickapi import KickAPI
from rich.console import Console
from rich.panel import Panel
import questionary
import cloudscraper
from datetime import timedelta

# KickNoSub sınıfı, Kick video URL'sinden master kalitesinde akış (stream) URL'sini elde etmek için kullanılır.
class KickNoSub:
    def __init__(self):
        # Console objesi başlatılır
        self.console = Console()
        # CloudScraper ve API nesneleri
        self.session = cloudscraper.CloudScraper()
        self.api = KickAPI()
        self.os_name = platform.system()
        self.ffmpeg_local_path = os.path.join(
            os.path.dirname(__file__), 
            "ffmpeg", 
            "ffmpeg.exe" if self.os_name == "Windows" else "ffmpeg"
        )

    # İndirme ve FFmpeg ile ilgili fonksiyonlar kod bütünlüğü için tutulur, ancak run() metodunda çağrılmaz.
    def ffmpeg_exists(self):
        return shutil.which("ffmpeg") is not None or os.path.exists(self.ffmpeg_local_path)

    def install_ffmpeg(self):
        pass

    def download_video(self, stream_url: str, filename: str):
        pass

    def get_video_stream_url(self, video_url: str, quality: str) -> str | None:
        """Video URL'den ±5 dakika ofset kullanarak HLS akış URL'sini (belirtilen kalitede) bulur."""
        try:
            parts = video_url.split("/")
            if len(parts) < 6:
                return None
            channel_name = parts[3]
            video_slug = parts[5]

            channel = self.api.channel(channel_name)
            for video in channel.videos:
                if video.uuid == video_slug:
                    thumbnail_url = video.thumbnail["src"]
                    start_time = datetime.strptime(video.start_time, "%Y-%m-%d %H:%M:%S")
                    path_parts = thumbnail_url.split("/")
                    channel_id, video_id = path_parts[4], path_parts[5]

                    # Akış URL'sini bulmak için başlangıç zamanını ±5 dakika kaydırarak dener.
                    for offset in range(-5, 6):
                        adjusted_time = start_time + timedelta(minutes=offset)
                        
                        # Arama kalitesi (örneğimizde "480p30") URL yapısında kullanılır.
                        stream_url = (
                            f"https://stream.kick.com/ivs/v1/196233775518/"
                            f"{channel_id}/{adjusted_time.year}/{adjusted_time.month}/"
                            f"{adjusted_time.day}/{adjusted_time.hour}/{adjusted_time.minute}/"
                            f"{video_id}/media/hls/{quality}/playlist.m3u8"
                        )
                        
                        # Head isteği ile URL'nin geçerli olup olmadığını kontrol eder.
                        res = self.session.head(stream_url)
                        if res.status_code == 200:
                            self.console.print(
                                f"[green]✅ Found valid stream at offset {offset} minute(s) using {quality}[/green]"
                            )
                            # Çalışan URL'yi döndürür (480p30 içeren URL).
                            return stream_url

                    self.console.print(f"[red]❌ Could not find a valid stream using {quality} within ±5 minutes.[/red]")
                    return None
            return None
        except Exception as e:
            self.console.print(f"[red]Error:[/red] {e}")
            return None

    def run(self):
        """Ana program döngüsü: Sadece URL ister, 480p30 ile arar ve çıktıyı master.m3u8 olarak değiştirir."""
        
        # Kullanıcıdan sadece link istenir.
        video_url = questionary.text("Enter the Kick video URL:").ask()
        
        # Gerçek arama için kullanılan güvenilir kalite
        search_quality = "480p30" 
        # Çıktıda gösterilecek hedef dosya adı
        target_output_filename = "master.m3u8"

        self.console.print(f"[bold yellow]Searching for stream using reliable quality:[/bold yellow] [bold green]{search_quality}[/bold green]")
        
        if not video_url:
            self.console.print("[red]❌ Video URL is required. Exiting.[/red]")
            sys.exit()

        # Çalışan kalite ile akış URL'si aranır.
        stream_url = self.get_video_stream_url(video_url, search_quality)

        if not stream_url:
            self.console.print("[red]❌ Video not found or stream URL could not be retrieved. Exiting.[/red]")
            sys.exit()

        # --- ÇIKTI ÖNCESİ ÖNEMLİ DEĞİŞİKLİK ---
        # Bulunan URL'deki kalite klasörü ve dosya adı segmenti (/480p30/playlist.m3u8) değiştirilir.
        search_segment = f"/{search_quality}/playlist.m3u8"
        target_segment = f"/{target_output_filename}" # "/master.m3u8"
        
        # URL'nin kalite ve dosya adı kısmını değiştiriyoruz.
        final_stream_url = stream_url.replace(search_segment, target_segment)

        # Başarılı mesajı Rich konsola yazdırılır.
        self.console.print(f"\n[bold green]Successfully retrieved Stream URL (Output Filename: {target_output_filename}):[/bold green]")
        
        # İstenildiği gibi SADECE linkin kendisi standart çıktıya yazdırılır.
        print(final_stream_url)

if __name__ == "__main__":
    app = KickNoSub()
    app.run()
```eof
