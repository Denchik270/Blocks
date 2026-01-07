# ads.py
import time
import json
import os
from functools import partial
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.app import App
import socket
# локальная валюта/баланс (твой модуль)
from currency import currency

# Конфиг лимитов
MAX_PER_HOUR = 3
MAX_PER_DAY = 12

# где храним историю показов (по пользователю; у тебя может быть профиль — тут простая реализация)
HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'ads_history.json')





def _load_history():
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"timestamps": []}


def _save_history(data):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception:
        pass


def _prune_and_count(history, now=None):
    """Вернуть (timestamps_filtered, count_last_hour, count_today)."""
    now = now or time.time()
    one_hour_ago = now - 3600
    midnight = time.mktime(time.localtime(now)[:3] + (0, 0, 0, 0, 0, -1))  # 00:00 today (approx)
    # проще: filter by today using localtime day/month/year
    l = history.get("timestamps", [])
    # фильтруем старые
    last_hour = [t for t in l if t >= one_hour_ago]
    today_struct = time.localtime(now)
    def is_today(ts):
        s = time.localtime(ts)
        return (s.tm_year, s.tm_yday) == (today_struct.tm_year, today_struct.tm_yday)
    today = [t for t in l if is_today(t)]
    # обновим историю to keep only recent (e.g. last 7 days)
    cutoff = now - 7 * 24 * 3600
    history["timestamps"] = [t for t in l if t >= cutoff]
    return history, len(last_hour), len(today)


def can_watch_ad():
    hist = _load_history()
    hist, last_hour_count, today_count = _prune_and_count(hist)
    if last_hour_count >= MAX_PER_HOUR:
        wait = get_next_ad_wait_time()
        return False, f"⏳ Доступно через {format_seconds(wait)}"
    if today_count >= MAX_PER_DAY:
        wait = get_next_ad_wait_time()
        return False, f"⏳ Следующий день через {format_seconds(wait)}"
    return True, None

def get_next_ad_wait_time():
    hist = _load_history()
    now = time.time()
    timestamps = sorted(hist.get("timestamps", []))

    if not timestamps:
        return 0

    # лимит в час
    if len([t for t in timestamps if t >= now - 3600]) >= MAX_PER_HOUR:
        oldest = min(t for t in timestamps if t >= now - 3600)
        return max(0, int((oldest + 3600) - now))

    # лимит в день
    today = time.localtime(now)
    today_ts = [t for t in timestamps
                if time.localtime(t).tm_yday == today.tm_yday
                and time.localtime(t).tm_year == today.tm_year]

    if len(today_ts) >= MAX_PER_DAY:
        tomorrow = time.mktime((
            today.tm_year, today.tm_mon, today.tm_mday + 1,
            0, 0, 0, 0, 0, -1
        ))
        return max(0, int(tomorrow - now))

    return 0

def format_seconds(sec):
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}ч {m}м"
    if m:
        return f"{m}м {s}с"
    return f"{s}с"


def record_ad_watch():
    hist = _load_history()
    hist.setdefault("timestamps", [])
    hist["timestamps"].append(time.time())
    _save_history(hist)


# -----------------------
# простой тестовый Popup (desktop / тестовые сборки)
# -----------------------
class AdPopup(Popup):
    def __init__(self, reward_callback=None, reward_amount=10, **kwargs):
        super().__init__(**kwargs)
        self.title = "Watch ads to get reward"
        self.size_hint = (0.8, 0.6)
        self.reward_callback = reward_callback
        self.reward_amount = reward_amount

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.ad_content = Label(text="[Simulated Ad] Watch to get reward", halign='center')
        layout.add_widget(self.ad_content)

        self.timer_label = Label(text="Closing in: 5")
        layout.add_widget(self.timer_label)

        self.close_btn = Button(text="Close (disabled)", disabled=True, size_hint_y=None, height=50)
        self.close_btn.bind(on_press=self._on_close_pressed)
        layout.add_widget(self.close_btn)

        self.content = layout
        self.countdown = 5
        self._evt = Clock.schedule_interval(self._tick, 1)
        # если пользователю нужно прогонять тест — можно позволить закрыть раньше, но для репликации real ad — блокируем

    def _tick(self, dt):
        self.countdown -= 1
        if self.countdown <= 0:
            self.timer_label.text = "You can close ad"
            self.close_btn.disabled = False
            Clock.unschedule(self._evt)
            return False
        else:
            self.timer_label.text = f"Closing in: {self.countdown}"

    def _on_close_pressed(self, *_):
        # Считаем просмотр состоявшимся (тест)
        try:
            # сначала запишем историю просмотров (cooldown)
            record_ad_watch()
            # затем начислим монеты тут или делегировать менеджеру (зависит от режима)
            currency.add(self.reward_amount)
            # и вызовем external callback, чтобы игра могла обновить UI
            if self.reward_callback:
                try:
                    self.reward_callback()
                except Exception:
                    pass
        finally:
            self.dismiss()

    def on_dismiss(self):
        # гарантия что таймер не останется
        try:
            Clock.unschedule(self._evt)
        except Exception:
            pass


# -----------------------
# AdManager: единый интерфейс для показа rewarded
# -----------------------
class AdManager:
    def __init__(self, android_bridge=None, reward_amount=10):
        """
        android_bridge: optional autoclass('...AdsBridge') object (если на Android реализуешь Java bridge)
        """
        self.android_bridge = android_bridge
        self.reward_amount = reward_amount
        self._is_showing = False
        # тестовый popup
        self._popup = None

    
    def is_internet_available(self, host="8.8.8.8", port=53, timeout=3):
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except Exception:
            return False

    def show_rewarded(self, on_reward=None, test_fallback=True):
        """
        on_reward: функция без аргументов, вызываемая когда пользователь заработал награду.
        test_fallback: если True и нет android_bridge, откроет тестовый popup.
        """
        ok, reason = can_watch_ad()
        if not ok:
            popup = Popup(title="Ad", content=Label(text=reason), size_hint=(0.7,0.3))
            popup.open()
            return False, reason   # <-- ВАЖНО: явный возврат

        if not self.is_internet_available():
            popup = Popup(title="No Internet",
                        content=Label(text="Check your connection"),
                        size_hint=(0.7, 0.3))
            popup.open()
            return False, "no internet"


        # Если есть bridge на Android — попросим показать реальную рекламу
        if self.android_bridge:
            try:
                self._is_showing = True
                self.android_bridge.showRewarded()  # <- нужно реализовать в Java
                # запись просмотра и начисление делаем когда придёт callback из Java
                return True, None
            except Exception as e:
                print("Android bridge show failed:", e)
                # fallback to popup (далее пойдёт fallback)

        # fallback: локальный popup (desktop / тест)
        if test_fallback:
            self._popup = AdPopup(reward_callback=partial(self._on_test_reward, on_reward),
                                reward_amount=self.reward_amount)
            self._popup.open()
            return True, None

        return False, "no ad backend"

    def _on_test_reward(self, external_cb=None):
        # вызывается когда тестовый popup закончился -> выдаём reward и записываем просмотр
        # запись уже сделана в AdPopup, но перестрахуемся:
        record_ad_watch()
        currency.add(self.reward_amount)
        if external_cb:
            try:
                external_cb()
            except Exception:
                pass

    # Этот метод должен быть вызван из Android bridge, когда SDK подтвердит onUserEarnedReward.
    def on_android_reward_received(self):
        record_ad_watch()
        currency.add(self.reward_amount)
        app = App.get_running_app()
        if app and hasattr(app, 'refresh_ui_after_reward'):
            try:
                app.refresh_ui_after_reward()
            except Exception:
                pass
        self._is_showing = False



# глобальный менеджер, который можно импортировать в shop.py
AD_MANAGER = AdManager()
