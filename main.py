from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.core.audio import SoundLoader
from kivy.properties import StringProperty
from kivy.metrics import dp, sp
from collections import deque
import requests
import json
import os
import time

try:
    LabelBase.register(name='Chinese', fn_regular='/system/fonts/NotoSansCJK-Regular.ttc')
except:
    try:
        LabelBase.register(name='Chinese', fn_regular='/system/fonts/DroidSansFallback.ttf')
    except:
        LabelBase.register(name='Chinese', fn_regular='/system/fonts/Roboto-Regular.ttf')

Window.clearcolor = (0.1, 0.1, 0.18, 1)

API_URL = "http://www.txff-online.com/openline"
MAX_HISTORY = 3
POS_KEYS = ["wan", "qian", "bai", "shi", "ge"]
POS_NAMES_CN = {"wan": "万位", "qian": "千位", "bai": "百位", "shi": "十位", "ge": "个位"}
DATA_FILE = "rolling_stats.json"
CONFIG_FILE = "app_config.json"

TRIPLE_PATTERN = ['111', '222', '333', '444', '555', '666', '777', '888', '999', '000']


class RollingApp(App):
    sound_path = StringProperty('')
    
    def build(self):
        self.rolling_history = {k: deque(maxlen=MAX_HISTORY) for k in POS_KEYS}
        self.last_raw_number = None
        self.sound = None
        self.triplet_positions = set()
        
        self.load_stats()
        self.load_config()
        
        root = BoxLayout(orientation='vertical', padding=dp(20))
        
        root.add_widget(Widget(size_hint_y=0.03))
        
        root.add_widget(Label(
            text='滚动历史统计',
            font_size=sp(26),
            color=(0.91, 0.27, 0.38, 1),
            size_hint_y=None,
            height=dp(40),
            font_name='Chinese',
            bold=True
        ))
        
        root.add_widget(Widget(size_hint_y=None, height=dp(15)))
        
        self.result_label = Label(
            text='-----',
            font_size=sp(44),
            color=(0, 1, 0.53, 1),
            font_name='Roboto',
            bold=True,
            size_hint_y=None,
            height=dp(55)
        )
        root.add_widget(self.result_label)
        
        root.add_widget(Widget(size_hint_y=None, height=dp(8)))
        
        self.sum_label = Label(
            text='各位之和: -',
            font_size=sp(15),
            color=(0.63, 0.63, 0.69, 1),
            font_name='Chinese',
            size_hint_y=None,
            height=dp(25)
        )
        root.add_widget(self.sum_label)
        
        root.add_widget(Widget(size_hint_y=None, height=dp(35)))
        
        header_grid = GridLayout(cols=5, spacing=dp(10), size_hint_y=None, height=dp(28))
        for pos in POS_KEYS:
            header_grid.add_widget(Label(
                text=POS_NAMES_CN[pos],
                font_size=sp(15),
                color=(0.91, 0.27, 0.38, 1),
                font_name='Chinese'
            ))
        root.add_widget(header_grid)
        
        root.add_widget(Widget(size_hint_y=None, height=dp(8)))
        
        self.value_labels = {}
        digits_grid = GridLayout(cols=5, spacing=dp(10), size_hint_y=None, height=dp(45))
        for pos in POS_KEYS:
            lbl = Label(
                text='-',
                font_size=sp(32),
                color=(1, 1, 1, 1),
                font_name='Roboto',
                bold=True
            )
            self.value_labels[pos] = lbl
            digits_grid.add_widget(lbl)
        root.add_widget(digits_grid)
        
        root.add_widget(Widget(size_hint_y=None, height=dp(30)))
        
        self.status_label = Label(
            text='共 0 条 | --:--:--',
            font_size=sp(13),
            color=(0.4, 0.4, 0.53, 1),
            font_name='Chinese',
            size_hint_y=None,
            height=dp(22)
        )
        root.add_widget(self.status_label)
        
        root.add_widget(Widget(size_hint_y=None, height=dp(10)))
        
        self.alert_label = Label(
            text='',
            font_size=sp(15),
            color=(1, 0.27, 0.27, 1),
            font_name='Chinese',
            bold=True,
            size_hint_y=None,
            height=dp(28)
        )
        root.add_widget(self.alert_label)
        
        root.add_widget(Widget(size_hint_y=1))
        
        btn_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(12))
        
        refresh_btn = Button(
            text='立即刷新',
            size_hint_x=0.5,
            background_color=(0.06, 0.2, 0.38, 1),
            color=(1, 1, 1, 1),
            font_name='Chinese',
            font_size=sp(14)
        )
        refresh_btn.bind(on_press=lambda x: self.update_data())
        
        sound_btn = Button(
            text='设置铃声',
            size_hint_x=0.5,
            background_color=(0.2, 0.38, 0.06, 1),
            color=(1, 1, 1, 1),
            font_name='Chinese',
            font_size=sp(14)
        )
        sound_btn.bind(on_press=self.show_sound_chooser)
        
        btn_box.add_widget(refresh_btn)
        btn_box.add_widget(sound_btn)
        root.add_widget(btn_box)
        
        root.add_widget(Widget(size_hint_y=None, height=dp(15)))
        
        Clock.schedule_interval(self.update_data, 10)
        Clock.schedule_once(self.update_data, 0)
        
        return root
    
    def load_stats(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    data = json.load(f)
                    for pos in POS_KEYS:
                        items = data.get(pos, [])
                        self.rolling_history[pos] = deque([str(x) for x in items], maxlen=MAX_HISTORY)
            except:
                pass
    
    def save_stats(self):
        try:
            data = {pos: list(self.rolling_history[pos]) for pos in POS_KEYS}
            with open(DATA_FILE, 'w') as f:
                json.dump(data, f)
        except:
            pass
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.sound_path = config.get('sound_path', '')
                    if self.sound_path and os.path.exists(self.sound_path):
                        self.sound = SoundLoader.load(self.sound_path)
            except:
                pass
    
    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'sound_path': self.sound_path}, f)
        except:
            pass
    
    def show_sound_chooser(self, instance):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        
        storage_path = '/storage/emulated/0'
        if not os.path.exists(storage_path):
            storage_path = '/sdcard'
        
        filechooser = FileChooserListView(
            path=storage_path,
            filters=['*.mp3', '*.wav', '*.ogg', '*.m4a', '*.WAV', '*.MP3', '*.flac', '*.aac'],
            size_hint_y=0.7
        )
        content.add_widget(filechooser)
        
        current_sound = Label(
            text=f'当前: {os.path.basename(self.sound_path) if self.sound_path else "默认"}',
            font_size=sp(13),
            color=(0.63, 0.63, 0.69, 1),
            size_hint_y=None,
            height=dp(25),
            font_name='Chinese'
        )
        content.add_widget(current_sound)
        
        btn_box = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
        
        select_btn = Button(text='选择', font_name='Chinese', font_size=sp(14))
        preview_btn = Button(text='试听', font_name='Chinese', font_size=sp(14))
        cancel_btn = Button(text='取消', font_name='Chinese', font_size=sp(14))
        
        popup = Popup(title='选择铃声 (支持 MP3/WAV/OGG)', content=content, size_hint=(0.95, 0.85))
        
        def on_select(instance):
            if filechooser.selection:
                self.sound_path = filechooser.selection[0]
                self.sound = SoundLoader.load(self.sound_path)
                self.save_config()
                current_sound.text = f'当前: {os.path.basename(self.sound_path)}'
                self.status_label.text = f'铃声已设置 | {time.strftime("%H:%M:%S")}'
            popup.dismiss()
        
        def on_preview(instance):
            if filechooser.selection:
                preview_sound = SoundLoader.load(filechooser.selection[0])
                if preview_sound:
                    preview_sound.play()
            elif self.sound:
                self.sound.play()
        
        select_btn.bind(on_press=on_select)
        preview_btn.bind(on_press=on_preview)
        cancel_btn.bind(on_press=popup.dismiss)
        
        btn_box.add_widget(select_btn)
        btn_box.add_widget(preview_btn)
        btn_box.add_widget(cancel_btn)
        content.add_widget(btn_box)
        
        popup.open()
    
    def play_alert(self):
        if self.sound:
            try:
                self.sound.play()
            except:
                pass
    
    def check_triplets(self):
        triplets = []
        self.triplet_positions.clear()
        
        for pos in POS_KEYS:
            val = ''.join(self.rolling_history[pos])
            if val in TRIPLE_PATTERN:
                triplets.append(f"{POS_NAMES_CN[pos]}:{val}")
                self.triplet_positions.add(pos)
        
        return triplets
    
    def convert_to_5digit(self, number_str):
        digits = [int(d) for d in number_str]
        digit_sum = sum(digits)
        ten_thousands = digit_sum % 10
        n = len(digits)
        thousands = digits[-4] if n >= 4 else 0
        hundreds = digits[-3] if n >= 3 else 0
        tens = digits[-2] if n >= 2 else 0
        units = digits[-1] if n >= 1 else 0
        result = ten_thousands * 10000 + thousands * 1000 + hundreds * 100 + tens * 10 + units
        result_str = str(result).zfill(5)
        pos_digits = {"wan": ten_thousands, "qian": thousands, "bai": hundreds, "shi": tens, "ge": units}
        return result_str, digit_sum, pos_digits
    
    def update_data(self, dt=None):
        try:
            resp = requests.get(API_URL, timeout=10)
            data = resp.json()
            if data.get("success"):
                raw = data["onlineDataNow"].replace(",", "")
                is_new = (raw != self.last_raw_number)
                
                if is_new:
                    self.last_raw_number = raw
                    result, digit_sum, pos_digits = self.convert_to_5digit(raw)
                    
                    for pos, digit in pos_digits.items():
                        self.rolling_history[pos].append(str(digit))
                    
                    self.save_stats()
                    self.result_label.text = result
                    self.sum_label.text = f'各位之和: {digit_sum}'
                
                triplets = self.check_triplets()
                if triplets:
                    self.alert_label.text = f'警报: {" ".join(triplets)}'
                    if is_new:
                        self.play_alert()
                else:
                    self.alert_label.text = ''
                
                for pos in POS_KEYS:
                    val = ''.join(self.rolling_history[pos]) if self.rolling_history[pos] else "-"
                    if pos in self.triplet_positions:
                        self.value_labels[pos].color = (1, 0.27, 0.27, 1)
                    else:
                        self.value_labels[pos].color = (1, 1, 1, 1)
                    self.value_labels[pos].text = val
                
                self.status_label.text = f'共 {len(self.rolling_history["ge"])} 条 | {time.strftime("%H:%M:%S")}'
        except Exception as e:
            self.status_label.text = f'获取失败 | {time.strftime("%H:%M:%S")}'


if __name__ == '__main__':
    RollingApp().run()
