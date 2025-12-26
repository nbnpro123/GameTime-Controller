import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime, timedelta
import threading
import sys
from pathlib import Path
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import time








class PCController:
    def __init__(self):

        self.settings_file = "settings.json"
        self.sessions_file = "sessions.json"
        self.default_settings = {
            "limit_mode": True,
            "management_password": "123",
            "game_time_minutes": 120,
            "rest_time_minutes": 60,
            "shutdown_request_minutes": 3,
            "shutdown_schedule": [
                {"day": "Monday", "time": "22:00"},
                {"day": "Tuesday", "time": "22:00"},
                {"day": "Wednesday", "time": "22:00"},
                {"day": "Thursday", "time": "22:00"},
                {"day": "Friday", "time": "23:00"},
                {"day": "Saturday", "time": "23:30"},
                {"day": "Sunday", "time": "22:30"}
            ]
        }

        # Текущая сессия
        self.current_session_start = None
        self.shutdown_timer = None
        self.warning_window = None



        # Загружаем настройки
        self.settings = self.load_settings()

        # Загружаем историю сессий
        self.sessions = self.load_sessions()

        # 🔴 ВАЖНО: сначала закрываем старую сессию
        self.close_previous_session_if_needed()

        # потом проверяем лимиты
        self.check_limits_at_startup()

        threading.Thread(target=self.background_checker, daemon=True).start()
        self.create_tray_icon()





    def load_settings(self):
        """Загружает настройки из файла или создает файл с настройками по умолчанию"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # Проверяем, что все необходимые поля есть
                    for key in self.default_settings:
                        if key not in settings:
                            settings[key] = self.default_settings[key]
                    return settings
            else:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(self.default_settings, f, indent=2, ensure_ascii=False)
                return self.default_settings.copy()
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            return self.default_settings.copy()

    def save_settings(self):
        """Сохраняет настройки в файл"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def load_sessions(self):
        """Загружает историю сессий"""
        try:
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"sessions": [], "current_session_start": None}
        except Exception as e:
            print(f"Ошибка загрузки сессий: {e}")
            return {"sessions": [], "current_session_start": None}

    def save_sessions(self):
        """Сохраняет историю сессий"""
        try:
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(self.sessions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения сессий: {e}")

    def get_shutdown_time_for_today(self):
        """Получает время выключения для текущего дня недели"""
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        current_day = day_names[datetime.now().weekday()]

        for schedule in self.settings["shutdown_schedule"]:
            if schedule["day"] == current_day:
                return schedule["time"]

        # Если время для дня не найдено, возвращаем 22:00
        return "22:00"

    def calculate_total_game_time_today(self):
        """Рассчитывает суммарное время игр за сегодня"""
        today = datetime.now().strftime("%Y-%m-%d")
        total_minutes = 0

        for session in self.sessions.get("sessions", []):
            if session.get("date") == today:
                total_minutes += session.get("duration_minutes", 0)

        return total_minutes

    def calculate_rest_time(self):
        """Рассчитывает время отдыха с последней сессии"""
        if not self.sessions.get("sessions"):
            return float('inf')  # Если сессий не было, отдых бесконечен

        last_session_end = None
        for session in reversed(self.sessions.get("sessions", [])):
            if "end_time" in session:
                try:
                    last_session_end = datetime.strptime(
                        f"{session['date']} {session['end_time']}",
                        "%Y-%m-%d %H:%M"
                    )
                    break
                except:
                    continue

        if not last_session_end:
            return float('inf')

        rest_time = datetime.now() - last_session_end
        return rest_time.total_seconds() / 60  # Возвращаем в минутах

    def add_session(self, start_time, end_time=None):
        """Добавляет сессию в историю"""
        session_date = start_time.strftime("%Y-%m-%d")

        if end_time:
            duration = (end_time - start_time).total_seconds() / 60
            end_str = end_time.strftime("%H:%M")
        else:
            duration = 0
            end_str = None

        session = {
            "date": session_date,
            "start_time": start_time.strftime("%H:%M"),
            "end_time": end_str,
            "duration_minutes": duration
        }

        self.sessions.setdefault("sessions", []).append(session)
        self.save_sessions()

    def check_limits_at_startup(self):
        """Проверяет лимиты при запуске программы"""
        if not self.settings["limit_mode"]:
            self.show_management_interface()
            return

        current_time = datetime.now()
        shutdown_time_str = self.get_shutdown_time_for_today()

        # Преобразуем время выключения в объект datetime
        try:
            shutdown_time = datetime.strptime(
                f"{current_time.strftime('%Y-%m-%d')} {shutdown_time_str}",
                "%Y-%m-%d %H:%M"
            )
        except:
            shutdown_time = datetime.strptime(
                f"{current_time.strftime('%Y-%m-%d')} 22:00",
                "%Y-%m-%d %H:%M"
            )

        # Проверяем условия
        conditions_failed = []

        # 1. Проверка времени выключения
        if current_time >= shutdown_time:
            conditions_failed.append(f"Превышено время выключения ({shutdown_time_str})")

        # 2. Проверка времени игр
        game_time_today = self.calculate_total_game_time_today()
        if game_time_today >= self.settings["game_time_minutes"]:
            conditions_failed.append(
                f"Исчерпан лимит игрового времени ({game_time_today}/{self.settings['game_time_minutes']} мин)")

        # 3. Проверка времени отдыха
        rest_time = self.calculate_rest_time()
        if rest_time < self.settings["rest_time_minutes"]:
            conditions_failed.append(
                f"Недостаточно времени отдыха ({rest_time:.1f}/{self.settings['rest_time_minutes']} мин)")

        # Если есть нарушения, показываем предупреждение
        if conditions_failed:
            self.show_warning_window(conditions_failed)
        else:
            # Запускаем новую сессию
            self.current_session_start = datetime.now()
            self.sessions["current_session_start"] = self.current_session_start.isoformat()
            self.save_sessions()

            # Показываем интерфейс управления
            self.show_management_interface()

    def show_warning_window(self, reasons):
        """Показывает окно предупреждения с обратным отсчетом"""
        self.warning_window = tk.Tk()
        self.warning_window.title("⚠️ Превышены лимиты")
        self.warning_window.geometry("500x400")
        self.warning_window.configure(bg='#2c3e50')
        self.warning_window.resizable(False, False)

        # Делаем окно поверх всех
        self.warning_window.attributes('-topmost', True)

        # Заголовок
        title_frame = tk.Frame(self.warning_window, bg='#e74c3c', height=80)
        title_frame.pack(fill='x', side='top')
        title_frame.pack_propagate(False)

        tk.Label(title_frame, text="⚠️ ВНИМАНИЕ!",
                 font=("Arial", 24, "bold"),
                 fg="white", bg='#e74c3c').pack(expand=True)

        # Основное содержание
        content_frame = tk.Frame(self.warning_window, bg='#2c3e50', padx=20, pady=20)
        content_frame.pack(fill='both', expand=True)

        # Причины
        tk.Label(content_frame, text="Обнаружены нарушения лимитов:",
                 font=("Arial", 14, "bold"),
                 fg="white", bg='#2c3e50').pack(anchor='w', pady=(0, 10))

        reasons_frame = tk.Frame(content_frame, bg='#34495e', bd=2, relief='solid')
        reasons_frame.pack(fill='x', pady=(0, 20))

        for reason in reasons:
            tk.Label(reasons_frame, text=f"• {reason}",
                     font=("Arial", 11),
                     fg="#ecf0f1", bg='#34495e',
                     anchor='w', justify='left').pack(fill='x', padx=10, pady=5)

        # Обратный отсчет
        self.countdown_label = tk.Label(content_frame,
                                        text="",
                                        font=("Arial", 16, "bold"),
                                        fg="#e74c3c", bg='#2c3e50')
        self.countdown_label.pack(pady=(0, 20))

        # Поле для пароля
        password_frame = tk.Frame(content_frame, bg='#2c3e50')
        password_frame.pack(fill='x', pady=(0, 20))

        tk.Label(password_frame, text="Пароль для отключения ограничения:",
                 font=("Arial", 11),
                 fg="white", bg='#2c3e50').pack(anchor='w')

        self.password_entry = tk.Entry(password_frame,
                                       font=("Arial", 12),
                                       show="*",
                                       width=30)
        self.password_entry.pack(fill='x', pady=(5, 0))

        # Кнопки
        button_frame = tk.Frame(content_frame, bg='#2c3e50')
        button_frame.pack(fill='x')

        tk.Button(button_frame, text="Отключить ограничение",
                  font=("Arial", 11, "bold"),
                  bg="#2ecc71", fg="white",
                  command=self.disable_limit_mode,
                  padx=20, pady=10).pack(side='left', padx=(0, 10))

        tk.Button(button_frame, text="Выключить сейчас",
                  font=("Arial", 11, "bold"),
                  bg="#e74c3c", fg="white",
                  command=self.shutdown_now,
                  padx=20, pady=10).pack(side='left')

        # Запускаем обратный отсчет
        self.countdown_seconds = self.settings["shutdown_request_minutes"] * 60
        self.update_countdown()

        self.warning_window.mainloop()

    def update_countdown(self):
        """Обновляет обратный отсчет"""
        if self.countdown_seconds > 0:
            minutes = self.countdown_seconds // 60
            seconds = self.countdown_seconds % 60
            self.countdown_label.config(
                text=f"Компьютер выключится через: {minutes:02d}:{seconds:02d}"
            )
            self.countdown_seconds -= 1
            self.warning_window.after(1000, self.update_countdown)
        else:
            self.shutdown_now()

    def disable_limit_mode(self):
        """Отключает режим ограничения после проверки пароля"""
        entered_password = self.password_entry.get()

        if entered_password == self.settings["management_password"]:
            self.settings["limit_mode"] = False
            self.save_settings()
            messagebox.showinfo("Успех", "Режим ограничений отключен!")

            if self.warning_window:
                self.warning_window.destroy()

            self.show_management_interface()
        else:
            messagebox.showerror("Ошибка", "Неверный пароль!")

    def shutdown_now(self):
        """Немедленное выключение компьютера"""
        if self.warning_window:
            self.warning_window.destroy()

        os.system('shutdown /s /f /t 30')

        # Сохраняем текущую сессию, если она есть
        if self.current_session_start:
            self.add_session(self.current_session_start, datetime.now())

        sys.exit(0)

    def show_management_interface(self):




        """Показывает интерфейс управления"""
        interface = tk.Tk()
        interface.title("Контроль времени ПК")
        interface.geometry("800x600")

        # Стиль
        style = ttk.Style()
        style.theme_use('clam')

        # Настройка цветов
        bg_color = '#f0f0f0'
        interface.configure(bg=bg_color)

        # Заголовок
        header_frame = tk.Frame(interface, bg='#3498db', height=100)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="🕒 Контроль времени ПК",
                 font=("Arial", 28, "bold"),
                 fg="white", bg='#3498db').pack(expand=True)

        # Статус режима
        status_frame = tk.Frame(interface, bg=bg_color, padx=20, pady=20)
        status_frame.pack(fill='x')

        mode_text = "Отключен" if not self.settings["limit_mode"] else "Включен"
        mode_color = "#2ecc71" if not self.settings["limit_mode"] else "#e74c3c"

        tk.Label(status_frame, text=f"Режим ограничений: ",
                 font=("Arial", 14),
                 bg=bg_color).pack(side='left')

        tk.Label(status_frame, text=mode_text,
                 font=("Arial", 14, "bold"),
                 fg=mode_color, bg=bg_color).pack(side='left')

        # Информационные карточки
        cards_frame = tk.Frame(interface, bg=bg_color, padx=20, pady=10)
        cards_frame.pack(fill='x')

        # Сегодняшняя статистика
        stats_frame = tk.LabelFrame(cards_frame, text="📊 Статистика за сегодня",
                                    font=("Arial", 12, "bold"),
                                    bg=bg_color, padx=20, pady=20)
        stats_frame.pack(fill='x', pady=(0, 10))

        today_game_time = self.calculate_total_game_time_today()
        today_rest_time = self.calculate_rest_time()

        stats_grid = tk.Frame(stats_frame, bg=bg_color)
        stats_grid.pack(fill='x')

        # Лимит игрового времени
        limit_frame = tk.Frame(stats_grid, bg=bg_color)
        limit_frame.grid(row=0, column=0, padx=20, pady=10, sticky='w')

        tk.Label(limit_frame, text="Игровое время:",
                 font=("Arial", 11), bg=bg_color).pack(anchor='w')

        progress = min(today_game_time / self.settings["game_time_minutes"] * 100, 100)
        progress_color = "#2ecc71" if progress < 80 else "#f39c12" if progress < 100 else "#e74c3c"

        # Прогресс бар
        progress_frame = tk.Frame(limit_frame, bg='#ddd', height=20, width=200)
        progress_frame.pack(fill='x', pady=5)
        progress_frame.pack_propagate(False)

        tk.Frame(progress_frame, bg=progress_color, width=progress * 2).pack(side='left', fill='y')

        tk.Label(limit_frame,
                 text=f"{today_game_time:.0f} / {self.settings['game_time_minutes']} мин ({progress:.0f}%)",
                 font=("Arial", 10, "bold"), bg=bg_color).pack(anchor='w')

        # Время отдыха
        rest_frame = tk.Frame(stats_grid, bg=bg_color)
        rest_frame.grid(row=0, column=1, padx=20, pady=10, sticky='w')

        tk.Label(rest_frame, text="Время отдыха:",
                 font=("Arial", 11), bg=bg_color).pack(anchor='w')

        if today_rest_time == float('inf'):
            rest_text = "∞"
            rest_color = "#2ecc71"
        else:
            rest_text = f"{today_rest_time:.0f} мин"
            if today_rest_time >= self.settings["rest_time_minutes"]:
                rest_color = "#2ecc71"
            else:
                rest_color = "#e74c3c"

        tk.Label(rest_frame, text=rest_text,
                 font=("Arial", 14, "bold"),
                 fg=rest_color, bg=bg_color).pack(pady=5)

        tk.Label(rest_frame,
                 text=f"(минимум: {self.settings['rest_time_minutes']} мин)",
                 font=("Arial", 9), fg="#7f8c8d", bg=bg_color).pack()

        # Текущее время выключения
        shutdown_frame = tk.Frame(stats_grid, bg=bg_color)
        shutdown_frame.grid(row=0, column=2, padx=20, pady=10, sticky='w')

        tk.Label(shutdown_frame, text="Выключение сегодня:",
                 font=("Arial", 11), bg=bg_color).pack(anchor='w')

        shutdown_time = self.get_shutdown_time_for_today()
        tk.Label(shutdown_frame, text=shutdown_time,
                 font=("Arial", 14, "bold"),
                 fg="#3498db", bg=bg_color).pack(pady=5)

        # Кнопки управления
        control_frame = tk.LabelFrame(cards_frame, text="⚙️ Управление",
                                      font=("Arial", 12, "bold"),
                                      bg=bg_color, padx=20, pady=20)
        control_frame.pack(fill='x', pady=(10, 0))

        button_grid = tk.Frame(control_frame, bg=bg_color)
        button_grid.pack()

        # Кнопка изменения настроек
        tk.Button(button_grid, text="⚙️ Настройки",
                  font=("Arial", 11, "bold"),
                  bg="#3498db", fg="white",
                  command=self.show_settings_window,
                  width=15, height=2).grid(row=0, column=0, padx=10, pady=5)

        # Кнопка выключения
        tk.Button(button_grid, text="🔌 Выключить сейчас",
                  font=("Arial", 11, "bold"),
                  bg="#e74c3c", fg="white",
                  command=self.shutdown_now,
                  width=15, height=2).grid(row=0, column=1, padx=10, pady=5)

        # Кнопка перезапуска проверки
        tk.Button(button_grid, text="🔄 Проверить лимиты",
                  font=("Arial", 11, "bold"),
                  bg="#f39c12", fg="white",
                  command=self.restart_check,
                  width=15, height=2).grid(row=0, column=2, padx=10, pady=5)

        # Кнопка выхода
        tk.Button(button_grid, text="🚪 Выход",
                  font=("Arial", 11, "bold"),
                  bg="#7f8c8d", fg="white",
                  command=lambda: self.close_program(interface),
                  width=15, height=2).grid(row=0, column=3, padx=10, pady=5)

        # История сессий
        history_frame = tk.LabelFrame(interface, text="📅 История сессий",
                                      font=("Arial", 12, "bold"),
                                      bg=bg_color, padx=20, pady=20)
        history_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Таблица истории
        columns = ("Дата", "Начало", "Конец", "Длительность", "Статус")
        tree = ttk.Treeview(history_frame, columns=columns, show="headings", height=8)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)

        tree.column("Дата", width=100)
        tree.column("Начало", width=80)
        tree.column("Конец", width=80)
        tree.column("Длительность", width=100)
        tree.column("Статус", width=80)

        # Заполняем таблицу
        for session in reversed(self.sessions.get("sessions", [])[-10:]):  # Последние 10 сессий
            status = "✓ Завершена" if session.get("end_time") else "▶ Активна"
            duration = f"{session.get('duration_minutes', 0):.0f} мин"

            tree.insert("", "end", values=(
                session["date"],
                session["start_time"],
                session.get("end_time", "-"),
                duration,
                status
            ))

        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        interface.protocol("WM_DELETE_WINDOW", lambda: interface.withdraw())

        interface.mainloop()

    def show_settings_window(self):
        """Окно настроек"""
        settings_window = tk.Toplevel()
        settings_window.title("Настройки")
        settings_window.geometry("600x700")
        settings_window.resizable(False, False)

        # Заголовок
        tk.Label(settings_window, text="⚙️ Настройки контроля времени",
                 font=("Arial", 20, "bold")).pack(pady=20)

        # Фрейм с настройками
        main_frame = tk.Frame(settings_window, padx=30, pady=20)
        main_frame.pack(fill='both', expand=True)

        # Режим ограничения
        tk.Label(main_frame, text="Режим ограничения:",
                 font=("Arial", 12, "bold")).grid(row=0, column=0, sticky='w', pady=10)

        limit_var = tk.BooleanVar(value=self.settings["limit_mode"])
        limit_check = tk.Checkbutton(main_frame, variable=limit_var)
        limit_check.grid(row=0, column=1, sticky='w', pady=10)

        # Пароль
        tk.Label(main_frame, text="Пароль управления:",
                 font=("Arial", 12, "bold")).grid(row=1, column=0, sticky='w', pady=10)

        password_var = tk.StringVar(value=self.settings["management_password"])
        password_entry = tk.Entry(main_frame, textvariable=password_var, width=20)
        password_entry.grid(row=1, column=1, sticky='w', pady=10)

        # Лимит игрового времени
        tk.Label(main_frame, text="Лимит игр (минут):",
                 font=("Arial", 12, "bold")).grid(row=2, column=0, sticky='w', pady=10)

        game_time_var = tk.IntVar(value=self.settings["game_time_minutes"])
        game_time_spin = tk.Spinbox(main_frame, from_=30, to=480, increment=30,
                                    textvariable=game_time_var, width=10)
        game_time_spin.grid(row=2, column=1, sticky='w', pady=10)

        # Лимит отдыха
        tk.Label(main_frame, text="Лимит отдыха (минут):",
                 font=("Arial", 12, "bold")).grid(row=3, column=0, sticky='w', pady=10)

        rest_time_var = tk.IntVar(value=self.settings["rest_time_minutes"])
        rest_time_spin = tk.Spinbox(main_frame, from_=15, to=240, increment=15,
                                    textvariable=rest_time_var, width=10)
        rest_time_spin.grid(row=3, column=1, sticky='w', pady=10)

        # Время на подтверждение
        tk.Label(main_frame, text="Время подтверждения (минут):",
                 font=("Arial", 12, "bold")).grid(row=4, column=0, sticky='w', pady=10)

        confirm_time_var = tk.IntVar(value=self.settings["shutdown_request_minutes"])
        confirm_time_spin = tk.Spinbox(main_frame, from_=1, to=10, increment=1,
                                       textvariable=confirm_time_var, width=10)
        confirm_time_spin.grid(row=4, column=1, sticky='w', pady=10)

        # Расписание выключения
        tk.Label(main_frame, text="Расписание выключения:",
                 font=("Arial", 12, "bold")).grid(row=5, column=0, sticky='nw', pady=10)

        schedule_frame = tk.Frame(main_frame)
        schedule_frame.grid(row=5, column=1, sticky='w', pady=10)

        schedule_vars = {}
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        eng_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        # Находим текущее расписание
        current_schedule = {}
        for item in self.settings["shutdown_schedule"]:
            current_schedule[item["day"]] = item["time"]

        for i, (ru_day, eng_day) in enumerate(zip(days, eng_days)):
            tk.Label(schedule_frame, text=ru_day,
                     font=("Arial", 10)).grid(row=i, column=0, sticky='w', padx=(0, 10))

            time_var = tk.StringVar(value=current_schedule.get(eng_day, "22:00"))
            time_entry = tk.Entry(schedule_frame, textvariable=time_var, width=8)
            time_entry.grid(row=i, column=1, sticky='w', pady=2)

            schedule_vars[eng_day] = time_var

        # Кнопки сохранения
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=30)

        def save_settings():
            self.settings["limit_mode"] = limit_var.get()
            self.settings["management_password"] = password_var.get()
            self.settings["game_time_minutes"] = game_time_var.get()
            self.settings["rest_time_minutes"] = rest_time_var.get()
            self.settings["shutdown_request_minutes"] = confirm_time_var.get()

            # Сохраняем расписание
            self.settings["shutdown_schedule"] = []
            for eng_day, time_var in schedule_vars.items():
                self.settings["shutdown_schedule"].append({
                    "day": eng_day,
                    "time": time_var.get()
                })

            self.save_settings()
            messagebox.showinfo("Сохранено", "Настройки успешно сохранены!")
            settings_window.destroy()

        tk.Button(button_frame, text="💾 Сохранить",
                  font=("Arial", 12, "bold"),
                  bg="#2ecc71", fg="white",
                  command=save_settings,
                  padx=30, pady=10).pack(side='left', padx=10)

        tk.Button(button_frame, text="❌ Отмена",
                  font=("Arial", 12, "bold"),
                  bg="#e74c3c", fg="white",
                  command=settings_window.destroy,
                  padx=30, pady=10).pack(side='left', padx=10)

    def restart_check(self):
        """Перезапускает проверку лимитов"""
        self.check_limits_at_startup()

    def close_program(self, window):
        if self.current_session_start:
            self.sessions["current_session_start"] = None
            self.add_session(self.current_session_start, datetime.now())

        window.destroy()
        sys.exit(0)

    def exit_app(self):
        if self.tray_icon:
            self.tray_icon.stop()
        sys.exit(0)


    def create_tray_icon(self):
        image = Image.new('RGB', (64, 64), color='#3498db')
        d = ImageDraw.Draw(image)
        d.text((18, 18), "PC", fill="white")

        menu = (
            item('Открыть', self.open_interface),
            item('Проверить лимиты', self.restart_check),
            item('Выход', self.exit_app)
        )

        self.tray_icon = pystray.Icon("PCController", image, "Контроль ПК", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def background_checker(self):
        while True:
            time.sleep(60)
            if self.settings["limit_mode"]:
                self.check_limits_at_startup()

    def close_previous_session_if_needed(self):
        """Корректно закрывает предыдущую сессию, если она была активна"""
        stored_start = self.sessions.get("current_session_start")

        if not stored_start:
            return  # активной сессии не было

        try:
            start_time = datetime.fromisoformat(stored_start)
        except ValueError:
            self.sessions["current_session_start"] = None
            self.save_sessions()
            return

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60

        session = {
            "date": start_time.strftime("%Y-%m-%d"),
            "start_time": start_time.strftime("%H:%M"),
            "end_time": end_time.strftime("%H:%M"),
            "duration_minutes": duration
        }

        self.sessions.setdefault("sessions", []).append(session)
        self.sessions["current_session_start"] = None
        self.save_sessions()

    def open_interface(self):
        threading.Thread(target=self.show_management_interface).start()

def main():
    root = tk.Tk()
    root.withdraw()  # скрываем главное окно
    app = PCController()
    root.mainloop()


if __name__ == "__main__":
    main()