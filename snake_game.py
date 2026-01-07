from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Line  # Добавь в начало файла
from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty
import random
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.floatlayout import FloatLayout




GRID_SIZE = 20
GRID_WIDTH = 20
GRID_HEIGHT = 20

class SnakeGame(Widget):
    snake = ListProperty([])
    food = ListProperty([0, 0])
    direction = ListProperty([1, 0])

    def __init__(self, screen_manager=None, **kwargs):
        super().__init__(**kwargs)
        self.cell_size = GRID_SIZE
        self.screen_manager = screen_manager
        self.reset_game()
        Clock.schedule_interval(self.update, 0.2)

    def reset_game(self):
        self.snake = [[5, 5], [4, 5], [3, 5]]
        self.direction = [1, 0]
        self.spawn_food()
        self.game_over = False

    def spawn_food(self):
        while True:
            food = [random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1)]
            if food not in self.snake:
                self.food = food
                break
    
    
    
    
    
    def on_touch_up(self, touch):
        dx = touch.x - touch.opos[0]
        dy = touch.y - touch.opos[1]
        if abs(dx) > abs(dy):
            if dx > 0 and self.direction != [-1, 0]:
                self.direction = [1, 0]
            elif dx < 0 and self.direction != [1, 0]:
                self.direction = [-1, 0]
        else:
            if dy > 0 and self.direction != [0, -1]:
                self.direction = [0, 1]
            elif dy < 0 and self.direction != [0, 1]:
                self.direction = [0, -1]

    def update(self, dt):
        if self.game_over:
            if self.screen_manager:
                self.screen_manager.current = 'game_over'
            return

    
        head = self.snake[0]
        new_head = [head[0] + self.direction[0], head[1] + self.direction[1]]

        if (new_head in self.snake or
            new_head[0] < 0 or new_head[0] >= GRID_WIDTH or
            new_head[1] < 0 or new_head[1] >= GRID_HEIGHT):
            self.game_over = True
            return


        self.snake = [new_head] + self.snake

        if new_head == self.food:
            self.spawn_food()
        else:
            self.snake.pop()

        self.draw()

    def draw(self):
        self.canvas.clear()
        with self.canvas:
            # Фон
            Color(0.1, 0.1, 0.1)
            Rectangle(pos=self.pos, size=self.size)
            
            # Зелёная рамка (толщина 2px)
            Color(0, 1, 0)  # Зелёный цвет
            # Внешняя граница
            Line(rectangle=(self.x, self.y, self.width, self.height), width=2)
        self.canvas.clear()
        with self.canvas:
            # фон
            Color(0.1, 0.1, 0.1)
            Rectangle(pos=self.pos, size=self.size)

            # еда
            Color(1, 0, 0)
            Rectangle(pos=(self.food[0] * self.cell_size, self.food[1] * self.cell_size),
                      size=(self.cell_size, self.cell_size))

            # змейка
            Color(0, 1, 0)
            for segment in self.snake:
                Rectangle(pos=(segment[0] * self.cell_size, segment[1] * self.cell_size),
                          size=(self.cell_size, self.cell_size))

def get_game_over_screen(switch_to_snake_game):
    screen = Screen(name='game_over')
    layout = BoxLayout(orientation='vertical')
    
    # Добавляем текст "GAME OVER"
    label = Label(text='GAME OVER', font_size=50)
    layout.add_widget(label)
    
    # Кнопка RESTART
    restart_btn = Button(text='RESTART', size_hint=(0.5, 0.2))
    restart_btn.bind(on_press=lambda x: switch_to_snake_game())
    layout.add_widget(restart_btn)
    
    screen.add_widget(layout)
    return screen

def get_snake_screen(switch_to_menu, screen_manager):
    game = SnakeGame(size_hint=(1, 1), screen_manager=screen_manager)

    # Включаем screen_manager в параметры функции
    screen = Screen(name='snake')
    
    # Создаем layout для основного экрана
    main_layout = BoxLayout(orientation='vertical')
    
    # Создаем layout для игрового поля с отступами
    game_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.8))
    
    game_layout.add_widget(game)
    main_layout.add_widget(game_layout)
    
    # Создаем layout для кнопок управления (ромбиком)
    controls_layout = FloatLayout(size_hint=(1, 0.2))
    
    # Координаты для кнопок в форме ромба
    button_positions = [
        ('←', [-1, 0], (0.4, 0.1)),   # лево
        ('↑', [0, 1], (0.5, 0.2)),    # верх
        ('↓', [0, -1], (0.5, 0.0)),   # низ
        ('→', [1, 0], (0.6, 0.1))     # право
    ]
    
    for text, vector, pos in button_positions:
        btn = Button(
            text=text,
            size_hint=(0.1, 0.1),
            pos_hint={'x': pos[0], 'y': pos[1]}
        )
        btn.bind(on_press=lambda instance, v=vector: setattr(game, 'direction', v))
        controls_layout.add_widget(btn)
    
    # Кнопка меню
    menu_btn = Button(
        text='Меню',
        size_hint=(0.2, 0.1),
        pos_hint={'x': 0.8, 'y': 0.1}
    )
    menu_btn.bind(on_press=lambda x: switch_to_menu())
    controls_layout.add_widget(menu_btn)
    
    main_layout.add_widget(controls_layout)
    screen.add_widget(main_layout)
    return screen

# Перенесем создание ScreenManager в конец файла, после всех определений
# и исправим вызовы функций:

if __name__ == '__main__':
    sm = ScreenManager()
    
    # Исправленные лямбда-функции:
    sm.add_widget(get_snake_screen(lambda: setattr(sm, 'current', 'menu'), sm))
    
    def restart_game():
        sm.current = 'snake'
        snake_screen = sm.get_screen('snake')
        # Получаем доступ к игровому виджету через иерархию виджетов
        for child in snake_screen.children:
            if isinstance(child, BoxLayout):
                for grandchild in child.children:
                    if isinstance(grandchild, SnakeGame):
                        grandchild.reset_game()
    
    sm.add_widget(get_game_over_screen(restart_game))
    sm.current = 'snake'