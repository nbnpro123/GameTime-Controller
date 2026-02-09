import json
import time as tm  # Переименовываем модуль time
from datetime import datetime, timedelta, time as dt_time
import os
import sys


JSON_PATH = r"C:\PC_control\time.json" #"time.json"
txt_path = r"C:\PC_control\my_file.txt"
Json = r"C:\PC_control\settings.json" #"settings.json"





def post():
    now_start = datetime.now()

    while True:
        now = datetime.now()
        data = {
            "time_off": now.isoformat(),
            "time_start": now_start.isoformat(),
        }
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[{now.strftime('%H:%M:%S')}] Записано в {JSON_PATH}")
        tm.sleep(300)


def shutdown_pc():
    import tkinter as tk
    from tkinter import messagebox
    import os, platform, json
    import time as tm                     # модуль sleep
    from datetime import datetime, timedelta, time as dt_time

    TOTAL_SECONDS = 180          # 3минуты
    CANCEL_PASSWORD = "123"

    root = tk.Tk()
    root.title("Внимание! Выключение ПК")
    root.geometry("280x150")

    # ---------------------------------------------------------
    # 1️⃣ Переопределяем действие при нажатии на «X»
    # ---------------------------------------------------------
    def on_close():
        """Сворачиваем окно вместо его уничтожения."""
        # Вариант 1 – свернуть в панель задач
        root.iconify()
        # Если хотите полностью скрыть окно, замените на:
        # root.withdraw()
        # (и при желании вернуть его позже через root.deiconify())

    root.protocol("WM_DELETE_WINDOW", on_close)   # <-- самое важное

    # ---------------------------------------------------------
    # 2️⃣ Обычное GUI‑оформление
    # ---------------------------------------------------------
    tk.Label(root,
             text="Через некоторое время ваш компьютер будет выключен."
            ).pack(pady=5)

    timer_lbl = tk.Label(root, text="03:00",
                         font=("Helvetica", 20), fg="red")
    timer_lbl.pack(pady=5)

    frm = tk.Frame(root)
    frm.pack(pady=5)
    tk.Label(frm, text="Пароль:").pack(side="left")
    pwd_entry = tk.Entry(frm, show="*", width=8)
    pwd_entry.pack(side="left", padx=5)

    # ---------------------------------------------------------
    # 3️⃣ Обработчик кнопки «Отменить выключение»
    # ---------------------------------------------------------
    def cancel():
        """Проверка пароля, остановка таймера и запись в файл."""
        if pwd_entry.get() == CANCEL_PASSWORD:
            root.after_cancel(timer_id[0])
            messagebox.showinfo("Отмена", "Выключение отменено.")
            root.destroy()
            post()
        else:
            messagebox.showerror("Ошибка", "Неверный пароль.")

    tk.Button(root, text="Отменить выключение", command=cancel).pack(pady=5)

    # ---------------------------------------------------------
    # 4️⃣ Таймер обратного отсчёта
    # ---------------------------------------------------------
    remaining = [TOTAL_SECONDS]   # список, чтобы менять из вложенной функции
    timer_id = [None]

    def tick():
        sec = remaining[0]
        mins, secs = divmod(sec, 60)
        timer_lbl.config(text=f"{mins:02d}:{secs:02d}")

        if sec == 0:                     # время вышло → выключаем ПК
            sys_name = platform.system()
            if sys_name == "Windows":
                os.system("shutdown /s /t 0")
            elif sys_name == "Linux":
                os.system("shutdown -h now")
            elif sys_name == "Darwin":
                os.system(
                    "osascript -e 'tell application \"System Events\" to shut down'"
                )
            else:
                messagebox.showerror("Ошибка",
                                     f"Неизвестная ОС: {sys_name}")
            root.destroy()
            return

        remaining[0] -= 1
        timer_id[0] = root.after(1000, tick)

    # ---------------------------------------------------------
    # 5️⃣ Запуск таймера и главного цикла
    # ---------------------------------------------------------
    tick()
    root.mainloop()


def write_time():
    now_start = datetime.now()

    with open(Json, "r", encoding="utf-8") as f:
        game_time = json.load(f)['game_time']

    while True:
        now = datetime.now()
        data = {"time_off": now.isoformat(),
                "time_start" : now_start.isoformat(),}
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if now - now_start >= timedelta(hours=game_time): # проверка времени
            shutdown_pc()
        else:
            print(f"[{now.strftime('%H:%M:%S')}] Записано в {JSON_PATH}")
            tm.sleep(5)


def read_time():

        with open(JSON_PATH, "r", encoding="utf-8") as f:
            past_time_str = json.load(f)['time_off']
        past_time = datetime.fromisoformat(past_time_str)
        now = datetime.now()

        with open(Json, "r", encoding="utf-8") as f:
            game_chill = json.load(f)['game_chill']

        if now - past_time >= timedelta(hours=game_chill):
            write_time()                  # всё хорошо начинаем записывать время
        else:
            shutdown_pc()


def cheak_week_date():
    now = datetime.now()
    today_index = now.weekday()
    schedule = {
        0: dt_time(22, 0),
        1: dt_time(22, 0),
        2: dt_time(22, 0),
        3: dt_time(22, 0),
        4: dt_time(22, 0),
        5: dt_time(23, 0),
        6: dt_time(23, 0),
    }

    target_time = schedule.get(today_index)
    if target_time is None:
        return

    current_time = now.time()
    if (current_time.hour > target_time.hour or
        (current_time.hour == target_time.hour and current_time.minute >= target_time.minute)):
        shutdown_pc()

def main():
    cheak_week_date()
    read_time()


if __name__ == "__main__":
    main()
