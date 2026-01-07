# shop.py
from daily_tasks import load_tasks
import os
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Rectangle
from kivy.app import App
from kivy.clock import Clock
from ads import AD_MANAGER
from currency import currency
from profile1 import profile
from config import settings
from music_manager import music_manager
from daily_tasks import mark_task_completed

# --------- Пути и константы ---------
BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
AVATARS_DIR = os.path.join(ASSETS_DIR, 'avatars')
FON_DIR = os.path.join(ASSETS_DIR, 'fon')
MUSIC_DIR = os.path.join(ASSETS_DIR, 'music')

# Дефолты (не продаются)
DEFAULT_AVATAR = os.path.join(ASSETS_DIR, 'default_avatar.png')          # при наличии
DEFAULT_FON = os.path.join(ASSETS_DIR, 'fon1.png')                        # дефолтный фон
MAIN_MENU_TRACK = os.path.join(ASSETS_DIR, 'dream-pop-lofi-317545.mp3')          # основная музыка меню
MAIN_GAME_TRACK = os.path.join(ASSETS_DIR, 'dream-pop-lofi-317545.mp3')      # основная музыка игры

# Цены / списания
AVATAR_DISPLAY_PRICE = 40   # отображаемая цена
AVATAR_CHARGE = 50          # реально списываемая
MUSIC_PRICE = 50
FON_PRICE = 100

# Допустимые расширения
IMG_EXTS = ('.png', '.jpg', '.jpeg', '.webp')
AUDIO_EXTS = ('.mp3', '.wav', '.ogg', '.m4a')


class Shop(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Shop"
        self.size_hint = (0.9, 0.9)
        self.layout = BoxLayout(orientation='vertical')

        

        # состояние предпрослушки
        self.preview_sound = None
        self.current_preview = None
        self.current_preview_btn = None
        self._menu_prev_volume = None
        self._menu_was_playing = False

        # гарантируем наличие папок
        for d in (AVATARS_DIR, FON_DIR, MUSIC_DIR):
            os.makedirs(d, exist_ok=True)

        # чиним сохранённые старые пути (главная причина твоих ошибок assets/fon2.png и assets/avatar/ava1.png)
        self._repair_saved_paths()

        # приводим в порядок списки музыки
        self._sanitize_unlocked_tracks()

        # вкладки
        self.tabs = TabbedPanel(do_default_tab=False)
        self.create_inventory_tab()
        self.create_music_tab()
        self.create_avatars_tab()
        self.create_backgrounds_tab()
        self.create_earn_coins_tab()

        self.layout.add_widget(self.tabs)
        self.add_close_button()
        self.content = self.layout

        # при закрытии — только останавливаем ИМЕННО предпрослушку
        self.bind(on_dismiss=lambda *_: self.stop_current_preview(resume_menu=True))


        # Это просто коллбек после просмотра рекламы
        def _update_after_ad():
            shop.update_all_tabs()

        



    # ---------- Починка старых путей ----------
    def _repair_saved_paths(self):
        """
        Чинит старые кривые пути из сохранений:
        - assets/fon2.png          -> assets/fon/fon2.png
        - assets/avatar/ava1.png   -> assets/avatars/ava1.png
        Также переносит любые элементы по basename в нужные папки, если там они реально существуют.
        """
        def fixed_img_path(p, kind):
            if not p:
                return p
            if os.path.exists(p):
                return p
            base = os.path.basename(p)

            # варианты для фон/аватар/музыка
            if kind == 'fon':
                for cand in (
                    os.path.join(FON_DIR, base),
                    os.path.join(ASSETS_DIR, base),  # вдруг лежит в корне ассетов
                ):
                    if os.path.exists(cand):
                        return cand
                # старый формат вообще без подпапки 'fon' типа assets/fon2.png
                if os.path.exists(os.path.join(ASSETS_DIR, 'fon', base)):
                    return os.path.join(ASSETS_DIR, 'fon', base)

            if kind == 'avatar':
                for cand in (
                    os.path.join(AVATARS_DIR, base),
                    os.path.join(ASSETS_DIR, 'avatar', base),  # старое имя папки
                ):
                    if os.path.exists(cand):
                        return cand

            if kind == 'music':
                for cand in (
                    os.path.join(MUSIC_DIR, base),
                    os.path.join(ASSETS_DIR, base),  # могли лежать в корне
                ):
                    if os.path.exists(cand):
                        return cand

            return p  # если не нашли — вернём как есть (но UI просто не покажет)

        try:
            # фоновые картинки
            settings.unlocked_backgrounds = [
                fixed_img_path(p, 'fon') for p in (getattr(settings, 'unlocked_backgrounds', []) or [])
            ]
            settings.unlocked_backgrounds = [p for p in settings.unlocked_backgrounds if os.path.exists(p)]

            # текущий выбранный фон
            if getattr(settings, 'game_background', None):
                settings.game_background = fixed_img_path(settings.game_background, 'fon')

            # аватарки
            settings.unlocked_avatars = [
                fixed_img_path(p, 'avatar') for p in (getattr(settings, 'unlocked_avatars', []) or [])
            ]
            settings.unlocked_avatars = [p for p in settings.unlocked_avatars if os.path.exists(p)]
            if getattr(profile, 'avatar', None):
                profile.avatar = fixed_img_path(profile.avatar, 'avatar')
                profile.save_profile()

            # музыка
            settings.unlocked_menu_tracks = [
                fixed_img_path(p, 'music') for p in (getattr(settings, 'unlocked_menu_tracks', []) or [])
            ]
            settings.unlocked_menu_tracks = [p for p in settings.unlocked_menu_tracks if os.path.exists(p)]

            settings.unlocked_game_tracks = [
                fixed_img_path(p, 'music') for p in (getattr(settings, 'unlocked_game_tracks', []) or [])
            ]
            settings.unlocked_game_tracks = [p for p in settings.unlocked_game_tracks if os.path.exists(p)]

            if getattr(settings, 'menu_music', None):
                settings.menu_music = fixed_img_path(settings.menu_music, 'music')
            if getattr(settings, 'game_music', None):
                settings.game_music = fixed_img_path(settings.game_music, 'music')

            settings.save()
        except Exception:
            # ничего страшного, просто не чиним
            pass

    # ---------- Утилиты ----------
    def _sanitize_unlocked_tracks(self):
        """Удаляем дубли и исключаем пересечение меню/игра."""
        try:
            def unique(seq):
                seen = set()
                out = []
                for x in seq:
                    if x not in seen:
                        seen.add(x)
                        out.append(x)
                return out

            settings.unlocked_menu_tracks = unique(getattr(settings, 'unlocked_menu_tracks', []) or [])
            settings.unlocked_game_tracks = unique(getattr(settings, 'unlocked_game_tracks', []) or [])

            # если трек есть в меню — его не должно быть в игре
            settings.unlocked_game_tracks = [t for t in settings.unlocked_game_tracks
                                             if t not in settings.unlocked_menu_tracks]
            settings.save()
        except Exception:
            pass

    def _list_images(self, folder):
        try:
            files = []
            for f in sorted(os.listdir(folder)):
                if f.startswith('.'):
                    continue
                p = os.path.join(folder, f)
                if os.path.isfile(p) and f.lower().endswith(IMG_EXTS):
                    files.append(p)
            return files
        except Exception:
            return []

    def _list_audio(self, folder):
        try:
            files = []
            for f in sorted(os.listdir(folder)):
                if f.startswith('.'):
                    continue
                p = os.path.join(folder, f)
                if os.path.isfile(p) and f.lower().endswith(AUDIO_EXTS):
                    files.append(p)
            return files
        except Exception:
            return []

    # ---------- Вкладка Music (покупка) ----------
    def create_music_tab(self):
        tab = TabbedPanelItem(text='Music')
        scroll = ScrollView()
        layout = GridLayout(cols=2, spacing=10, padding=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        # берём только из assets/music, исключая основные
        all_tracks = self._list_audio(MUSIC_DIR)
        exclude = {os.path.normpath(MAIN_MENU_TRACK), os.path.normpath(MAIN_GAME_TRACK)}
        tracks_for_sale = [t for t in all_tracks if os.path.normpath(t) not in exclude]

        if not tracks_for_sale:
            layout.add_widget(Label(text="No additional music found in assets/music",
                                    size_hint_y=None, height=40))

        for track in tracks_for_sale:
            item_box = BoxLayout(orientation='vertical', size_hint_y=None, height=230)

            # картинка
            img = Image(source=os.path.join(ASSETS_DIR, 'music_icon.png'),
                        size_hint=(1, None), height=120, fit_mode='contain')

            # предпрослушка
            preview_btn = Button(text='▶', size_hint_y=None, height=40)
            preview_btn.track_path = track
            preview_btn.track_type = None
            preview_btn.is_playing = False
            preview_btn.bind(on_press=self.toggle_music_preview)

            price_lbl = Label(text=f"{os.path.basename(track)}\n{MUSIC_PRICE}$ coins",
                              size_hint_y=None, height=50)

            # купить отдельно для меню/игры
            row = BoxLayout(size_hint_y=None, height=44, spacing=6)
            is_bought_menu = track in settings.unlocked_menu_tracks
            is_bought_game = track in settings.unlocked_game_tracks

            btn_menu = Button(text=("Bought" if is_bought_menu else f"Buy (Menu) {MUSIC_PRICE}"),
                              disabled=is_bought_menu)
            btn_menu.bind(on_press=lambda btn, t=track: self.buy_music(t, MUSIC_PRICE, 'menu'))

            btn_game = Button(text=("Bought" if is_bought_game else f"Buy (Game) {MUSIC_PRICE}"),
                              disabled=is_bought_game)
            btn_game.bind(on_press=lambda btn, t=track: self.buy_music(t, MUSIC_PRICE, 'game'))

            row.add_widget(btn_menu)
            row.add_widget(btn_game)

            item_box.add_widget(img)
            item_box.add_widget(preview_btn)
            item_box.add_widget(price_lbl)
            item_box.add_widget(row)
            layout.add_widget(item_box)

        scroll.add_widget(layout)
        tab.content = scroll
        self.tabs.add_widget(tab)

    def toggle_music_preview(self, instance):
        if self.preview_sound and self.current_preview != instance.track_path:
            self.stop_current_preview(resume_menu=False)

        if getattr(instance, 'is_playing', False):
            self.stop_current_preview(resume_menu=True)
            return

        self.start_preview(instance.track_path, 'Menu', instance)  # громкость возьмём из menu_volume

    def start_preview(self, track_path, track_type, btn):
        from kivy.core.audio import SoundLoader

        if self.preview_sound and self.current_preview != track_path:
            self.stop_current_preview(resume_menu=False)

        # приглушим текущую музыку меню (если играла)
        self._menu_prev_volume = None
        self._menu_was_playing = False
        try:
            if music_manager.current_sound and getattr(music_manager.current_sound, 'state', None) == 'play':
                self._menu_was_playing = True
                try:
                    self._menu_prev_volume = music_manager.current_sound.volume
                    music_manager.current_sound.volume = 0
                except Exception:
                    self._menu_prev_volume = None
        except Exception:
            pass

        music_manager.is_preview = True

        self.preview_sound = SoundLoader.load(track_path)
        if not self.preview_sound:
            # откатим громкость
            if self._menu_prev_volume is not None and music_manager.current_sound:
                try:
                    music_manager.current_sound.volume = self._menu_prev_volume
                except Exception:
                    pass
            music_manager.is_preview = False
            return

        try:
            if track_type == 'Menu':
                self.preview_sound.volume = getattr(settings, 'menu_volume', 1.0)
            else:
                self.preview_sound.volume = getattr(settings, 'game_volume', 1.0)
        except Exception:
            self.preview_sound.volume = 1.0

        self.preview_sound.bind(on_stop=self._on_preview_stopped)

        self.update_music_buttons()
        btn.is_playing = True
        btn.text = '■'
        self.current_preview_btn = btn
        self.current_preview = track_path

        try:
            self.preview_sound.play()
        except Exception:
            self.stop_current_preview(resume_menu=True)

    def stop_current_preview(self, resume_menu=True):
        if self.preview_sound:
            try:
                self.preview_sound.unbind(on_stop=self._on_preview_stopped)
            except Exception:
                pass
            try:
                if getattr(self.preview_sound, 'state', None) == 'play':
                    self.preview_sound.stop()
            except Exception:
                pass
            self.preview_sound = None

        if self.current_preview_btn:
            try:
                self.current_preview_btn.is_playing = False
                self.current_preview_btn.text = '▶'
            except Exception:
                pass
            self.current_preview_btn = None

        self.current_preview = None
        music_manager.is_preview = False

        # вернём громкость меню-музыки и при необходимости перезапустим
        try:
            if self._menu_prev_volume is not None and music_manager.current_sound:
                try:
                    music_manager.current_sound.volume = self._menu_prev_volume
                except Exception:
                    pass
        except Exception:
            pass

        if resume_menu:
            try:
                playing = (music_manager.current_sound and getattr(music_manager.current_sound, 'state', None) == 'play')
            except Exception:
                playing = False

            if not playing and self._menu_was_playing:
                try:
                    music_manager.play_menu_music(resume=True)
                except Exception:
                    pass

        self._menu_prev_volume = None
        self._menu_was_playing = False

    def _on_preview_stopped(self, *_):
        self.stop_current_preview(resume_menu=True)

    def buy_music(self, track_path, price, music_type):
        # списываем фиксированную цену MUSIC_PRICE
        if currency.amount < MUSIC_PRICE:
            self.show_not_enough_coins()
            return
        if not currency.spend(MUSIC_PRICE):
            return

        try:
            if music_type == 'menu':
                if track_path not in settings.unlocked_menu_tracks:
                    settings.unlocked_menu_tracks.append(track_path)
                # убрать из игры
                settings.unlocked_game_tracks = [t for t in settings.unlocked_game_tracks if t != track_path]
                settings.menu_music = track_path
                settings.save()
                music_manager.play_menu_music()
            else:
                if track_path not in settings.unlocked_game_tracks:
                    settings.unlocked_game_tracks.append(track_path)
                # убрать из меню
                settings.unlocked_menu_tracks = [t for t in settings.unlocked_menu_tracks if t != track_path]
                settings.game_music = track_path
                settings.save()
                music_manager.play_game_music()
        except Exception:
            settings.save()

        # сразу обновим UI
        self.update_all_tabs()

    # ---------- Вкладка Avatars ----------
    def create_avatars_tab(self):
        tab = TabbedPanelItem(text='Avatars')
        scroll = ScrollView()
        layout = GridLayout(cols=2, spacing=10, padding=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        avatars = self._list_images(AVATARS_DIR)

        if not avatars:
            layout.add_widget(Label(text="No avatars found in assets/avatars",
                                    size_hint_y=None, height=40))

        for path in avatars:
            # не продаём дефолт (если есть)
            if os.path.normpath(path) == os.path.normpath(DEFAULT_AVATAR):
                continue

            item_box = BoxLayout(orientation='vertical', size_hint_y=None, height=220)
            img = Image(source=path, size_hint=(1, None), height=140, fit_mode='contain')

            is_unlocked = path in settings.unlocked_avatars
            is_selected = path == profile.avatar

            buy_btn = Button(
                text=("Chosen" if is_selected else ("Bought" if is_unlocked else f"{AVATAR_DISPLAY_PRICE}$ coins")),
                size_hint_y=None, height=40,
                disabled=is_unlocked or is_selected
            )
            buy_btn.bind(on_press=lambda btn, p=path: self.buy_avatar(p))

            select_btn = Button(text="Choose", size_hint_y=None, height=40,
                                disabled=(not is_unlocked and not is_selected))
            select_btn.bind(on_press=lambda btn, p=path: self.select_avatar(p))

            item_box.add_widget(img)
            item_box.add_widget(buy_btn)
            item_box.add_widget(select_btn)
            layout.add_widget(item_box)

        scroll.add_widget(layout)
        tab.content = scroll
        self.tabs.add_widget(tab)

    def buy_avatar(self, path):
        if currency.amount < AVATAR_CHARGE:
            self.show_not_enough_coins()
            return

        try:
            awarded, already = mark_task_completed('buy_avatar')
            # обновим экран заданий, если открыт
            try:
                app = App.get_running_app()
                if app and app.root:
                    dt_screen = app.root.get_screen('daily_tasks')
                    try:
                        dt_screen.refresh_ui()
                        if awarded and not already:
                            dt_screen.show_praise(f"+{awarded} монет")
                            # возможно: показать герб, если бонус выпал
                            data = load_tasks()
                            if 'complete_all' in data.get('completed', []):
                                dt_screen.show_hero_badge()
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass


    def select_avatar(self, path):
        profile.avatar = path
        profile.save_profile()

        app = App.get_running_app()
        if app and app.root:
            menu_screen = app.root.get_screen('menu')
            if hasattr(menu_screen, 'profile_btn'):
                menu_screen.profile_btn.background_normal = path
                menu_screen.profile_btn.background_down = path

            blocks_screen = app.root.get_screen('blocks')
            if blocks_screen.children:
                blocks_game = blocks_screen.children[0]
                if hasattr(blocks_game, 'profile_btn'):
                    blocks_game.profile_btn.background_normal = path

        self.update_all_tabs()
        self.update_coin_display()

    # ---------- Вкладка Backgrounds ----------
    def create_backgrounds_tab(self):
        tab = TabbedPanelItem(text='Backgrounds')
        scroll = ScrollView()
        layout = GridLayout(cols=2, spacing=10, padding=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        bgs = self._list_images(FON_DIR)
        # дефолтный фон лежит в assets/, в продажу он не попадает автоматом (мы читаем только из assets/fon)
        if not bgs:
            layout.add_widget(Label(text="No backgrounds found in assets/fon",
                                    size_hint_y=None, height=40))

        for path in bgs:
            item_box = BoxLayout(orientation='vertical', size_hint_y=None, height=260)
            img = Image(source=path, size_hint=(1, None), height=160, fit_mode='contain')

            is_unlocked = path in settings.unlocked_backgrounds
            is_selected = path == settings.game_background

            buy_btn = Button(
                text=("Chose" if is_selected else ("Bought" if is_unlocked else f"{FON_PRICE}$ coins")),
                size_hint_y=None, height=40,
                disabled=is_unlocked or is_selected
            )
            buy_btn.bind(on_press=lambda btn, p=path: self.buy_background(p))

            select_btn = Button(text="Choose", size_hint_y=None, height=40,
                                disabled=(not is_unlocked and not is_selected))
            select_btn.bind(on_press=lambda btn, p=path: self.select_background(p))

            item_box.add_widget(img)
            item_box.add_widget(buy_btn)
            item_box.add_widget(select_btn)
            layout.add_widget(item_box)

        scroll.add_widget(layout)
        tab.content = scroll
        self.tabs.add_widget(tab)

    def buy_background(self, path):
        if currency.amount < FON_PRICE:
            self.show_not_enough_coins()
            return

        if currency.spend(FON_PRICE):
            if path not in settings.unlocked_backgrounds:
                settings.unlocked_backgrounds.append(path)
            settings.game_background = path
            settings.save()

            # применим сразу в игре
            app = App.get_running_app()
            if app and app.root:
                blocks_screen = app.root.get_screen('blocks')
                if blocks_screen.children:
                    blocks_game = blocks_screen.children[0]
                    if hasattr(blocks_game, 'bg_rect'):
                        blocks_game.bg_rect.source = path
                        blocks_game.bg_rect.texture = None

            self.update_coin_display()
            self.update_all_tabs()

    def select_background(self, path):
        if settings.game_background == path:
            popup = Popup(title="Info", size_hint=(0.6, 0.3))
            content = BoxLayout(orientation='vertical')
            content.add_widget(Label(text="This background is already selected."))
            btn = Button(text="OK", size_hint_y=None, height=40)
            btn.bind(on_press=popup.dismiss)
            content.add_widget(btn)
            popup.content = content
            popup.open()
            return

        settings.game_background = path
        settings.save()

        app = App.get_running_app()
        if app and app.root:
            blocks_screen = app.root.get_screen('blocks')
            if blocks_screen.children:
                blocks_game = blocks_screen.children[0]
                if hasattr(blocks_game, 'bg_rect'):
                    blocks_game.bg_rect.source = path
                    blocks_game.bg_rect.texture = None
                    if hasattr(blocks_game, 'update_bg'):
                        blocks_game.update_bg()
                    if hasattr(blocks_game, 'redraw'):
                        blocks_game.redraw()

        self.update_all_tabs()

    # ---------- Вкладка My inventory ----------
    def create_inventory_tab(self):
        tab = TabbedPanelItem(text='My inventory')
        scroll = ScrollView()
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # Backgrounds
        bg_label = Label(text="Background:", size_hint_y=None, height=30)
        layout.add_widget(bg_label)

        bg_scroll = ScrollView(size_hint_y=None, height=220)
        bg_grid = GridLayout(cols=2, spacing=10, size_hint_y=None)
        bg_grid.bind(minimum_height=bg_grid.setter('height'))

        for bg in settings.unlocked_backgrounds:
            item_box = BoxLayout(orientation='vertical', size_hint_y=None, height=180)
            img = Image(source=bg, size_hint=(1, None), height=120, fit_mode='contain')
            btn = Button(text="Choose", size_hint_y=None, height=40)
            btn.bind(on_press=lambda btn, p=bg: self.select_background(p))
            item_box.add_widget(img)
            item_box.add_widget(btn)
            bg_grid.add_widget(item_box)

        bg_scroll.add_widget(bg_grid)
        layout.add_widget(bg_scroll)

        # Avatars
        ava_label = Label(text="Avatars:", size_hint_y=None, height=30)
        layout.add_widget(ava_label)

        ava_scroll = ScrollView(size_hint_y=None, height=220)
        ava_grid = GridLayout(cols=2, spacing=10, size_hint_y=None)
        ava_grid.bind(minimum_height=ava_grid.setter('height'))

        all_avatars = [DEFAULT_AVATAR] + settings.unlocked_avatars
        for ava in all_avatars:
            item_box = BoxLayout(orientation='vertical', size_hint_y=None, height=180)
            img = Image(source=ava, size_hint=(1, None), height=120, fit_mode='contain')
            btn = Button(text="Choose", size_hint_y=None, height=40)
            btn.bind(on_press=lambda btn, p=ava: self.select_avatar(p))
            item_box.add_widget(img)
            item_box.add_widget(btn)
            ava_grid.add_widget(item_box)

        ava_scroll.add_widget(ava_grid)
        layout.add_widget(ava_scroll)

        # Music
        music_label = Label(text="Music:", size_hint_y=None, height=30)
        layout.add_widget(music_label)

        music_scroll = ScrollView(size_hint_y=None, height=320)
        music_grid = GridLayout(cols=1, spacing=8, size_hint_y=None)
        music_grid.bind(minimum_height=music_grid.setter('height'))

        # Menu music
        music_grid.add_widget(Label(text="— Menu —", size_hint_y=None, height=30))
        for track in settings.unlocked_menu_tracks:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=48, spacing=10)
            name_lbl = Label(text=os.path.basename(track), size_hint_x=0.7)
            # одна кнопка Start: запускает через music_manager и НЕ останавливается при закрытии магазина
            start_btn = Button(text='Start', size_hint_x=0.15)
            start_btn.bind(on_press=lambda btn, t=track: self._play_music_from_inventory(t, 'menu'))
            '''choose_btn = Button(text='Choose', size_hint_x=0.15)
            choose_btn.bind(on_press=lambda btn, t=track: self._choose_music_from_inventory(t, 'menu'))'''
            row.add_widget(name_lbl)
            row.add_widget(start_btn)
            #row.add_widget(choose_btn)
            music_grid.add_widget(row)

        # Game music
        music_grid.add_widget(Label(text="— Game —", size_hint_y=None, height=30))
        for track in settings.unlocked_game_tracks:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=48, spacing=10)
            name_lbl = Label(text=os.path.basename(track), size_hint_x=0.7)
            start_btn = Button(text='Start', size_hint_x=0.15)
            start_btn.bind(on_press=lambda btn, t=track: self._play_music_from_inventory(t, 'game'))
            '''choose_btn = Button(text='Choose', size_hint_x=0.15)
            choose_btn.bind(on_press=lambda btn, t=track: self._choose_music_from_inventory(t, 'game'))'''
            row.add_widget(name_lbl)
            row.add_widget(start_btn)
            #row.add_widget(choose_btn)
            music_grid.add_widget(row)

        music_scroll.add_widget(music_grid)
        layout.add_widget(music_scroll)

        scroll.add_widget(layout)
        tab.content = scroll
        self.tabs.add_widget(tab)

    def _choose_music_from_inventory(self, track, kind='game'):
        """Просто выбрать трек как дефолтный (без проигрывания)."""
        if kind == 'menu':
            settings.menu_music = track
            if track not in settings.unlocked_menu_tracks:
                settings.unlocked_menu_tracks.append(track)
            settings.unlocked_game_tracks = [t for t in settings.unlocked_game_tracks if t != track]
            settings.save()
        else:
            settings.game_music = track
            if track not in settings.unlocked_game_tracks:
                settings.unlocked_game_tracks.append(track)
            settings.unlocked_menu_tracks = [t for t in settings.unlocked_menu_tracks if t != track]
            settings.save()
        self.update_all_tabs()

    def _play_music_from_inventory(self, track, kind='menu'):
        """
        Запускаем через music_manager — музыка продолжит играть и после закрытия магазина.
        """
        try:
            if kind == 'menu':
                settings.menu_music = track
                if track not in settings.unlocked_menu_tracks:
                    settings.unlocked_menu_tracks.append(track)
                settings.unlocked_game_tracks = [t for t in settings.unlocked_game_tracks if t != track]
                settings.save()
                music_manager.play_menu_music()
            else:
                settings.game_music = track
                if track not in settings.unlocked_game_tracks:
                    settings.unlocked_game_tracks.append(track)
                settings.unlocked_menu_tracks = [t for t in settings.unlocked_menu_tracks if t != track]
                settings.save()
                music_manager.play_game_music()
        except Exception:
            settings.save()
        # не трогаем предпрослушку тут — потому что мы не её используем

    # ---------- Coins ----------
    def create_earn_coins_tab(self):
        tab = TabbedPanelItem(text='Coins')
        layout = BoxLayout(orientation='vertical', spacing=20, padding=20)
        layout.add_widget(Label(text="Get coins", size_hint_y=None, height=50))

        watch_ad_btn = Button(text="Watch ad(+10$ coins)", size_hint_y=None, height=100)

        def on_watch_ad(_):
            # on_reward будет вызван когда юзер действительно досмотрел рекламу
            def on_reward():
                # ПРОВЕРЬ ОТСТУПЫ ЗДЕСЬ! Должны быть табуляции
                # пометка задачи и награда
                try:
                    mark_task_completed('watch_ad')
                except Exception:
                    pass
                # обновим вкладки/UI
                try:
                    shop.update_all_tabs()
                except Exception:
                    pass

            # А здесь тоже должен быть отступ для вызова show_rewarded
            ok, reason = AD_MANAGER.show_rewarded(on_reward=on_reward)
            

        watch_ad_btn.bind(on_press=on_watch_ad)
        layout.add_widget(watch_ad_btn)

        tab.content = layout
        self.tabs.add_widget(tab)

    # ---------- Общие хелперы ----------
    def show_not_enough_coins(self):
        popup = Popup(title="Error", size_hint=(0.7, 0.3))
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text="Not enough coins!"))
        btn = Button(text="OK", size_hint_y=None, height=50)
        btn.bind(on_press=popup.dismiss)
        content.add_widget(btn)
        popup.content = content
        popup.open()

    def update_music_buttons(self):
        if not self.tabs:
            return
        for tab in self.tabs.tab_list:
            if tab.text == 'Music':
                scroll = tab.content
                if hasattr(scroll, 'children'):
                    for child in scroll.children:
                        if isinstance(child, GridLayout):
                            for item in child.children:
                                if hasattr(item, 'children'):
                                    for widget in item.children:
                                        if isinstance(widget, Button) and hasattr(widget, 'track_path'):
                                            widget.is_playing = (self.current_preview == widget.track_path)
                                            widget.text = '■' if widget.is_playing else '▶'

    def update_all_tabs(self):
        current_tab_text = None
        if hasattr(self.tabs, 'current_tab') and self.tabs.current_tab:
            current_tab_text = self.tabs.current_tab.text

        self.tabs.clear_tabs()

        # снова санитиз и перечитывание контента папок
        self._sanitize_unlocked_tracks()

        self.create_inventory_tab()
        self.create_music_tab()
        self.create_avatars_tab()
        self.create_backgrounds_tab()
        self.create_earn_coins_tab()

        if current_tab_text:
            for tab in self.tabs.tab_list:
                if tab.text == current_tab_text:
                    self.tabs.switch_to(tab)
                    break

        self.update_coin_display()

    def update_coin_display(self):
        app = App.get_running_app()
        if app and app.root:
            menu_screen = app.root.get_screen('menu')
            if hasattr(menu_screen, 'coin_label'):
                menu_screen.coin_label.text = f"Coins: {currency.amount}$"
                menu_screen.coin_label.canvas.ask_update()

    def add_close_button(self):
        close_btn = Button(text="Close", size_hint_y=None, height=50)

        def _close(_):
            # останавливаем только ПРЕДПРОСЛУШКУ; музыка, запущенная Start, идет через music_manager и будет играть дальше
            self.stop_current_preview(resume_menu=True)
            self.dismiss()
            app = App.get_running_app()
            if app and app.root:
                menu_screen = app.root.get_screen('menu')
                if hasattr(menu_screen, 'update_coin_display'):
                    menu_screen.update_coin_display()

        close_btn.bind(on_press=_close)
        self.layout.add_widget(close_btn)

    def show_category(self, title: str):
        for tab in self.tabs.tab_list:
            if tab.text == title:
                self.tabs.switch_to(tab)
                break

    def on_tab_change(self, instance, tab):
        self.stop_current_preview(resume_menu=True)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


# глобальный объект магазина
shop = Shop()
