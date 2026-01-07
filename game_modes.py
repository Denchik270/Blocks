from config import settings
from kivy.clock import Clock

class GameMode:
    def activate(self, game):
        """Метод активации режима. Должен быть переопределён."""
        pass


class NormalMode(GameMode):
    def activate(self, game):
        game.is_visible = True
        game.hard_drop_enabled = True
        game.lock_delay = 0.5
        game.use_ghost_piece = True
        game.apply_standard_rendering()

        # теперь *speed_level* управляет скоростью
        def new_increase_speed(inst):
            if game.speed_level < 10:         # предел – 10
                game.speed_level += 1
            game.update_fall_speed()

        def new_decrease_speed(inst):
            if game.speed_level > 1:          # минимум – 1
                game.speed_level -= 1
            game.update_fall_speed()

        game.increase_speed = new_increase_speed
        game.decrease_speed = new_decrease_speed

class GostMode(GameMode):
    def __init__(self, level=1):
        self.level = level
        self.step_count = 0
        # Добавьте настройки сразу в конструкторе
        self.gost_mode_settings = {
            'steps_to_disappear': 5,  # 5 шагов для уровня 1
            'appear_on_lock': True,
            'lock_appear_time': 1.5,
            'show_next': True
        }
        
    def activate(self, game):
        game.is_visible = True  # Сначала показываем фигуру
        game.use_ghost_piece = False
        self.game = game
        self.step_count = 0  # Сброс счетчика шагов

        # Обновляем настройки в зависимости от уровня
        if self.level == 1:
            self.gost_mode_settings = {
                'steps_to_disappear': 5,
                'appear_on_lock': True,
                'lock_appear_time': 1.5,
                'show_next': True
            }
        elif self.level == 2:
            self.gost_mode_settings = {
                'steps_to_disappear': 3,
                'appear_on_lock': True,
                'lock_appear_time': 0.1,  # Показывается только до следующего хода
                'show_next': True
            }
        elif self.level == 3:
            self.gost_mode_settings = {
                'steps_to_disappear': 1,
                'appear_on_lock': False,
                'lock_appear_time': 0,
                'show_next': False
            }
        
        # Сохраняем настройки в игре
        game.gost_mode_settings = self.gost_mode_settings
        
        if self.gost_mode_settings['show_next'] == False:
            settings.show_next = False
            game.set_show_next(False)
            
        game.apply_invisible_rendering()

class LightningMode(GameMode):
    def activate(self, game):
        game.is_visible = True
        game.hard_drop_enabled = False
        game.lock_delay = 0.05  # Уменьшаем задержку фиксации
        game.instant_rotate = True
        game.disable_hold = True
        game.apply_tgm_rendering()

        # Ограничиваем максимальную скорость для стабильности
        def new_increase_speed(inst):
            if game.speed_level < 15:  # Максимум 15 вместо 20
                game.speed_level += 1
            game.update_fall_speed()

        def new_decrease_speed(inst):
            if game.speed_level > 11:  # Минимум 10 вместо 11
                game.speed_level -= 1
            game.update_fall_speed()

        game.increase_speed = new_increase_speed  
        game.decrease_speed = new_decrease_speed