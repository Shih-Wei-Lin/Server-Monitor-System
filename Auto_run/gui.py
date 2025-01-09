import util
import tkinter as tk 

from tkinter import *
from db_config import DefaultConfig

# 視窗設定
window = tk.Tk()
window.title('Auto-Executioner')

screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()

window_width = 600
window_height = 400
left = int((screen_width - window_width) / 2)
top = int((screen_height - window_height) / 2)

window.geometry(f'{window_width}x{window_height}+{left}+{top}')
window.resizable(False, False)
#window.mainloop()

# 生成填空視窗
# 變數設定
count = tk.StringVar()
min = tk.StringVar()
sec = tk.StringVar()

entry_width = 400
entry_height = 100
left = int((screen_width - window_width) / 2)
top = int((screen_height - window_height) / 2)


# 執行次數
label_count = tk.Label(window, 
                       text = '執行次數:',
                       font = ('Arial', 20, 'bold'),
                       )
label_count.grid(column=0, row=0, padx=10, pady=20)

entry_count = tk.Entry(window,
                       width=5,
                       textvariable = count,
                       font = ('Arial', 20))
entry_count.grid(column=1, row=0, padx=5)

# 執行時間
label_time = tk.Label(window,
                      text = '每次間隔:',
                      font = ('Arial', 20, 'bold'),
                      )
label_time.grid(column=0, row=1)

# 分鐘
entry_min = tk.Entry(window,
                     width=5,
                     textvariable = min,
                     font = ('Arial', 20)
                     )
entry_min.grid(column=1, row=1)

label_unit_min = tk.Label(window, 
                          text = 'Min',
                          font = ('Arial', 20),
                          )
label_unit_min.grid(column=2, row=1, padx=10)

# 秒數
entry_sec = tk.Entry(window,
                     width=5,
                     textvariable = sec,
                     font = ('Arial', 20)
                     )
entry_sec.grid(column=3, row=1)

label_unit_sec = tk.Label(window, 
                          text = 'Sec',
                          font = ('Arial', 20),
                          )
label_unit_sec.grid(column=4,row=1, padx=10)

# 輸出視窗
# dp = tk.Text(window, height=2)
# dp.place()

# 按鈕功能
def clear():
    count.set('')
    min.set('')
    sec.set('')
    
    entry_count.delete(0, 'end')
    entry_min.delete(0, 'end')  
    entry_sec.delete(0, 'end')
    pass    

def execute():
    file_path = DefaultConfig.FILE_PATH
    file_name = DefaultConfig.FILE_NAME

    file = file_path + file_name
    util.periodical_execution(file, int(min.get()), float(sec.get()), int(count.get()))

# 執行
btn_execute = tk.Button(window, 
                      text = '執行',
                      font = ('Arial', 20),
                      command = execute)
btn_execute.grid(column=1, row=3, pady=30)

# 清除
btn_clear = tk.Button(window, 
                      text = '清除',
                      font = ('Arial', 20),
                      command = clear)
btn_clear.grid(column=3, row=3)



# 生成視窗
window.mainloop()

#