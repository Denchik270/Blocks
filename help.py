from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from config import settings
import os
from kivy.graphics import Color, Rectangle, Line

class HelpScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        with self.canvas.before:
            # статический фон настроек (не зависит от game_background)
            self.bg_rect = Rectangle(source='assets/seting.jpg', size=self.size, pos=self.pos)
        self.bind(size=self.update_bg, pos=self.update_bg)
        
        scroll = ScrollView()
        help_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        help_layout.bind(minimum_height=help_layout.setter('height'))
        
        instructions = settings.translations.get(
            settings.language,
            settings.translations['en']
        ).get('help_text', 'No help available')
        
        help_label = Label(
            text=instructions, markup=True,
            font_size='16sp', halign='left', valign='top',
            size_hint_y=None
        )
        # важный костыль: меняем размер после загрузки текстуры
        help_label.bind(texture_size=lambda instance, value: setattr(instance, 'size', value))
        
        help_layout.add_widget(help_label)
        scroll.add_widget(help_layout)
        layout.add_widget(scroll)
        
        back_btn = Button(text='Back', size_hint=(1, 0.1))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        layout.add_widget(back_btn)
        
        self.add_widget(layout)
    
    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size