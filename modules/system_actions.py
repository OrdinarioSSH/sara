"""
Módulo de Ações do Sistema — SARA
Controle do PC via comandos de voz: abrir apps, controlar mídia, volume,
screenshot, status do sistema, calculadora, notas, Wikipedia, localização.
"""
import subprocess
import platform
import os
import datetime
import webbrowser
import ctypes
import math
from typing import Optional, Dict, Callable
from pathlib import Path
import re


# ==================== TECLAS DE MÍDIA (Windows) ====================

def _press_media_key(vk_code):
    """Simula tecla de mídia no Windows via keybd_event (funciona com Spotify, YouTube, etc)."""
    if platform.system().lower() != "windows":
        return False
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    return True


# Virtual key codes para mídia
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_MUTE = 0xAD


class SystemActions:
    def __init__(self):
        self.os_name = platform.system().lower()

        # Apps conhecidos para cada plataforma
        self.app_aliases: Dict[str, Dict[str, str]] = {
            "windows": {
                "bloco de notas": "notepad",
                "notepad": "notepad",
                "calculadora": "calc",
                "calculator": "calc",
                "explorador": "explorer",
                "explorer": "explorer",
                "navegador": "start chrome",
                "chrome": "start chrome",
                "google chrome": "start chrome",
                "firefox": "start firefox",
                "edge": "start msedge",
                "spotify": "spotify:",
                "vscode": "code",
                "visual studio code": "code",
                "vs code": "code",
                "terminal": "wt",
                "cmd": "cmd",
                "powershell": "powershell",
                "paint": "mspaint",
                "word": "start winword",
                "excel": "start excel",
                "powerpoint": "start powerpnt",
                "discord": "discord:",
                "telegram": "telegram:",
                "whatsapp": "whatsapp:",
                "steam": "steam:",
                "epic games": "com.epicgames.launcher:",
                "gerenciador de tarefas": "taskmgr",
                "task manager": "taskmgr",
                "configurações": "ms-settings:",
                "configuracoes": "ms-settings:",
                "loja": "ms-windows-store:",
                "microsoft store": "ms-windows-store:",
            },
            "linux": {
                "bloco de notas": "gedit",
                "notepad": "gedit",
                "calculadora": "gnome-calculator",
                "explorador": "nautilus",
                "chrome": "google-chrome",
                "firefox": "firefox",
                "spotify": "spotify",
                "vscode": "code",
                "terminal": "gnome-terminal",
                "discord": "discord",
            },
            "darwin": {
                "bloco de notas": "open -a TextEdit",
                "calculadora": "open -a Calculator",
                "finder": "open -a Finder",
                "chrome": "open -a 'Google Chrome'",
                "safari": "open -a Safari",
                "firefox": "open -a Firefox",
                "spotify": "open -a Spotify",
                "vscode": "open -a 'Visual Studio Code'",
                "terminal": "open -a Terminal",
                "discord": "open -a Discord",
            }
        }

        # URLs diretas para sites comuns
        self.site_aliases: Dict[str, str] = {
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
            "gmail": "https://mail.google.com",
            "github": "https://github.com",
            "twitter": "https://twitter.com",
            "x": "https://twitter.com",
            "instagram": "https://www.instagram.com",
            "facebook": "https://www.facebook.com",
            "reddit": "https://www.reddit.com",
            "twitch": "https://www.twitch.tv",
            "netflix": "https://www.netflix.com",
            "amazon": "https://www.amazon.com.br",
            "mercado livre": "https://www.mercadolivre.com.br",
            "chatgpt": "https://chat.openai.com",
            "claude": "https://claude.ai",
            "whatsapp web": "https://web.whatsapp.com",
            "linkedin": "https://www.linkedin.com",
            "notion": "https://www.notion.so",
            "figma": "https://www.figma.com",
        }

    # ==================== AÇÕES ====================

    def get_time(self) -> str:
        now = datetime.datetime.now()
        return f"Senhor, são {now.strftime('%H:%M')}."

    def get_date(self) -> str:
        now = datetime.datetime.now()
        dias = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
                "sexta-feira", "sábado", "domingo"]
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                 "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        return f"Hoje é {dias[now.weekday()]}, {now.day} de {meses[now.month - 1]} de {now.year}."

    def open_app(self, app_name: str) -> str:
        app_key = app_name.lower().strip()

        # Verifica se é um site conhecido
        if app_key in self.site_aliases:
            webbrowser.open(self.site_aliases[app_key])
            return f"Abrindo {app_name}, Senhor."

        # Verifica aliases de aplicativos
        apps = self.app_aliases.get(self.os_name, {})
        command = apps.get(app_key)

        if not command:
            command = app_key

        try:
            # URIs de protocolo (spotify:, discord:, ms-settings:, etc.) precisam de os.startfile
            if self.os_name == "windows" and ":" in command and not command.startswith("start "):
                os.startfile(command)
            elif self.os_name == "windows" and command.startswith("start "):
                # Comandos "start X" precisam de título vazio para não confundir com URIs
                app_part = command[6:]  # remove "start "
                subprocess.Popen(f'start "" "{app_part}"', shell=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(command, shell=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Abrindo {app_name}, Senhor."
        except Exception as e:
            return f"Não foi possível abrir {app_name}. Erro: {str(e)}"

    def web_search(self, query: str, engine: str = "google") -> str:
        try:
            if engine == "youtube":
                url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                webbrowser.open(url)
                return f"Pesquisando '{query}' no YouTube, Senhor."
            else:
                url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                webbrowser.open(url)
                return f"Pesquisando '{query}' no Google, Senhor."
        except Exception as e:
            return f"Erro ao pesquisar: {str(e)}"

    def play_music(self, query: Optional[str] = None, platform_name: str = "youtube") -> str:
        try:
            if query:
                if platform_name == "spotify":
                    return self._spotify_play(query)
                else:
                    import threading
                    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                    webbrowser.open(url)
                    # Clica no primeiro resultado automaticamente
                    threading.Thread(target=_youtube_click_first_result, daemon=True).start()
                    return f"Reproduzindo '{query}' no YouTube, Senhor."
            else:
                return self.open_app("spotify")
        except Exception as e:
            return f"Erro ao reproduzir: {str(e)}"

    def _spotify_play(self, query: str) -> str:
        """Abre busca no Spotify desktop via URI e clica no primeiro resultado."""
        import urllib.parse
        import threading

        encoded = urllib.parse.quote(query)
        uri = f"spotify:search:{encoded}"

        if self.os_name == "windows":
            # Verifica se o Spotify já está aberto
            hwnd = _find_spotify_window()
            already_open = hwnd is not None

            if already_open:
                # Spotify já está aberto — usa Ctrl+L para buscar diretamente
                threading.Thread(
                    target=_spotify_search_when_open, args=(hwnd, query,), daemon=True
                ).start()
            else:
                # Spotify não está aberto — abre primeiro, depois busca
                os.startfile("spotify:")
                threading.Thread(
                    target=self._spotify_open_then_search, args=(uri,), daemon=True
                ).start()

            return f"Reproduzindo '{query}' no Spotify, Senhor."
        else:
            webbrowser.open(f"https://open.spotify.com/search/{encoded}")
            return f"Procurando '{query}' no Spotify, Senhor."

    def _spotify_open_then_search(self, search_uri: str):
        """Espera o Spotify abrir e depois envia o URI de busca."""
        import time as _t

        # Espera o Spotify aparecer (até 10 segundos)
        for _ in range(20):
            _t.sleep(0.5)
            hwnd = _find_spotify_window()
            if hwnd:
                break
        else:
            print("[SARA] Spotify nao abriu a tempo.")
            return

        # Spotify abriu — espera mais um pouco para estabilizar
        _t.sleep(1.5)

        # Envia URI de busca
        os.startfile(search_uri)

        # Espera a busca carregar e clica no resultado
        _spotify_click_play(3.5)

    # ==================== CONTROLE DE MÍDIA ====================

    def media_play_pause(self) -> str:
        if _press_media_key(VK_MEDIA_PLAY_PAUSE):
            return "Alternando reprodução, Senhor."
        return "Controle de mídia indisponível neste sistema."

    def media_next(self) -> str:
        if _press_media_key(VK_MEDIA_NEXT_TRACK):
            return "Próxima faixa, Senhor."
        return "Controle de mídia indisponível neste sistema."

    def media_previous(self) -> str:
        if _press_media_key(VK_MEDIA_PREV_TRACK):
            return "Faixa anterior, Senhor."
        return "Controle de mídia indisponível neste sistema."

    def media_stop(self) -> str:
        if _press_media_key(VK_MEDIA_STOP):
            return "Reprodução interrompida, Senhor."
        return "Controle de mídia indisponível neste sistema."

    # ==================== CONTROLE DE VOLUME ====================

    def volume_up(self, steps: int = 5) -> str:
        for _ in range(steps):
            _press_media_key(VK_VOLUME_UP)
        return "Volume aumentado, Senhor."

    def volume_down(self, steps: int = 5) -> str:
        for _ in range(steps):
            _press_media_key(VK_VOLUME_DOWN)
        return "Volume reduzido, Senhor."

    def volume_mute(self) -> str:
        if _press_media_key(VK_VOLUME_MUTE):
            return "Volume alternado para mudo, Senhor."
        return "Controle de volume indisponível neste sistema."

    # ==================== CONTROLE DE ANÚNCIOS ====================

    def skip_ad(self) -> str:
        """Tenta pular anúncio do YouTube simulando clique no botão 'Pular'."""
        if self.os_name != "windows":
            return "Função disponível apenas no Windows."

        try:
            import time
            # Simula Tab para focar no botão "Pular anúncio" e Enter para clicar
            # Alternativa: envia Escape para sair de fullscreen + clica no botão
            _press_key(0x09)  # Tab
            time.sleep(0.1)
            _press_key(0x0D)  # Enter
            return "Tentando pular o anúncio, Senhor."
        except Exception:
            return "Não foi possível pular o anúncio."

    # ==================== CONTROLE DE JANELAS ====================

    def minimize_all(self) -> str:
        if self.os_name == "windows":
            try:
                ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)  # Win down
                ctypes.windll.user32.keybd_event(0x44, 0, 0, 0)  # D down
                ctypes.windll.user32.keybd_event(0x44, 0, 0x0002, 0)  # D up
                ctypes.windll.user32.keybd_event(0x5B, 0, 0x0002, 0)  # Win up
                return "Janelas minimizadas, Senhor."
            except Exception:
                return "Não foi possível minimizar as janelas."
        return "Função disponível apenas no Windows."

    def close_window(self) -> str:
        if self.os_name == "windows":
            try:
                ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)  # Alt down
                ctypes.windll.user32.keybd_event(0x73, 0, 0, 0)  # F4 down
                ctypes.windll.user32.keybd_event(0x73, 0, 0x0002, 0)  # F4 up
                ctypes.windll.user32.keybd_event(0x12, 0, 0x0002, 0)  # Alt up
                return "Fechando janela ativa, Senhor."
            except Exception:
                return "Não foi possível fechar a janela."
        return "Função disponível apenas no Windows."

    # ==================== SISTEMA ====================

    def shutdown(self) -> str:
        return "Senhor, para desligar o computador, confirme o comando por segurança."

    def lock_screen(self) -> str:
        if self.os_name == "windows":
            try:
                ctypes.windll.user32.LockWorkStation()
                return "Tela bloqueada, Senhor."
            except Exception:
                return "Não foi possível bloquear a tela."
        return "Função disponível apenas no Windows."

    # ==================== SCREENSHOT ====================

    def take_screenshot(self, filename: str = "") -> str:
        """Captura a tela e salva com nome personalizado."""
        try:
            from PIL import ImageGrab

            # Diretório de screenshots
            screenshots_dir = Path.home() / "Pictures" / "SARA_Screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)

            # Nome do arquivo
            if not filename:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}"

            # Remove caracteres inválidos do nome
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            if not filename.endswith('.png'):
                filename += '.png'

            filepath = screenshots_dir / filename
            screenshot = ImageGrab.grab()
            screenshot.save(str(filepath))
            return f"Screenshot salvo como '{filename}' em {screenshots_dir}, Senhor."
        except ImportError:
            return "Módulo Pillow não instalado. Instale com: pip install Pillow"
        except Exception as e:
            return f"Erro ao capturar tela: {str(e)}"

    # ==================== STATUS DO SISTEMA ====================

    def get_system_status(self) -> str:
        """Retorna status do sistema: CPU, RAM, bateria."""
        try:
            import psutil

            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.5)

            # RAM
            mem = psutil.virtual_memory()
            ram_used_gb = mem.used / (1024 ** 3)
            ram_total_gb = mem.total / (1024 ** 3)
            ram_percent = mem.percent

            # Bateria
            battery = psutil.sensors_battery()
            if battery:
                bat_percent = battery.percent
                plugged = "carregando" if battery.power_plugged else "na bateria"
                bat_info = f"Bateria em {bat_percent:.0f}%, {plugged}."
            else:
                bat_info = "Sem bateria detectada, provavelmente desktop."

            return (
                f"Senhor, status do sistema: "
                f"CPU em {cpu_percent:.0f}% de uso. "
                f"RAM usando {ram_used_gb:.1f} de {ram_total_gb:.1f} GB, {ram_percent:.0f}% ocupado. "
                f"{bat_info}"
            )
        except ImportError:
            return "Módulo psutil não instalado. Instale com: pip install psutil"
        except Exception as e:
            return f"Erro ao verificar sistema: {str(e)}"

    # ==================== WIKIPEDIA ====================

    def search_wikipedia(self, query: str) -> str:
        """Pesquisa na Wikipedia e retorna um resumo."""
        try:
            import urllib.request
            import urllib.parse
            import json

            encoded = urllib.parse.quote(query)
            headers = {"User-Agent": "SARA-Assistant/1.0"}
            title = query
            extract = ""

            # Tenta acesso direto à página
            try:
                url = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{encoded}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode('utf-8'))

                if data.get("type") == "disambiguation":
                    return f"Senhor, '{query}' tem vários significados na Wikipedia. Pode ser mais específico?"

                title = data.get("title", query)
                extract = data.get("extract", "")
            except urllib.error.HTTPError:
                pass  # Não encontrou direto, tenta busca

            # Fallback: busca por opensearch API
            if not extract:
                search_url = (
                    f"https://pt.wikipedia.org/w/api.php?"
                    f"action=opensearch&search={encoded}&limit=1&format=json"
                )
                req2 = urllib.request.Request(search_url, headers=headers)
                with urllib.request.urlopen(req2, timeout=8) as resp2:
                    search_data = json.loads(resp2.read().decode('utf-8'))

                if len(search_data) > 1 and search_data[1]:
                    found_title = urllib.parse.quote(search_data[1][0])
                    url2 = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{found_title}"
                    req3 = urllib.request.Request(url2, headers=headers)
                    with urllib.request.urlopen(req3, timeout=8) as resp3:
                        data2 = json.loads(resp3.read().decode('utf-8'))
                    title = data2.get("title", query)
                    extract = data2.get("extract", "")

            if extract:
                # Limita o tamanho para resposta por voz
                if len(extract) > 500:
                    cut = extract[:500]
                    last_dot = cut.rfind('.')
                    if last_dot > 200:
                        extract = cut[:last_dot + 1]
                    else:
                        extract = cut + "..."

                return f"Segundo a Wikipedia sobre {title}: {extract}"
            else:
                return f"Senhor, não encontrei informações sobre '{query}' na Wikipedia."

        except Exception as e:
            return f"Erro ao buscar na Wikipedia: {str(e)}"

    # ==================== LOCALIZAÇÃO / GOOGLE MAPS ====================

    def show_location(self, place: str) -> str:
        """Abre localização no Google Maps."""
        try:
            import urllib.parse
            encoded = urllib.parse.quote(place)
            url = f"https://www.google.com/maps/search/{encoded}"
            webbrowser.open(url)
            return f"Mostrando '{place}' no Google Maps, Senhor."
        except Exception as e:
            return f"Erro ao abrir localização: {str(e)}"

    def show_distance(self, origin: str, destination: str) -> str:
        """Mostra distância entre dois locais no Google Maps."""
        try:
            import urllib.parse
            origin_enc = urllib.parse.quote(origin)
            dest_enc = urllib.parse.quote(destination)
            url = f"https://www.google.com/maps/dir/{origin_enc}/{dest_enc}"
            webbrowser.open(url)
            return f"Mostrando rota de '{origin}' até '{destination}' no Google Maps, Senhor."
        except Exception as e:
            return f"Erro ao calcular distância: {str(e)}"

    # ==================== CALCULADORA ====================

    def calculate(self, expression: str) -> str:
        """Calcula expressão matemática de forma segura."""
        try:
            # Limpa a expressão
            expr = expression.strip()

            # Converte palavras para operadores
            replacements = {
                'mais': '+', 'menos': '-', 'vezes': '*', 'multiplicado por': '*',
                'dividido por': '/', 'sobre': '/', 'ao quadrado': '**2',
                'ao cubo': '**3', 'elevado a': '**', 'raiz quadrada de': 'sqrt(',
                'raiz de': 'sqrt(', 'por cento de': '*0.01*', 'porcentagem de': '*0.01*',
                'x': '*', 'X': '*',
                'pi': str(math.pi), 'π': str(math.pi),
            }
            for word, op in replacements.items():
                expr = expr.replace(word, op)

            # Conta parênteses e fecha se necessário
            open_p = expr.count('(')
            close_p = expr.count(')')
            if open_p > close_p:
                expr += ')' * (open_p - close_p)

            # Apenas permite caracteres seguros
            allowed = set('0123456789+-*/.() ,')
            safe_funcs = {'sqrt', 'sin', 'cos', 'tan', 'log', 'abs', 'pow', 'round'}
            test_expr = expr
            for func in safe_funcs:
                test_expr = test_expr.replace(func, '')

            if not all(c in allowed for c in test_expr):
                return "Senhor, expressão contém caracteres inválidos."

            # Namespace seguro com funções matemáticas
            safe_dict = {
                'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
                'tan': math.tan, 'log': math.log, 'abs': abs,
                'pow': pow, 'round': round, 'pi': math.pi, 'e': math.e,
                '__builtins__': {},
            }

            result = eval(expr, safe_dict)

            # Formata o resultado
            if isinstance(result, float):
                if result == int(result) and abs(result) < 1e15:
                    result = int(result)
                else:
                    result = round(result, 6)

            return f"Senhor, o resultado é {result}."
        except ZeroDivisionError:
            return "Senhor, divisão por zero não é permitida."
        except Exception as e:
            return f"Não consegui calcular essa expressão. Verifique se está correta."

    # ==================== BLOCO DE NOTAS ====================

    def save_note(self, content: str) -> str:
        """Salva uma anotação no bloco de notas."""
        try:
            notes_dir = Path.home() / "Documents" / "SARA_Notas"
            notes_dir.mkdir(parents=True, exist_ok=True)

            notes_file = notes_dir / "notas.txt"

            timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            entry = f"\n[{timestamp}] {content}\n"

            with open(notes_file, 'a', encoding='utf-8') as f:
                f.write(entry)

            return f"Anotação salva, Senhor. Arquivo em {notes_file}"
        except Exception as e:
            return f"Erro ao salvar anotação: {str(e)}"

    def open_notes(self) -> str:
        """Abre o arquivo de anotações no bloco de notas."""
        try:
            notes_file = Path.home() / "Documents" / "SARA_Notas" / "notas.txt"

            if not notes_file.exists():
                notes_file.parent.mkdir(parents=True, exist_ok=True)
                notes_file.write_text("=== Notas SARA ===\n", encoding='utf-8')

            if self.os_name == "windows":
                os.startfile(str(notes_file))
            else:
                subprocess.Popen(['xdg-open', str(notes_file)])

            return "Abrindo suas anotações, Senhor."
        except Exception as e:
            return f"Erro ao abrir notas: {str(e)}"

    def read_notes(self) -> str:
        """Lê as últimas anotações."""
        try:
            notes_file = Path.home() / "Documents" / "SARA_Notas" / "notas.txt"

            if not notes_file.exists():
                return "Senhor, ainda não há anotações salvas."

            lines = notes_file.read_text(encoding='utf-8').strip().split('\n')
            # Pega as últimas 5 entradas
            entries = [l for l in lines if l.startswith('[')]
            if not entries:
                return "Senhor, ainda não há anotações salvas."

            recent = entries[-5:]
            notes_text = ". ".join(recent)
            return f"Suas últimas anotações: {notes_text}"
        except Exception as e:
            return f"Erro ao ler notas: {str(e)}"

    # ==================== PARSER PRINCIPAL ====================

    def parse_and_execute(self, text: str) -> Optional[str]:
        """Analisa texto e executa ação do sistema. Retorna None se não for um comando."""
        text = text.lower().strip()

        # --- Hora ---
        if any(kw in text for kw in ["que horas", "hora atual", "horas são", "que hora"]):
            return self.get_time()

        # --- Data ---
        if any(kw in text for kw in ["que dia", "data de hoje", "qual a data", "que data"]):
            return self.get_date()

        # --- Controle de mídia (detectar ANTES de "abrir") ---
        if any(kw in text for kw in [
            "pausa", "pause", "pausar", "pausa a música", "pausa a musica",
            "pausa a reprodução", "pausa a reproducao"
        ]):
            return self.media_play_pause()

        if any(kw in text for kw in [
            "play", "dá play", "da play", "despausa", "despausar",
            "continua", "continue", "retomar", "retoma",
            "volta a tocar", "continua a música", "continua a musica",
            "despausar a música", "despausar a musica",
            "tira da pausa", "tira a pausa"
        ]):
            return self.media_play_pause()

        if any(kw in text for kw in [
            "próxima", "proxima", "próxima música", "proxima musica",
            "pula música", "pula musica", "pula essa", "skip",
            "passa a música", "passa a musica", "passa essa",
            "muda a música", "muda a musica", "troca a música", "troca a musica",
            "próxima faixa", "proxima faixa", "pula pra próxima", "pula pra proxima"
        ]):
            return self.media_next()

        if any(kw in text for kw in [
            "anterior", "volta música", "volta musica",
            "música anterior", "musica anterior", "volta essa",
            "volta a música", "volta a musica", "faixa anterior",
            "música de antes", "musica de antes"
        ]):
            return self.media_previous()

        if any(kw in text for kw in [
            "para a música", "para a musica", "para de tocar",
            "parar música", "parar musica", "stop", "para tudo"
        ]):
            return self.media_stop()

        # --- Volume ---
        if any(kw in text for kw in ["aumenta volume", "aumentar volume", "volume mais alto",
                                      "sobe o volume", "mais alto", "aumenta o som", "som mais alto"]):
            return self.volume_up()

        if any(kw in text for kw in ["diminui volume", "diminuir volume", "volume mais baixo",
                                      "abaixa o volume", "mais baixo", "diminui o som", "som mais baixo"]):
            return self.volume_down()

        if any(kw in text for kw in ["mudo", "mute", "silencia", "silenciar", "tira o som"]):
            return self.volume_mute()

        # --- Pular anúncio ---
        if any(kw in text for kw in ["pula anúncio", "pula anuncio", "pular anúncio", "pular anuncio",
                                      "skip ad", "pula o anúncio", "pula o anuncio"]):
            return self.skip_ad()

        # --- Controle de janelas ---
        if any(kw in text for kw in ["minimiza tudo", "minimizar tudo", "minimiza as janelas",
                                      "esconde tudo", "mostrar desktop", "mostra desktop",
                                      "mostra a área de trabalho", "mostra a area de trabalho"]):
            return self.minimize_all()

        if any(kw in text for kw in ["fecha a janela", "fechar janela", "fecha isso",
                                      "fecha essa janela", "fechar isso"]):
            return self.close_window()

        # --- Bloquear tela ---
        if any(kw in text for kw in ["bloqueia a tela", "bloquear tela", "bloqueia o pc",
                                      "bloquear computador", "trava a tela", "travar tela"]):
            return self.lock_screen()

        # --- Screenshot ---
        screenshot_patterns = [
            r"(?:tir[aei]r?|faz(?:er)?|captur[aei]r?)\s+(?:um(?:a)?\s+)?(?:screenshot|captura|print|foto)\s*(?:da\s+tela\s*)?(?:com\s+(?:o\s+)?nome\s+(?:de\s+)?)(.+)$",
            r"(?:tir[aei]r?|faz(?:er)?|captur[aei]r?)\s+(?:um(?:a)?\s+)?(?:screenshot|captura|print|foto)\s*(?:da\s+tela)?",
            r"screenshot\s+(.+)$",
            r"screenshot$",
            r"print\s+(?:da\s+)?tela\s*(.*)$",
            r"captura\s+(?:de\s+)?tela\s+(?:com\s+(?:o\s+)?nome\s+(?:de\s+)?)(.+)$",
            r"captura\s+(?:de\s+)?tela$",
        ]
        for pattern in screenshot_patterns:
            match = re.search(pattern, text)
            if match:
                filename = match.group(1).strip() if match.lastindex and match.group(1) else ""
                return self.take_screenshot(filename)

        # --- Status do sistema ---
        if any(kw in text for kw in [
            "status do sistema", "status do pc", "status do computador",
            "como está o sistema", "como esta o sistema",
            "uso de cpu", "uso de ram", "uso de memória", "uso de memoria",
            "quanta memória", "quanta memoria", "quanto de ram",
            "bateria", "nível de bateria", "nivel de bateria",
            "saúde do sistema", "saude do sistema",
            "como está o pc", "como esta o pc",
            "como está o computador", "como esta o computador",
            "diagnóstico", "diagnostico",
        ]):
            return self.get_system_status()

        # --- Wikipedia ---
        wiki_patterns = [
            r"(?:pesquis|busc|procur)[aei]r?\s+(.+?)\s+(?:na|no)\s+wikip[eé]dia",
            r"(?:o\s+que\s+[eé]|quem\s+[eé]|quem\s+foi)\s+(.+?)\s+(?:na|no)\s+wikip[eé]dia",
            r"wikip[eé]dia\s+(?:sobre\s+)?(.+)",
        ]
        for pattern in wiki_patterns:
            match = re.search(pattern, text)
            if match:
                query = match.group(1).strip()
                if query:
                    return self.search_wikipedia(query)

        # --- Calculadora ---
        # Expressões diretas com "raiz quadrada de X"
        raiz_match = re.search(r"raiz\s+(?:quadrada\s+)?(?:de\s+)?(\d+[\d\.\s]*)", text)
        if raiz_match:
            return self.calculate(f"raiz quadrada de {raiz_match.group(1).strip()}")

        calc_patterns = [
            r"(?:calcul[aei]r?|quant[oa]\s+[eé])\s+(.+)",
            r"(?:quanto\s+(?:que\s+)?(?:dá|da|é|e))\s+(.+)",
            r"(?:resolve(?:r)?)\s+(.+)",
            r"(?:resultado\s+de)\s+(.+)",
        ]
        for pattern in calc_patterns:
            match = re.search(pattern, text)
            if match:
                expr = match.group(1).strip()
                # Verifica se parece uma expressão matemática
                if any(op in expr for op in ['+', '-', '*', '/', 'mais', 'menos', 'vezes',
                                              'dividido', 'raiz', 'elevado', 'ao quadrado',
                                              'ao cubo', 'por cento']):
                    return self.calculate(expr)
                # Se contém apenas números e operadores simples
                if re.match(r'^[\d\s\+\-\*\/\.\(\)x]+$', expr):
                    return self.calculate(expr)

        # --- Ler/Abrir Anotações (antes de salvar para não conflitar) ---
        if any(kw in text for kw in [
            "lê as notas", "le as notas", "ler notas", "ler anotações", "ler anotacoes",
            "leia as notas", "leia as anotações", "quais são minhas notas",
            "quais sao minhas notas", "últimas notas", "ultimas notas",
        ]):
            return self.read_notes()

        if any(kw in text for kw in [
            "abre as notas", "abrir notas", "abrir anotações", "abrir anotacoes",
            "mostra as notas", "mostrar notas", "ver notas", "ver anotações",
            "abre o bloco de notas das anotações", "minhas notas", "minhas anotações",
        ]):
            return self.open_notes()

        # --- Salvar Anotações ---
        note_patterns = [
            r"(?:anot[aei]r?|salv[aei]r?\s+(?:uma?\s+)?nota|not[aei]r?)\s*(?:que\s+|isso\s*[:\s]\s*)?(.+)",
            r"(?:guard[aei]r?|lembr[aei]r?\s+(?:de\s+)?que)\s+(.+)",
            r"(?:escrev[aei]r?|adicionar?)\s+(?:no\s+)?(?:bloco\s+de\s+notas|notas?)\s*[:\s]\s*(.+)",
        ]
        for pattern in note_patterns:
            match = re.search(pattern, text)
            if match:
                content = match.group(1).strip()
                if content:
                    return self.save_note(content)

        # --- Localização / Google Maps ---
        location_patterns = [
            r"(?:onde\s+fica|localiz[aei]r?|mostr[aei]r?\s+(?:no\s+mapa\s+)?(?:a\s+localiza[cç][aã]o\s+de)?)\s+(.+?)(?:\s+no\s+mapa)?$",
            r"(?:mostr[aei]r?|abr[aei]r?)\s+(.+?)\s+no\s+(?:google\s+)?maps?",
            r"(?:como\s+cheg[aeo]r?\s+(?:em|a|ao|na|no))\s+(.+)",
        ]
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                place = match.group(1).strip()
                if place and len(place) > 1:
                    return self.show_location(place)

        # Distância entre dois locais
        distance_patterns = [
            r"dist[aâ]ncia\s+(?:entre|de)\s+(.+?)\s+(?:e|at[eé]|para|a)\s+(.+)",
            r"(?:quanto\s+(?:tem|falta)\s+(?:de|entre))\s+(.+?)\s+(?:e|at[eé]|para|a)\s+(.+)",
            r"rota\s+(?:de|entre)\s+(.+?)\s+(?:e|at[eé]|para|a)\s+(.+)",
        ]
        for pattern in distance_patterns:
            match = re.search(pattern, text)
            if match:
                origin = match.group(1).strip()
                dest = match.group(2).strip()
                if origin and dest:
                    return self.show_distance(origin, dest)

        # --- Pesquisa no YouTube ---
        yt_search_patterns = [
            r"pesquis[aei]r?\s+(.+?)\s+no\s+youtube",
            r"buscar?\s+(.+?)\s+no\s+youtube",
            r"procurar?\s+(.+?)\s+no\s+youtube",
        ]
        for pattern in yt_search_patterns:
            match = re.search(pattern, text)
            if match:
                query = match.group(1).strip()
                return self.web_search(query, engine="youtube")

        # --- Música no Spotify ---
        spotify_patterns = [
            r"toc[aei]r?\s+(.+?)\s+no\s+spotify",
            r"coloc[aei]r?\s+(.+?)\s+no\s+spotify",
            r"reproduz[aei]r?\s+(.+?)\s+no\s+spotify",
        ]
        for pattern in spotify_patterns:
            match = re.search(pattern, text)
            if match:
                query = match.group(1).strip()
                return self.play_music(query, platform_name="spotify")

        # --- Música (genérico → YouTube) ---
        music_patterns = [
            r"toc[aei]r?\s+(?:a\s+)?(?:música\s+|musica\s+)?(.+)",
            r"coloc[aei]r?\s+(?:a\s+)?(?:música\s+|musica\s+)?(.+)",
            r"reproduz[aei]r?\s+(.+)",
            r"bota(?:r)?\s+(?:a\s+)?(?:música\s+|musica\s+)?(.+)",
        ]
        for pattern in music_patterns:
            match = re.search(pattern, text)
            if match:
                query = match.group(1).strip()
                if query:
                    return self.play_music(query)

        # --- Abrir aplicativos/sites ---
        open_patterns = [
            r"abr[aei]r?\s+(?:o\s+|a\s+)?(.+)",
            r"abre\s+(?:o\s+|a\s+)?(.+)",
            r"execut[aei]r?\s+(?:o\s+|a\s+)?(.+)",
            r"iniciar?\s+(?:o\s+|a\s+)?(.+)",
            r"liga(?:r)?\s+(?:o\s+|a\s+)?(.+)",
        ]
        for pattern in open_patterns:
            match = re.search(pattern, text)
            if match:
                app = match.group(1).strip()
                if app:
                    return self.open_app(app)

        # --- Pesquisa na web (genérico → Google) ---
        search_patterns = [
            r"pesquis[aei]r?\s+(?:sobre\s+)?(.+)",
            r"buscar?\s+(?:sobre\s+)?(.+)",
            r"procurar?\s+(?:sobre\s+)?(.+)",
        ]
        for pattern in search_patterns:
            match = re.search(pattern, text)
            if match:
                query = match.group(1).strip()
                if query:
                    return self.web_search(query)

        # Nenhuma ação detectada
        return None

    def list_available_apps(self) -> list:
        """Lista apps disponíveis para abrir."""
        apps = list(self.app_aliases.get(self.os_name, {}).keys())
        sites = list(self.site_aliases.keys())
        return apps + sites


# Função auxiliar para pressionar teclas genéricas
def _press_key(vk_code):
    """Pressiona e solta uma tecla genérica no Windows."""
    if platform.system().lower() != "windows":
        return
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, 0x0002, 0)


def _mouse_click(x, y, double=False):
    """Move o mouse e clica em coordenadas absolutas (Windows)."""
    import time as _t
    ctypes.windll.user32.SetCursorPos(x, y)
    _t.sleep(0.05)
    # Left button down + up
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
    if double:
        _t.sleep(0.05)
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)


def _find_spotify_window():
    """Encontra a janela do Spotify pelo título (parcial)."""
    from ctypes import wintypes

    result = [None]

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _enum_cb(hwnd, _):
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.lower()
            if "spotify" in title and ctypes.windll.user32.IsWindowVisible(hwnd):
                result[0] = hwnd
                return False
        return True

    ctypes.windll.user32.EnumWindows(_enum_cb, 0)
    return result[0]


def _get_window_rect(hwnd):
    """Retorna (left, top, width, height) da janela."""
    from ctypes import wintypes
    rect = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def _spotify_click_play(wait_seconds=3.5):
    """Espera o Spotify carregar a busca e clica no primeiro resultado da seção 'Músicas'.

    Layout do Spotify após busca:
    +--------------------------------------+
    |  [barra de busca]                    |
    |                                      |
    |  Melhor resultado  |  Músicas        |
    |  +----------+      |  Song 1  <--    | double-click aqui
    |  |  Capa     |      |  Song 2        |
    |  |          >|      |  Song 3        |
    |  +----------+      |  Song 4        |
    |                                      |
    |  Artistas                            |
    +--------------------------------------+

    A primeira música em 'Músicas' esta em ~58% da largura, ~32% da altura.
    Double-click nela inicia reproducao imediatamente.
    """
    import time as _t
    _t.sleep(wait_seconds)

    # Tenta encontrar a janela do Spotify (com retry)
    hwnd = None
    for attempt in range(5):
        hwnd = _find_spotify_window()
        if hwnd:
            break
        _t.sleep(0.5)

    if not hwnd:
        print("[SARA] Janela do Spotify nao encontrada.")
        return

    # Traz o Spotify para frente
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    _t.sleep(0.5)

    x, y, w, h = _get_window_rect(hwnd)

    # Posicao da primeira musica na secao "Musicas" (lado direito)
    click_x = x + int(w * 0.58)
    click_y = y + int(h * 0.32)

    # Double-click para tocar a musica
    _mouse_click(click_x, click_y, double=True)
    print(f"[SARA] Clique no Spotify em ({click_x}, {click_y}) janela=({x},{y},{w},{h})")

    # Se o primeiro clique nao funcionar, tenta novamente apos um momento
    _t.sleep(1.0)
    hwnd2 = _find_spotify_window()
    if hwnd2:
        ctypes.windll.user32.SetForegroundWindow(hwnd2)
        _t.sleep(0.3)
        x2, y2, w2, h2 = _get_window_rect(hwnd2)
        click_x2 = x2 + int(w2 * 0.58)
        click_y2 = y2 + int(h2 * 0.32)
        # Segundo double-click de confirmacao
        _mouse_click(click_x2, click_y2, double=True)
        print(f"[SARA] Segundo clique no Spotify em ({click_x2}, {click_y2})")


def _spotify_search_when_open(hwnd, query):
    """Busca no Spotify quando já está aberto usando Ctrl+L + digitar query.

    Quando o Spotify já está rodando, os.startfile(spotify:search:...)
    pode não funcionar. Alternativa: foca a barra de busca via Ctrl+L,
    limpa, digita a query, e pressiona Enter.
    """
    import time as _t

    # Traz para frente
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    _t.sleep(0.5)

    # Ctrl+L = foca a barra de busca no Spotify
    ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
    ctypes.windll.user32.keybd_event(0x4C, 0, 0, 0)  # L down
    ctypes.windll.user32.keybd_event(0x4C, 0, 0x0002, 0)  # L up
    ctypes.windll.user32.keybd_event(0x11, 0, 0x0002, 0)  # Ctrl up
    _t.sleep(0.3)

    # Ctrl+A para selecionar texto existente na barra
    ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
    ctypes.windll.user32.keybd_event(0x41, 0, 0, 0)  # A down
    ctypes.windll.user32.keybd_event(0x41, 0, 0x0002, 0)  # A up
    ctypes.windll.user32.keybd_event(0x11, 0, 0x0002, 0)  # Ctrl up
    _t.sleep(0.1)

    # Digita a query usando SendInput (suporta unicode)
    for char in query:
        # Usa WM_CHAR via SendInput para cada caractere (unicode-safe)
        vk = ctypes.windll.user32.VkKeyScanW(ord(char))
        if vk == -1:
            # Caractere especial — usa unicode input
            _type_unicode_char(char)
        else:
            shift = (vk >> 8) & 0x01
            vk_code = vk & 0xFF
            if shift:
                ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)  # Shift down
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, 0x0002, 0)
            if shift:
                ctypes.windll.user32.keybd_event(0x10, 0, 0x0002, 0)  # Shift up
            _t.sleep(0.02)

    _t.sleep(0.3)

    # Enter para buscar
    ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)  # Enter down
    ctypes.windll.user32.keybd_event(0x0D, 0, 0x0002, 0)  # Enter up

    # Espera carregar e clica no resultado
    _spotify_click_play(2.5)


def _type_unicode_char(char):
    """Digita um caractere unicode via SendInput KEYEVENTF_UNICODE."""
    import ctypes.wintypes

    INPUT_KEYBOARD = 1
    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_KEYUP = 0x0002

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.wintypes.WORD),
            ("wScan", ctypes.wintypes.WORD),
            ("dwFlags", ctypes.wintypes.DWORD),
            ("time", ctypes.wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]
        _fields_ = [
            ("type", ctypes.wintypes.DWORD),
            ("_input", _INPUT),
        ]

    code = ord(char)

    # Key down
    inp_down = INPUT()
    inp_down.type = INPUT_KEYBOARD
    inp_down._input.ki.wVk = 0
    inp_down._input.ki.wScan = code
    inp_down._input.ki.dwFlags = KEYEVENTF_UNICODE
    inp_down._input.ki.time = 0
    inp_down._input.ki.dwExtraInfo = None

    # Key up
    inp_up = INPUT()
    inp_up.type = INPUT_KEYBOARD
    inp_up._input.ki.wVk = 0
    inp_up._input.ki.wScan = code
    inp_up._input.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    inp_up._input.ki.time = 0
    inp_up._input.ki.dwExtraInfo = None

    inputs = (INPUT * 2)(inp_down, inp_up)
    ctypes.windll.user32.SendInput(2, inputs, ctypes.sizeof(INPUT))


def _find_browser_window():
    """Encontra a janela do navegador (Chrome, Edge, Firefox) com YouTube aberto."""
    result = [None]

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _enum_cb(hwnd, _):
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.lower()
            # Procura janela de navegador com YouTube no titulo
            if "youtube" in title and ctypes.windll.user32.IsWindowVisible(hwnd):
                result[0] = hwnd
                return False
        return True

    ctypes.windll.user32.EnumWindows(_enum_cb, 0)
    return result[0]


def _youtube_click_first_result():
    """Espera o YouTube carregar e clica no primeiro video dos resultados.

    Layout do YouTube apos busca:
    +--------------------------------------+
    |  [logo] [barra de busca]   [perfil]  |
    |  All | Videos | Shorts | ...         |
    |                                      |
    |  [Thumbnail]  Titulo do video        | <-- clique aqui
    |               Canal - 1M views       |
    |                                      |
    |  [Thumbnail]  Segundo video          |
    +--------------------------------------+

    O primeiro video esta em ~35% da largura, ~38% da altura.
    """
    import time as _t
    _t.sleep(3.5)  # Espera a pagina carregar

    # Tenta encontrar a janela do navegador com YouTube
    hwnd = None
    for _ in range(8):
        hwnd = _find_browser_window()
        if hwnd:
            break
        _t.sleep(0.5)

    if not hwnd:
        print("[SARA] Janela do YouTube nao encontrada no navegador.")
        return

    # Traz o navegador para frente
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    _t.sleep(0.5)

    x, y, w, h = _get_window_rect(hwnd)

    # Posicao do primeiro resultado (thumbnail do primeiro video)
    # O thumbnail fica no lado esquerdo, centralizado verticalmente no primeiro card
    click_x = x + int(w * 0.35)
    click_y = y + int(h * 0.38)

    # Clique simples no primeiro video
    _mouse_click(click_x, click_y)
    print(f"[SARA] Clique no YouTube em ({click_x}, {click_y}) janela=({x},{y},{w},{h})")


if __name__ == "__main__":
    print("Testando System Actions...")

    actions = SystemActions()
    print(f"Sistema: {actions.os_name}")
    print(f"Apps/sites disponíveis: {actions.list_available_apps()}")

    print(f"\n{actions.get_time()}")
    print(actions.get_date())

    test_commands = [
        "que horas são",
        "abre o youtube",
        "pesquisa python no youtube",
        "toca bohemian rhapsody",
        "toca imagine dragons no spotify",
        "pausa",
        "próxima música",
        "aumenta volume",
        "minimiza tudo",
        "como está o tempo hoje",  # Deve retornar None (vai pra IA)
    ]

    for cmd in test_commands:
        result = actions.parse_and_execute(cmd)
        status = result if result else "[IA]"
        print(f"  '{cmd}' -> {status}")
