import os
os.environ["KIVY_AUDIO"] = "sdl2"

from daily_tasks import DailyTasksScreen

import hashlib
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.core.window import Window
from blocks_game import get_blocks_screen
from kivy.uix.image import Image
from kivy.animation import Animation
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock
from profile1 import profile
from currency import currency
from help import HelpScreen
from settings import SettingsScreen
from config import settings
from kivy.uix.label import Label
from music_manager import music_manager
from shop import shop
from ads import AD_MANAGER
import random
from pathlib import Path
import sys

def get_expected_sha256():
    """Считывает ожидаемый SHA256 из sha256.txt"""
    try:
        path = Path(__file__).parent / "keys/sha256.txt"
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip().replace(":", "").upper()
    except Exception as e:
        print(f"⚠️ Не удалось прочитать sha256.txt: {e}")
        return None

def _sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def _apk_path_on_android():
    """Пытаемся получить путь к APK через pyjnius (работает на Android)."""
    try:
        try:
            from jnius import autoclass
        except ImportError:
            autoclass = lambda x: None  # безопасный заглушка

        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        # Попробуем несколько способов получить путь к apk
        apk_path = None
        try:
            apk_path = activity.getPackageCodePath()
        except Exception:
            pass
        if not apk_path:
            try:
                ApplicationInfo = autoclass('android.content.pm.ApplicationInfo')
                app_info = activity.getApplicationInfo()
                apk_path = app_info.sourceDir
            except Exception:
                pass
        return apk_path
    except Exception as e:
        # pyjnius отсутствует (не на Android или не установлено) — возвращаем None
        # print("pyjnius unavailable:", e)
        return None

def verify_apk_signature():
    """
    Безопасно проверяет SHA256 подпись:
      - на Android: берёт путь к APK через pyjnius и считает SHA256 APK.
      - при локальной разработке (не Android) — пропускает проверку (или можно опционально сравнить main.py).
    """
    try:
        expected = get_expected_sha256()
        if not expected:
            print("⚠️ Нет эталонного SHA256 — проверка пропущена.")
            return True

        # Попробуем получить apk_path (только на Android должно сработать)
        apk_path = _apk_path_on_android()

        if apk_path:
            # На устройстве сравниваем SHA от самого apk
            print("ℹ️ Проверяем SHA256 APK по пути:", apk_path)
            actual = _sha256_of_file(apk_path)
            print("🧩 Текущий SHA256 (APK):", actual)
            if actual == expected:
                print("✅ Подпись APK прошла проверку.")
                return True
            else:
                print("❌ Подпись APK не совпадает!")
                return False
        else:
            # Мы, видимо, в режиме разработки/PC — пропускаем проверку.
            # (Альтернатива: вычислять SHA main.py и сравнивать с тестовым значением)
            print("⚠️ APK не найден (не на Android). Пропускаем проверку подписи в режиме разработки.")
            return True

    except Exception as e:
        print(f"Ошибка при проверке подписи: {e}")
        return False

def check_file_integrity():
    key_files = ["main.py", "config.py", "settings.py", "shop.py", "ads.py", "blocks_game.py"]
    for file in key_files:
        path = Path(__file__).parent / file
        if not path.exists():
            print(f"⚠️ Файл {file} отсутствует!")
            sys.exit(0)
        # Проверяем только контрольную сумму
        try:
            with open(path, "rb") as f:
                data = f.read()
            # Простая проверка — не пустой ли файл
            if len(data) < 50:
                print(f"🚨 Файл {file} подозрительно короткий! Закрытие приложения.")
                sys.exit(0)
        except Exception as e:
            print(f"Ошибка при проверке {file}: {e}")
            sys.exit(0)



from kivy.utils import platform

if platform == "android":
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    AdsBridge = autoclass('org.kivy.yourapp.AdsBridge')  # ⚠️ замени yourapp на имя пакета
    bridge = AdsBridge(PythonActivity.mActivity)
    
    from ads import AD_MANAGER
    AD_MANAGER.android_bridge = bridge


Window.size = (480, 800)

def refresh_after_ad():
    shop.update_all_tabs()
    App.get_running_app().root.get_screen('menu').update_coin_display()





class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Фон
        with self.canvas.before:
            self.bg_color = Color(1, 0.95, 0.6, 1)  # мягкий жёлтый
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)

        self.bind(size=self._update_rect, pos=self._update_rect)

        # Логотип
        layout = BoxLayout(orientation='vertical')
        self.logo = Label(
            text="BrainUp",
            font_size=50,
            color=(1, 1, 1, 0),  # прозрачный в начале
            bold=True
        )
        layout.add_widget(self.logo)
        self.add_widget(layout)

        # Частицы
        self.particles = []
        with self.canvas:
            for _ in range(22):
                r, g, b = random.random(), random.random(), random.random()
                col = Color(r, g, b, 0)  # альфа = 0 (появятся анимацией)
                rect = Rectangle(
                    pos=(random.randint(0, int(self.width)), random.randint(0, int(self.height))),
                    size=(5 * (1 + random.random()), 5 * (1 + random.random()))
                )
                self.particles.append({'color': col, 'rect': rect})

        # Запуск анимаций
        Clock.schedule_once(self.start_animations, 0.1)
        Clock.schedule_once(self.fade_and_switch_to_menu, 4.5)


    def _update_rect(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def start_animations(self, dt):
        # Появление логотипа
        anim_show = Animation(color=(1, 1, 1, 1), duration=1.2)
        anim_size = Animation(font_size=70, duration=1.2)
        (anim_show & anim_size).start(self.logo)

        # Прыгающий логотип
        anim_pulse = (
            Animation(font_size=80, t='out_elastic', duration=1.0) +
            Animation(font_size=70, t='out_elastic', duration=1.0)
        )
        anim_pulse.repeat = True
        anim_pulse.start(self.logo)

        # Фон — плавная смена цветов
        self.animate_bg_color()

        # Анимации частиц
        for p in self.particles:
            Animation(a=1.0, duration=0.8).start(p['color'])  # появление
            self._animate_particle(p)

    def animate_bg_color(self):
        # Цветовая палитра
        colors = [
            (1.0, 0.85, 0.9),   # розово-жёлтый (теплый пастельный)
            (1.0, 0.75, 0.5),   # светло-оранжевый
            (1.0, 0.55, 0.2),   # ярко-оранжевый
            (0.85, 0.5, 0.2),   # ярко-оранжевый
            (0.7, 0.4, 0.2),    # мягкий коричневый
        ]

        duration = 2.0
        total_time = 0
        for r, g, b in colors:
            anim = Animation(r=r, g=g, b=b, duration=duration)
            anim.start(self.bg_color)
            total_time += duration
        Clock.schedule_once(lambda dt: self.animate_bg_color(), total_time)

    def _animate_particle(self, p):
        # Циклическое движение
        tx = random.randint(0, int(self.width))
        ty = random.randint(0, int(self.height))
        dur = 2.0 + random.random() * 2.0
        anim = Animation(pos=(tx, ty), duration=dur)

        def _on_complete(anim_obj, widget):
            self._animate_particle(p)  # повторяем движение
        anim.bind(on_complete=_on_complete)
        anim.start(p['rect'])

    def fade_and_switch_to_menu(self, dt):
        # Исчезновение логотипа
        fade_logo = Animation(color=(1, 1, 1, 0), duration=0.6)
        fade_logo.start(self.logo)

        # Затемнение фона
        fade_bg = Animation(r=0, g=0, b=0, duration=0.6)
        fade_bg.start(self.bg_color)

        # Частицы исчезают
        for p in self.particles:
            Animation(a=0.0, duration=0.6).start(p['color'])
            Animation(size=(0, 0), duration=0.6).start(p['rect'])

        # Переход в меню после fade-out
        def _switch(*_):
            try:
                self.manager.current = 'menu'
            except Exception:
                pass
        fade_bg.bind(on_complete=_switch)


    



class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        bg_path = getattr(settings, 'menu_background', 'assets/menu1.jpg')
        if not os.path.exists(bg_path):
            bg_path = 'assets/menu1.jpg'
        with self.canvas.before:
            self.bg_rect = Rectangle(source=bg_path, size=self.size, pos=self.pos)
        self.bind(size=self.update_bg, pos=self.update_bg)
        
        # Основной лайаут с отступами
        layout = BoxLayout(orientation='vertical', spacing=20, padding=[20, 40, 20, 40])
        
        Clock.schedule_once(lambda dt: music_manager.play_menu_music())
        
        # Кнопка профиля 
        btn_size = int(50 * Window.width / 480)  # Адаптивный размер
        
        profile_layout = BoxLayout(size_hint=(1, None), height=btn_size)
        
        # Кнопка help в левом углу
        help_btn = Button(
            background_normal='assets/help_icon.png',
            background_down='assets/help_icon.png',
            background_color=(1,1,1,1),
            border=(0,0,0,0),
            size_hint=(None, None),
            size=(btn_size, btn_size),
            pos_hint={'x': 0}
        )

        help_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'help'))
        
        # Кнопка настроек (шестеренка)
        settings_btn = Button(
            background_normal='assets/settings_icon.png',
            background_down='assets/settings_icon.png',
            background_color=(1,1,1,1),
            border=(0,0,0,0),
            size_hint=(None, None),
            size=(btn_size, btn_size),
            pos_hint={'right': 1, 'top': 0.85}
        )
        settings_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'settings'))
        
        # Кнопка профиля
        self.profile_btn = Button(
            background_normal=profile.avatar,
            background_down=profile.avatar,
            background_color=(1,1,1,1),
            border=(0,0,0,0),
            size_hint=(None, None),
            size=(btn_size, btn_size),
            pos_hint={'right': 1, 'top': 1}
        )

        self.profile_btn.bind(on_press=lambda x: profile.show_profile_popup())
        # **Эта строка НЕ должна быть удалена** – без неё кнопка бы не появилась
        profile_layout.add_widget(self.profile_btn)
        
        profile_layout.add_widget(help_btn)
        profile_layout.add_widget(Label())  # Пустое пространство
        profile_layout.add_widget(settings_btn)
        layout.add_widget(profile_layout)
        
        #Кнопка Магазина
        shop_btn = Button(
            background_normal='assets/store_icon.png',
            background_down='assets/store_icon.png',
            background_color=(1,1,1,1),
            border=(0,0,0,0),
            size_hint=(None, None),
            size=(btn_size, btn_size),
            pos_hint={'center_x': 0.5, 'y': 0.1}
        )
        shop_btn.bind(on_press=lambda x: shop.open())
        profile_layout.add_widget(shop_btn)
        
        # Кнопка blocks (переименованная в Offline)
        offline_btn = Button(
            text='Game',
            font_size='24sp',
            size_hint=(1, None),
            height=80,
            pos_hint={'center_x': 0.5, 'y': 0.1},
            background_normal='',
            background_down='',
            background_color=(0.2, 0.6, 0.8, 1),
            color=(1, 1, 1, 1),
            border=(20, 20, 20, 20)
        )
        offline_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'mode_select'))
        
        layout.add_widget(Label())  # Пустое пространство
        layout.add_widget(Label())  # Пустое пространство
        layout.add_widget(offline_btn)
        
        self.add_widget(layout)
        
        # Кнопка ежедневных заданий
        tasks_btn = Button(
            background_normal='assets/tasks_icon.png' if os.path.exists('assets/tasks_icon.png') else '',
            text="Tasks" if not os.path.exists('assets/tasks_icon.png') else "",
            font_size='20sp',
            size_hint=(None, None),
            size=(btn_size, btn_size),
            background_color=(1,1,1,1),
        )
        tasks_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'daily_tasks'))
        profile_layout.add_widget(tasks_btn)


        # Добавьте отображение монет
        self.coin_label = Label(text=f"Coins: {currency.amount}$", 
                              size_hint=(1, None),
                              height=30,
                              font_size='16sp')
        self.add_widget(self.coin_label)
        
        self.bind(on_pre_enter=self.update_texts)
        
        # Обновляем при каждом показе экрана
        self.bind(on_pre_enter=self.update_coin_display)

    
    def update_bg_source(self, new_source):
        # Применяем новый фон для меню (с проверкой)
        if not new_source or not os.path.exists(new_source):
            return
        try:
            settings.menu_background = new_source
            settings.save()
            self.bg_rect.source = new_source
            self.bg_rect.texture = None
            self.bg_rect.ask_update()
        except Exception:
            pass


    
    def on_pre_enter(self, *args):
        """Вызывается перед показом экрана"""
        self.update_coin_display()
        # Обновляем аватар если он изменился
        if hasattr(self, 'profile_btn'):
            self.profile_btn.background_normal = profile.avatar
            self.profile_btn.background_down = profile.avatar
    
    def refresh_ui_after_purchase(self):
        """Обновление всего UI после покупок"""
        self.update_coin_display()
        if hasattr(self, 'profile_btn'):
            self.profile_btn = profile.avatar
            self.profile_btn = profile.avatar
    
    
    def update_coin_display(self, *args):
        self.coin_label.text = f"Coins: {currency.amount}$"
    
    def update_texts(self, *args):
        # Здесь можно обновить тексты кнопок если нужно
        pass
    
    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

class ModeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', spacing=20, padding=[40, 80, 40, 80])
        self.gost_level = 1
        self.setup_ui()
        self.add_widget(self.layout)
        
        
        
        bg_path = getattr(settings, 'menu_background', 'assets/menu1.jpg')
        if not os.path.exists(bg_path):
            bg_path = 'assets/menu1.jpg'
        with self.canvas.before:
            self.bg_rect = Rectangle(source=bg_path, size=self.size, pos=self.pos)
        self.bind(size=self.update_bg, pos=self.update_bg)

    def setup_ui(self):
        # Очищаем layout
        self.layout.clear_widgets()
        
        title = Label(text="Select mode", font_size='32sp', size_hint=(1, 0.2))

        btn_normal = Button(text='Normal', font_size='28sp', size_hint=(1, 0.2))
        btn_invisible = Button(text='Gost', font_size='28sp', size_hint=(1, 0.2))
        btn_tgm = Button(text='Lightning', font_size='28sp', size_hint=(1, 0.2))
        back_btn = Button(text='Back', font_size='20sp', size_hint=(1, 0.1))

        # Используем self.layout
        self.layout.add_widget(title)
        self.layout.add_widget(btn_normal)
        self.layout.add_widget(btn_invisible)
        self.layout.add_widget(btn_tgm)
        self.layout.add_widget(back_btn)

        btn_normal.bind(on_press=lambda x: self.start_game('normal'))
        btn_invisible.bind(on_press=lambda x: self.start_game('gost'))
        btn_tgm.bind(on_press=lambda x: self.start_game('lightning'))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))

    def start_game(self, mode):
        # Устанавливаем режим в настройках
        from settings import settings
        settings.game_mode = mode
        
        self.manager.current = 'blocks'
        blocks_screen = self.manager.get_screen('blocks')
        
        # Удаляем старую игру
        for child in blocks_screen.children[:]:
            blocks_screen.remove_widget(child)
        
        # Создаём новую с режимом
        blocks_game = get_blocks_screen(lambda: setattr(self.manager, 'current', 'menu'), mode)
        
        # Для Ghost режима устанавливаем уровень
        if mode == 'gost':
            blocks_game.gost_level = self.gost_level
            blocks_game.set_gost_level(self.gost_level)
        
        # Пытаемся загрузить сессию ТОЛЬКО для текущего режима
        session_available = blocks_game.check_saved_session_for_mode()
        print(f"Session available for {mode}: {session_available}")
        
        if session_available and mode != 'gost':
            # Для Normal и Lightning пытаемся загрузить
            loaded = blocks_game.load_game_session()
            print(f"Session loaded: {loaded}")
            if not loaded:
                blocks_game.reset_for_new_mode()
        elif mode == 'gost':
            # Для Ghost режима всегда загружаем или сбрасываем
            if session_available:
                loaded = blocks_game.load_game_session()
                if not loaded:
                    blocks_game.reset_for_new_mode()
            else:
                blocks_game.reset_for_new_mode()
        else:
            # Для Normal и Lightning без сохранения
            blocks_game.reset_for_new_mode()
        
        blocks_game.settings_opener = 'menu'
        blocks_screen.add_widget(blocks_game)
        try:
            from daily_tasks import mark_task_completed
            mark_task_completed('play_mode')
        except Exception:
            pass
    
    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


class MainApp(App): 
    def on_pause(self):
        """Когда приложение сворачивается"""
        if music_manager.current_sound:
            try:
                music_manager.current_sound.volume = 0
                print("🎵 Музыка приглушена (приложение свернуто)")
            except Exception as e:
                print("Ошибка при приглушении:", e)
        return True  # обязательно вернуть True, чтобы Kivy поставил приложение на паузу

    def on_resume(self):
        """Когда возвращаемся в приложение"""
        if music_manager.current_sound and music_manager.sound_enabled:
            try:
                # восстановим громкость в зависимости от режима
                if music_manager.current_track_path in getattr(settings, 'unlocked_game_tracks', []):
                    vol = getattr(settings, 'game_volume', 1.0)
                else:
                    vol = getattr(settings, 'menu_volume', 1.0)
                music_manager.current_sound.volume = vol
                print("🎵 Музыка восстановлена (приложение вернулось)")
            except Exception as e:
                print("Ошибка при восстановлении громкости:", e)

    def build(self):
        if not verify_apk_signature():
            print("❌ Приложение остановлено: неверная подпись APK.")
            sys.exit(0)  # Закрываем приложение
        settings.load()
        currency.load()
        sm = ScreenManager()

        sm.add_widget(SplashScreen(name='splash'))
        
        def switch_to_menu():
            if self.has_pieces_on_bottom():
                self.save_game_session()
                self.paused = True
            sm.current = 'menu'

        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(ModeScreen(name='mode_select'))

        settings_screen = SettingsScreen(switch_to_menu, name='settings')
        sm.add_widget(settings_screen)
        sm.add_widget(HelpScreen(name='help'))
        blocks_screen = Screen(name='blocks')
        # Игра создастся позже, при выборе режима
        sm.add_widget(blocks_screen)

        sm.add_widget(DailyTasksScreen(name="daily_tasks"))


        return sm
    
    def refresh_ui_after_reward(self):
        app = App.get_running_app()
        if not app:
            return
        root = getattr(app, 'root', None)
        # если корень — ScreenManager
        if root and hasattr(root, 'get_screen'):
            try:
                menu = root.get_screen('menu')
                if hasattr(menu, 'update_coin_display'):
                    menu.update_coin_display()
            except Exception:
                pass
        else:
            # фолбэк: пройтись по дереву и найти виджет с name == 'menu'
            try:
                for w in getattr(root, 'walk', lambda: [])():
                    if getattr(w, 'name', None) == 'menu' and hasattr(w, 'update_coin_display'):
                        w.update_coin_display()
                        break
            except Exception:
                pass




def ensure_saves_dir():
    saves_dir = Path(__file__).parent / 'saves'
    if not saves_dir.exists():
        saves_dir.mkdir()

if __name__ == '__main__':
    ensure_saves_dir()
    check_file_integrity()
    MainApp().run()