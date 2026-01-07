from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.core.window import Window
from typing import Dict, Any
import json
import os

class PlayerProfile:
    def __init__(self):
        self.unlocked_avatars = ['assets/default_avatar.png']
        self.high_scores = {
            'normal': 0,
            'gost': 0,
            'lightning': 0
        }
        self.player_name = "Player"
        self.avatar = "assets/default_avatar.png"  # Путь к изображению аватара
        self.load_profile()
        
    def save_profile(self):
        """Сохраняет все данные профиля в файл"""
        profile_data = {
            'unlocked_avatars': self.unlocked_avatars,
            'high_scores': self.high_scores,
            'player_name': self.player_name,
            'avatar': self.avatar
        }
        try:
            if not os.path.exists('saves'):
                os.makedirs('saves')
            with open('saves/player_profile.json', 'w') as f:
                json.dump(profile_data, f)
        except Exception as e:
            print(f"Error saving profile: {e}")

    def load_profile(self):
        """Загружает данные профиля из файла"""
        try:
            if os.path.exists('saves/player_profile.json'):
                with open('saves/player_profile.json', 'r') as f:
                    data = json.load(f)
                    self.unlocked_avatars = data.get('unlocked_avatars', ['assets/default_avatar.png'])
                    self.high_scores = data.get('high_scores', self.high_scores)
                    self.player_name = data.get('player_name', "Player")
                    self.avatar = data.get('avatar', "assets/default_avatar.png")
        except Exception as e:
            print(f"Error saving profile: {e}")

    def update_high_score(self, mode, score):
        """Обновляет рекорд для указанного режима"""
        if score > self.high_scores.get(mode, 0):
            self.high_scores[mode] = score
            self.save_profile()

    def show_profile_popup(self):
        """Показывает всплывающее окно с профилем"""
        popup = Popup(
            title=f"{self.player_name}'s Profile",
            size_hint=(0.8, 0.7),
            auto_dismiss=True
        )
        
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Аватар
        avatar = Image(
            source=self.avatar,
            size_hint=(1, 0.4),
            fit_mode="contain"
        )
        layout.add_widget(avatar)
        
        # Имя игрока
        name_label = Label(
            text=f"Name: {self.player_name}",
            font_size=35,
            size_hint=(1, 0.1)
        )
        layout.add_widget(name_label)
        
        # Рекорды
        scores_label = Label(
            text="High Scores:",
            font_size=32,
            size_hint=(1, 0.1)
        )
        layout.add_widget(scores_label)
        
        for mode, score in self.high_scores.items():
            score_label = Label(
                text=f"{mode.capitalize()}: {score}",
                font_size=28,
                size_hint=(1, 0.08)
            )
            layout.add_widget(score_label)
        
        # Кнопки
        btn_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)
        edit_btn = Button(text="Edit Profile")
        edit_btn.bind(on_press=lambda x: self.edit_profile(popup))
        btn_layout.add_widget(edit_btn)
        
        close_btn = Button(text="Close")
        close_btn.bind(on_press=popup.dismiss)
        btn_layout.add_widget(close_btn)
        
        layout.add_widget(btn_layout)
        popup.content = layout
        popup.open()

    def edit_profile(self, popup):
        """Редактирование профиля"""
        edit_popup = Popup(
            title="Edit Profile",
            size_hint=(0.8, 0.6)
        )
        
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Поле для ввода имени
        from kivy.uix.textinput import TextInput
        name_input = TextInput(
            text=self.player_name,
            size_hint=(1, 0.2),
            multiline=False
        )
        
        # Кнопка смены аватара
        change_avatar_btn = Button(
            text="Change Avatar",
            size_hint=(1, 0.2)
        )
        change_avatar_btn.bind(on_press=lambda x: self.change_avatar(edit_popup))
        
        # Кнопки сохранения/отмены
        btn_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)
        save_btn = Button(text="Save")
        save_btn.bind(on_press=lambda x: self.save_profile_changes(name_input.text, edit_popup, popup))
        btn_layout.add_widget(save_btn)
        
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_press=edit_popup.dismiss)
        btn_layout.add_widget(cancel_btn)
        
        layout.add_widget(Label(text="Your Name:"))
        layout.add_widget(name_input)
        layout.add_widget(change_avatar_btn)
        layout.add_widget(btn_layout)
        
        edit_popup.content = layout
        edit_popup.open()

    def change_avatar(self, popup):
        popup.dismiss()
        from shop import shop
        shop.open()
        shop.show_category('Avatars')


    def set_avatar(self, path, selection, popup):
        """Устанавливает новый аватар"""
        if selection:
            self.avatar = selection[0]
            self.save_profile()
        popup.dismiss()

    def save_profile_changes(self, new_name, edit_popup, profile_popup):
        """Сохраняет изменения профиля"""
        self.player_name = new_name
        self.save_profile()
        edit_popup.dismiss()
        profile_popup.dismiss()
        self.show_profile_popup()

# Глобальный экземпляр профиля
profile = PlayerProfile()