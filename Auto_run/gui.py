import util
import tkinter as tk
from tkinter import messagebox, ttk
from db_config import DefaultConfig
import os
import logging

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='auto_run.log'
)

class AutoExecutionerApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Auto-Executioner')
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 設定視窗大小及位置
        window_width = 600
        window_height = 450
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        left = int((screen_width - window_width) / 2)
        top = int((screen_height - window_height) / 2)
        root.geometry(f'{window_width}x{window_height}+{left}+{top}')
        root.resizable(False, False)
        
        # 建立變數
        self.count = tk.StringVar(value="5")
        self.min = tk.StringVar(value="0")
        self.sec = tk.StringVar(value="30")
        self.status_var = tk.StringVar(value="就緒")
        
        # 建立分頁
        self.tab_control = ttk.Notebook(root)
        
        # 建立兩個分頁: 週期執行和持續執行
        self.tab1 = ttk.Frame(self.tab_control)
        self.tab2 = ttk.Frame(self.tab_control)
        
        self.tab_control.add(self.tab1, text='定時執行')
        self.tab_control.add(self.tab2, text='持續執行')
        self.tab_control.pack(expand=1, fill="both")
        
        # 設置第一個分頁 - 定時執行
        self.setup_tab1()
        
        # 設置第二個分頁 - 持續執行
        self.setup_tab2()
        
        # 狀態列
        status_frame = tk.Frame(root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        tk.Label(status_frame, text="狀態: ").pack(side=tk.LEFT)
        tk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # 關於按鈕
        about_button = tk.Button(status_frame, text="關於", command=self.show_about)
        about_button.pack(side=tk.RIGHT, padx=10)
    
    def setup_tab1(self):
        """設置定時執行分頁"""
        frame = ttk.LabelFrame(self.tab1, text="定時執行設定")
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # 執行次數
        tk.Label(frame, text='執行次數:', font=('Arial', 16)).grid(column=0, row=0, padx=10, pady=20, sticky=tk.W)
        tk.Entry(frame, width=5, textvariable=self.count, font=('Arial', 16)).grid(column=1, row=0, padx=5)
        
        # 執行時間
        tk.Label(frame, text='每次間隔:', font=('Arial', 16)).grid(column=0, row=1, padx=10, pady=10, sticky=tk.W)
        
        # 分鐘
        min_frame = tk.Frame(frame)
        min_frame.grid(column=1, row=1, columnspan=2, sticky=tk.W)
        
        tk.Entry(min_frame, width=5, textvariable=self.min, font=('Arial', 16)).pack(side=tk.LEFT)
        tk.Label(min_frame, text='分', font=('Arial', 16)).pack(side=tk.LEFT, padx=5)
        
        # 秒數
        tk.Entry(min_frame, width=5, textvariable=self.sec, font=('Arial', 16)).pack(side=tk.LEFT, padx=10)
        tk.Label(min_frame, text='秒', font=('Arial', 16)).pack(side=tk.LEFT, padx=5)
        
        # 執行檔選擇
        tk.Label(frame, text='執行檔:', font=('Arial', 16)).grid(column=0, row=2, padx=10, pady=20, sticky=tk.W)
        
        self.file_var = tk.StringVar(value=os.path.join(DefaultConfig.FILE_PATH, DefaultConfig.FILE_NAME))
        file_entry = tk.Entry(frame, textvariable=self.file_var, width=30, font=('Arial', 12))
        file_entry.grid(column=1, row=2, columnspan=3, padx=5, sticky=tk.W)
        
        browse_button = tk.Button(frame, text="瀏覽", command=self.browse_file)
        browse_button.grid(column=4, row=2, padx=5)
        
        # 日誌顯示區域
        log_frame = ttk.LabelFrame(self.tab1, text="執行日誌")
        log_frame.pack(padx=10, pady=5, fill="both", expand=True)
        
        self.log_text = tk.Text(log_frame, height=5, width=50)
        self.log_text.pack(padx=5, pady=5, fill="both", expand=True)
        
        # 按鈕
        button_frame = tk.Frame(self.tab1)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text='執行', font=('Arial', 16), command=self.execute).pack(side=tk.LEFT, padx=20)
        tk.Button(button_frame, text='清除', font=('Arial', 16), command=self.clear).pack(side=tk.LEFT, padx=20)
        tk.Button(button_frame, text='保存當前設定', font=('Arial', 16), command=self.save_settings).pack(side=tk.LEFT, padx=20)
    
    def setup_tab2(self):
        """設置持續執行分頁"""
        frame = ttk.LabelFrame(self.tab2, text="持續執行設定")
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # 檢查連接設定
        tk.Label(frame, text='檢查連接間隔:', font=('Arial', 16)).grid(column=0, row=0, padx=10, pady=10, sticky=tk.W)
        
        check_frame = tk.Frame(frame)
        check_frame.grid(column=1, row=0, columnspan=2, sticky=tk.W)
        
        self.check_min = tk.StringVar(value="60")
        self.check_sec = tk.StringVar(value="0")
        
        tk.Entry(check_frame, width=5, textvariable=self.check_min, font=('Arial', 16)).pack(side=tk.LEFT)
        tk.Label(check_frame, text='分', font=('Arial', 16)).pack(side=tk.LEFT, padx=5)
        
        tk.Entry(check_frame, width=5, textvariable=self.check_sec, font=('Arial', 16)).pack(side=tk.LEFT, padx=10)
        tk.Label(check_frame, text='秒', font=('Arial', 16)).pack(side=tk.LEFT, padx=5)
        
        # 數據獲取設定
        tk.Label(frame, text='數據獲取間隔:', font=('Arial', 16)).grid(column=0, row=1, padx=10, pady=10, sticky=tk.W)
        
        extract_frame = tk.Frame(frame)
        extract_frame.grid(column=1, row=1, columnspan=2, sticky=tk.W)
        
        self.extract_min = tk.StringVar(value="0")
        self.extract_sec = tk.StringVar(value="5")
        
        tk.Entry(extract_frame, width=5, textvariable=self.extract_min, font=('Arial', 16)).pack(side=tk.LEFT)
        tk.Label(extract_frame, text='分', font=('Arial', 16)).pack(side=tk.LEFT, padx=5)
        
        tk.Entry(extract_frame, width=5, textvariable=self.extract_sec, font=('Arial', 16)).pack(side=tk.LEFT, padx=10)
        tk.Label(extract_frame, text='秒', font=('Arial', 16)).pack(side=tk.LEFT, padx=5)
        
        # 檢查連接檔案
        tk.Label(frame, text='檢查連接檔:', font=('Arial', 16)).grid(column=0, row=2, padx=10, pady=10, sticky=tk.W)
        
        self.check_file_var = tk.StringVar(value=os.path.join(DefaultConfig.FILE_PATH, DefaultConfig.FILE_CHECK_CONNECT))
        check_entry = tk.Entry(frame, textvariable=self.check_file_var, width=30, font=('Arial', 12))
        check_entry.grid(column=1, row=2, columnspan=3, padx=5, sticky=tk.W)
        
        check_browse_button = tk.Button(frame, text="瀏覽", command=lambda: self.browse_file('check'))
        check_browse_button.grid(column=4, row=2, padx=5)
        
        # 數據獲取檔案
        tk.Label(frame, text='數據獲取檔:', font=('Arial', 16)).grid(column=0, row=3, padx=10, pady=10, sticky=tk.W)
        
        self.extract_file_var = tk.StringVar(value=os.path.join(DefaultConfig.FILE_PATH, DefaultConfig.FILE_EXTRACT))
        extract_entry = tk.Entry(frame, textvariable=self.extract_file_var, width=30, font=('Arial', 12))
        extract_entry.grid(column=1, row=3, columnspan=3, padx=5, sticky=tk.W)
        
        extract_browse_button = tk.Button(frame, text="瀏覽", command=lambda: self.browse_file('extract'))
        extract_browse_button.grid(column=4, row=3, padx=5)
        
        # 日誌顯示區域
        log_frame = ttk.LabelFrame(self.tab2, text="執行日誌")
        log_frame.pack(padx=10, pady=5, fill="both", expand=True)
        
        self.log_text2 = tk.Text(log_frame, height=5, width=50)
        self.log_text2.pack(padx=5, pady=5, fill="both", expand=True)
        
        # 按鈕
        button_frame = tk.Frame(self.tab2)
        button_frame.pack(pady=10)
        
        self.continuous_running = False
        self.continuous_button = tk.Button(button_frame, text='開始連續執行', font=('Arial', 16), command=self.toggle_continuous)
        self.continuous_button.pack(side=tk.LEFT, padx=20)
        
        tk.Button(button_frame, text='清除', font=('Arial', 16), command=self.clear_tab2).pack(side=tk.LEFT, padx=20)
        tk.Button(button_frame, text='保存當前設定', font=('Arial', 16), command=self.save_settings).pack(side=tk.LEFT, padx=20)
    
    def browse_file(self, file_type='normal'):
        """瀏覽文件"""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            initialdir=DefaultConfig.FILE_PATH,
            title="選擇檔案",
            filetypes=(("Python 檔案", "*.py"), ("所有檔案", "*.*"))
        )
        if filename:
            if file_type == 'check':
                self.check_file_var.set(filename)
            elif file_type == 'extract':
                self.extract_file_var.set(filename)
            else:
                self.file_var.set(filename)
    
    def execute(self):
        """執行定時執行功能"""
        try:
            count_val = int(self.count.get())
            min_val = int(self.min.get())
            sec_val = float(self.sec.get())
            file_path = self.file_var.get()
            
            if not os.path.isfile(file_path):
                messagebox.showerror("錯誤", "找不到指定檔案")
                return
            
            self.status_var.set("執行中...")
            self.log("開始執行: " + file_path)
            self.log(f"設定: {count_val}次, 每次間隔{min_val}分{sec_val}秒")
            
            # 使用 try/except 捕獲可能的錯誤
            try:
                util.periodical_execution(file_path, min_val, sec_val, count_val, log_callback=self.log)
                self.status_var.set("執行完成")
            except Exception as e:
                self.log(f"執行錯誤: {str(e)}")
                self.status_var.set("執行錯誤")
                messagebox.showerror("執行錯誤", str(e))
        except ValueError:
            messagebox.showerror("輸入錯誤", "請確保所有輸入都是有效的數字")
    
    def toggle_continuous(self):
        """切換連續執行狀態"""
        if not self.continuous_running:
            try:
                check_min_val = int(self.check_min.get())
                check_sec_val = float(self.check_sec.get())
                extract_min_val = int(self.extract_min.get())
                extract_sec_val = float(self.extract_sec.get())
                
                check_file = self.check_file_var.get()
                extract_file = self.extract_file_var.get()
                
                if not os.path.isfile(check_file):
                    messagebox.showerror("錯誤", "找不到檢查連接檔案")
                    return
                
                if not os.path.isfile(extract_file):
                    messagebox.showerror("錯誤", "找不到數據獲取檔案")
                    return
                
                self.continuous_running = True
                self.continuous_button.config(text="停止連續執行")
                self.status_var.set("連續執行中...")
                
                self.log2("開始連續執行")
                self.log2(f"檢查連接檔案: {check_file}, 間隔: {check_min_val}分{check_sec_val}秒")
                self.log2(f"數據獲取檔案: {extract_file}, 間隔: {extract_min_val}分{extract_sec_val}秒")
                
                # 使用多線程執行連續任務
                import threading
                self.continuous_thread = threading.Thread(
                    target=self.run_continuous,
                    args=(check_file, extract_file, check_min_val, check_sec_val, extract_min_val, extract_sec_val),
                    daemon=True
                )
                self.continuous_thread.start()
            except ValueError:
                messagebox.showerror("輸入錯誤", "請確保所有輸入都是有效的數字")
        else:
            self.continuous_running = False
            self.continuous_button.config(text="開始連續執行")
            self.status_var.set("已停止")
            self.log2("已停止連續執行")
    
    def run_continuous(self, check_file, extract_file, check_min, check_sec, extract_min, extract_sec):
        """在新線程中運行連續執行功能"""
        try:
            util.continuous_execution(
                check_file, extract_file, 
                check_min, check_sec, 
                extract_min, extract_sec, 
                log_callback=self.log2,
                stop_check=lambda: not self.continuous_running
            )
        except Exception as e:
            self.log2(f"執行錯誤: {str(e)}")
            self.status_var.set("執行錯誤")
            self.continuous_running = False
            self.root.after(0, lambda: self.continuous_button.config(text="開始連續執行"))
    
    def clear(self):
        """清除定時執行分頁的輸入"""
        self.count.set("5")
        self.min.set("0")
        self.sec.set("30")
        self.log_text.delete(1.0, tk.END)
    
    def clear_tab2(self):
        """清除連續執行分頁的輸入"""
        self.check_min.set("60")
        self.check_sec.set("0")
        self.extract_min.set("0")
        self.extract_sec.set("5")
        self.log_text2.delete(1.0, tk.END)
    
    def save_settings(self):
        """保存當前設定"""
        try:
            config = {
                "count": self.count.get(),
                "min": self.min.get(),
                "sec": self.sec.get(),
                "file": self.file_var.get(),
                "check_min": self.check_min.get(),
                "check_sec": self.check_sec.get(),
                "extract_min": self.extract_min.get(),
                "extract_sec": self.extract_sec.get(),
                "check_file": self.check_file_var.get(),
                "extract_file": self.extract_file_var.get()
            }
            
            import json
            with open("auto_run_settings.json", "w") as f:
                json.dump(config, f, indent=4)
            
            messagebox.showinfo("保存成功", "已將當前設定保存")
        except Exception as e:
            messagebox.showerror("保存失敗", f"設定保存失敗: {str(e)}")
    
    def load_settings(self):
        """載入設定"""
        try:
            import json
            if os.path.exists("auto_run_settings.json"):
                with open("auto_run_settings.json", "r") as f:
                    config = json.load(f)
                
                self.count.set(config.get("count", "5"))
                self.min.set(config.get("min", "0"))
                self.sec.set(config.get("sec", "30"))
                self.file_var.set(config.get("file", ""))
                self.check_min.set(config.get("check_min", "60"))
                self.check_sec.set(config.get("check_sec", "0"))
                self.extract_min.set(config.get("extract_min", "0"))
                self.extract_sec.set(config.get("extract_sec", "5"))
                self.check_file_var.set(config.get("check_file", ""))
                self.extract_file_var.set(config.get("extract_file", ""))
        except Exception as e:
            logging.error(f"載入設定失敗: {str(e)}")
    
    def log(self, message):
        """記錄日誌到第一個分頁的日誌區域"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        logging.info(message)
    
    def log2(self, message):
        """記錄日誌到第二個分頁的日誌區域"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text2.insert(tk.END, log_message)
        self.log_text2.see(tk.END)
        logging.info(message)
    
    def show_about(self):
        """顯示關於對話框"""
        messagebox.showinfo("關於", "Auto-Executioner 1.0\n\n一個自動執行腳本的工具")
    
    def on_closing(self):
        """視窗關閉時的處理"""
        if self.continuous_running:
            if messagebox.askyesno("確認", "連續執行還在進行中，確定要離開嗎？"):
                self.continuous_running = False
                self.root.destroy()
        else:
            self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    app = AutoExecutionerApp(window)
    app.load_settings()
    window.mainloop()