# music_manager.py
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from config import settings
from kivy.app import App

class MusicManager:
    def __init__(self):
        self.current_sound = None
        self.track_list = []
        self.current_index = 0
        self.last_position = 0.0         # сохранённая позиция в секундах
        self.last_menu_track = None
        self.is_preview = False
        
        
        # состояния
        self.is_paused = False
        self.current_track_path = None
        
        # флаг для отслеживания состояния звука
        self.sound_enabled = True
        
        # таймер для отслеживания позиции (на случай ненадёжного get_pos)
        self._pos_event = None
        self._use_manual_timer = False   # переключится в True если get_pos() ненадёжен
        self._manual_elapsed = 0.0
        
        # флаг для отслеживания состояния звука
        self.sound_enabled = True
        
        # защита от параллельных scheduled loads
        self._load_event = None

    # -------------------- внутренние хелперы --------------------
    def _start_position_tracker(self):
        """Запускает периодическое обновление last_position.
           Если backend поддерживает get_pos() — используем его; иначе используем ручной счётчик."""
        if self._pos_event:
            return
        
        # проверим get_pos() разово — если он возвращает >0 в следующую секунду — используем его
        self._manual_elapsed = 0.0
        self._pos_event = Clock.schedule_interval(self._update_position, 0.5)

    def _stop_position_tracker(self):
        if self._pos_event:
            try:
                self._pos_event.cancel()
            except Exception:
                pass
            self._pos_event = None

    def _update_position(self, dt):
        # пытаемся прочитать у current_sound реальную позицию
        if self.current_sound:
            try:
                pos = self.current_sound.get_pos()
                if pos is not None and pos > 0:
                    # backend даёт корректную позицию
                    self.last_position = float(pos)
                    # не используем manual timer в этом случае
                    self._use_manual_timer = False
                    return
            except Exception:
                pass
        
        # fallback: увеличиваем ручной счётчик
        self._manual_elapsed += dt
        self.last_position += dt
        self._use_manual_timer = True
        return

    def toggle_music_state(self):
        """Переключает состояние включения/выключения музыки и сохраняет/восстанавливает позицию."""
        if self.sound_enabled:
            # Музыка включена - выключаем, сохраняя позицию
            self.sound_enabled = False
            if self.current_sound and getattr(self.current_sound, 'state', None) == 'play':
                self.last_position = getattr(self.current_sound, 'get_pos', lambda: 0)() or 0.0
                try:
                    self.current_sound.stop()
                except Exception:
                    pass
            return False  # Музыка выключена
        else:
            # Музыка выключена - включаем с сохраненной позиции
            self.sound_enabled = True
            self.play_game_music(resume=True)
            return True  # Музыка включена

    # -------------------- основные методы воспроизведения --------------------
    def play_menu_music(self, resume=False):
        if self.is_preview:
            return
            
        self.track_list = getattr(settings, 'unlocked_menu_tracks', []) or []
        if not self.track_list:
            return
            
        if resume and self.last_menu_track and self.last_menu_track in self.track_list:
            track = self.last_menu_track
            self.current_index = self.track_list.index(track)
        else:
            track = settings.menu_music if settings.menu_music in self.track_list else self.track_list[0]
            if not resume:
                self.last_position = 0.0
                
        # если у нас пауза и это тот же трек — ресюмим
        if self.is_paused and self.current_track_path == track:
            self._resume_paused(volume=getattr(settings, 'menu_volume', 1.0))
            self.last_menu_track = track
            self.is_preview = False
            return
            
        self._play_new_track(track, resume=resume, volume=getattr(settings, 'menu_volume', 1.0))
        self.last_menu_track = track
        self.is_preview = False

    def play_game_music(self, resume=False, force=False):
        if self.is_preview and not force:
            return

        # получаем актуальный список игровых треков
        self.track_list = getattr(settings, 'unlocked_game_tracks', []) or []
        if not self.track_list:
            return

        # предпочитаем settings.game_music если он есть в списке, иначе первый трек
        preferred = getattr(settings, 'game_music', None)
        if preferred and preferred in self.track_list:
            track = preferred
        else:
            track = self.track_list[0]

        # если у нас была пауза и это тот же трек — ресюмим
        if self.is_paused and self.current_track_path == track and resume:
            self._resume_paused(volume=getattr(settings, 'game_volume', 1.0))
            self.is_preview = False
            return

        # стартуем выбранный трек
        self._play_new_track(track, resume=resume, volume=getattr(settings, 'game_volume', 1.0))
        self.is_preview = False


    def _play_new_track(self, track, resume=False, volume=1.0):
        """Non-blocking play: отложим фактическую загрузку/воспроизведение на следующий кадр.
        Гарантируем, что предыдущий запланированный load будет отменён — чтобы не запустить
        несколько Sound одновременно из-за race-условий.
        """
        # отменяем уже запланированную загрузку (если была)
        if self._load_event:
            try:
                self._load_event.cancel()
            except Exception:
                pass
            self._load_event = None

        # подготовка: аккуратно очистим старый объект (только флаги, выгрузка можно отложить)
        try:
            if self.current_sound and not self.is_paused:
                try:
                    self.current_sound.unbind(on_stop=self._on_track_end)
                except Exception:
                    pass
                try:
                    if getattr(self.current_sound, 'state', None) == 'play':
                        self.current_sound.stop()
                except Exception:
                    pass
                try:
                    self.current_sound.unload()
                except Exception:
                    pass
                self.current_sound = None
        except Exception as e:
            print("MusicManager: error during pre-cleanup in _play_new_track:", e)

        # Если уже играет тот же трек и это не preview — не планируем новую загрузку
        if (self.current_sound is not None and getattr(self.current_sound, 'state', None) == 'play'
                and self.current_track_path == track and not self.is_preview):
            return

        # Планируем фактическую загрузку/воспроизведение на следующий цикл
        def _do_load_and_play(dt):
            # сбрасываем маркер — мы уже выполняем загрузку
            self._load_event = None
            try:
                # Если в процессе до этого кто-то выключил звук — не запускаем
                if not getattr(self, 'sound_enabled', True):
                    return

                sound = SoundLoader.load(track)
                if not sound:
                    print("MusicManager: failed to load", track)
                    self.current_sound = None
                    return

                # Если в момент загрузки другой play/stop уже сменил план — защитимся:
                # если self.current_track_path уже стал другим треком и current_sound играет — не перезаписываем
                self.current_track_path = track
                self.current_sound = sound
                try:
                    self.current_sound.volume = volume
                except Exception:
                    pass

                if resume and getattr(self, 'last_position', 0.0):
                    try:
                        self.current_sound.seek(self.last_position)
                    except Exception as e:
                        print("MusicManager: seek before play failed:", e)

                try:
                    self.current_sound.play()
                    self.current_sound.bind(on_stop=self._on_track_end)
                    self._start_position_tracker()
                except Exception as e:
                    print("MusicManager: play failed:", e)

                self.is_paused = False
            except Exception as e:
                print("MusicManager: unexpected error in _do_load_and_play:", e)

        # schedule on next frame — non-blocking; сохраняем событие чтобы можно было отменить
        try:
            self._load_event = Clock.schedule_once(_do_load_and_play, 0)
        except Exception:
            # fallback: если schedule не получилось — запускаем синхронно
            _do_load_and_play(0)

        

    def _resume_paused(self, volume=1.0):
        """Надёжный резюм: создаём новый Sound и делаем seek перед play — но делаем это отложенно чтобы не блокировать UI."""
        if not self.current_track_path:
            return
        
        # отменяем уже запланированную загрузку, если есть
        if self._load_event:
            try:
                self._load_event.cancel()
            except Exception:
                pass
            self._load_event = None
        
        # выгружаем старый объект, чтобы создать новый (не блокируя интерфейс)
        try:
            if self.current_sound:
                try:
                    self.current_sound.unbind(on_stop=self._on_track_end)
                except Exception:
                    pass
                try:
                    self.current_sound.unload()
                except Exception:
                    pass
                self.current_sound = None
        except Exception as e:
            print("MusicManager: error cleaning current_sound in resume:", e)
            
        def _do_resume(dt):
            try:
                sound = SoundLoader.load(self.current_track_path)
                if not sound:
                    print("MusicManager: resume failed — couldn't load track:", self.current_track_path)
                    self.is_paused = False
                    return
                    
                self.current_sound = sound
                try:
                    self.current_sound.volume = volume
                except Exception:
                    pass
                    
                # попытка seek до play
                if getattr(self, 'last_position', 0.0):
                    try:
                        print(f"MusicManager: resume -> seeking to {self.last_position:.3f}s BEFORE play (deferred)")
                        self.current_sound.seek(self.last_position)
                    except Exception as e:
                        print("MusicManager: resume seek (deferred) failed:", e)
                        
                try:
                    self.current_sound.play()
                    self.current_sound.bind(on_stop=self._on_track_end)
                except Exception as e:
                    print("MusicManager: resume play failed:", e)
                    
                self._start_position_tracker()
                self.is_paused = False
                
                # debug: проверим позицию чуть позже
                def _check_pos(dt2):
                    try:
                        pos = None
                        if self.current_sound:
                            pos = self.current_sound.get_pos()
                        print("MusicManager: DEBUG after deferred resume - get_pos() ->", pos, " expected ~", self.last_position)
                    except Exception as e:
                        print("MusicManager: DEBUG check_pos error:", e)
                Clock.schedule_once(_check_pos, 0.6)
                
            except Exception as e:
                print("MusicManager: unexpected error in _do_resume:", e)
                self.is_paused = False
                
        Clock.schedule_once(_do_resume, 0)


    def _on_track_end(self, instance):
        # если пауза — ничего не делаем
        if self.is_preview or self.is_paused:
            return
        if not self.track_list:
            return
        if settings.sequential_playback and len(self.track_list) >= 1:
            self._play_selected(self.current_index + 1)
        else:
            self._play_selected(self.current_index)
            
    def _play_selected(self, index):
        if not self.track_list:
            return
        idx = index % len(self.track_list)
        self.current_index = idx
        track = self.track_list[self.current_index]
        if self.track_list == getattr(settings, 'unlocked_menu_tracks', []):
            vol = getattr(settings, 'menu_volume', getattr(settings, 'volume', 1.0))
        else:
            vol = getattr(settings, 'game_volume', getattr(settings, 'volume', 1.0))
        self._play_new_track(track, resume=False, volume=vol)

    # -------------------- пауза / стоп --------------------
    def stop(self):
        """Полная остановка: выгрузить звук и сбросить позицию."""
        # отменяем любую отложенную загрузку
        if self._load_event:
            try:
                self._load_event.cancel()
            except Exception:
                pass
            self._load_event = None
        
        if self.current_sound:
            try:
                self.current_sound.unbind(on_stop=self._on_track_end)
            except Exception:
                pass
            try:
                if getattr(self.current_sound, 'state', None) == 'play':
                    self.current_sound.stop()
            except Exception:
                pass
            try:
                self.current_sound.unload()
            except Exception:
                pass
        self.current_sound = None
        self.last_position = 0.0
        self.is_paused = False
        self.sound_enabled = True
        self._stop_position_tracker()
        
    def pause(self):
        """Пауза: сохраняем позицию и НЕ выгружаем sound — сохраняем объект и last_position."""
        if self.current_sound and getattr(self.current_sound, 'state', None) == 'play':
            try:
                self.current_sound.unbind(on_stop=self._on_track_end)
            except Exception:
                pass
                
            # пробуем получить позицию из backend; если не получается — используем manual timer value
            pos = None
            try:
                pos = self.current_sound.get_pos()
            except Exception:
                pos = None
                
            if pos is None or pos == 0:
                # если backend не дал позицию, попробуем использовать наш ручной счётчик
                print("MusicManager: get_pos unreliable — using manual last_position:", self.last_position)
            else:
                self.last_position = float(pos)
                print("MusicManager: saved last_position from backend:", self.last_position)
                
            try:
                self.current_sound.stop()
            except Exception:
                pass
                
            # не выгружаем sound, чтобы resume мог использовать тот же объект
            self.is_paused = True
            self._stop_position_tracker()
            
    # -------------------- toggle --------------------
    def toggle_music(self, context='game'):
        if self.current_sound and getattr(self.current_sound, 'state', None) == 'play':
            if not self.is_paused:
                # вместо stop — делаем mute
                self.last_position = self.current_sound.get_pos() or 0.0
                self.current_sound.volume = 0
                self.is_paused = True
                print("MusicManager: muted instead of pause at", self.last_position)
            else:
                # возвращаем громкость
                if self.current_track_path in getattr(settings, 'unlocked_game_tracks', []):
                    vol = getattr(settings, 'game_volume', getattr(settings, 'volume', 1.0))
                else:
                    vol = getattr(settings, 'menu_volume', getattr(settings, 'volume', 1.0))
                self.current_sound.volume = vol
                self.is_paused = False
                print("MusicManager: unmuted, resuming at", self.current_sound.get_pos())
            return

        
    # -------------------- UI helpers (как было) --------------------
    def update_music_tab(self):
        self.update_all_tabs()
        self._update_settings_spinners()
        
    def update_inventory_tab(self):
        self.update_all_tabs()
        self._update_settings_spinners()
        
    def _update_settings_spinners(self):
        app = App.get_running_app()
        if not app or not getattr(app, 'root', None):
            return
        try:
            settings_screen = app.root.get_screen('settings')
        except Exception:
            settings_screen = None
        if not settings_screen:
            return
        from kivy.uix.spinner import Spinner
        menu_names = [t.split('/')[-1] for t in getattr(settings, 'unlocked_menu_tracks', [])]
        game_names = [t.split('/')[-1] for t in getattr(settings, 'unlocked_game_tracks', [])]
        menu_name_current = settings.menu_music.split('/')[-1] if settings.menu_music else None
        game_name_current = settings.game_music.split('/')[-1] if settings.game_music else None
        for widget in settings_screen.walk():
            if isinstance(widget, Spinner):
                vals = list(widget.values) if widget.values else []
                if menu_name_current and widget.text == menu_name_current or any(v in menu_names for v in vals):
                    widget.values = menu_names
                    widget.text = menu_name_current if menu_name_current else (menu_names[0] if menu_names else widget.text)
                elif game_name_current and widget.text == game_name_current or any(v in game_names for v in vals):
                    widget.values = game_names
                    widget.text = game_name_current if game_name_current else (game_names[0] if game_names else widget.text)

    def get_next_track(self):
        if not self.track_list:
            return None
        next_index = (self.current_index + 1) % len(self.track_list)
        return self.track_list[next_index]
        
    def get_previous_track(self):
        if not self.track_list:
            return None
        prev_index = (self.current_index - 1) % len(self.track_list)
        return self.track_list[prev_index]

# Singleton
music_manager = MusicManager()