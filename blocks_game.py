from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Rectangle, Line
from kivy.graphics import RoundedRectangle
from config import settings
from profile1 import profile
from music_manager import music_manager
import json
from kivy.core.image import Image as CoreImage
from kivy.app import App
from ads import AD_MANAGER
from currency import currency
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
import os
from kivy.uix.image import Image
from game_modes import NormalMode, LightningMode, GostMode
from kivy.core.window import Window
import random





# Обновляем размеры и масштаб при запуске
def get_scale():
    # Используй минимальный коэффициент для пропорций
    screen_width, screen_height = Window.size
    base_width, base_height = 480, 800  # Твой эталонный размер
            
    width_scale = screen_width / base_width
    height_scale = screen_height / base_height
            
    return min(width_scale, height_scale) * 0.9  # 10% отступы

def get_dimensions():
    scale = get_scale()
    screen_width, screen_height = Window.size
    
    # Адаптивное позиционирование игрового поля по центру
    cell_size = int(17.5 * scale)
    grid_width = 10
    grid_height = 20
    
    # Центрируем игровое поле
    grid_total_width = grid_width * cell_size
    grid_total_height = grid_height * cell_size
    
    grid_x_offset = (screen_width - grid_total_width) // 2 - int(50 * scale)
    grid_y_offset = (screen_height - grid_total_height) // 2 + int(150 * scale)  # Немного вверх для баланса
    
    return {
        'scale': scale,
        'screen_width': screen_width,
        'screen_height': screen_height,
        'CELL_SIZE': cell_size,
        'GRID_WIDTH': grid_width,
        'GRID_HEIGHT': grid_height,
        'GRID_X_OFFSET': grid_x_offset,
        'GRID_Y_OFFSET': grid_y_offset
    }

SHAPES = {
    # Классические фигуры
    'I': [[1, 1, 1, 1]],
    'J': [[1, 0, 0], [1, 1, 1]],
    'L': [[0, 0, 1], [1, 1, 1]],
    'O': [[1, 1], [1, 1]],
    'S': [[0, 1, 1], [1, 1, 0]],
    'T': [[0, 1, 0], [1, 1, 1]],
    'Z': [[1, 1, 0], [0, 1, 1]],
}

COLORS = {
    'I': (0.2, 0.6, 0.8, 1),  # Синий
    'J': (0.2, 0.4, 0.8, 1),  # Темно-синий
    'L': (0.9, 0.5, 0.2, 1),  # Оранжевый
    'O': (0.9, 0.9, 0.2, 1),  # Желтый
    'S': (0.2, 0.7, 0.2, 1),  # Зеленый
    'T': (0.6, 0.2, 0.8, 1),  # Фиолетовый
    'Z': (0.8, 0.2, 0.2, 1),  # Красный
}


class FallingBlock:
    def __init__(self, rect, line):
        self.rect = rect
        self.line = line



class blocksGame(RelativeLayout):
    def __init__(self, switch_to_menu_callback, **kwargs):
        super().__init__(**kwargs)
        
        self.blocks = []
        self.falling_blocks = []
        self.update_dimensions()
        self.switch_to_menu = switch_to_menu_callback
        
        self.gost_level = 1
        self.gost_step_count = 0  # Счетчик шагов для Gost режима
        
        self.piece_spawn_time = 0
        
        # СОЗДАЕМ GRID РАНЬШЕ, чем он может быть использован
        self.grid = [[0 for _ in range(self.GRID_WIDTH)] for _ in range(self.GRID_HEIGHT)]
        
        self.paused = False
        self.score = 0
        self.game_over = False
        self.combo_multiplier = 1.0  # Множитель для комбо линий

        # СОХРАНЯЕМ ОРИГИНАЛЬНЫЙ МЕТОД REDRAW ДЛЯ ИСПОЛЬЗОВАНИЯ В РЕНДЕРИНГЕ
        self.original_redraw = self.redraw

        
        # --- вставить в __init__ класса blocksGame ---
        def _apply_app_root_background(dt=None):
            try:
                app = App.get_running_app()
                if not app or not getattr(app, 'root', None):
                    return

                
                
                base_dir = os.path.dirname(__file__)
                bg = getattr(settings, 'game_background', 'assets/fon1.png') or 'assets/fon1.png'
                bg_path = bg if os.path.isabs(bg) else os.path.join(base_dir, bg)

                if not os.path.exists(bg_path):
                    alt = os.path.join(base_dir, 'assets', os.path.basename(bg))
                    if os.path.exists(alt):
                        bg_path = alt
                    else:
                        bg_path = os.path.join(base_dir, 'assets', 'fon1.png')

                print("Applying app-root background:", bg_path, "exists:", os.path.exists(bg_path))

                tex = None
                try:
                    ci = CoreImage(bg_path)
                    tex = ci.texture
                    print("CoreImage loaded texture for app-root:", getattr(tex, 'width', None), getattr(tex, 'height', None))
                except Exception as e:
                    print("CoreImage failed for app-root bg:", e)
                    tex = None

                # создаём/обновляем Rectangle в app.root.canvas.before
                root = app.root
                if hasattr(root, '_blocks_bg_rect') and root._blocks_bg_rect:
                    rect = root._blocks_bg_rect
                    if tex:
                        rect.texture = tex
                    else:
                        rect.source = bg_path
                    rect.pos = (0, 0)
                    rect.size = root.size
                else:
                    with root.canvas.before:
                        if tex:
                            root._blocks_bg_rect = Rectangle(texture=tex, pos=(0, 0), size=root.size)
                        else:
                            root._blocks_bg_rect = Rectangle(source=bg_path, pos=(0, 0), size=root.size)

                # биндим размер, чтобы фон растягивался вместе с root
                def _on_root_resize(inst, size):
                    if hasattr(root, '_blocks_bg_rect') and root._blocks_bg_rect:
                        root._blocks_bg_rect.size = size
                        root._blocks_bg_rect.pos = (0, 0)
                root.bind(size=_on_root_resize)

            except Exception as e:
                print("Error applying app-root bg:", e)

        # планируем выполнение после того, как виджет добавлен в дерево
        Clock.schedule_once(_apply_app_root_background, 0)

        with self.canvas.before:
            Color(0.8, 0.8, 0.8, 1)
            self.game_bg = Rectangle(
                pos=(self.GRID_X_OFFSET, self.GRID_Y_OFFSET),
                size=(self.GRID_WIDTH*self.CELL_SIZE, self.GRID_HEIGHT*self.CELL_SIZE)
            )

        self.bind(size=self.update_bg, pos=self.update_bg)
        Window.bind(on_resize=self.on_window_resize)

        # Инициализация режимов и настроек
        self.mode = 'normal'
        self.is_visible = True
        self.fall_speed = 0.5
        self.hard_drop_enabled = True
        self.lock_delay = 0.5
        self.use_ghost_piece = True
        self.disable_hold = False
        self.instant_rotate = False
        
        
        # набор координат невидимых клеток (они остаются в self.grid, но не рисуются)
        self._invisible_cells = set()  # набор кортежей (x,y)
        # флаг видимости текущей падающей фигуры (True = видна)
        self.current_piece_visible = True
        # счётчик шагов для текущей падающей фигуры (для режима gost)
        self.gost_step_count = 0
        # уровень gost (1/2/3) — если не установлен извне, по умолчанию 1
        if not hasattr(self, 'gost_level'):
            self.gost_level = getattr(settings, 'gost_level', 1)
        # опции для gost — можно обновлять извне (GameMode должен их выставлять)
        if not hasattr(self, 'gost_mode_settings'):
            # дефолтные значения
            self.gost_mode_settings = {
                'steps_to_disappear': 5,
                'appear_on_lock': True,
                'lock_appear_time': 1.5,
                'show_next': True
            }
        
        
        # Регистрируем обработчик закрытия приложения
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.bind(on_stop=self.on_app_stop)
        
        # Добавляем переменные для новой анимации
        self.clear_animation_active = False
        self.clear_lines_queue = []
        self.clear_animation_step = 0
        self.clear_line_index = 0
        
        
        self.gost_mode = False        # активен ли режим gost
        self.gost_level = 1           # уровень (1, 2 или 3)
        self.steps_since_spawn = 0    # сколько шагов сделала текущая фигура
        self.piece_landed = False     # приземлилась ли текущая фигура
        self.current_piece_visible = True
        self.landed_pieces = []       # список приземлившихся фигур (для уровня 3)
        
        
        
        self.defeat_count = 0  # Считаем количество поражений в текущей сессии
        
        
        self.lock_timer = None
        self.lock_scheduled = False
        
        
        self.settings_opener = 'menu'  # По умолчанию из меню
        
        self.modes = {
            'normal': NormalMode(),
            'gost': GostMode(),
            'lightning': LightningMode()
        }
        
        
            
        # Правильное управление музыкой
        self.manage_music('stop')  # Останавливаем при инициализации
        
        if hasattr(self, 'sound') and self.sound:
            self.sound.bind(state=self.on_sound_state_change)

        # Физические элементы для анимации
        self.falling_letters = []
        self.game_over_displayed = False  # Флаг для отображения надписи GAME OVER
        self.start_screen_active = True
        self.game_started = False  # Игра не начата
        
        # Инициализация игровых элементов СНАЧАЛА
        self.create_ui_elements()
        
        # Создаем все кнопки ПОСЛЕ UI элементов
        self.create_buttons()
        
        # Создаем стартовый экран
        self.create_start_screen()
        
        self._last_locked_cells = []   # список [(x,y,color), ...] для последней зафиксированной фигуры
        self._prev_locked_cells = []   # предыдущая (чтобы можно было убрать её после следующей фиксации)
        
        self.speed_level = 1                 # 1‑25, 1 – самое медленное
        self.update_fall_speed()
        
        # Создаем первую фигуру
        self.next_piece = self.random_piece()
        self.spawn_new_piece()
        # Обновляем превью после создания всех элементов
        Clock.schedule_once(lambda dt: self.update_next_preview(), 0.1)
        
        self.update_settings_from_config()
        # Игровой цикл запускается, но проверяет game_started
        self.game_clock = Clock.schedule_interval(self.update, 1.0/60.0)  # 60 FPS для плавной анимации


    
    def on_sound_state_change(self, instance, value):
        if value == 'stop':
            self.sound.seek(0) 
    
    # blocks_game.py –‑‑‑ blocksGame.update_fall_speed

    def update_fall_speed(self):
        if self.mode == 'normal':
            # 1 — заморозка
            if self.speed_level == 1:
                self.fall_speed = float('inf')
            else:
                # 2 → 1 шаг/сек, 3 → 2 шага/сек, 4 → 3 шага/сек ...
                freq = self.speed_level - 1
                self.fall_speed = 1.0 / freq
        elif self.mode == 'lightning':
            # 11 → 11 шагов/сек, 12 → 12 шагов/сек ...
            freq = self.speed_level
            self.fall_speed = 1.0 / freq
        self.update_speed_display()

    
    def update_settings_from_config(self):
        # Обновляем фоновое изображение
        if hasattr(self, 'bg_rect'):
            try:
                self.bg_rect.source = settings.game_background  # Используем правильный атрибут
                # Форсируем обновление текстуры
                self.bg_rect.texture = None
            except:
                self.bg_rect.source = 'assets/fon1.png'  # Фолбек
                self.bg_rect.texture = None
        
        # Обновляем отображение next
        if hasattr(self, 'next_preview') and hasattr(self, 'next_piece'):
            self.update_next_preview()
            
        # Обновляем музыку
        if hasattr(self, 'sound') and self.sound:
            self.sound.volume = settings.volume
        
        # Обновляем цвета or not has блоков на поле
        if hasattr(self, 'grid'):
            self.redraw()
    
    def increase_speed(self, *_):
        if self.mode == 'lightning':
            if self.speed_level < 13:
                self.speed_level += 1
        elif self.mode == 'normal':
            if self.speed_level < 10:
                self.speed_level += 1
        self.update_fall_speed()

    def decrease_speed(self, *_):
        if self.mode == 'lightning':
            if self.speed_level > 11:
                self.speed_level -= 1
        elif self.mode == 'normal':
            if self.speed_level > 1:
                self.speed_level -= 1
        self.update_fall_speed()

        
        
    def update_speed_display(self):
        """Обновляет speed_label и гарантирует, что он видим."""
        if not hasattr(self, 'speed_label'):
            return
        try:
            if getattr(self, 'mode', 'normal') == 'normal':
                if getattr(self, 'speed_level', 1) <= 1:
                    sp = "∞"
                else:
                    sp = f"{self.speed_level - 1}/s"
            else:
                sp = f"{getattr(self, 'speed_level', 1)}/s"
            self.speed_label.text = f"Speed: {self.speed_level}"
            self.speed_label.opacity = 1
        except Exception:
            self.speed_label.text = f"Level {getattr(self, 'speed_level', 1)}"
            self.speed_label.opacity = 1


    def _tick_play_seconds(self, dt):
        if not getattr(self, 'game_started', False) or getattr(self, 'paused', False) or getattr(self, 'game_over', False):
            return

        # Добавляем секунду к накопительному времени
        try:
            from daily_tasks import add_play_seconds
            add_play_seconds(1)
        except Exception as e:
            print("Error updating play time:", e)


    def on_window_resize(self, *args):
        """Обработчик изменения размера окна"""
        self.update_dimensions()
        # Пересоздаем элементы интерфейса при изменении размера
        if self.start_screen_active:
            self.remove_widget(self.start_screen)
            self.create_start_screen()
    
    def has_pieces_on_bottom(self):
        """Проверка наличия фигур на нижнем ряду"""
        if not hasattr(self, 'grid'):
            return False
        # Проверяем нижний ряд
        for x in range(self.GRID_WIDTH):
            if self.grid[self.GRID_HEIGHT - 1][x]:  # Последний ряд (нижний)
                return True
        return False

    def on_app_stop(self, *args):
        """Вызывается при закрытии приложения"""
        if self.game_started and not self.game_over and not self.start_screen_active:
            # Сохраняем если есть фигуры на игровом поле
            has_pieces = any(any(row) for row in self.grid) or hasattr(self, 'current_piece')
            if has_pieces:
                self.save_game_session()
        return True
        
    def create_ui_elements(self):
        """Отдельный метод для создания UI элементов с адаптивным позиционированием"""
        # Безопасно удаляем старые элементы
        for name in ('score_label', 'preview_label', 'next_preview', 'speed_label'):
            if hasattr(self, name):
                try:
                    self.remove_widget(getattr(self, name))
                except:
                    pass

        side_margin = int(20 * self.scale)
        top_margin = int(20 * self.scale)

        # Score
        self.score_label = Label(
            text='Score: 0',
            size_hint=(None, None),
            font_size=18 * self.scale,
            pos=(self.screen_width - int(210 * self.scale), self.screen_height - int(260 * self.scale))
        )
        self.add_widget(self.score_label)

        # --- вычисляем место для превью так, чтобы next_preview был сразу под label 'Next' ---
        next_size = self.CELL_SIZE * 4  # размер превью (квадрат)
        preview_x = self.screen_width - side_margin - next_size
        # отступ сверху: top_margin + высота превью + небольшой gap
        gap = int(6 * self.scale)
        preview_y = self.screen_height - top_margin - next_size - gap

        # Label "Next" — ставим прямо над превью, по той же x-координате
        self.preview_label = Label(
            text='Next:',
            size_hint=(None, None),
            size=(next_size, int(20 * self.scale)),
            font_size=18 * self.scale,
            pos=(self.screen_width - int(210 * self.scale), self.screen_height - int(300 * self.scale))
        )
        self.add_widget(self.preview_label)

        # next_preview — прямо под надписью
        self.next_preview = Widget(
            size=(next_size, next_size),
            pos=(self.screen_width - int(100 * self.scale), self.screen_height - int(100 * self.scale))
        )
        # при изменениях pos/size обновим отрисовку
        self.next_preview.bind(size=self.update_next_preview_pos, pos=self.update_next_preview_pos)
        self.add_widget(self.next_preview)

        # Скорость под счетом (чётко слева сверху, с цветом, чтобы было ясно)
        self.speed_label = Label(
            text=f'Speed: {self.fall_speed:.1f}',
            size_hint=(None, None),
            font_size=18 * self.scale,
            pos=(self.screen_width - int(210 * self.scale), self.screen_height - int(200 * self.scale)),
            color=(1, 1, 1, 1)  # белый — чтобы не сливаться с фоном
        )
        self.add_widget(self.speed_label)

        # Монеты (оставляем, как было, но ставим явно size и text_size биндинг)
        coin_w = int(140 * self.scale)
        coin_h = int(28 * self.scale)
        self.coin_label = Label(
            text=f"Coins: {getattr(currency, 'amount', 0)}$",
            size_hint=(None, None),
            size=(coin_w, coin_h),
            pos=(self.screen_width - int(240 * self.scale), self.screen_height - int(440 * self.scale)),
            font_size=int(18 * self.scale),
            halign='right',
            valign='middle',
            color=(1, 1, 0, 1)
        )
        self.coin_label.bind(size=lambda inst, *_: setattr(inst, 'text_size', inst.size))
        self.add_widget(self.coin_label)

        self.game_over_label = None

        # Профиль (как был)
        self.profile_btn = Button(
            background_normal=profile.avatar,
            size_hint=(None, None),
            size=(int(50 * self.scale), int(50 * self.scale)),
            pos=(self.screen_width - int(70 * self.scale), self.screen_height - int(70 * self.scale))
        )
        self.profile_btn.bind(on_press=lambda x: profile.show_profile_popup())
        self.add_widget(self.profile_btn)


    def update_next_preview(self):
        if not settings.show_next:
            if hasattr(self, 'next_preview'):
                self.next_preview.canvas.clear()
                if hasattr(self, 'preview_label'):
                    self.preview_label.text = ''
            return

        if hasattr(self, 'preview_label'):
            self.preview_label.text = 'Next:'

        if self.next_preview.width <= 0 or self.next_preview.height <= 0:
            return
        if not self.next_preview.parent:
            return

        self.next_preview.canvas.clear()
        next_shape, next_color, _ = self.next_piece

        cell_size = max(4, int(self.CELL_SIZE * 0.8))
        shape_width = len(next_shape[0]) * cell_size
        shape_height = len(next_shape) * cell_size

        # Центрируем фигуру ВНУТРИ next_preview
        offset_x = (self.next_preview.width - shape_width) / 2
        offset_y = (self.next_preview.height - shape_height) / 2

        with self.next_preview.canvas:
            for i, row in enumerate(next_shape):
                for j, cell in enumerate(row):
                    if cell:
                        Color(*next_color)
                        block_size = cell_size - 2
                        RoundedRectangle(
                            pos=(
                                offset_x + j * cell_size + 1 + int(90 * self.scale),
                                offset_y + (len(next_shape)-i-1) * cell_size + 1 + int(100 * self.scale)
                            ),
                            size=(block_size, block_size),
                            radius=[block_size * 0.15]
                        )
                        Color(0, 0, 0, 0.8)
                        Line(
                            rectangle=(
                                offset_x + j * cell_size + int(90 * self.scale),
                                offset_y + (len(next_shape)-i-1) * cell_size + int(100 * self.scale),
                                cell_size, cell_size
                            ),
                            width=1
                        )


    def update_next_preview_pos(self, *args):
        """Помещаем next_preview прямо под preview_label и перерисовываем её."""
        if not (hasattr(self, 'preview_label') and hasattr(self, 'next_preview')):
            return
        try:
            
            self.next_preview.pos = (self.screen_width - int(100 * self.scale), self.screen_height - int(100 * self.scale))
        except Exception:
            pass
        # Перерисуем содержимое превью (с небольшой задержкой, чтобы размеры успели примениться)
        Clock.schedule_once(lambda dt: self.update_next_preview(), 0)


    
    def set_gost_level(self, level: int):
        self.gost_mode = True
        self.gost_level = level
        self.steps_since_spawn = 0
        self.piece_landed = False
        self.current_piece_visible = True
        self.landed_pieces.clear()
   

    def get_session_filename(self):
        """Получение имени файла сессии для текущего режима"""
        mode_session_map = {
            'normal': 'saves/normal_session.json',
            'gost': 'saves/gost_session.json',
            'lightning': 'saves/lightning_session.json'
        }
        return mode_session_map.get(self.mode, 'saves/session.json')

    def check_saved_session_for_mode(self):
        """Проверка наличия сохраненной сессии для текущего режима"""
        try:
            session_file = self.get_session_filename()
            print(f"Checking session file: {session_file}")
            exists = (os.path.exists(session_file) and 
                    os.path.isfile(session_file) and
                    os.path.getsize(session_file) > 0)
            print(f"Session file exists and not empty: {exists}")
            return exists
        except Exception as e:
            print(f"Error checking session: {e}")
            return False

    def save_game_session(self):
        """Сохранение текущей сессии игры"""
        try:
            session_data = {
                'score': self.score,
                'grid': [[cell for cell in row] for row in self.grid],  # Сохраняем копию сетки
                'fall_speed': self.fall_speed,
                'current_piece': [[cell for cell in row] for row in self.current_piece] if hasattr(self, 'current_piece') else None,
                'current_x': self.current_x if hasattr(self, 'current_x') else 0,
                'current_y': self.current_y if hasattr(self, 'current_y') else 0,
                'color': list(self.color) if hasattr(self, 'color') else None,
                'shape_name': self.shape_name if hasattr(self, 'shape_name') else None,
                'next_piece_shape': self.next_piece[2] if hasattr(self, 'next_piece') else None,
                'game_started': self.game_started,
                'paused': self.paused,
                'mode': self.mode,
                'speed_level': self.speed_level,
                'show_next': settings.show_next,
                'gost_level': self.gost_level if hasattr(self, 'gost_level') else 1,
                'gost_step_count': self.gost_step_count if hasattr(self, 'gost_step_count') else 0,
                'combo_multiplier': self.combo_multiplier if hasattr(self, 'combo_multiplier') else 1.0,
                'gost_mode_settings': self.gost_mode_settings if hasattr(self, 'gost_mode_settings') else None
            }
            
            if not os.path.exists('saves'):
                os.makedirs('saves')
                
            session_file = self.get_session_filename()
            with open(session_file, 'w') as f:
                json.dump(session_data, f)
                
        except Exception as e:
            print(f"Ошибка сохранения сессии: {e}")

    def load_game_session(self):
        """Загрузка сохраненной сессии игры"""
        try:
            session_file = self.get_session_filename()
            print(f"Trying to load session from: {session_file}")
            
            
            if not os.path.exists('saves'):
                os.makedirs('saves')
            
            if not os.path.exists(session_file):
                print("Session file not found")
                return False
            
            if os.path.getsize(session_file) == 0:
                print("Session file is empty")
                return False

            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            self.speed_level = session_data.get('speed_level', 1 if self.mode == 'normal' else 11)
                
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            self.speed_level = session_data.get('speed_level', 1 if self.mode == 'normal' else 11)  # Дефолтные значения
            
            self.mode = session_data.get('mode', 'normal')  # восстановить режим перед остальным
            

            
            # Восстанавливаем данные
            self.score = session_data.get('score', 0)
            self.grid = session_data.get('grid', [[0 for _ in range(self.GRID_WIDTH)] for _ in range(self.GRID_HEIGHT)])
            self.fall_speed = session_data.get('fall_speed', 0.5)
            self.game_started = session_data.get('game_started', False)
            self.paused = session_data.get('paused', False)
            self.gost_level = session_data.get('gost_level', 1)
            self.gost_step_count = session_data.get('gost_step_count', 0)
            self.combo_multiplier = session_data.get('combo_multiplier', 1.0)
           
            if hasattr(self, 'score_label'):
                self.score_label.text = f'Score: {self.score}'
                
            self.update_speed_display()
            self.update_fall_speed()
            
            
            # Восстанавливаем следующую фигуру
            next_shape_name = session_data.get('next_piece_shape')
            if next_shape_name and next_shape_name in SHAPES:
                self.next_piece = (SHAPES[next_shape_name], COLORS[next_shape_name], next_shape_name)
            else:
                self.next_piece = self.random_piece()
                
            # Восстанавливаем текущую фигуру
            if session_data.get('current_piece'):
                self.current_piece = session_data['current_piece']
                self.current_x = session_data.get('current_x', 0)
                self.current_y = session_data.get('current_y', 0)
                self.color = session_data.get('color')
                self.shape_name = session_data.get('shape_name', 'I')
            else:
                self.spawn_new_piece()
                    
            self.update_next_preview()
            
            # Убираем стартовый экран
            if hasattr(self, 'start_screen'):
                self.remove_widget(self.start_screen)
                
            self._session_loaded = True
            self.start_screen_active = False  # Вот это ключевое изменение
            self.game_started = True
            self.redraw()
            # вверху файла можно не импортировать; делаем динамический import внутри функции, чтобы избежать циклических импортов
            try:
                from daily_tasks import mark_task_completed
                # инициализация счётчика с запасом
                self._play_seconds = 0
                # если уже был таймер — отменим
                if hasattr(self, '_play_timer') and self._play_timer:
                    try:
                        self._play_timer.cancel()
                    except Exception:
                        pass
                # запускаем тикер каждую секунду
                self._play_timer = Clock.schedule_interval(self._tick_play_seconds, 1.0)
            except Exception:
                # на устройствах без saves/currency или при ошибках — просто пропускаем
                pass

            return True
            
        except Exception as e:
            print(f"Ошибка загрузки сессии: {e}")
            return False


    
    def clear_two_bottom_rows(self):
        """Удаление двух нижних строк"""
        if self.game_over or self.paused or self.start_screen_active:
            return
        
        # Проверяем есть ли что удалять
        has_blocks = any(self.grid[-1]) or any(self.grid[-2]) if len(self.grid) >= 2 else False
        
        if has_blocks:
            # Удаляем 2 нижних ряда и вставляем 2 пустых сверху
            for _ in range(min(2, len(self.grid))):  # Безопасное удаление
                if self.grid:  # Проверяем что список не пуст
                    try:
                        self.grid.pop()  # Удаляем последний ряд
                    except Exception:
                        pass
            # Вставляем 2 пустых ряда сверху
            for _ in range(2):
                self.grid.insert(0, [0 for _ in range(self.GRID_WIDTH)])
            
            # Перерисовать игровое поле
            self.redraw()
            
            # Добавляем небольшое визуальное подтверждение
            if hasattr(self, 'score_label'):
                old_text = self.score_label.text
                self.score_label.text = "Cleared!"
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: setattr(self.score_label, 'text', old_text), 0.5)

    def set_game_mode(self, mode_name):
        if mode_name in self.modes and self.mode != mode_name:
            # Сохраняем текущую сессию если игра начата
            if self.game_started and not self.game_over and self.has_pieces_on_bottom():
                print(f"Saving current session before mode change to {mode_name}")
                self.save_game_session()

            self.mode = mode_name
            if mode_name == 'gost':
                self.modes[mode_name] = GostMode(level=self.gost_level)
            self.modes[mode_name].activate(self)
            
            if mode_name == 'gost' and hasattr(self.modes[mode_name], 'gost_mode_settings'):
                self.gost_mode_settings = self.modes[mode_name].gost_mode_settings

            if self.check_saved_session_for_mode():
                self.load_game_session()
            else:
                self.reset_for_new_mode()
                
                
            if mode_name == 'normal':
                self.speed_level = 1
            elif mode_name == 'lightning':
                self.speed_level = 11
            else:  # gost
                self.speed_level = self.gost_level

            self.update_fall_speed()

        

    def check_saved_session(self):
        """Проверка наличия сохраненной сессии для текущего режима"""
        return self.check_saved_session_for_mode()

    def reset_for_new_mode(self):
        """Сброс состояния для нового режима"""
        self.game_over = False
        self.game_started = False
        self.score = 0
        self.combo_multiplier = 1.0
        self.gost_step_count = 0
        
        # Обновляем фон при смене режима
        if hasattr(self, 'bg_rect'):
            try:
                self.bg_rect.source = settings.background
                self.bg_rect.texture = None
            except:
                self.bg_rect.source = 'assets/fon1.png'
                self.bg_rect.texture = None
            
        # Очищаем игровое поле
        self.grid = [[0 for _ in range(self.GRID_WIDTH)] for _ in range(self.GRID_HEIGHT)]
        
        # Создаем новые фигуры
        self.next_piece = self.random_piece()
        self.spawn_new_piece()
        
        # Обновляем UI
        if hasattr(self, 'score_label'):
            self.score_label.text = 'Score: 0'
        
        # Показываем стартовый экран
        self.create_start_screen()
        self.start_screen_active = True
    
    def manage_music(self, action='play'):
        """Управление музыкой через music_manager, fallback — локальный sound."""
        try:
            if action == 'play':
                music_manager.play_game_music()
            elif action == 'stop':
                music_manager.stop()
        except Exception:
            # fallback на локальный self.sound
            if hasattr(self, 'sound') and self.sound:
                try:
                    if action == 'play' and getattr(self.sound, 'state', None) != 'play':
                        self.sound.play()
                    elif action == 'stop':
                        self.sound.stop()
                except:
                    pass

                
    def update_dimensions(self):
        dims = get_dimensions()
        self.scale = dims['scale']
        self.screen_width = dims['screen_width']
        self.screen_height = dims['screen_height']
        self.CELL_SIZE = dims['CELL_SIZE']
        self.GRID_WIDTH = dims['GRID_WIDTH']
        self.GRID_HEIGHT = dims['GRID_HEIGHT']
        self.GRID_X_OFFSET = dims['GRID_X_OFFSET']
        self.GRID_Y_OFFSET = dims['GRID_Y_OFFSET']

        # Обновляем элементы интерфейса если они есть
        side_margin = int(20 * self.scale)
        top_margin = int(20 * self.scale)
        btn_size = int(50 * self.scale)

        if hasattr(self, 'score_label'):
            self.score_label.pos = (self.screen_width - int(210 * self.scale), self.screen_height - int(260 * self.scale))
            self.score_label.font_size = 18 * self.scale

        if hasattr(self, 'speed_label'):
            self.speed_label.pos = (self.screen_width - int(210 * self.scale), self.screen_height - int(200 * self.scale))
            self.speed_label.font_size = 18 * self.scale
            self.speed_label.color = (1, 1, 1, 1)

        if hasattr(self, 'preview_label'):
            # держим preview_label прямо над next_preview (расчёт совпадает с create_ui_elements)
            next_size = self.CELL_SIZE * 4
            preview_x = self.screen_width - side_margin - next_size
            preview_y = self.screen_height - top_margin - next_size - int(6 * self.scale)
            self.preview_label.size = (next_size, int(20 * self.scale))
            self.preview_label.pos = (self.screen_width - int(210 * self.scale), self.screen_height - int(300 * self.scale))
            self.preview_label.font_size = 18 * self.scale

        if hasattr(self, 'next_preview'):
            next_size = self.CELL_SIZE * 4
            preview_x = self.screen_width - side_margin - next_size
            preview_y = self.screen_height - top_margin - next_size - int(6 * self.scale)
            self.next_preview.size = (next_size, next_size)
            self.next_preview.pos = (self.screen_width - int(100 * self.scale), self.screen_height - int(100 * self.scale))

        if hasattr(self, 'coin_label'):
            self.coin_label.pos = (self.screen_width - int(240 * self.scale), self.screen_height - int(440 * self.scale))
            self.coin_label.font_size = 18 * self.scale

        if hasattr(self, 'game_bg'):
            self.game_bg.pos = (self.GRID_X_OFFSET, self.GRID_Y_OFFSET)
            self.game_bg.size = (self.GRID_WIDTH*self.CELL_SIZE, self.GRID_HEIGHT*self.CELL_SIZE)

        # Пересоздаем кнопки при изменении размеров
        self.create_buttons()

        # --- ВАЖНО: возвращаем ключевые метки на передний план (чтобы не перекрывались кнопками) ---
        for name in ('preview_label', 'next_preview', 'speed_label', 'score_label', 'coin_label'):
            if hasattr(self, name):
                widget = getattr(self, name)
                try:
                    # remove + add гарантирует, что виджет окажется выше по z-order
                    if widget in self.children:
                        self.remove_widget(widget)
                    self.add_widget(widget)
                except Exception:
                    pass


    def update_bg(self, *args):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = self.pos
            self.bg_rect.size = self.size
        if hasattr(self, 'game_bg'):
            self.game_bg.pos = (self.GRID_X_OFFSET, self.GRID_Y_OFFSET)
            self.game_bg.size = (self.GRID_WIDTH*self.CELL_SIZE, self.GRID_HEIGHT*self.CELL_SIZE)

    def create_buttons(self):
        """Создание кнопок с изображениями (переписанный метод)."""
        # --- 1) Защищённые элементы, которые НЕ трогаем ---
        protected = {
            getattr(self, 'score_label', None),
            getattr(self, 'preview_label', None),
            getattr(self, 'next_preview', None),
            getattr(self, 'speed_label', None),
            getattr(self, 'coin_label', None),
            getattr(self, 'start_screen', None)
        }

        # --- 2) Удаляем предыдущие временные UI-виджеты, которые мы создавали ранее ---
        # Храним ссылки для безопасного удаления при повторном создании
        prev = getattr(self, '_ui_buttons', None)
        if prev:
            for w in prev:
                try:
                    self.remove_widget(w)
                except Exception:
                    pass
        # Создаём новый список для текущей итерации
        self._ui_buttons = []

        # Дополнительно — на всякий случай убираем старые Image/Button/Label (которые не в protected)
        for child in self.children[:]:
            if child in protected:
                continue
            if isinstance(child, (Image, Button, Label)):
                try:
                    self.remove_widget(child)
                except Exception:
                    pass

        # --- 3) размеры и отступы (адаптивно через self.scale) ---
        btn_size = int(50 * self.scale)
        side_margin = int(20 * self.scale)
        bottom_margin = int(30 * self.scale)

        # --- 4) Конфиг кнопок управления (обычные игровые кнопки: картинки, без текста) ---
        control_buttons = [
            ('assets/left.png',
            self.GRID_X_OFFSET - btn_size - side_margin,
            self.GRID_Y_OFFSET - btn_size - int(140 * self.scale),
            lambda x: self.handle_start_screen_button('left') if self.start_screen_active else self.player_move(-1, 0)),
            ('assets/right.png',
            self.GRID_X_OFFSET + self.GRID_WIDTH * self.CELL_SIZE + side_margin - int(160 * self.scale),
            self.GRID_Y_OFFSET - btn_size - int(140 * self.scale),
            lambda x: self.handle_start_screen_button('right') if self.start_screen_active else self.player_move(1, 0)),
            ('assets/down.png',
            self.GRID_X_OFFSET + (self.GRID_WIDTH * self.CELL_SIZE) // 2 - btn_size // 2 - int(80 * self.scale),
            self.GRID_Y_OFFSET - btn_size - bottom_margin - int(165 * self.scale),
            lambda x: self.handle_start_screen_button('down') if self.start_screen_active else self.player_move(0, 1)),
            ('assets/rotate.png',
            self.GRID_X_OFFSET + (self.GRID_WIDTH * self.CELL_SIZE) // 2 - btn_size * 2 // 2 + int(150 * self.scale),
            self.GRID_Y_OFFSET + self.GRID_HEIGHT * self.CELL_SIZE + bottom_margin - int(600 * self.scale),
            lambda x: self.handle_start_screen_button('rotate') if self.start_screen_active else self.rotate()),
            ('assets/up.png',
            self.GRID_X_OFFSET + (self.GRID_WIDTH * self.CELL_SIZE) // 2 - btn_size // 2 - int(80 * self.scale),
            self.GRID_Y_OFFSET - 2 * btn_size - bottom_margin - int(10 * self.scale),
            lambda x: self.handle_start_screen_button('hard_drop') if self.start_screen_active else self.hard_drop()),
        ]

        # --- 5) Функциональные кнопки (с текстом ВНУТРИ) ---
        func_buttons = [
            ('Pause', 'assets/buttons.png', side_margin + int(50 * self.scale), self.screen_height - int(550 * self.scale),
            lambda x: self.start_game(None) if self.start_screen_active else self.toggle_pause(), 1.0, 1.0),
            ('Menu', 'assets/buttons.png', side_margin + int(135 * self.scale), self.screen_height - int(550 * self.scale),
            lambda x: (self._save_and_go_menu()), 1.0, 1.0),
            ('Restart', 'assets/buttons.png', side_margin + int(220 * self.scale), self.screen_height - int(550 * self.scale),
            lambda x: self.restart_game(), 1.0, 1.0),
            ('Sound', 'assets/buttons.png', side_margin + int(305 * self.scale), self.screen_height - int(550 * self.scale),
            lambda x: music_manager.toggle_music('game'), 1.0, 1.0),
            ('Settings', 'assets/buttons.png', side_margin + int(390 * self.scale), self.screen_height - int(550 * self.scale),
            lambda x: self.open_settings_from_game(), 1.0, 1.0),
            ('Swap 1$', 'assets/rotate.png', side_margin + int(170 * self.scale), self.screen_height - int(800 * self.scale),
            lambda x: self.buy_swap_piece(), 1.15, 1.0),
            ('Del 2$', 'assets/rotate.png', side_margin + int(250 * self.scale), self.screen_height - int(800 * self.scale),
            lambda x: self.buy_clear_two_rows(), 1.1, 1.0),
        ]

        # Утилита для автоподгонки текста внутри Label
        def _fit_label(instance, *_):
            instance.text_size = (max(1, instance.width - 8), max(1, instance.height - 8))
            instance.font_size = max(10, int(instance.height * 0.25))

        # --- 6) Создаём control_buttons (Image + on_touch_down как раньше, но keep_ratio=True) ---
        for img_path, x, y, callback in control_buttons:
            if "rotate.png" in img_path:
                size = (btn_size * 3, btn_size * 3)
            else:
                size = (btn_size, btn_size)
            img = Image(
                source=img_path,
                size_hint=(None, None),
                size=size,
                pos=(x, y),
                allow_stretch=True,
                keep_ratio=True  # важно: сохраняем пропорции, чтобы не было странных "холмов"
            )
            # Как и раньше — реагируем на on_touch_down (передаём touch объект в callback)
            def _bind_touch(inst, cb):
                inst.bind(on_touch_down=lambda instance, touch: cb(touch) if instance.collide_point(*touch.pos) else None)
            _bind_touch(img, callback)

            # помечаем виджет и сохраняем для последующего удаления
            setattr(img, 'is_game_button', True)
            self.add_widget(img)
            self._ui_buttons.append(img)

        # --- 7) Создаём func_buttons: Image (фон) + Label (текст, внутри) + прозрачная Button (поверх для событий) ---
        for text, img_path, x, y, callback, w_mul, h_mul in func_buttons:
            w = int(btn_size * w_mul)
            h = int(btn_size * h_mul)

            # фон (изображение) — показываем как Image, не используем background_normal Button
            bg = Image(
                source=img_path,
                size_hint=(None, None),
                size=(w, h),
                pos=(x, y),
                allow_stretch=True,
                keep_ratio=True  # сохраняем пропорции изображения
            )
            setattr(bg, 'is_game_button', True)
            self.add_widget(bg)
            self._ui_buttons.append(bg)

            # текст поверх — внутри границ изображения
            lbl = Label(
                text=text,
                size_hint=(None, None),
                size=(w, h),
                pos=(x, y),
                halign='center',
                valign='middle',
                markup=True,
                color=(1, 1, 1, 1)
            )
            lbl.bind(size=_fit_label, pos=_fit_label)
            # сразу инициализируем text_size/font_size
            _fit_label(lbl)
            setattr(lbl, 'is_game_button', True)
            self.add_widget(lbl)
            self._ui_buttons.append(lbl)

            # прозрачная кнопка сверху для обработки нажатия (вызовем callback(None))
            btn = Button(
                size_hint=(None, None),
                size=(w, h),
                pos=(x, y),
                background_normal='',
                background_down='',
                background_color=(0, 0, 0, 0)
            )
            # callback может ожидать аргумент (touch), поэтому передаём None — в целом у тебя callbacks это обрабатывают
            btn.bind(on_press=lambda instance, cb=callback: cb(None))
            setattr(btn, 'is_game_button', True)
            self.add_widget(btn)
            self._ui_buttons.append(btn)

    
    
    def buy_clear_two_rows(self):
        """Покупка удаления двух нижних строк за 1 монету"""
        if self.game_over or self.paused or self.start_screen_active:
            return
        
        # Проверяем достаточно ли монет
        if currency.amount < 2:
            self.show_not_enough_coins_popup()
            return
        
        # Списываем монету
        if currency.spend(2):
            # Удаляем 2 нижних ряда
            self.clear_two_bottom_rows()
            # Обновляем отображение монет
            self.update_coin_display_in_menu()
            # ОБНОВЛЯЕМ ОТОБРАЖЕНИЕ МОНОЕТ НА ЭКРАНЕ ИГРЫ
            self.update_coin_display()

    def show_not_enough_coins_popup(self):
        """Показать popup с недостатком монет"""
        popup = Popup(title="Error", size_hint=(0.6, 0.3))
        layout = BoxLayout(orientation='vertical', spacing=10)
        layout.add_widget(Label(text="Not enough coins!"))
        btn = Button(text="ОК", size_hint_y=None, height=40)
        btn.bind(on_press=popup.dismiss)
        layout.add_widget(btn)
        popup.content = layout
        popup.open()

    def update_coin_display_in_menu(self):
        """Обновить отображение монет в меню"""
        from kivy.app import App
        app = App.get_running_app()
        if app and app.root:
            try:
                menu_screen = app.root.get_screen('menu')
                menu_screen.update_coin_display()
            except Exception:
                pass

    
    def _save_and_go_menu(self):
        
        
        # остановим централизованную музыку (music_manager) и включим музыку меню
        try:
            music_manager.play_menu_music()
        except:
            # fallback: остановим локальный sound
            if hasattr(self, 'sound') and self.sound:
                try:
                    self.sound.stop()
                except:
                    pass

        
        try:
            if self.has_pieces_on_bottom():
                self.save_game_session()
                self.paused = True
        except Exception:
            pass
        
        # Добавьте обновление монет на экране игры
        self.update_coin_display()
        # потом переход
        self.switch_to_menu()
        

    
    def handle_start_screen_button(self, button_type):
        """Обработка кнопок на стартовом экране"""
        if not self.start_screen_active:
            return
            
        if self.mode == 'gost':
            # Специальная обработка для Gost режима
            if button_type == 'hard_drop':
                self.increase_gost_level()
            elif button_type == 'down':
                self.decrease_gost_level()
            elif button_type == 'rotate' or button_type == 'pause':
                self.start_game(None)
        else:
            # Обычная обработка для других режимов
            if button_type == 'left':
                self.decrease_speed(None)
            elif button_type == 'right':
                self.increase_speed(None)
            elif button_type in ['pause', 'rotate']:
                self.start_game(None)

    
    def set_show_next(self, show):
        """Установка видимости следующей фигуры"""
        if hasattr(self, 'next_preview'):
            self.next_preview.opacity = 1 if show else 0
        if hasattr(self, 'preview_label'):
            self.preview_label.opacity = 1 if show else 0
    
    def random_piece(self):
        if not hasattr(self, 'shape_history'):
            self.shape_history = []

        attempts = 0
        while attempts < 10:
            shape = random.choice(list(SHAPES.keys()))
            if self.shape_history.count(shape) < 4:
                self.shape_history.append(shape)
                if len(self.shape_history) > 10:
                    self.shape_history.pop(0)
                return SHAPES[shape], COLORS[shape], shape
            attempts += 1
        # Используем пользовательские цвета
        color = settings.piece_colors.get(shape, COLORS[shape])
        return SHAPES[shape], color, shape
        

    def apply_standard_rendering(self):
        self.is_visible = True
        if hasattr(self, 'original_redraw'):
            self.redraw = self.original_redraw

    # вставить в класс blocksGame
    def apply_invisible_rendering(self):
        # включаем гост-режим и инициализируем вспомогательные поля
        self.gost_mode = True
        # счётчики для шагов и видимости
        self._gost_steps = getattr(self, '_gost_steps', 0)
        self.steps_since_spawn = getattr(self, 'steps_since_spawn', 0)
        self.current_piece_visible = getattr(self, 'current_piece_visible', True)
        self.piece_landed = getattr(self, 'piece_landed', False)
        # список снимков приземлённых фигур (каждый элемент - list of (x,y,color))
        self.landed_pieces = getattr(self, 'landed_pieces', [])
        # последние зафиксированные клетки (для визуалок/откатов)
        self._last_locked_cells = getattr(self, '_last_locked_cells', [])
        self._prev_locked_cells = getattr(self, '_prev_locked_cells', [])
        # стандартные настройки, если не пришли из game_modes
        if not hasattr(self, 'gost_mode_settings'):
            self.gost_mode_settings = {
                'steps_to_disappear': 5,
                'appear_on_lock': True,
                'lock_appear_time': 1.5,
                'show_next': True
            }
        # всегда показываем next в соответствии с настройкой
        if self.gost_mode_settings.get('show_next') is False:
            settings.show_next = False
            self.set_show_next(False)



    def handle_gost_visibility(self):
        if not self.gost_mode:
            return
        
        if self.gost_level == 1:
            if self.steps_since_spawn >= 5 and not self.piece_landed:
                self.current_piece_visible = False
            else:
                self.current_piece_visible = True

        elif self.gost_level == 2:
            # Уровень 2: фигура исчезает после 3 шагов, но продолжает двигаться
            if self.steps_since_spawn >= 3 and not self.piece_landed:
                self.current_piece_visible = False
            else:
                self.current_piece_visible = True
                
        elif self.gost_level == 3:
            # Для уровня 3: видим только если только что появилась или приземлилась
            if self.piece_landed or self.steps_since_spawn == 0:
                self.current_piece_visible = True
            else:
                self.current_piece_visible = False



    def _gost_count_step(self):
        """
        Вызывать ТОЛЬКО при действиях игрока: left, right, rotate, soft_drop.
        Инкрементируем steps_since_spawn и обновляем видимость.
        """
        if getattr(self, 'mode', '') != 'gost':
            return

        # Всегда увеличиваем счетчик
        if not hasattr(self, 'steps_since_spawn'):
            self.steps_since_spawn = 0
        self.steps_since_spawn += 1
        
        # Обновляем видимость
        self.handle_gost_visibility()
            



    def player_move(self, dx, dy):
        moved = self.move(dx, dy)
        if moved:
                # считаем шагы только когда это действие игрока (не гравитация)
            self._gost_count_step()
        return moved


    def draw_semi_invisible_block(self, x, y, color):
        px = self.GRID_X_OFFSET + x * self.CELL_SIZE
        py = self.GRID_Y_OFFSET + (self.GRID_HEIGHT - y - 1) * self.CELL_SIZE
        with self.canvas:
            Color(*color[:3], 0.3)
            Rectangle(pos=(px, py), size=(self.CELL_SIZE, self.CELL_SIZE))
            Color(1, 1, 1, 1)
            Line(rectangle=(px, py, self.CELL_SIZE, self.CELL_SIZE), width=1.2)

    def apply_tgm_rendering(self):
        self.is_visible = True
        if hasattr(self, 'original_redraw'):
            self.redraw = self.original_redraw


    def _handle_gost_mode(self):
        if (self.gost_mode_settings or {}).get('steps_to_disappear') is not None:
            return
        """Обработка Ghost режима в игровом цикле"""
        if not hasattr(self, 'piece_spawn_time'):
            self.piece_spawn_time = Clock.get_time()
                    
        elapsed = Clock.get_time() - self.piece_spawn_time
        # Используем steps_to_disappear вместо disappear_time
        steps_needed = self.gost_mode_settings.get('steps_to_disappear', 5)
        if self.gost_step_count >= steps_needed:
            self.is_visible = False
            self.redraw()

    def spawn_new_piece(self):
        if hasattr(self, 'game_over') and self.game_over:
            return
        
        self.gost_step_count = 0
        self.current_piece_visible = True

        
        if self.mode == 'gost':
            # Сброс состояния для новой фигуры
            self.steps_since_spawn = 0
            self.piece_landed = False
            self.current_piece_visible = True
            
        
        if not hasattr(self, 'gost_mode_settings') and self.mode == 'gost':
            # Если вдруг настройки не установлены, инициализируем их
            self.modes['gost'] = GostMode(level=self.gost_level)
            self.modes['gost'].activate(self)
            self.gost_mode_settings = self.modes['gost'].gost_mode_settings
        
        if not hasattr(settings, 'piece_colors'):
            settings.piece_colors = {
                'I': [1, 0, 0, 1], 'O': [0, 1, 0, 1], 
                'T': [0, 0, 1, 1], 'S': [1, 1, 0, 1],
                'Z': [1, 0, 1, 1], 'J': [0, 1, 1, 1],
                'L': [1, 0.5, 0, 1]
            }
            
        if hasattr(self, 'next_piece'):
            self.current_piece, self.color, self.shape_name = self.next_piece
            # Используем пользовательский цвет
            self.color = settings.piece_colors.get(self.shape_name, self.color)
        else:
            shape = random.choice(list(SHAPES.keys()))
            self.current_piece = SHAPES[shape]
            self.shape_name = shape
            self.color = settings.piece_colors.get(shape, COLORS[shape])
            
        # Генерируем следующую фигуру с учетом пользовательских цветов
        next_shape = random.choice(list(SHAPES.keys()))
        self.next_piece = (
            SHAPES[next_shape], 
            settings.piece_colors.get(next_shape, COLORS[next_shape]),
            next_shape
        )
        
        # Обновляем превью
        self.update_next_preview()
        
        self.current_x = self.GRID_WIDTH // 2 - len(self.current_piece[0]) // 2
        self.current_y = 0

        if not self.can_move(0, 0):
            # если gost — считаем это концом игры (покажем окно возрождения)
            if self.mode == 'gost':
                self.game_over = True
                # если у тебя есть функция показа окна — вызови её; в коде есть разные варианты,
                # пробуем максимально безопасно:
                try:
                    if hasattr(self, '_show_game_over_popup'):
                        self._show_game_over_popup()
                    elif hasattr(self, 'show_start_screen_after_game_over'):
                        self.show_start_screen_after_game_over()
                        
                except:
                    pass
            
            else:
                # Для обычного режима - нельзя спавнить, просто заканчиваем
                self.game_over = True
                try:
                    if hasattr(self, '_show_game_over_popup'):
                        self._show_game_over_popup()
                except:
                    pass
            
            return  # не продолжаем спавн
            

        
        # Для Gost режима сразу делаем фигуру видимой
        if self.mode == 'gost':
            self.is_visible = True
            if hasattr(self, 'gost_mode_settings'):
                steps_needed = self.gost_mode_settings.get('steps_to_disappear', 5)
                if self.gost_step_count >= steps_needed:
                    Clock.schedule_once(
                        lambda dt: setattr(self, 'is_visible', False), 
                        self.gost_mode_settings['disappear_time']
                    )

        # Проверка на game over (касание при появлении)
        if not self.can_move(0, 0):
            self.show_game_over()

    
    def buy_swap_piece(self):
        # проверяем состояние игры
        if self.game_over or self.paused or self.start_screen_active:
            return
        try:
            if currency.amount < 1:
                popup = Popup(title="Error", size_hint=(0.6,0.3))
                layout = BoxLayout(orientation='vertical')
                layout.add_widget(Label(text="Not enough coins!"))
                btn = Button(text="ОК", size_hint_y=None, height=40)
                btn.bind(on_press=popup.dismiss)
                layout.add_widget(btn)
                popup.content = layout
                popup.open()
                return
            # списываем монету
            if currency.spend(1):
                # замена текущей фигуры на next
                self.current_piece, self.color, self.shape_name = self.next_piece
                self.next_piece = self.random_piece()
                self.update_next_preview()
                self.redraw()
                # Обновляем отображение монет в меню
                app = App.get_running_app()
                if app and app.root:
                    try:
                        app.root.get_screen('menu').update_coin_display()
                        self.coin_label.text = f"Coins: {currency.amount}$"
                    except Exception:
                        pass
        except Exception as e:
            print("Error buy_swap_piece:", e)
    
    def update_coin_display(self):
        """Обновление количества монет на экране игры"""
        if hasattr(self, 'coin_label'):
            self.coin_label.text = f"Coins: {currency.amount}$"
    
    # В классе blocksGame (blocks_game.py) измените метод open_settings_from_game:
    def open_settings_from_game(self):
        # Убедитесь, что не создается дублирующих элементов
        #self.clear_buttons()  # Добавьте этот метод для очистки старых кнопок
        
        # Сохраняем позицию музыки
        if hasattr(self, 'sound') and self.sound:
            self.pause_music_pos = self.sound.get_pos()
            
        # Остальной код метода без изменений
        try:
            if self.has_pieces_on_bottom():
                self.save_game_session()
                self.paused = True
        except Exception:
            pass

        self.settings_opener = 'game'
        self.parent.parent.current = 'settings'

    
    def clear_buttons(self):
        """Очистка всех кнопок управления"""
        for child in self.children[:]:
            if isinstance(child, Button) and child not in [self.profile_btn]:
                self.remove_widget(child)
    
                    
    def draw_block(self, x, y, color):
        px = self.GRID_X_OFFSET + x * self.CELL_SIZE
        py = self.GRID_Y_OFFSET + (self.GRID_HEIGHT - y - 1) * self.CELL_SIZE
        with self.canvas:
            Color(*color)
            radius = self.CELL_SIZE * 0.15
            rect = RoundedRectangle(
                pos=(px, py),
                size=(self.CELL_SIZE, self.CELL_SIZE),
                radius=[radius]
            )
            self.blocks.append(rect)

            Color(0, 0, 0, 0.8)
            line = Line(rectangle=(px, py, self.CELL_SIZE, self.CELL_SIZE), width=1)
            self.blocks.append(line)  # Добавляем линию в blocks тоже

    

    def toggle_sound(self):
        """Toggle звука — делегируем музыку централизованному music_manager."""
        try:
            music_manager.toggle_music('game')
        except Exception:
            # резервный fallback на локальный sound, если что-то пошло не так
            if hasattr(self, 'sound') and self.sound:
                try:
                    if getattr(self.sound, 'state', None) == 'play':
                        self.sound.stop()
                    else:
                        self.sound.play()
                except:
                    pass


    def clear_falling_blocks(self):
        """Очищаем только падающие блоки"""
        for falling_block in self.falling_blocks:
            if falling_block.rect in self.canvas.children:
                self.canvas.remove(falling_block.rect)
            if falling_block.line in self.canvas.children:
                self.canvas.remove(falling_block.line)
        self.falling_blocks = []

    def clear_blocks(self):
        """Очищаем все блоки"""
        for block in self.blocks:
            if block in self.canvas.children:
                self.canvas.remove(block)
        self.blocks = []

    
    
    def update(self, dt):
        if self.start_screen_active or self.paused or not self.game_started:
            return
            
        if self.mode == 'gost':
            self._handle_gost_mode()
            return
            
        now = Clock.get_time()
        if not hasattr(self, 'last_move_time'):
            self.last_move_time = now
            
        if now - self.last_move_time >= self.fall_speed:
            self.last_move_time = now
            self.move(0, 1)

    def update_clear_animation(self, dt):
        """Обновление построчной анимации очистки"""
        if not self.clear_lines_queue:
            self.clear_animation_active = False
            # Сразу показываем начальный экран после завершения анимации
            Clock.schedule_once(lambda dt: self.show_start_screen_after_game_over(), 0.1)
            return
            
        self.clear_animation_step += 1
        
        # Очищаем одну линию каждые 10 шагов
        if self.clear_animation_step >= 3:
            if self.clear_line_index < len(self.clear_lines_queue):
                line_to_clear = self.clear_lines_queue[self.clear_line_index]
                # Очищаем линию
                for x in range(self.GRID_WIDTH):
                    if line_to_clear < self.GRID_HEIGHT:
                        self.grid[line_to_clear][x] = 0
                self.clear_line_index += 1
            else:
                self.clear_animation_active = False
                # Сразу показываем начальный экран после завершения анимации
                Clock.schedule_once(lambda dt: self.show_start_screen_after_game_over(), 0.1)
            self.clear_animation_step = 0
        
    

    
    def on_app_pause(self):
        """Вызывается когда приложение сворачивается"""
        if self.game_started and not self.game_over:
            self.save_game_session()
        return True

    def on_app_resume(self):
        """Вызывается когда приложение разворачивается"""
        # Можно добавить логику для возобновления игры
        pass
    
    def watch_ad_for_continue(self):
        """Показать рекламу для получения монет и обновить интерфейс"""
        ok, reason = AD_MANAGER.show_rewarded(on_reward=self.after_reward_ad)
        if not ok:
            popup = Popup(title="Ad Error", content=Label(text=reason), size_hint=(0.7, 0.3))
            popup.open()

    def after_reward_ad(self):
        """Вызывается после просмотра рекламы"""
        try:
            from shop import shop
            shop.update_all_tabs()
        except:
            pass

        # Обновляем отображение монет
        try:
            self.update_coin_display()
        except:
            pass

        # Пересобираем popup после награды
        try:
            self.update_game_over_popup_contents()
        except:
            pass


    def move(self, dx, dy):
        if self.game_over or self.paused or self.start_screen_active:
            return False
        
        moved = False
        
        if self.can_move(dx, dy):
            self.current_x += dx
            self.current_y += dy
            moved = True
            
            # Для gost режима считаем шаги только при действиях игрока
            if self.mode == 'gost':
                self._gost_count_step()
            
            # Сбрасываем таймер фиксации
            if self.lock_timer:
                self.lock_timer.cancel()
                self.lock_timer = None
                self.lock_scheduled = False
                
        elif dy == 1:  # Двигаемся вниз, но уперлись - сразу фиксируем
            # Для gost режима считаем шаг перед фиксированием
            if self.mode == 'gost':
                self._gost_count_step()
            self.lock_piece()
            return False
        
        # Перерисовываем только если что-то изменилось
        if moved:
            self.redraw()
        
        return moved



    def can_move(self, dx, dy):
        if not hasattr(self, 'current_piece') or not hasattr(self, 'current_x') or not hasattr(self, 'current_y'):
            return False
        
        if not getattr(self, 'current_piece', None):
            # нет фигуры — ничего не рисуем/не фиксируем
            return
        
        
        for i, row in enumerate(self.current_piece):
            for j, cell in enumerate(row):
                if cell:
                    new_x = self.current_x + j + dx
                    new_y = self.current_y + i + dy
                    
                    # Проверка границ
                    if new_x < 0 or new_x >= self.GRID_WIDTH:
                        return False
                    if new_y >= self.GRID_HEIGHT:
                        return False
                    if new_y >= 0 and self.grid[new_y][new_x]:
                        return False
        return True

    def lock_piece(self):
        # Добавляем 3 очка за приземление
        self.score += 3
        if hasattr(self, 'score_label'):
            self.score_label.text = f'Score: {self.score}'
        
        if self.mode == 'gost' and self.gost_level == 3:
            # Для уровня 3 при приземлении добавляем фигуру в список приземлённых
            if not hasattr(self, 'current_piece') or self.current_piece is None:
                return
                
            locked = []
            for i, row in enumerate(self.current_piece):
                for j, cell in enumerate(row):
                    if cell:
                        x, y = self.current_x + j, self.current_y + i
                        if 0 <= x < self.GRID_WIDTH and 0 <= y < self.GRID_HEIGHT:
                            locked.append((x, y, self.color))
                            self.grid[y][x] = self.color
                            # И добавляем их в набор невидимых клеток
                            self._invisible_cells.add((x, y))
            
            # Добавляем текущую фигуру в список приземлённых
            self.landed_pieces.append(locked)
            
            # Оставляем только последние 2 приземлённые фигуры
            if len(self.landed_pieces) > 2:
                self.landed_pieces = self.landed_pieces[-2:]
            
            # При приземлении делаем текущую фигуру видимой
            self.piece_landed = True
            self.current_piece_visible = True
            self.handle_gost_visibility()
            
            # Проверяем и удаляем полные строки (учитывая невидимые блоки)
            self.check_filled_lines_with_invisible_blocks()
            
            # Создаем новую фигуру
            self.spawn_new_piece()
            
            # Новая фигура появляется на поле
            self.piece_landed = False
            self.current_piece_visible = True
            self.handle_gost_visibility()
            
        elif self.mode == 'gost' and self.gost_level == 2:
            # Для уровня 2 при приземлении находим верхний слой каждого столбца
            self.piece_landed = True
            self.current_piece_visible = True
            self.handle_gost_visibility()
            
            # Сначала сохраняем фигуру в сетку как обычно
            if not hasattr(self, 'current_piece') or self.current_piece is None:
                return
                
            # Добавляем все блоки фигуры в сетку
            for i, row in enumerate(self.current_piece):
                for j, cell in enumerate(row):
                    if cell:
                        x, y = self.current_x + j, self.current_y + i
                        if 0 <= y < self.GRID_HEIGHT and 0 <= x < self.GRID_WIDTH:
                            self.grid[y][x] = self.color
                            # И добавляем их в набор невидимых клеток
                            self._invisible_cells.add((x, y))
            
            # Проверяем и удаляем полные строки (учитывая все блоки, включая невидимые)
            self.clear_lines()
            
            # Теперь оставляем только верхний слой каждого столбца
            for x in range(self.GRID_WIDTH):
                # Находим самую высокую позицию в столбце (минимальный y)
                top_y = None
                for y in range(self.GRID_HEIGHT):
                    if self.grid[y][x]:  # Если есть блок в позиции (x,y)
                        top_y = y
                        break  # Нашли самый верхний блок в столбце
                
                # Если нашли верхний блок, скрываем все блоки под ним
                if top_y is not None:
                    for y in range(top_y + 1, self.GRID_HEIGHT):
                        self.grid[y][x] = 0  # Удаляем блоки под верхним слоем
            
            self.spawn_new_piece()
            
        else:
            # Обычная обработка для других случаев
            if not hasattr(self, 'current_piece') or self.current_piece is None:
                return
                
            for i, row in enumerate(self.current_piece):
                for j, cell in enumerate(row):
                    if cell:
                        x, y = self.current_x + j, self.current_y + i
                        if 0 <= y < self.GRID_HEIGHT and 0 <= x < self.GRID_WIDTH:
                            self.grid[y][x] = self.color

            # Для других режимов просто проверяем и удаляем полные строки
            self.clear_lines()
            
            # Для gost уровня 1 при приземлении делаем фигуру видимой
            if self.mode == 'gost' and self.gost_level == 1:
                self.piece_landed = True
                self.current_piece_visible = True
                self.handle_gost_visibility()
            
            self.spawn_new_piece()

        
    
    def check_filled_lines_with_invisible_blocks(self):
        """Проверка и удаление полных строк с учетом невидимых блоков"""
        lines_to_clear = []
        
        # Для каждого ряда проверяем, полностью ли он заполнен (включая невидимые блоки)
        for y in range(min(len(self.grid), self.GRID_HEIGHT)):
            line_filled = True
            for x in range(self.GRID_WIDTH):
                # Проверяем, есть ли в этой ячейке либо видимый блок, либо невидимый блок
                cell_filled = False
                
                # Сначала проверяем обычную сетку
                if self.grid[y][x] != 0:
                    cell_filled = True
                # Затем проверяем набор невидимых блоков
                elif hasattr(self, '_invisible_cells') and (x, y) in self._invisible_cells:
                    cell_filled = True
                
                if not cell_filled:
                    line_filled = False
                    break
            
            if line_filled:
                lines_to_clear.append(y)
        
        # Удаляем заполненные линии
        for y in lines_to_clear:
            if 0 <= y < len(self.grid):
                # Удаляем линию
                del self.grid[y]
                # Вставляем пустую строку сверху
                self.grid.insert(0, [0 for _ in range(self.GRID_WIDTH)])
                
                # Обновляем набор невидимых ячеек для соответствия новой структуре сетки
                if hasattr(self, '_invisible_cells'):
                    # Создаем новый набор невидимых ячеек
                    new_invisible_cells = set()
                    for (ix, iy) in self._invisible_cells:
                        # Если невидимая ячейка была выше удаляемой строки, она сдвигается вниз
                        if iy < y:
                            new_invisible_cells.add((ix, iy + 1))
                        # Если невидимая ячейка была ниже удаляемой строки, она остается на месте
                        elif iy > y:
                            new_invisible_cells.add((ix, iy))
                        # Если невидимая ячейка была в удаляемой строке, она удаляется
                    self._invisible_cells = new_invisible_cells
        
        # Добавляем очки по новой системе
        if lines_to_clear:
            # Система очков: 100, 250, 600, 1400
            score_map = {1: 100, 2: 250, 3: 600, 4: 1400}
            base_score = score_map.get(len(lines_to_clear), len(lines_to_clear) * 400)
            
            # Применяем множитель комбо
            final_score = int(base_score * self.combo_multiplier)
            self.score += final_score
            
            # Увеличиваем множитель для следующего комбо
            self.combo_multiplier += 0.5
            
            if hasattr(self, 'score_label'):
                self.score_label.text = f'Score: {self.score}'
            
            # Проверяем и обновляем максимальный счет при каждом увеличении
            if hasattr(self, 'update_high_score'):
                self.update_high_score()
        else:
            # Сброс множителя если не очищены линии
            self.combo_multiplier = 1.0
    

    def decrease_gost_level(self):
        """Уменьшение уровня Gost"""
        if hasattr(self, 'gost_level'):
            self.gost_level = max(1, self.gost_level - 1)
            self.set_gost_level(self.gost_level)
            # Обновляем отображение на стартовом экране
            if hasattr(self, 'gost_level_label'):
                self.gost_level_label.text = f"Level: {self.gost_level}"

    def increase_gost_level(self):
        """Увеличение уровня Gost"""
        if hasattr(self, 'gost_level'):
            self.gost_level = min(3, self.gost_level + 1)
            self.set_gost_level(self.gost_level)
            # Обновляем отображение на стартовом экране
            if hasattr(self, 'gost_level_label'):
                self.gost_level_label.text = f"Level: {self.gost_level}"
        
      
    def create_start_screen(self):
        """Создание стартового экрана с адаптацией под экран"""
        print("create_start_screen called")
        
        # ОСТАНАВЛИВАЕМ МУЗЫКУ МЕНЮ
        from music_manager import music_manager
        music_manager.stop()
        
        if hasattr(self, 'start_screen'):
            self.remove_widget(self.start_screen)
            
        self.start_screen = RelativeLayout(size=self.size)
        
        if self.mode == 'gost':
            # Специальный стартовый экран для Gost
            title = Label(text="Gost mode", font_size=32 * self.scale,
                        pos_hint={'center_x': 0.5, 'center_y': 0.8})
            
            instruction = Label(text="Use ↓ or ▼▼\nto change difficulty\nPress ⭮ or Pause to start",
                            font_size=16 * self.scale,
                            pos_hint={'center_x': 0.5, 'center_y': 0.5})
            
            # Отображение текущего уровня
            self.gost_level_label = Label(text=f"Level: {self.gost_level}",
                                        font_size=18 * self.scale,
                                        pos_hint={'center_x': 0.68, 'center_y': 0.56})
            
            self.start_screen.add_widget(title)
            self.start_screen.add_widget(instruction)
            self.start_screen.add_widget(self.gost_level_label)
        else:
            # Обычный стартовый экран
            instruction = Label(text='Use the ← → buttons to change the speed Press ⭮ or Pause to start',
                            font_size=14 * self.scale,
                            pos_hint={'center_x': 0.5, 'center_y': 0.6})
            self.start_screen.add_widget(instruction)
        
        self.add_widget(self.start_screen)
        
        # Пытаемся загрузить сохраненную сессию, но только если это первый запуск
        if not hasattr(self, '_session_checked'):
            self._session_checked = True
            if self.check_saved_session():
                print("Found saved session, loading...")
                if self.load_game_session():
                    # Если сессия загружена, сразу начинаем игру
                    print("Session loaded successfully")
                    self.start_screen_active = False
                    self.game_started = True
                    self._session_loaded = True  # Добавляем флаг загрузки
                    try:
                        music_manager.play_game_music()
                    except:
                        pass
            else:
                print("No saved session found")
        
        self.redraw()
    
        
    
    def clear_lines(self):
        """Удаление заполненных строк. Учитывает невидимые клетки из self._invisible_cells."""
        lines_to_clear = []

        # helper: клетка считается заполненной если в grid есть значение или она отмечена как невидимая
        def cell_is_filled(y, x):
            try:
                if self.grid[y][x]:
                    return True
            except Exception:
                return False
            if hasattr(self, '_invisible_cells') and ((x, y) in self._invisible_cells):
                return True
            return False

        max_y = min(len(self.grid), getattr(self, 'GRID_HEIGHT', len(self.grid)))

        for y in range(max_y):
            filled = True
            for x in range(getattr(self, 'GRID_WIDTH', len(self.grid[y]))):
                if not cell_is_filled(y, x):
                    filled = False
                    break
            if filled:
                lines_to_clear.append(y)

        # Отладочная информация (выключи/комментируй при необходимости)
        if getattr(self, 'debug_clear_lines', False):
            print("clear_lines: found", lines_to_clear)
            if hasattr(self, '_invisible_cells'):
                print("clear_lines: invisibles before:", sorted(self._invisible_cells))

        if not lines_to_clear:
            self.combo_multiplier = 1.0
            return

        # Удаляем с конца, чтобы индексы не смещались
        lines_to_clear.sort(reverse=True)

        for y in lines_to_clear:
            if 0 <= y < len(self.grid):
                del self.grid[y]
                self.grid.insert(0, [0 for _ in range(getattr(self, 'GRID_WIDTH', len(self.grid[0])))])

                # Обновляем невидимые клетки
                if hasattr(self, '_invisible_cells'):
                    new_invisible = set()
                    for (ix, iy) in self._invisible_cells:
                        # приводим к int на всякий случай
                        try:
                            ix_i, iy_i = int(ix), int(iy)
                        except Exception:
                            continue
                        if iy_i < y:
                            # была выше удаляемой строки -> сдвигается вниз на 1
                            new_invisible.add((ix_i, iy_i + 1))
                        elif iy_i > y:
                            # была ниже -> остаётся
                            new_invisible.add((ix_i, iy_i))
                        # если iy_i == y -> удаляем (не добавляем)
                    self._invisible_cells = new_invisible

        # Очки / множитель (твоя логика)
        score_map = {1: 100, 2: 250, 3: 600, 4: 1400}
        base_score = score_map.get(len(lines_to_clear), len(lines_to_clear) * 400)
        final_score = int(base_score * getattr(self, 'combo_multiplier', 1.0))
        self.score = getattr(self, 'score', 0) + final_score
        self.combo_multiplier = getattr(self, 'combo_multiplier', 1.0) + 0.5

        if hasattr(self, 'score_label'):
            try:
                self.score_label.text = f'Score: {self.score}'
            except Exception:
                pass

        if hasattr(self, 'update_high_score'):
            try:
                self.update_high_score()
            except Exception:
                pass

        # Перерисовать поле
        try:
            self.redraw()
        except Exception:
            pass

        if getattr(self, 'debug_clear_lines', False) and hasattr(self, '_invisible_cells'):
            print("clear_lines: invisibles after:", sorted(self._invisible_cells))


            
    def redraw(self):
        if not hasattr(self, 'grid'):
            return
        
        # Очищаем все блоки
        self.clear_blocks()

        # Рисуем зафиксированные блоки (только если игра начата)
        if self.game_started:
            if self.mode == 'gost' and self.gost_level == 3:
                # Для уровня 3 — показываем только предыдущую приземлённую фигуру
                if len(self.landed_pieces) > 0:
                    # Рисуем только предыдущую приземлённую фигуру
                    prev_piece = self.landed_pieces[-1]
                    for (x, y, color) in prev_piece:
                        if 0 <= x < self.GRID_WIDTH and 0 <= y < self.GRID_HEIGHT:
                            self.draw_block(x, y, color)
            elif self.mode == 'gost' and self.gost_level == 2:
                # Для gost уровня 2 рисуем только верхний слой каждого столбца
                for x in range(self.GRID_WIDTH):
                    # Находим самую высокую позицию в столбце (минимальный y)
                    top_y = None
                    for y in range(self.GRID_HEIGHT):
                        if self.grid[y][x]:  # Если есть блок в позиции (x,y)
                            top_y = y
                            break  # Нашли самый верхний блок в столбце
                    
                    # Если нашли верхний блок, рисуем его
                    if top_y is not None:
                        self.draw_block(x, top_y, self.grid[top_y][x])
            else:
                # Для остальных случаев рисуем все блоки как обычно
                for y, row in enumerate(self.grid):
                    for x, cell in enumerate(row):
                        if cell:
                            self.draw_block(x, y, cell)

        # Рисуем текущую фигуру (только если игра начата и не game over)
        if (self.game_started and hasattr(self, 'current_piece') and hasattr(self, 'current_x') and 
            hasattr(self, 'current_y') and hasattr(self, 'color') and not self.game_over):
            
            if not getattr(self, 'current_piece', None):
                # нет фигуры — ничего не рисуем/не фиксируем
                return
            
            # Для gost уровня 3 рисуем текущую фигуру только если она видима
            if self.mode == 'gost' and self.gost_level == 3 and self.current_piece_visible:
                for i, row in enumerate(self.current_piece):
                    for j, cell in enumerate(row):
                        if cell:
                            self.draw_block(self.current_x + j, self.current_y + i, self.color)
            elif not (self.mode == 'gost' and not self.current_piece_visible):
                # Для других режимов или если фигура видимая, рисуем её
                for i, row in enumerate(self.current_piece):
                    for j, cell in enumerate(row):
                        if cell:
                            self.draw_block(self.current_x + j, self.current_y + i, self.color)

        self.draw_grid()

    def draw_grid(self):
        """Отдельный метод для отрисовки сетки"""
        # Очищаем только сетку, не всю canvas.after
        if hasattr(self, '_grid_lines'):
            for line in self._grid_lines:
                if line in self.canvas.after.children:
                    self.canvas.after.remove(line)
        
        self._grid_lines = []
        
        with self.canvas.after:
            Color(0.5, 0.5, 0.5, 0.3)
            radius = self.CELL_SIZE * 0.1
            for y in range(self.GRID_HEIGHT + 1):
                if y == 0 or y == self.GRID_HEIGHT:
                    line = Line(points=[self.GRID_X_OFFSET, 
                            self.GRID_Y_OFFSET + y * self.CELL_SIZE,
                            self.GRID_X_OFFSET + self.GRID_WIDTH * self.CELL_SIZE,
                            self.GRID_Y_OFFSET + y * self.CELL_SIZE], width=2)
                    self._grid_lines.append(line)
                else:
                    line = Line(points=[self.GRID_X_OFFSET + radius, 
                            self.GRID_Y_OFFSET + y * self.CELL_SIZE,
                            self.GRID_X_OFFSET + self.GRID_WIDTH * self.CELL_SIZE - radius,
                            self.GRID_Y_OFFSET + y * self.CELL_SIZE])
                    self._grid_lines.append(line)
            
            for x in range(self.GRID_WIDTH + 1):
                if x == 0 or x == self.GRID_WIDTH:
                    line = Line(points=[self.GRID_X_OFFSET + x * self.CELL_SIZE,
                            self.GRID_Y_OFFSET,
                            self.GRID_X_OFFSET + x * self.CELL_SIZE,
                            self.GRID_Y_OFFSET + self.GRID_HEIGHT * self.CELL_SIZE], width=2)
                    self._grid_lines.append(line)
                else:
                    line = Line(points=[self.GRID_X_OFFSET + x * self.CELL_SIZE,
                            self.GRID_Y_OFFSET + radius,
                            self.GRID_X_OFFSET + x * self.CELL_SIZE,
                            self.GRID_Y_OFFSET + self.GRID_HEIGHT * self.CELL_SIZE - radius])
                    self._grid_lines.append(line)
                    
    def rotate(self):
        if self.start_screen_active:
            self.start_game(None)
            return
            
        if self.game_over:
            # При game over кнопка поворота возобновляет игру
            self.resume_game_after_game_over()
            return
            
        if self.paused:
            return
        
        # Выполняем поворот
        rotated = list(zip(*self.current_piece[::-1]))
        old_piece = self.current_piece
        self.current_piece = [list(row) for row in rotated]
        
        # Для gost режима считаем шаг после поворота
        if self.mode == 'gost':
            self._gost_count_step()
        
        # Проверка на возможность поворота
        if not self.can_move(0, 0):
            # Пытаемся сдвинуть для избежания коллизии
            kicks = [0, -1, 1, -2, 2]
            rotated_back = False
            for dx in kicks:
                self.current_x += dx
                if self.can_move(0, 0):
                    break
                self.current_x -= dx
            else:
                # Если не можем разместить, возвращаем старую фигуру
                self.current_piece = old_piece
                rotated_back = True
            
            if not rotated_back:
                self.redraw()
        else:
            self.redraw()

    def hard_drop(self):
        if self.game_over or self.paused or self.start_screen_active:
            return

        if self.mode == 'gost':
            while self.can_move(0, 1):
                self.current_y += 1
            self.lock_piece()
            self.redraw()
            return
        
        while self.can_move(0, 1):
            self.current_y += 1
        self.lock_piece()
        self.redraw()

    def toggle_pause(self):
        print(f"toggle_pause called: start_screen_active={self.start_screen_active}, game_over={self.game_over}, game_started={self.game_started}")
        
        if self.start_screen_active:
            print("Starting game from start screen")
            self.start_game(None)
            return
            
        if self.game_over:
            # При game over кнопка паузы возобновляет игру
            print("Resuming game after game over")
            self.resume_game_after_game_over()
            return
        
        # Если игра не начата, но стартовый экран уже убран - начинаем игру
        if not self.game_started and not self.start_screen_active:
            print("Game not started but start screen removed - starting game")
            self.start_game(None)
            return
            
        # Просто переключаем состояние паузы
        print(f"Toggling pause: {self.paused} -> {not self.paused}")
        self.paused = not self.paused
        
        # Перерисовываем чтобы обновить отображение
        if not self.paused:
            self.redraw()


    def update_ui_language(self):
        """Обновление текстов интерфейса согласно текущему языку"""
        if hasattr(self, 'score_label'):
            score_text = settings.translations[settings.language].get('score', 'Score')
            self.score_label.text = f"{score_text}: {self.score}"
        
        if hasattr(self, 'preview_label') and settings.show_next:
            next_text = settings.translations[settings.language].get('next', 'Next')
            self.preview_label.text = next_text


    def resume_game_after_game_over(self):
        """Возобновление игры после game over"""
        self.game_over = False
        self.game_over_displayed = False
        self.falling_letters = []  # Очищаем падающие буквы
        self.paused = False
        
        # Очищаем сетку
        self.grid = [[0 for _ in range(self.GRID_WIDTH)] for _ in range(self.GRID_HEIGHT)]
        
        # Создаем новую фигуру
        self.next_piece = self.random_piece()
        self.spawn_new_piece()
        self.update_next_preview()
        
        # Обновляем счет
        if hasattr(self, 'score_label'):
            self.score_label.text = 'Score: 0'
        self.score = 0
        
        try:
            music_manager.play_game_music()
        except:
            pass
        self.redraw()

    def start_game(self, instance):
        """Начинаем игру с правильным управлением музыкой"""
        # Останавливаем музыку меню перед запуском игры
        music_manager.stop()
        
        # Сбрасываем счетчик поражений
        self.defeat_count = 0
        
        try:
            from daily_tasks import mark_task_completed
            mark_task_completed('play_mode')
        except Exception as e:
            print("Failed to mark task play_mode:", e)

        # Обновляем фон перед началом игры
        if hasattr(self, 'bg_rect'):
            try:
                self.bg_rect.source = settings.background
                self.bg_rect.texture = None
            except:
                pass
        
        # Начинаем музыку игры (если она еще не играет)
        if not (hasattr(self, 'sound') and self.sound and self.sound.state == 'play'):
            music_manager.play_game_music()
            
        print("start_game called")
        if hasattr(self, 'start_screen'):
            self.remove_widget(self.start_screen)
            
        self.start_screen_active = False
        self.game_started = True
        
        # Убедимся, что играет музыка (через music_manager)
        try:
            music_manager.play_game_music()
        except:
            # резервный fallback на локальный объект, если он есть
            if hasattr(self, 'sound') and self.sound:
                try:
                    if getattr(self.sound, 'state', None) != 'play':
                        self.sound.play()
                    else:
                        try:
                            self.sound.seek(0)
                        except:
                            pass
                except:
                    pass

        
        # Только при новой игре удаляем сохранение, при загрузке оставляем
        if not hasattr(self, '_session_loaded') or not self._session_loaded:
            try:
                session_file = self.get_session_filename()
                if os.path.exists(session_file):
                    os.remove(session_file)
            except:
                pass
        else:
            print("Resuming loaded session")
        
        # где-то в блоке старта игры:
        self._play_seconds = 0
        if hasattr(self, '_play_timer') and self._play_timer:
            self._play_timer.cancel()
        self._play_timer = Clock.schedule_interval(self._tick_play_seconds, 1.0)

        # Сбрасываем флаг загрузки сессии
        if hasattr(self, '_session_loaded'):
            delattr(self, '_session_loaded')
        
        self.debug_clear_lines = True   # включаем отладочный вывод (если используешь его в clear_lines)
        if not hasattr(self, '_invisible_cells'):
            self._invisible_cells = set()
        
        

        self.redraw()

    
    
    
    def show_start_screen_after_game_over(self):
        self.game_over = False
        self.game_started = False
        self.start_screen_active = True
        self.grid = [[0 for _ in range(self.GRID_WIDTH)] for _ in range(self.GRID_HEIGHT)]
        self.score = 0
        if hasattr(self, 'score_label'):
            self.score_label.text = 'Score: 0'
        self.next_piece = self.random_piece()
        if hasattr(self, 'start_screen'):
            self.remove_widget(self.start_screen)
        self.create_start_screen()
        try:
            music_manager.stop()
        except:
            pass
        self.redraw()
    
        
    def show_game_over(self):
        # Очищаем таймеры
        self.cleanup_timers()
        
        # Обновляем максимальный счет в профиле
        self.update_high_score()
        
        if self.mode == 'gost':
            # Для Gost режима показываем фигуры на 2 секунды
            self.is_visible = True
            self.redraw()
            Clock.schedule_once(lambda dt: self.show_game_over(), 2)
            return
        
        try:
            music_manager.stop()
        except:
            pass

        # Вычисляем цену возрождения: 3, 7, 15, 31...
        # Формула: 2^(n+1) - 1, где n - количество поражений
        revival_cost = ((self.defeat_count + 2) ** 2)
        
        # Создаем popup только если его еще нет
        if not hasattr(self, 'game_over_popup') or not self.game_over_popup:
            self.game_over_popup = Popup(title="Continue the game?", 
                                    size_hint=(0.8, 0.5))
            
            layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
            
            # Отображаем актуальную цену возрождения
            if currency.amount >= revival_cost:
                layout.add_widget(Label(text=f"Continue for {revival_cost}$ coins? (You have: {currency.amount})"))
                
                btn_box = BoxLayout(spacing=10)
                
                # Кнопка оплаты монетами
                continue_btn = Button(text=f"Yes ({revival_cost}$ coins)")
                continue_btn.bind(on_press=self.continue_game)
                btn_box.add_widget(continue_btn)
                
                # Кнопка просмотра рекламы
                ad_btn = Button(text="Watch ad(+10$ coins)")
                ad_btn.bind(on_press=lambda x: self.watch_ad_for_continue())
                btn_box.add_widget(ad_btn)
                
                close_btn = Button(text="No")
                close_btn.bind(on_press=self.close_game_over)
                btn_box.add_widget(close_btn)
                
                layout.add_widget(btn_box)
            else:
                layout.add_widget(Label(text=f"Not enough coins to respawn! Required: {revival_cost}\nYou have: {currency.amount}"))
                
                btn_box = BoxLayout(spacing=10)
                
                # Кнопка просмотра рекламы
                ad_btn = Button(text="Watch ad(+10$ coins)")
                ad_btn.bind(on_press=lambda x: self.watch_ad_for_continue())
                btn_box.add_widget(ad_btn)
                
                close_btn = Button(text="No")
                close_btn.bind(on_press=self.close_game_over)
                btn_box.add_widget(close_btn)
                
                layout.add_widget(btn_box)
            
            self.game_over_popup.content = layout
            self.game_over_popup.open()
        
    def continue_game_with_ad(self):
        """Возрождение после просмотра рекламы"""
        self.game_over = False
        
        # Безопасно закрываем popup если он существует
        if hasattr(self, 'game_over_popup') and self.game_over_popup:
            try:
                self.game_over_popup.dismiss()
            except:
                pass
            self.game_over_popup = None
        
        # Очищаем верхнюю половину поля
        mid_point = self.GRID_HEIGHT // 2
        for y in range(mid_point):
            self.grid[y] = [0] * self.GRID_WIDTH
        
        self.redraw()
        
        # Воспроизводим музыку через music_manager
        try:
            music_manager.play_game_music()
        except:
            pass
        
        # ОБНОВЛЯЕМ ОТОБРАЖЕНИЕ МОНОЕТ ПОСЛЕ ВОССТАНОВЛЕНИЯ
        self.update_coin_display()

    # Добавь метод для обновления максимального счета:
    def update_high_score(self):
        """Обновляет максимальный счет в профиле"""
        if hasattr(self, 'score') and self.score > 0:
            profile.update_high_score(self.mode, self.score)
    
    def close_game_over(self, instance):
        # Безопасно закрываем popup
        if hasattr(self, 'game_over_popup') and self.game_over_popup:
            try:
                self.game_over_popup.dismiss()
            except:
                pass
            self.game_over_popup = None
        
        # Показываем анимацию поражения
        self.show_defeat_animation()
    
    def update_game_over_popup_contents(self):
        """(Re)построить содержимое self.game_over_popup по текущему состоянию."""
        if not hasattr(self, 'game_over_popup') or not self.game_over_popup:
            return

        # цена возрождения: 4,9,16,... => (defeat_count + 2)**2
        revival_cost = (self.defeat_count + 2) ** 2

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # Верхний лейбл с информацией
        if currency.amount >= revival_cost:
            layout.add_widget(Label(text=f"Continue for {revival_cost}$ coins? (You have: {currency.amount})"))
            btn_box = BoxLayout(spacing=10)

            continue_btn = Button(text=f"Yes ({revival_cost}$ coins)")
            # привяжем обработчик, он ожидает аргумент instance
            continue_btn.bind(on_press=self.continue_game)
            btn_box.add_widget(continue_btn)

            ad_btn = Button(text="Watch ad(+10$ coins)")
            ad_btn.bind(on_press=lambda x: self.watch_ad_for_continue())
            btn_box.add_widget(ad_btn)

            close_btn = Button(text="No")
            close_btn.bind(on_press=self.close_game_over)
            btn_box.add_widget(close_btn)

            layout.add_widget(btn_box)
        else:
            layout.add_widget(Label(text=f"Not enough coins to respawn! Required: {revival_cost}\nYou have: {currency.amount}"))
            btn_box = BoxLayout(spacing=10)

            ad_btn = Button(text="Watch ad(+10$ coins)")
            ad_btn.bind(on_press=lambda x: self.watch_ad_for_continue())
            btn_box.add_widget(ad_btn)

            close_btn = Button(text="No")
            close_btn.bind(on_press=self.close_game_over)
            btn_box.add_widget(close_btn)

            layout.add_widget(btn_box)

        # подставляем в popup (перезаписываем контент)
        try:
            self.game_over_popup.content = layout
        except Exception as e:
            print("Error updating game_over_popup contents:", e)


    def _show_game_over_popup(self):
        """Показать popup возрождения (создаёт popup один раз и обновляет его содержимое)."""
        # создаём popup если ещё нет
        if not hasattr(self, 'game_over_popup') or not self.game_over_popup:
            self.game_over_popup = Popup(title="Continue the game?", size_hint=(0.8, 0.5))
        # обновляем/построим контент
        self.update_game_over_popup_contents()
        # и открываем (если ещё не открыт)
        try:
            self.game_over_popup.open()
        except Exception:
            pass
    
    def continue_game(self, instance):
        """Оплатить и продолжить игру — списываем корректную сумму."""
        # цена возрождения: 4,9,16,...
        revival_cost = (self.defeat_count + 2) ** 2

        if currency.amount < revival_cost:
            self.show_not_enough_coins_popup()
            return

        if not currency.spend(revival_cost):
            # не смог списать — на всякий случай
            self.show_not_enough_coins_popup()
            return

        # успешно списали — фиксируем поражение как использованное возрождение
        self.defeat_count += 1

        self.game_over = False
        if hasattr(self, 'game_over_popup') and self.game_over_popup:
            try:
                self.game_over_popup.dismiss()
            except:
                pass
            self.game_over_popup = None

        # Очищаем верхнюю половину поля (как у тебя было реализовано)
        mid_point = self.GRID_HEIGHT // 2
        for y in range(mid_point):
            self.grid[y] = [0] * self.GRID_WIDTH

        self.redraw()
        # обновляем отображение монет в меню/магазине
        try:
            self.update_coin_display_in_menu()
            # ДОБАВЬТЕ ОБНОВЛЕНИЕ ПОСЛЕ ВОССТАНОВЛЕНИЯ
            self.update_coin_display()
        except:
            pass

        try:
            from shop import shop
            shop.update_all_tabs()
        except:
            pass

        try:
            music_manager.play_game_music()
        except:
            pass


    def show_defeat_animation(self):
        """Анимация поражения перед возвратом к стартовому экрану"""
        # Можно добавить визуальные эффекты здесь
        Clock.schedule_once(lambda dt: self.show_start_screen_after_game_over(), 1)
    
    def restart_game(self):
        # Полный сброс состояния
        self.game_over = False
        self.game_over_displayed = False
        self.paused = False
        self.score = 0
        self.falling_letters = []  # Очищаем падающие буквы
        self.start_screen_active = False  # Убираем стартовый экран
        self.game_started = True  # Игра активна
        
        # Пересоздаем сетку
        self.grid = [[0 for _ in range(self.GRID_WIDTH)] for _ in range(self.GRID_HEIGHT)]
        
        # Обновляем счет
        if hasattr(self, 'score_label'):
            self.score_label.text = 'Score: 0'
        
        # Создаем новые фигуры
        self.next_piece = self.random_piece()
        self.spawn_new_piece()
        self.update_next_preview()
        
        try:
            music_manager.play_game_music()
        except:
            pass
        
        
        # Перерисовываем
        self.redraw()
        Clock.schedule_once(lambda dt: self.show_start_screen_after_game_over(), 1)
    
    def cleanup_timers(self):
        """Очистка всех таймеров"""
        if hasattr(self, 'lock_timer') and self.lock_timer:
            self.lock_timer.cancel()
            self.lock_timer = None
        if hasattr(self, 'game_over_timer') and self.game_over_timer:
            self.game_over_timer.cancel()
            self.game_over_timer = None
        if hasattr(self, '_play_timer') and self._play_timer:
            try:
                self._play_timer.cancel()
            except Exception:
                pass
            self._play_timer = None

def get_blocks_screen(switch_to_menu, mode='normal'):
    game = blocksGame(switch_to_menu)
    game.set_game_mode(mode)
    return game