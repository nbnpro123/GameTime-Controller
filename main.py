from datetime import datetime, timedelta, time as dt_time
import tkinter as tk
from tkinter import messagebox
import os, platform, json, asyncio

#===========================Переменные=============================#
JSON_PATH = r"C:\PC_control\time.json"              #"time.json"
Json = r"C:\PC_control\settings.json"               #"settings.json"
#==================================================================#


#---------------------------Всплывающие окна-----------------------#
async def shutdown_pc():
    import tkinter as tk
    from tkinter import messagebox
    import os, platform, json
    import time as tm
    from datetime import datetime, timedelta, time as dt_time

    with open(Json, "r", encoding="utf-8") as f:
        CANCEL_PASSWORD = json.load(f)['password']
    print(CANCEL_PASSWORD)
    TOTAL_SECONDS = 180

    root = tk.Tk()
    root.title("Внимание! Выключение ПК")
    root.geometry("1200x700")           # ✨ Увеличено окно для крупного шрифта
    root.configure(bg='red')

    # ---------------------------------------------------------
    # 1️⃣ Переопределяем действие при нажатии на «X»
    # ---------------------------------------------------------
    def on_close():
        root.iconify()
    root.protocol("WM_DELETE_WINDOW", on_close)

    # ---------------------------------------------------------
    # 2️⃣ Крупный шрифт — устанавливаем базовый для всех виджетов
    # ---------------------------------------------------------
    root.option_add('*Font', 'Arial 24')   # все надписи, кнопки, поля будут 24 размера

    # Заголовок — чуть больше и жирнее
    tk.Label(root,
             text="Через некоторое время ваш компьютер будет выключен.",
             bg='red', fg='white',
             font=("Arial", 28, "bold")    # ещё крупнее
            ).pack(pady=30)

    # Таймер — очень крупный
    timer_lbl = tk.Label(root, text="03:00",
                         font=("Helvetica", 64, "bold"), fg="white", bg='red')
    timer_lbl.pack(pady=20)

    # Рамка для поля пароля
    frm = tk.Frame(root, bg='red')
    frm.pack(pady=20)
    tk.Label(frm, text="Пароль:", bg='red', fg='white',
             font=("Arial", 26)).pack(side="left", padx=20)
    pwd_entry = tk.Entry(frm, show="*", width=12,
                         font=("Arial", 26),      # крупный шрифт в поле
                         bg='white', fg='black')
    pwd_entry.pack(side="left", padx=20)

    # ---------------------------------------------------------
    # 3️⃣ Кнопка отмены — большая и заметная
    # ---------------------------------------------------------
    def cancel():
        if pwd_entry.get() == str(CANCEL_PASSWORD):
            root.after_cancel(timer_id[0])
            messagebox.showinfo("Отмена", "Выключение отменено.")
            root.destroy()
        else:
            messagebox.showerror("Ошибка", "Неверный пароль.")

    tk.Button(root, text="Отменить выключение", command=cancel,
              bg='red', fg='white', activebackground='darkred', activeforeground='white',
              font=("Arial", 26, "bold"),
              width=20, height=2          # ширина и высота кнопки
             ).pack(pady=30)

    # ---------------------------------------------------------
    # 4️⃣ Таймер обратного отсчёта (без изменений в логике)
    # ---------------------------------------------------------
    remaining = [TOTAL_SECONDS]
    timer_id = [None]

    def tick():
        sec = remaining[0]
        mins, secs = divmod(sec, 60)
        timer_lbl.config(text=f"{mins:02d}:{secs:02d}")

        if sec == 0:
            sys_name = platform.system()
            if sys_name == "Windows":
                os.system("shutdown /s /t 0")
            elif sys_name == "Linux":
                os.system("shutdown -h now")
            elif sys_name == "Darwin":
                os.system("osascript -e 'tell application \"System Events\" to shut down'")
            else:
                messagebox.showerror("Ошибка", f"Неизвестная ОС: {sys_name}")
            root.destroy()
            return

        remaining[0] -= 1
        timer_id[0] = root.after(1000, tick)

    tick()
    root.mainloop()



def warning_window(parent=None, auto_close_sec=5):
    import tkinter as tk
    import json
    from datetime import datetime, timedelta

    # Чтение времени из JSON
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        past_time_str = json.load(f)['time_off']

    past_time = datetime.fromisoformat(past_time_str)
    now = datetime.now()
    delta = now - past_time
    total_sec = int(delta.total_seconds())
    total_min = total_sec // 60
    shutdown_time = now + timedelta(seconds=total_sec)

    # Создание окна
    if parent:
        win = tk.Toplevel(parent)
    else:
        win = tk.Tk()
        win.title("Осталось времени")

    # ----- УВЕЛИЧЕНИЕ РАЗМЕРОВ И ШРИФТОВ -----
    win.configure(bg='#d4f1d4')
    win.geometry("800x350")                     # значительно больше
    win.resizable(False, False)

    # Базовый крупный шрифт для всех дочерних виджетов
    win.option_add('*Font', 'Arial 24')

    # Центрирование
    win.update_idletasks()
    width = win.winfo_width()
    height = win.winfo_height()
    x = (win.winfo_screenwidth() // 2) - (width // 2)
    y = (win.winfo_screenheight() // 2) - (height // 2)
    win.geometry(f'{width}x{height}+{x}+{y}')

    # Таймер авто-закрытия
    timer_id = None

    def close_window():
        if win.winfo_exists():
            win.destroy()

    def start_auto_close():
        nonlocal timer_id
        timer_id = win.after(auto_close_sec * 1000, close_window)

    def cancel_auto_close():
        nonlocal timer_id
        if timer_id:
            win.after_cancel(timer_id)
            timer_id = None

    def on_closing():
        win.iconify()
    win.protocol("WM_DELETE_WINDOW", on_closing)

    # --- Метка с временем (очень крупная) ---
    label = tk.Label(
        win,
        text=f"Вам осталось играть: {total_min} минут",
        font=("Arial", 32, "bold"),          # большой жирный шрифт
        bg='#d4f1d4',
        fg='black'
    )
    label.pack(pady=60)                      # увеличен отступ

    # --- Кнопка ОК (крупная) ---
    def ok_click():
        cancel_auto_close()
        win.destroy()

    btn_ok = tk.Button(
        win,
        text="ОК",
        command=ok_click,
        width=12,
        height=2,
        font=("Arial", 28, "bold"),
        bg='#e6ffe6',
        activebackground='#c0e0c0'
    )
    btn_ok.pack(pady=30)

    # Запуск таймера авто-закрытия
    start_auto_close()

    # Запуск главного цикла, если это самостоятельное окно
    if not parent:
        win.mainloop()
#------------------------------------------------------------------#


#+++++++++++++++++++++++++Логика ограничений+++++++++++++++++++++++#
async def write_only_time():
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
        await asyncio.sleep(5)



async def cheak_week_date():
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
        return False
       # await shutdown_pc()



async def _test():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        past_time_str = json.load(f)['time_off']

    past_time = datetime.fromisoformat(past_time_str)
    now = datetime.now()
    delta = now - past_time  # правильно

    total_sec = int(delta.total_seconds())
    total_min = total_sec // 60                             # 60sec = 1 min                                      # 3600sec = 1 hour
    if total_min >= 60:
        task = asyncio.create_task(write_only_time())
        await asyncio.sleep(3600)
        await shutdown_pc()
    else:
        shutdown_time = now + timedelta(seconds=total_sec)
        print(f"🕒 Компьютер выключится в {shutdown_time.strftime('%H:%M:%S')}")
        print(f"можно играться: {total_min} минут или {total_sec} секунд")

        task = asyncio.create_task(write_only_time())
        await asyncio.sleep(total_sec)
        await shutdown_pc()
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#


def sync_function():
    loop = asyncio.get_running_loop()
    loop.create_task(write_only_time())


if __name__ == "__main__":
    warning_window()
    if asyncio.run(cheak_week_date()) is False:
        asyncio.run(shutdown_pc())
        asyncio.run(write_only_time())
    else:
        asyncio.run(_test())
        asyncio.run(write_only_time())
