# daily_tasks.py
import json
import os
from datetime import datetime, timedelta
from random import sample
from currency import currency
from kivy.uix.popup import Popup
from kivy.uix.image import Image as KivyImage
from ads import AD_MANAGER  # чтобы показывать рекламу

# UI
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle

TASKS_FILE = 'saves/daily_tasks.json'

# награды
REWARDS = {
    'stay_10_min': 2,
    'play_mode': 1,
    'watch_ad': 4,
    'buy_avatar': 6,
    'complete_all': 7,
}

# пул задач (complete_all всегда присутствует)
BASE_POOL = ['stay_10_min', 'play_mode', 'watch_ad', 'buy_avatar']

# описания задач (для экрана)
TASK_DESCRIPTIONS = {
    'stay_10_min': 'Spend 10 minutes in the game (cumulative)',
    'play_mode': 'Start any game mode',
    'watch_ad': 'Watch the ad',
    'buy_avatar': 'Buy an avatar in the store',
    'complete_all': 'Complete all tasks (bonus)',
}

# технические утилиты
def _ensure_saves_dir():
    if not os.path.exists('saves'):
        os.makedirs('saves')

def _today_iso():
    return datetime.utcnow().date().isoformat()

def seconds_until_reset():
    """Секунды до следующей UTC-полночи (обновления задач)."""
    now = datetime.utcnow()
    next_midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
    return int((next_midnight - now).total_seconds())

# управление задачами / хранилище
def generate_tasks_for_today():
    _ensure_saves_dir()
    today = _today_iso()
    chosen = sample(BASE_POOL, 3)  # 3 из 4 случайно
    tasks = chosen + ['complete_all']
    data = {
        'date': today,
        'tasks': tasks,
        'completed': [],        # помеченные задачи (уже начисленные)
        'play_seconds': 0       # накопительное время в секундах за этот день
    }
    save_tasks(data)
    return data

def load_tasks():
    _ensure_saves_dir()
    if not os.path.exists(TASKS_FILE):
        return generate_tasks_for_today()
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return generate_tasks_for_today()
    # если устарело — перегенерируем
    if data.get('date') != _today_iso():
        return generate_tasks_for_today()
    # гарантии полей
    data.setdefault('tasks', [])
    data.setdefault('completed', [])
    data.setdefault('play_seconds', 0)
    return data

def save_tasks(data):
    _ensure_saves_dir()
    try:
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

def mark_task_completed(task_id):
    """
    Помечает задачу выполненной и начисляет награду (если ещё не начислена).
    Возвращает (awarded_amount:int, already_done:bool)
    """
    data = load_tasks()

    # если задачи нет — ничего не делаем
    if task_id not in data.get('tasks', []):
        return (0, False)

    # если уже выполнена — выходим
    if task_id in data.get('completed', []):
        return (0, True)

    # не разрешаем вручную завершать "complete_all"
    if task_id == 'complete_all':
        # Проверяем — выполнены ли все остальные
        normal_tasks = [t for t in data.get('tasks', []) if t != 'complete_all']
        all_done = all(t in data['completed'] for t in normal_tasks)
        if all_done:
            # если действительно все готовы — выдать бонус
            bonus = REWARDS.get('complete_all', 0)
            if bonus:
                try:
                    currency.add(bonus)
                except Exception:
                    pass
            data['completed'].append('complete_all')
            save_tasks(data)
            return (bonus, False)
        else:
            # если не все выполнены — ничего не даём
            return (0, False)

    # обычные задания — начисляем награду сразу
    amount = REWARDS.get(task_id, 0)
    if amount:
        try:
            currency.add(amount)
        except Exception:
            pass
    data['completed'].append(task_id)

    # проверяем — можно ли теперь выдать бонус complete_all
    normal_tasks = [t for t in data.get('tasks', []) if t != 'complete_all']
    all_done = all(t in data['completed'] for t in normal_tasks)
    if all_done and 'complete_all' in data.get('tasks', []) and 'complete_all' not in data['completed']:
        bonus = REWARDS.get('complete_all', 0)
        if bonus:
            try:
                currency.add(bonus)
            except Exception:
                pass
        data['completed'].append('complete_all')

    save_tasks(data)
    return (amount, False)


def add_play_seconds(seconds):
    """
    Добавляет секунды к накопительному времени за день и, если достигнут порог,
    помечает задачу stay_10_min выполненной (и выдаёт награду).
    seconds — целое количество секунд (обычно 1).
    """
    if seconds <= 0:
        return
    data = load_tasks()
    data['play_seconds'] = int(data.get('play_seconds', 0)) + int(seconds)
    save_tasks(data)
    # если достигаем 10 минут (600s) - помечаем таск
    if 'stay_10_min' in data.get('tasks', []) and 'stay_10_min' not in data.get('completed', []):
        if data['play_seconds'] >= 10 * 60:
            mark_task_completed('stay_10_min')

# ------------------ UI: экран ежедневных заданий ------------------
class DailyTasksScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # фон
        with self.canvas.before:
            Color(0.07, 0.07, 0.07, 1)
            self.bg = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._upd_bg, pos=self._upd_bg)

        self.root_layout = BoxLayout(orientation='vertical', padding=12, spacing=8)
        # таймер до обновления
        self.timer_label = Label(text="", size_hint=(1, None), height=30, font_size='18sp')
        self.root_layout.add_widget(self.timer_label)

        # scroll area для тасков
        self.scroll = ScrollView()
        self.grid = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=6)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scroll.add_widget(self.grid)
        self.root_layout.add_widget(self.scroll)

        # кнопка назад
        self.btn_back = Button(text="Назад", size_hint=(1, None), height=48)
        self.btn_back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'menu'))
        self.root_layout.add_widget(self.btn_back)

        self.add_widget(self.root_layout)

        # обновление UI каждую секунду
        Clock.schedule_interval(self._update_timer, 1.0)
        # обновим тут и сейчас
        Clock.schedule_once(lambda dt: self.refresh_ui(), 0.05)

    def show_praise(self, text):
        """Показываем короткую похвалу/награждение."""
        try:
            popup = Popup(title="Отлично!",
                          content=Label(text=text, halign='center'),
                          size_hint=(0.6, 0.3))
            popup.open()
            # Автоматически закрыть через 1.2 с
            Clock.schedule_once(lambda dt: popup.dismiss(), 1.2)
        except Exception:
            pass

    def show_hero_badge(self):
        """Если есть значок Герой дня — показываем поверх экрана."""
        # не добавляем несколько штук
        if getattr(self, '_hero_badge', None):
            return
        # Поставь в assets/hero_badge.png свою картинку знака
        badge_path = 'assets/hero_badge.png'
        if not os.path.exists(badge_path):
            # если нет — просто не показываем
            return
        img = KivyImage(source=badge_path, size_hint=(None, None), size=(120, 120))
        # позиционируем (в правом верхнем углу)
        img.pos = (self.width - img.width - 16, self.height - img.height - 16)
        # обновлять позицию при ресайзе
        def _update_pos(inst, *a):
            img.pos = (self.width - img.width - 16, self.height - img.height - 16)
        self.bind(size=_update_pos, pos=_update_pos)
        self._hero_badge = img
        # добавляем поверх всех виджетов
        self.add_widget(img)


    def _upd_bg(self, *a):
        self.bg.size = self.size
        self.bg.pos = self.pos

    def _update_timer(self, dt):
        secs = seconds_until_reset()
        if secs <= 0:
            # дата сменилась — регенерация произойдёт при load_tasks()
            self.refresh_ui()
            return
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        self.timer_label.text = f"До обновления заданий: {h:02d}:{m:02d}:{s:02d}"

    def refresh_ui(self):
        # обновляем содержимое списка задач
        self.grid.clear_widgets()
        data = load_tasks()
        play_seconds = data.get('play_seconds', 0)

        for tid in data.get('tasks', []):
            desc = TASK_DESCRIPTIONS.get(tid, tid)
            reward = REWARDS.get(tid, 0)
            done = tid in data.get('completed', [])
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=8, padding=[6,6,6,6])
            left = BoxLayout(orientation='vertical')
            label = Label(text=f"{desc}", halign='left', valign='middle')
            label_text = f"{desc} (+{reward} мон.)"
            # для stay_10_min показываем прогресс
            if tid == 'stay_10_min':
                # минуты и секунды
                got = min(play_seconds, 10*60)
                mm = got // 60
                ss = got % 60
                progress = f"Прогресс: {mm:02d}:{ss:02d} / 10:00"
                status = "Выполнено" if done else progress
            else:
                status = "Выполнено" if done else "Не выполнено"
            left.add_widget(Label(text=label_text, halign='left', valign='middle'))
            left.add_widget(Label(text=status, font_size='14sp', halign='left', valign='middle'))
            row.add_widget(left)

            btn = Button(size_hint=(None, None), size=(120, 44))
            if done:
                btn.text = "Получено"
                btn.disabled = True
            else:
                # Разные действия для разных типов задач
                if tid == 'stay_10_min':
                    btn.text = "Играть"
                    def _go_play(instance):
                        # переводим на выбор режима, пользователь сам играет — накопление секунд происходит в blocks_game
                        try:
                            self.manager.current = 'mode_select'
                        except Exception:
                            pass
                    btn.bind(on_press=_go_play)

                elif tid == 'play_mode':
                    btn.text = "Запустить"
                    def _start_mode(instance):
                        # переводим прямо в выбор режима (или можно запустить норм. режим)
                        try:
                            self.manager.current = 'mode_select'
                        except Exception:
                            pass
                    btn.bind(on_press=_start_mode)

                elif tid == 'watch_ad':
                    btn.text = "Смотреть"
                    def _watch_ad(instance):
                        # при on_reward — помечаем таск и показываем похвалу
                        def on_reward():
                            try:
                                awarded, already = mark_task_completed('watch_ad')
                                if awarded and not already:
                                    self.show_praise(f"+{awarded} монет")
                            except Exception:
                                pass
                            # обновим UI
                            Clock.schedule_once(lambda dt: self.refresh_ui(), 0.1)

                        ok, reason = AD_MANAGER.show_rewarded(on_reward=on_reward)
                        if not ok:
                            Popup(title="Реклама", content=Label(text=reason), size_hint=(0.6,0.3)).open()

                    btn.bind(on_press=_watch_ad)

                elif tid == 'buy_avatar':
                    btn.text = "Открыть магазин"
                    def _open_shop(instance):
                        try:
                            from shop import shop
                            shop.open()
                        except Exception:
                            pass
                    btn.bind(on_press=_open_shop)

                else:
                    # дефолтный — безопасно пытаемся пометить (если задача не-зависимая)
                    btn.text = "Попытаться"
                    def _on_try_default(instance, task_id=tid):
                        awarded, already = mark_task_completed(task_id)
                        if awarded and not already:
                            self.show_praise(f"+{awarded} монет")
                        # проверим бонус all
                        data = load_tasks()
                        if 'complete_all' in data.get('completed', []):
                            self.show_hero_badge()
                        self.refresh_ui()
                    btn.bind(on_press=_on_try_default)

            row.add_widget(btn)

            self.grid.add_widget(row)

        # после заполнения grid и кнопок:
        data = load_tasks()
        if 'complete_all' in data.get('completed', []):
            self.show_hero_badge()
        else:
            # если был badge ранее, снимем
            if getattr(self, '_hero_badge', None):
                try:
                    self.remove_widget(self._hero_badge)
                except Exception:
                    pass
                self._hero_badge = None


        # обновим timer сразу
        self._update_timer(0)
