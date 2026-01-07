from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.button import Button
import json
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.spinner import Spinner
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.popup import Popup
from music_manager import music_manager
from kivy.uix.gridlayout import GridLayout
import os
from kivy.graphics import Rectangle
from kivy.metrics import dp


class ColorSettingsPopup(Popup):
    def __init__(self, shape_type, current_color, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = f"Color for {shape_type}"
        self.size_hint = (0.8, 0.8)

        layout = BoxLayout(orientation='vertical', padding=dp(6))
        self.color_picker = ColorPicker(color=current_color)
        layout.add_widget(self.color_picker)

        btn_box = BoxLayout(size_hint=(1, 0.1), spacing=dp(6), padding=dp(6))
        btn_ok = Button(text="OK")
        btn_ok.bind(on_press=lambda x: self.on_ok(callback))
        btn_box.add_widget(btn_ok)

        layout.add_widget(btn_box)
        self.content = layout

    def on_ok(self, callback):
        callback(self.color_picker.color)
        self.dismiss()


class SettingsScreen(Screen):
    def __init__(self, back_callback, **kwargs):
        super().__init__(**kwargs)
        self.back_callback = back_callback
        self._ensure_saves_dir_exists()
        self.setup_ui()

    def _track_name(self, path):
        """Возвращает читаемое имя трека (basename) — кроссплатформенно."""
        try:
            return os.path.basename(path) if path else ""
        except Exception:
            return str(path) if path else ""

    
    def _ensure_saves_dir_exists(self):
        saves_path = os.path.join(os.path.dirname(__file__), 'saves')
        if not os.path.exists(saves_path):
            os.makedirs(saves_path)

    def setup_ui(self):
        # Полностью очищаем экран перед созданием нового интерфейса
        self.clear_widgets()

        with self.canvas.before:
            # статический фон настроек (не зависит от game_background)
            self.bg_rect = Rectangle(source='assets/seting.jpg', size=self.size, pos=self.pos)
        self.bind(size=self.update_bg, pos=self.update_bg)

        # Основной контейнер
        main_layout = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))

        # ScrollView для прокрутки
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)

        # Основной контейнер для контента
        content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(15))
        content.bind(minimum_height=content.setter('height'))

        # Язык интерфейса
        lang_row = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(10))
        lang_row.add_widget(Label(text=self.get_translation('language'), size_hint=(0.5, 1)))
        lang_spinner = Spinner(
            text='English' if settings.language == 'en' else 'Русский',
            values=('English', 'Русский'),
            size_hint=(0.5, 1)
        )
        lang_spinner.bind(text=self.on_language_change)
        lang_row.add_widget(lang_spinner)
        content.add_widget(lang_row)

        

        # Кнопки для выбора цветов фигур
        content.add_widget(Label(text="Piece Colors:", size_hint=(1, None), height=dp(30)))
        color_layout = GridLayout(cols=2, spacing=dp(5), size_hint=(1, None), height=dp(300))

        for shape_type, color in settings.piece_colors.items():
            color_layout.add_widget(Label(text=shape_type, size_hint_x=0.4))
            btn = Button(background_color=color, size_hint_x=0.6)
            btn.shape_type = shape_type
            btn.bind(on_press=lambda btn, st=shape_type: self.open_color_picker(st))
            color_layout.add_widget(btn)

        content.add_widget(color_layout)

        # Pattern кнопки (Save/Load)
        pattern_btn_box = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(10))
        save_pattern_btn = Button(text="Save Pattern")
        load_pattern_btn = Button(text="Load Pattern")
        pattern_btn_box.add_widget(save_pattern_btn)
        pattern_btn_box.add_widget(load_pattern_btn)
        content.add_widget(pattern_btn_box)

        save_pattern_btn.bind(on_press=lambda x: self.save_pattern())
        load_pattern_btn.bind(on_press=lambda x: self.load_pattern())

        # Показывать следующую фигуру
        show_next_row = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(10))
        show_next_row.add_widget(Label(text="Show Next Piece:", size_hint=(0.5, 1)))
        show_next_toggle = ToggleButton(
            text='On' if settings.show_next else 'Off',
            state='down' if settings.show_next else 'normal',
            size_hint=(0.5, 1)
        )
        show_next_toggle.bind(on_press=self.on_toggle_change)
        show_next_row.add_widget(show_next_toggle)
        content.add_widget(show_next_row)

        # Громкость меню
        menu_vol_row = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(10))
        menu_vol_row.add_widget(Label(text="Menu Volume:", size_hint=(0.5, 1)))
        menu_volume_slider = Slider(min=0, max=1, value=getattr(settings, 'menu_volume', settings.volume),
                                    size_hint=(0.5, 1))
        menu_volume_slider.cursor_size = (dp(20), dp(20))
        menu_volume_slider.value_track = True
        def on_menu_volume_change(instance, value):
            settings.menu_volume = value
            settings.save()
            if music_manager.current_sound:
                try:
                    music_manager.current_sound.volume = value
                except:
                    pass
        menu_volume_slider.bind(value=on_menu_volume_change)
        menu_vol_row.add_widget(menu_volume_slider)
        content.add_widget(menu_vol_row)

        # Громкость игры
        game_vol_row = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(10))
        game_vol_row.add_widget(Label(text="Game Volume:", size_hint=(0.5, 1)))
        game_volume_slider = Slider(min=0, max=1, value=getattr(settings, 'game_volume', settings.volume),
                                    size_hint=(0.5, 1))
        game_volume_slider.cursor_size = (dp(20), dp(20))
        game_volume_slider.value_track = True
        def on_game_volume_change(instance, value):
            settings.game_volume = value
            settings.save()
            # Попробуем применить в игре (если она запущена)
                        # Попробуем применить в игре (если она запущена)
            app = App.get_running_app()
            if app and getattr(app, 'root', None):
                try:
                    blocks_screen = app.root.get_screen('blocks')
                    if blocks_screen.children:
                        blocks_game = blocks_screen.children[0]
                        if hasattr(blocks_game, 'sound') and blocks_game.sound:
                            blocks_game.sound.volume = value
                except:
                    pass

            # Если в менеджере сейчас играет игровой трек — обновим его громкость тоже,
            # чтобы изменение громкости в настройках влияло мгновенно на музыку.
            try:
                if music_manager.current_sound and music_manager.current_track_path in getattr(settings, 'unlocked_game_tracks', []):
                    music_manager.current_sound.volume = value
            except Exception:
                pass

        game_volume_slider.bind(value=on_game_volume_change)
        game_vol_row.add_widget(game_volume_slider)
        content.add_widget(game_vol_row)

        # -------------- Упрощённые настройки музыки --------------
        content.add_widget(Label(text="Music Controls:", size_hint=(1, None), height=dp(30)))

        # Sequential playback toggle
        seq_row = BoxLayout(size_hint=(1, None), height=dp(40))
        seq_row.add_widget(Label(text="Sequential Playback:", size_hint=(0.5, 1)))
        seq_toggle = ToggleButton(
            text='On' if settings.sequential_playback else 'Off',
            state='down' if settings.sequential_playback else 'normal',
            size_hint=(0.5, 1)
        )
        seq_toggle.bind(on_press=self._toggle_sequential)
        seq_row.add_widget(seq_toggle)
        content.add_widget(seq_row)

        # Reorder and set-current buttons
        music_buttons_box = BoxLayout(orientation='vertical', spacing=dp(8), size_hint=(1, None), height=dp(220))

        # Reorder menu/game
        row1 = BoxLayout(size_hint=(1, None), height=dp(45), spacing=dp(8))
        btn_reorder_menu = Button(text="Reorder Menu Playlist")
        btn_reorder_menu.bind(on_press=lambda x: self._open_reorder_popup('menu'))
        btn_reorder_game = Button(text="Reorder Game Playlist")
        btn_reorder_game.bind(on_press=lambda x: self._open_reorder_popup('game'))
        row1.add_widget(btn_reorder_menu)
        row1.add_widget(btn_reorder_game)

        # Set current playing
        row2 = BoxLayout(size_hint=(1, None), height=dp(45), spacing=dp(8))
        btn_set_menu = Button(text="Set Current Menu Track")
        btn_set_menu.bind(on_press=lambda x: self._open_set_current_popup('menu'))
        btn_set_game = Button(text="Set Current Game Track")
        btn_set_game.bind(on_press=lambda x: self._open_set_current_popup('game'))
        row2.add_widget(btn_set_menu)
        row2.add_widget(btn_set_game)

        # Quick play / preview currently playing
        row3 = BoxLayout(size_hint=(1, None), height=dp(45), spacing=dp(8))
        btn_play_menu_now = Button(text="Play Menu Now")
        btn_play_menu_now.bind(on_press=lambda x: self._apply_playlist_and_play('menu', start_track=None, resume=False))
        btn_play_game_now = Button(text="Play Game Now")
        btn_play_game_now.bind(on_press=lambda x: self._apply_playlist_and_play('game', start_track=None, resume=False))

        row3.add_widget(btn_play_menu_now)
        row3.add_widget(btn_play_game_now)

        music_buttons_box.add_widget(row1)
        music_buttons_box.add_widget(row2)
        music_buttons_box.add_widget(row3)

        content.add_widget(music_buttons_box)
        # ---------------------------------------------------------

        # Кнопка назад
        back_btn = Button(text="Back", size_hint=(1, None), height=dp(50))
        back_btn.bind(on_press=self.back_to_game_or_menu)
        content.add_widget(back_btn)

        # Добавляем контент в ScrollView
        scroll.add_widget(content)

        # Добавляем ScrollView в основной лейаут
        main_layout.add_widget(scroll)
        self.add_widget(main_layout)

    # -------------- GUI handlers и утилиты --------------

    def open_color_picker(self, shape_type):
        current_color = settings.piece_colors.get(shape_type, [1, 1, 1, 1])
        popup = ColorSettingsPopup(
            shape_type,
            current_color,
            lambda color: self.update_piece_color(shape_type, color)
        )
        popup.open()

    def update_piece_color(self, shape_type, color):
        settings.piece_colors[shape_type] = color
        # Обновляем кнопку этого shape_type сразу
        for child in self.walk():
            if isinstance(child, Button) and hasattr(child, 'shape_type') and child.shape_type == shape_type:
                child.background_color = color
        settings.save()

    def on_toggle_change(self, btn):
        settings.show_next = btn.state == 'down'
        btn.text = 'On' if settings.show_next else 'Off'
        blocks_game = self.get_blocks_game()
        if blocks_game:
            blocks_game.set_show_next(settings.show_next)

    def get_blocks_game(self):
        """Получаем текущий экземпляр игры с учетом возможного отсутствия"""
        app = App.get_running_app()
        if app and app.root:
            sm = app.root
            try:
                blocks_screen = sm.get_screen('blocks')
            except:
                return None

            try:
                if blocks_screen.children and hasattr(blocks_screen.children[0], 'settings_opener'):
                    return blocks_screen.children[0]
            except:
                pass
        return None

    def update_game_settings(self):
        app = App.get_running_app()
        if app and app.root:
            sm = app.root
            blocks_screen = sm.get_screen('blocks')
            if blocks_screen.children:
                blocks_game = blocks_screen.children[0]
                if hasattr(blocks_game, 'update_settings_from_config'):
                    blocks_game.update_settings_from_config()

    def back_to_game_or_menu(self, instance):
        app = App.get_running_app()
        sm = app.root

        blocks_screen = sm.get_screen('blocks')
        if blocks_screen.children:
            blocks_game = blocks_screen.children[0]
            if hasattr(blocks_game, 'settings_opener') and blocks_game.settings_opener == 'game':
                # Возвращаемся в игру
                blocks_game.settings_opener = 'menu'
                blocks_game.paused = False
                if hasattr(blocks_game, 'create_buttons'):
                    blocks_game.create_buttons()
                if hasattr(blocks_game, 'sound') and blocks_game.sound:
                    try:
                        blocks_game.sound.play()
                    except:
                        pass
                sm.current = 'blocks'
                return

        # Если мы тут — значит открывали из меню
        try:
            cur = music_manager.current_sound
            if cur and getattr(cur, 'state', None) == 'play':
                # просто обновим громкость
                cur.volume = getattr(settings, 'menu_volume', getattr(settings, 'volume', 1.0))
            else:
                music_manager.play_menu_music(resume=True)
        except Exception:
            try:
                music_manager.play_menu_music(resume=True)
            except Exception:
                pass

        sm.current = 'menu'



    def on_mode_change(self, spinner, text):
        blocks_game = self.get_blocks_game()
        if not blocks_game or blocks_game.settings_opener != 'game':
            return
        if blocks_game and hasattr(blocks_game, 'sound') and blocks_game.sound:
            blocks_game.sound.stop()

        mode_map = {
            'Normal': 'normal',
            'Gost': 'gost',
            'Lightning': 'lightning'
        }
        new_mode = mode_map.get(text, 'normal')
        settings.game_mode = new_mode

        app = App.get_running_app()
        sm = app.root

        blocks_screen = sm.get_screen('blocks')
        if blocks_screen.children:
            blocks_game = blocks_screen.children[0]

            if blocks_game.mode == new_mode:
                return

            if blocks_game.game_started and not blocks_game.game_over:
                blocks_game.save_game_session()

            blocks_game.set_game_mode(new_mode)

            if not blocks_game.start_screen_active:
                blocks_game.game_started = False
                blocks_game.create_start_screen()
                blocks_game.start_screen_active = True
                blocks_game.redraw()

    def on_pre_enter(self, *args):
        """Обновляем интерфейс перед показом экрана"""
        # обновим spinner'ы музыки (если они существуют)
        self.update_music_spinners()

    # -------------- Save / Load pattern helpers --------------
    def save_pattern(self):
        from kivy.uix.textinput import TextInput
        popup = Popup(title="Pattern Name", size_hint=(0.6, 0.4))
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        name_input = TextInput(hint_text="Enter name", multiline=False)
        save_btn = Button(text="Save")
        save_btn.bind(on_press=lambda x: self._save_pattern_data(name_input.text, popup))
        layout.add_widget(name_input)
        layout.add_widget(save_btn)
        popup.content = layout
        popup.open()

    def _save_pattern_data(self, name, popup):
        if name.strip():
            settings.color_patterns[name] = dict(settings.piece_colors)
            self._save_settings_file()
        popup.dismiss()

    def load_pattern(self):
        from kivy.uix.spinner import Spinner
        if not settings.color_patterns:
            return
        popup = Popup(title="Load Pattern", size_hint=(0.6, 0.4))
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        pattern_spinner = Spinner(values=list(settings.color_patterns.keys()))
        load_btn = Button(text="Load")
        load_btn.bind(on_press=lambda x: self._apply_pattern(pattern_spinner.text, popup))
        layout.add_widget(pattern_spinner)
        layout.add_widget(load_btn)
        popup.content = layout
        popup.open()

    def _apply_pattern(self, name, popup):
        if name in settings.color_patterns:
            settings.piece_colors = dict(settings.color_patterns[name])
            settings.save()
        popup.dismiss()

    def _save_settings_file(self):
        data = {
            'piece_colors': settings.piece_colors,
            'color_patterns': settings.color_patterns
        }
        if not os.path.exists('saves'):
            os.makedirs('saves')
        with open('saves/settings.json', 'w') as f:
            json.dump(data, f)

    def load_settings_file(self):
        try:
            with open('saves/settings.json', 'r') as f:
                data = json.load(f)
                settings.piece_colors = data.get('piece_colors', settings.piece_colors)
                settings.color_patterns = data.get('color_patterns', {})
        except:
            pass

    # -------------- Music helpers (reorder & set current) --------------
    def _open_reorder_popup(self, list_type='menu'):
        # Берём ровно тот список, который нужен
        if list_type == 'menu':
            tracks = list(settings.unlocked_menu_tracks)
        else:
            tracks = list(settings.unlocked_game_tracks)

        if not tracks:
            popup = Popup(title="The playlist is empty", size_hint=(0.6, 0.3))
            popup.content = Label(text="No tracks")
            popup.open()
            return

        content = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(6))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        grid.bind(minimum_height=grid.setter('height'))
        rows = []

        for t in tracks:
            row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            lbl = Label(text=self._track_name(t))
            up = Button(text='↑', size_hint_x=None, width=dp(40))
            down = Button(text='↓', size_hint_x=None, width=dp(40))
            row.add_widget(lbl)
            row.add_widget(up)
            row.add_widget(down)
            grid.add_widget(row)
            rows.append((row, lbl, up, down))

        sc = ScrollView(size_hint=(1, 1))
        sc.add_widget(grid)
        content.add_widget(sc)

        def swap(i, j):
            tracks[i], tracks[j] = tracks[j], tracks[i]
            for idx, (_r, lbl, _u, _d) in enumerate(rows):
                lbl.text = self._track_name(tracks[idx])


        for idx, (_r, _lbl, up_btn, down_btn) in enumerate(rows):
            i = idx
            up_btn.bind(on_press=lambda _, i=i: (swap(i, i - 1) if i > 0 else None))
            down_btn.bind(on_press=lambda _, i=i: (swap(i, i + 1) if i < len(tracks) - 1 else None))

        btn_box = BoxLayout(size_hint=(1, None), height=dp(44), spacing=dp(6))
        ok = Button(text='OK')
        cancel = Button(text='Cancel')
        btn_box.add_widget(ok)
        btn_box.add_widget(cancel)
        content.add_widget(btn_box)

        popup = Popup(title="Reorder playlist", content=content, size_hint=(0.9, 0.8))

        def on_ok(_):
            if list_type == 'menu':
                settings.unlocked_menu_tracks = tracks
            else:
                settings.unlocked_game_tracks = tracks
            settings.save()
            popup.dismiss()
            # Применим новый порядок в music_manager (не перезапуская музыку, если она уже играет)
            try:
                if list_type == 'menu':
                    music_manager.track_list = list(settings.unlocked_menu_tracks)
                else:
                    music_manager.track_list = list(settings.unlocked_game_tracks)
                # если текущий трек есть в новом списке — обновим индекс
                if music_manager.current_track_path and music_manager.current_track_path in music_manager.track_list:
                    music_manager.current_index = music_manager.track_list.index(music_manager.current_track_path)
                else:
                    # иначе выставим индекс по settings.menu_music/game_music (если есть), иначе 0
                    pref = settings.menu_music if list_type == 'menu' else settings.game_music
                    if pref and pref in music_manager.track_list:
                        music_manager.current_index = music_manager.track_list.index(pref)
                    else:
                        music_manager.current_index = 0
            except Exception:
                pass
            self.update_music_spinners()


        ok.bind(on_press=on_ok)
        cancel.bind(on_press=popup.dismiss)
        popup.open()

    def _open_set_current_popup(self, list_type='menu'):
        if list_type == 'menu':
            tracks = list(settings.unlocked_menu_tracks)
        else:
            tracks = list(settings.unlocked_game_tracks)

        if not tracks:
            popup = Popup(title="The playlist is empty", size_hint=(0.6, 0.3))
            popup.content = Label(text="No tracks")
            popup.open()
            return

        popup_content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
        spinner = Spinner(values=[self._track_name(t) for t in tracks], size_hint=(1, None), height=dp(44))
        # предвыбор текста
        current = settings.menu_music if list_type == 'menu' else settings.game_music
        if current:
            spinner.text = self._track_name(current)
        else:
            spinner.text = spinner.values[0] if spinner.values else "Select"

        popup_content.add_widget(spinner)
        btn_box = BoxLayout(size_hint=(1, None), height=dp(44), spacing=dp(6))
        ok = Button(text='Set')
        cancel = Button(text='Cancel')
        btn_box.add_widget(ok)
        btn_box.add_widget(cancel)
        popup_content.add_widget(btn_box)

        popup = Popup(title="Select current track", content=popup_content, size_hint=(0.8, 0.4))

        def on_set(_):
            chosen_name = spinner.text
            track = self._find_track_by_display(chosen_name, tracks)
            if track:
                if list_type == 'menu':
                    settings.menu_music = track
                    settings.save()
                    self._apply_playlist_and_play('menu', start_track=track, resume=False)
                else:
                    settings.game_music = track
                    settings.save()
                    self._apply_playlist_and_play('game', start_track=track, resume=False)
                self.update_music_spinners()
            popup.dismiss()



        ok.bind(on_press=on_set)
        cancel.bind(on_press=popup.dismiss)
        popup.open()

    def update_music_spinners(self):
        """Обновить (если есть) локальные spinner'ы музыки"""
        if hasattr(self, 'menu_music_spinner'):
            try:
                self.menu_music_spinner.values = [self._track_name(t) for t in settings.unlocked_menu_tracks]
                self.menu_music_spinner.text = self._track_name(settings.menu_music) if settings.menu_music else "Select music"
            except Exception:
                pass

        if hasattr(self, 'game_music_spinner'):
            try:
                self.game_music_spinner.values = [self._track_name(t) for t in settings.unlocked_game_tracks]
                self.game_music_spinner.text = self._track_name(settings.game_music) if settings.game_music else "Select music"
            except Exception:
                pass


    def _apply_playlist_and_play(self, list_type='menu', start_track=None, resume=False):
        """
        Обновить music_manager.track_list в соответствии с settings,
        установить current_index и запустить воспроизведение выбранного трека
        (или того, что указан в settings.menu_music / settings.game_music).
        """
        # Выбрать плейлист и громкость
        if list_type == 'menu':
            tracks = list(settings.unlocked_menu_tracks)
            vol = getattr(settings, 'menu_volume', getattr(settings, 'volume', 1.0))
            preferred = settings.menu_music
        else:
            tracks = list(settings.unlocked_game_tracks)
            vol = getattr(settings, 'game_volume', getattr(settings, 'volume', 1.0))
            preferred = settings.game_music

        if not tracks:
            return

        # выбрать начальный трек: start_track (если передан) или preferred или первый
        if start_track and start_track in tracks:
            idx = tracks.index(start_track)
        elif preferred and preferred in tracks:
            idx = tracks.index(preferred)
        else:
            idx = 0

        # Применить в music_manager
        try:
            music_manager.track_list = tracks
            music_manager.current_index = idx
            music_manager.current_track_path = tracks[idx]
            # Форсируем воспроизведение выбранного трека.
            # Использую внутренний метод _play_new_track (безопасно — у тебя он уже есть).
            music_manager._play_new_track(tracks[idx], resume=resume, volume=vol)
        except Exception as e:
            print("SettingsScreen: error applying playlist:", e)

                
    
    # -------------- helpers для музыки из старого кода --------------
    def _find_track_by_display(self, display_text, tracks):
        """Найдёт оригинальный путь по отображаемому имени (display_text)."""
        for t in tracks:
            name = self._track_name(t)
            if display_text == t or display_text == name or display_text in name:
                return t
        return None

    # пример использования в _on_menu_music_select:
    def _on_menu_music_select(self, spinner, text):
        try:
            track = self._find_track_by_display(text, settings.unlocked_menu_tracks)
            if track:
                settings.menu_music = track
                settings.save()
                music_manager.play_menu_music()
        except Exception:
            pass

            
    def get_translation(self, key):
        """Возвращает перевод для ключа в текущем языке настроек."""
        try:
            return settings.translations.get(settings.language, {}).get(key, key)
        except Exception:
            return key

    def on_language_change(self, spinner, text):
        """Обработчик смены языка из Spinner в UI настроек."""
        # обрабатываем значение Spinner: 'English' -> 'en', иначе 'ru'
        settings.language = 'en' if text == 'English' else 'ru'
        settings.save()

        # перестроим интерфейс экрана настроек, чтобы всё перевелось
        try:
            # аккуратно пересоздаём UI
            self.clear_widgets()
            self.setup_ui()
        except Exception:
            pass

        # если игра запущена — обновим её UI (если реализовано)
        try:
            blocks_game = self.get_blocks_game()
            if blocks_game and hasattr(blocks_game, 'update_ui_language'):
                blocks_game.update_ui_language()
        except Exception:
            pass
            
    def _toggle_sequential(self, btn):
        settings.sequential_playback = btn.state == 'down'
        settings.save()

    def apply_background(self, instance):
        """Применить выбранный (игровой) фон немедленно только в игре.
           В UI мы убрали выбор фона — но если ты вызовешь эту функцию вручную,
           она применит settings.game_background к игровому экрану."""
        app = App.get_running_app()
        if app and app.root:
            try:
                blocks_screen = app.root.get_screen('blocks')
                if blocks_screen.children:
                    blocks_game = blocks_screen.children[0]
                    if hasattr(blocks_game, 'bg_rect'):
                        blocks_game.bg_rect.source = settings.game_background
                        blocks_game.bg_rect.texture = None
                        try:
                            blocks_game.redraw()
                        except:
                            pass
            except:
                pass

        popup = Popup(title="Успех", size_hint=(0.6, 0.3))
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text="Фон (игры) применён."))
        btn = Button(text="OK", size_hint_y=None, height=40)
        btn.bind(on_press=popup.dismiss)
        content.add_widget(btn)
        popup.content = content
        popup.open()

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


# ---------------- Settings storage class ----------------

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
