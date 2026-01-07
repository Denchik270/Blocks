import json
import os

class GameSettings:
    def __init__(self):
        # Инициализируем все значения по умолчанию
        self.set_defaults()
        # Затем загружаем сохраненные настройки
        self.load()

    def set_defaults(self):
        """Устанавливает значения по умолчанию"""
        self.background = 'assets/menu1.jpg'
        self.menu_background = 'assets/menu1.jpg'   # фон для меню (не трогаем при выборе фона игры)
        self.game_background = 'assets/fon1.png'   # фон для игры (выбирается в инвентаре)
        self.volume = 1.0  # Общая громкость по умолчанию
        self.menu_volume = 1.0
        self.game_volume = 1.0
        self.game_mode = 'normal'
        self.show_next = True
        self.language = 'en'
        self.color_patterns = {}

        # Переводы
        self.translations = {
            'en': {
                'language': 'Language',
                'score': 'Score',
                'next': 'Next',
                'pause': 'Pause',
                'menu': 'Menu',
                'restart': 'Restart',
                'sound': 'Sound',
                'settings': 'Settings',
                'help_text': """
        [b]HOW TO PLAY[/b]

        - Use the ← → buttons to change the speed 
        - Press ⭮ or Pause to start

        The background for the game is selected in: 
        Store → My inventory

        [b]Ghost Mode:[/b]
        Use ↓ or ▼▼ to change difficulty

        [b]Controls:[/b]
        ← → - Move left/right
        ↓ - Move down faster
        ⭮ - Rotate piece
        ▼▼ - Hard drop (instant drop)

        [b]Game Modes:[/b]
        1. Normal - Classic blocks
        2. Ghost - Pieces disappear after steps
        3. Lightning - Very fast gameplay 

        [b]Scoring:[/b]
        - Single line: 100 points
        - Double lines: 250 points
        - Triple lines: 600 points
        - Quadruple lines: 1400 points

        [b]Ghost Mode Levels:[/b]
        1. Easy - Visible for 4 steps
        2. Medium - Visible for 2 steps
        3. Hard - Visible for 0 step
        """
            },
            'ru': {
                'language': 'Язык',
                'score': 'Счёт',
                'next': 'След.',
                'pause': 'Пауза',
                'menu': 'Меню',
                'restart': 'Рестарт',
                'sound': 'Звук',
                'settings': 'Настройки',
                'help_text': """
        [b]КАК ИГРАТЬ[/b]

        - Используйте кнопки ← → для перемещения фигуры
        - Нажмите ⭮ или «Пауза», чтобы начать игру

        Фон игры выбирается в:
        Магазин → Мой инвентарь

        [b]Режим «Призрак»:[/b]
        Используйте ↓ или ▼▼, чтобы изменить сложность

        [b]Управление:[/b]
        ← → - Движение влево/вправо
        ↓ - Ускоренное падение
        ⭮ - Поворот фигуры
        ▼▼ - Жёсткий дроп (моментальное падение)

        [b]Режимы игры:[/b]
        1. Обычный — Классический Тетрис
        2. Призрак — Фигуры исчезают через несколько шагов
        3. Молния — Очень быстрая игра

        [b]Очки:[/b]
        - 1 линия: 100 очков
        - 2 линии: 250 очков
        - 3 линии: 600 очков
        - 4 линии: 1400 очков

        [b]Уровни режима «Призрак»:[/b]
        1. Лёгкий — фигура видна 4 шагов
        2. Средний — фигура видна 2 шага
        3. Сложный — фигура видна 0 шаг
        
        
        """
            }
        }

        self.piece_colors = {
            'I': [1, 0, 0, 1],
            'O': [0, 1, 0, 1],
            'T': [0, 0, 1, 1],
            'S': [1, 1, 0, 1],
            'Z': [1, 0, 1, 1],
            'J': [0, 1, 1, 1],
            'L': [1, 0.5, 0, 1]
        }

        # Достижения/профиль
        self.unlocked_backgrounds = ['assets/fon1.png']
        self.unlocked_avatars = ['assets/default_avatar.png']

        # Музыка
        self.menu_music = 'assets/dream-pop-lofi-317545.mp3'
        self.game_music = 'assets/dream-pop-lofi-317545.mp3'
        self.unlocked_menu_tracks = ['assets/dream-pop-lofi-317545.mp3']
        self.unlocked_game_tracks = ['assets/dream-pop-lofi-317545.mp3']
        self.sequential_playback = False

    def save(self):
        data = {
            'piece_colors': self.piece_colors,
            'color_patterns': self.color_patterns,
            'unlocked_backgrounds': self.unlocked_backgrounds,
            'unlocked_avatars': self.unlocked_avatars,
            'volume': self.volume,
            'menu_volume': self.menu_volume,
            'game_volume': self.game_volume,
            'game_mode': self.game_mode,
            'show_next': self.show_next,
            'language': self.language,
            'menu_music': self.menu_music,
            'game_music': self.game_music,
            'unlocked_menu_tracks': self.unlocked_menu_tracks,
            'unlocked_game_tracks': self.unlocked_game_tracks,
            'sequential_playback': self.sequential_playback,
            'menu_background': self.menu_background,
            'game_background': self.game_background,
            'color_patterns': self.color_patterns
        }
        if not os.path.exists('saves'):
            os.makedirs('saves')
        with open('saves/settings.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        try:
            if os.path.exists('saves/settings.json'):
                with open('saves/settings.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Обновляем только те атрибуты, которые есть в файле
                    for key, value in data.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
        except Exception:
            # При ошибке просто оставляем значения по умолчанию
            pass


settings = GameSettings()
