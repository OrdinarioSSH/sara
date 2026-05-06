"""
Interface Gráfica do Pet Assistant - Versão Compacta
Pet flutuante no canto da tela (overlay)
"""
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
import threading
import time
from typing import Optional, Callable
import math


class FloatingPet(ctk.CTkToplevel):
    """Pet flutuante que fica no canto da tela."""
    
    def __init__(self, 
                 on_message_callback: Optional[Callable[[str], None]] = None,
                 on_voice_callback: Optional[Callable[[], None]] = None,
                 size: int = 120):
        
        # Cria janela root escondida
        self.root = ctk.CTk()
        self.root.withdraw()  # Esconde a janela principal
        
        super().__init__(self.root)
        
        self.size = size
        self.color = "#7C3AED"  # Roxo
        self.mood = "neutro"
        
        # Callbacks
        self.on_message_callback = on_message_callback
        self.on_voice_callback = on_voice_callback
        
        # Estados de animação
        self._bounce_offset = 0
        self._blink_state = False
        self._is_talking = False
        self._animation_running = True
        self._chat_visible = False
        
        # Configura janela flutuante
        self._setup_window()
        self._setup_pet()
        self._setup_chat_popup()
        
        # Inicia animação
        self._start_animation()
        
        # Posiciona no canto inferior direito
        self._position_bottom_right()
    
    def _setup_window(self):
        """Configura janela sem bordas."""
        self.title("")
        self.overrideredirect(True)  # Remove bordas
        self.attributes("-topmost", True)  # Sempre no topo
        
        # Cor de fundo escura (sem transparência)
        self.bg_color = "#1a1a2e"
        
        # Tamanho da janela
        window_size = self.size + 20
        self.geometry(f"{window_size}x{window_size}")
        
        # Permite arrastar
        self.bind("<Button-1>", self._start_drag)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<Double-Button-1>", self._toggle_chat)
        self.bind("<Button-3>", self._show_menu)  # Clique direito
    
    def _setup_pet(self):
        """Cria o canvas com o pet."""
        self.canvas = tk.Canvas(
            self,
            width=self.size,
            height=self.size,
            bg=self.bg_color,
            highlightthickness=0
        )
        self.canvas.pack(expand=True)
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<Double-Button-1>", self._toggle_chat)
        self.canvas.bind("<Button-3>", self._show_menu)
        
        # Desenha pet inicial
        self._draw_pet()
    
    def _draw_pet(self):
        """Desenha a cabeça do pet (círculo)."""
        self.canvas.delete("all")
        
        # Fundo
        self.canvas.create_rectangle(
            0, 0, self.size, self.size,
            fill=self.bg_color, outline=""
        )
        
        padding = 5
        bounce = self._bounce_offset
        
        # Cabeça (círculo)
        self.canvas.create_oval(
            padding, padding + bounce,
            self.size - padding, self.size - padding + bounce,
            fill=self.color,
            outline=""
        )
        
        # Olhos
        eye_size = self.size // 10
        eye_y = self.size // 3 + bounce
        left_eye_x = self.size // 3
        right_eye_x = 2 * self.size // 3
        
        if self._blink_state:
            # Olhos fechados
            self.canvas.create_line(
                left_eye_x - eye_size, eye_y,
                left_eye_x + eye_size, eye_y,
                fill="white", width=3
            )
            self.canvas.create_line(
                right_eye_x - eye_size, eye_y,
                right_eye_x + eye_size, eye_y,
                fill="white", width=3
            )
        else:
            # Olhos abertos
            self.canvas.create_oval(
                left_eye_x - eye_size, eye_y - eye_size,
                left_eye_x + eye_size, eye_y + eye_size,
                fill="white", outline=""
            )
            self.canvas.create_oval(
                right_eye_x - eye_size, eye_y - eye_size,
                right_eye_x + eye_size, eye_y + eye_size,
                fill="white", outline=""
            )
            
            # Pupilas
            pupil_size = eye_size // 2
            self.canvas.create_oval(
                left_eye_x - pupil_size, eye_y - pupil_size,
                left_eye_x + pupil_size, eye_y + pupil_size,
                fill="black", outline=""
            )
            self.canvas.create_oval(
                right_eye_x - pupil_size, eye_y - pupil_size,
                right_eye_x + pupil_size, eye_y + pupil_size,
                fill="black", outline=""
            )
        
        # Boca
        mouth_y = 2 * self.size // 3 + bounce
        mouth_width = self.size // 5
        center_x = self.size // 2
        
        if self._is_talking:
            # Boca aberta
            self.canvas.create_oval(
                center_x - mouth_width//2, mouth_y - 5,
                center_x + mouth_width//2, mouth_y + 12,
                fill="white", outline=""
            )
        elif self.mood == "feliz" or self.mood == "animado":
            # Sorriso
            self.canvas.create_arc(
                center_x - mouth_width, mouth_y - mouth_width//2,
                center_x + mouth_width, mouth_y + mouth_width,
                start=200, extent=140,
                style="arc", outline="white", width=3
            )
        elif self.mood == "triste":
            # Triste
            self.canvas.create_arc(
                center_x - mouth_width, mouth_y,
                center_x + mouth_width, mouth_y + mouth_width,
                start=20, extent=140,
                style="arc", outline="white", width=3
            )
        else:
            # Neutro
            self.canvas.create_arc(
                center_x - mouth_width//2, mouth_y - 3,
                center_x + mouth_width//2, mouth_y + 8,
                start=210, extent=120,
                style="arc", outline="white", width=2
            )
    
    def _setup_chat_popup(self):
        """Cria popup de chat."""
        self.chat_window = None
    
    def _toggle_chat(self, event=None):
        """Abre/fecha janela de chat."""
        if self._chat_visible and self.chat_window:
            self.chat_window.destroy()
            self.chat_window = None
            self._chat_visible = False
        else:
            self._show_chat()
    
    def _show_chat(self):
        """Mostra janela de chat."""
        self._chat_visible = True
        self._pending_image = None  # Imagem pendente para enviar
        
        self.chat_window = ctk.CTkToplevel(self)
        self.chat_window.title("💬 Buddy")
        self.chat_window.geometry("400x450")
        self.chat_window.attributes("-topmost", True)
        
        # Posiciona ao lado do pet
        pet_x = self.winfo_x()
        pet_y = self.winfo_y()
        self.chat_window.geometry(f"+{pet_x - 410}+{pet_y - 350}")
        
        # Frame principal
        main_frame = ctk.CTkFrame(self.chat_window)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Label de imagem anexada
        self.image_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#10B981"
        )
        self.image_label.pack(fill="x", padx=5)
        
        # Área de chat
        self.chat_display = ctk.CTkTextbox(
            main_frame,
            wrap="word",
            font=ctk.CTkFont(size=13),
            state="disabled"
        )
        self.chat_display.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Frame de entrada
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="x", padx=5, pady=5)
        
        # Botão de imagem
        self.image_btn = ctk.CTkButton(
            input_frame,
            text="📷",
            width=40,
            command=self._on_image_click
        )
        self.image_btn.pack(side="left", padx=(0, 5))
        
        # Botão de voz
        self.voice_btn = ctk.CTkButton(
            input_frame,
            text="🎤",
            width=40,
            command=self._on_voice_click
        )
        self.voice_btn.pack(side="left", padx=(0, 5))
        
        # Campo de texto
        self.input_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Digite...",
            font=ctk.CTkFont(size=13)
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.input_entry.bind("<Return>", self._on_send)
        
        # Botão enviar
        send_btn = ctk.CTkButton(
            input_frame,
            text="➤",
            width=40,
            command=self._on_send
        )
        send_btn.pack(side="right")
        
        # Foca no input
        self.input_entry.focus()
        
        # Callback quando fechar
        self.chat_window.protocol("WM_DELETE_WINDOW", self._toggle_chat)
    
    def _on_image_click(self):
        """Abre diálogo para selecionar imagem."""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title="Selecionar imagem",
            filetypes=[
                ("Imagens", "*.png *.jpg *.jpeg *.gif *.webp *.bmp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("Todos", "*.*")
            ]
        )
        
        if file_path:
            self._pending_image = file_path
            # Mostra nome do arquivo
            file_name = file_path.split("/")[-1].split("\\")[-1]
            if len(file_name) > 30:
                file_name = file_name[:27] + "..."
            self.image_label.configure(text=f"📎 {file_name} (clique ➤ para enviar)")
            self.image_btn.configure(text="✅")
    
    def _clear_pending_image(self):
        """Limpa imagem pendente."""
        self._pending_image = None
        if hasattr(self, 'image_label'):
            self.image_label.configure(text="")
        if hasattr(self, 'image_btn'):
            self.image_btn.configure(text="📷")
    
    def _on_send(self, event=None):
        """Envia mensagem (com ou sem imagem)."""
        if not self.chat_window:
            return
            
        message = self.input_entry.get().strip()
        image_path = getattr(self, '_pending_image', None)
        
        if message or image_path:
            self.input_entry.delete(0, "end")
            
            # Mostra mensagem do usuário
            display_msg = message if message else "(imagem enviada)"
            if image_path:
                display_msg = f"📷 {display_msg}"
            self.add_message(display_msg, is_user=True)
            
            # Limpa imagem pendente
            self._clear_pending_image()
            
            if self.on_message_callback:
                threading.Thread(
                    target=self.on_message_callback,
                    args=(message, image_path),
                    daemon=True
                ).start()
    
    def _on_voice_click(self):
        """Ativa reconhecimento de voz."""
        if self.on_voice_callback:
            self.voice_btn.configure(state="disabled", text="...")
            threading.Thread(target=self._voice_listen, daemon=True).start()
    
    def _voice_listen(self):
        """Executa callback de voz."""
        if self.on_voice_callback:
            self.on_voice_callback()
        self.after(0, lambda: self.voice_btn.configure(state="normal", text="🎤"))
    
    def add_message(self, message: str, is_user: bool = True):
        """Adiciona mensagem ao chat."""
        if not self.chat_window or not hasattr(self, 'chat_display'):
            return
            
        self.chat_display.configure(state="normal")
        prefix = "Você: " if is_user else "Buddy: "
        self.chat_display.insert("end", f"\n{prefix}{message}\n")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")
    
    def _show_menu(self, event):
        """Menu de contexto."""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="💬 Chat", command=self._toggle_chat)
        menu.add_command(label="🎤 Falar", command=self._on_voice_click)
        menu.add_separator()
        menu.add_command(label="❌ Fechar", command=self.quit_app)
        menu.post(event.x_root, event.y_root)
    
    def _position_bottom_right(self):
        """Posiciona no canto inferior direito."""
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = screen_w - self.size - 50
        y = screen_h - self.size - 100
        self.geometry(f"+{x}+{y}")
    
    def _start_drag(self, event):
        """Inicia arraste."""
        self._drag_x = event.x
        self._drag_y = event.y
    
    def _drag(self, event):
        """Arrasta a janela."""
        x = self.winfo_x() + event.x - self._drag_x
        y = self.winfo_y() + event.y - self._drag_y
        self.geometry(f"+{x}+{y}")
    
    def _start_animation(self):
        """Inicia loop de animação."""
        self._idle_animation()
    
    def _idle_animation(self):
        """Animação idle."""
        if not self._animation_running:
            return
        
        # Bounce suave
        self._bounce_offset = int(2 * math.sin(time.time() * 2))
        
        # Piscar ocasional
        t = int(time.time())
        if t % 4 == 0 and int(time.time() * 10) % 10 < 2:
            self._blink_state = True
        else:
            self._blink_state = False
        
        self._draw_pet()
        self.after(50, self._idle_animation)
    
    def set_mood(self, mood: str, color: str):
        """Define humor e cor do pet."""
        self.mood = mood
        self.color = color
        self._draw_pet()
    
    def start_talking(self):
        """Inicia animação de fala."""
        self._is_talking = True
        self._talk_loop()
    
    def stop_talking(self):
        """Para animação de fala."""
        self._is_talking = False
    
    def _talk_loop(self):
        """Loop de animação de fala."""
        if self._is_talking:
            self._draw_pet()
            self.after(150, self._talk_loop)
    
    def quit_app(self):
        """Fecha o aplicativo."""
        self._animation_running = False
        if self.chat_window:
            self.chat_window.destroy()
        self.destroy()
        self.root.quit()
    
    def run(self):
        """Inicia o mainloop."""
        self.root.mainloop()


class PetAssistantGUI:
    """Wrapper para manter compatibilidade."""
    
    def __init__(self, on_message_callback=None, on_voice_callback=None):
        self.pet = FloatingPet(
            on_message_callback=on_message_callback,
            on_voice_callback=on_voice_callback,
            size=120
        )
    
    def mainloop(self):
        self.pet.run()
    
    def add_message(self, message: str, is_user: bool = True):
        self.pet.after(0, lambda: self.pet.add_message(message, is_user))
    
    def set_pet_mood(self, mood: str, color: str):
        self.pet.after(0, lambda: self.pet.set_mood(mood, color))
    
    def set_status(self, status: str):
        pass  # Não tem status na versão compacta
    
    def start_talking_animation(self):
        self.pet.after(0, self.pet.start_talking)
    
    def stop_talking_animation(self):
        self.pet.after(0, self.pet.stop_talking)
    
    def set_listening_mode(self, listening: bool):
        pass
    
    def after(self, ms, func):
        self.pet.after(ms, func)


if __name__ == "__main__":
    def on_message(msg):
        print(f"Mensagem: {msg}")
        time.sleep(1)
        gui.add_message(f"Recebi: {msg}", is_user=False)
    
    def on_voice():
        print("Ouvindo...")
        time.sleep(2)
        gui.add_message("Teste de voz!", is_user=True)
    
    gui = PetAssistantGUI(on_message_callback=on_message, on_voice_callback=on_voice)
    gui.mainloop()
