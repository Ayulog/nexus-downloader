"""Chinese desktop frontend for nexus-downloader. Copyright (c) Ayulog."""
import json
import os
import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from gui_settings import BASE_DIR, atomic_write, load_settings, parse_links, save_settings, worker_command


class App:
    def __init__(self, root, base_dir=BASE_DIR):
        self.root = root
        self.base = Path(base_dir)
        self.config_path = self.base / 'config.toml'
        self.process = None
        self.events = queue.Queue()
        self.closing = False
        self.result = None
        self.mode = None
        self.editable = []
        self.status = tk.StringVar(value='就绪 · 添加链接后开始下载')
        self.auth_status = tk.StringVar(value='尚未验证授权')
        self.summary = tk.StringVar(value='成功 0    跳过 0    失败 0')
        self.amount = tk.StringVar(value='等待下载')
        values = load_settings(self.config_path)
        self.cookie = tk.StringVar(value=values['cookie'])
        self.folder = tk.StringVar(value=values['download_dir'])
        self.parallel = tk.StringVar(value=str(values['parallel']))
        self.extract = tk.BooleanVar(value=values['extract'])
        self.mod_path = self.base / values['mod_list']
        self.build()
        if self.mod_path.exists():
            self.links.insert('1.0', self.mod_path.read_text(encoding='utf-8-sig'))
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.after_id = root.after(100, self.poll)

    def build(self):
        root = self.root
        root.title('Nexus Downloader · 中文桌面版')
        root.geometry('1100x800')
        root.minsize(600, 420)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        root.configure(bg='#f3f5f7')
        root.option_add('*Font', ('Microsoft YaHei UI', 10))
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('Microsoft YaHei UI', 10))
        style.configure('TFrame', background='#f3f5f7')
        style.configure('TLabel', background='#f3f5f7', foreground='#243449')
        style.configure('TLabelframe', background='#f3f5f7')
        style.configure('TLabelframe.Label', background='#f3f5f7', foreground='#243449', font=('Microsoft YaHei UI', 10, 'bold'))
        style.configure('TButton', padding=(12, 7))
        style.configure('Accent.TButton', background='#087e8b', foreground='white')
        style.map('Accent.TButton', background=[('active', '#056674'), ('disabled', '#a5b7bc')])
        style.configure('TCheckbutton', background='#f3f5f7')
        style.configure('Treeview', rowheight=31, background='white', fieldbackground='white')
        style.configure('Treeview.Heading', font=('Microsoft YaHei UI', 9, 'bold'))
        style.configure('Horizontal.TProgressbar', background='#087e8b', troughcolor='#e0e6eb')

        header = tk.Frame(root, bg='#142b40', padx=24, pady=18)
        header.grid(row=0, column=0, sticky='ew')
        self.heading = tk.Label(header, text='NEXUS  /  DOWNLOADER', fg='white', bg='#142b40', font=('Segoe UI', 22, 'bold'), justify='left')
        self.heading.pack(anchor='w')
        tk.Label(header, text='批量下载 MOD，让每一步进度清晰可见。', fg='#b7d1de', bg='#142b40').pack(anchor='w', pady=(4, 0))
        viewport = ttk.Frame(root)
        viewport.grid(row=1, column=0, sticky='nsew')
        viewport.columnconfigure(0, weight=1)
        viewport.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(viewport, bg='#f3f5f7', highlightthickness=0, width=1, height=1)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(viewport, orient='vertical', command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.body = body = ttk.Frame(self.canvas, padding=18)
        self.body_window = self.canvas.create_window(0, 0, window=body, anchor='nw')
        self.left = left = ttk.Frame(body)
        self.right = right = ttk.Frame(body)
        self.stacked = None
        self.canvas.bind('<Configure>', self.reflow)
        body.bind('<Configure>', lambda event: root.after_idle(self.fit_body))
        root.bind('<MouseWheel>', self.scroll_body, add='+')

        links_box = ttk.LabelFrame(left, text='01  MOD 链接', padding=12)
        links_box.pack(fill='both', expand=True)
        ttk.Label(links_box, text='每行一个链接 · 自动去重 · 支持多个游戏').pack(anchor='w')
        self.links = scrolledtext.ScrolledText(links_box, height=6, width=24, wrap='word', relief='flat', padx=8, pady=8, undo=True)
        self.links.pack(fill='both', expand=True, pady=8)
        self.editable.append(self.links)
        row = ttk.Frame(links_box)
        row.pack(fill='x')
        self.editable.append(ttk.Button(row, text='导入 TXT', command=self.import_links))
        self.editable[-1].pack(side='left')
        self.editable.append(ttk.Button(row, text='清空', command=lambda: self.links.delete('1.0', 'end')))
        self.editable[-1].pack(side='left', padx=6)

        options = ttk.LabelFrame(left, text='02  下载设置', padding=12)
        options.pack(fill='x', pady=(12, 0))
        ttk.Label(options, text='保存目录').pack(anchor='w')
        row = ttk.Frame(options)
        row.pack(fill='x', pady=(4, 8))
        entry = ttk.Entry(row, textvariable=self.folder)
        entry.pack(side='left', fill='x', expand=True)
        button = ttk.Button(row, text='浏览', command=self.browse)
        button.pack(side='left', padx=(6, 0))
        self.editable.extend([entry, button])
        row = ttk.Frame(options)
        row.pack(fill='x')
        ttk.Label(row, text='并行数量').pack(side='left')
        spin = ttk.Spinbox(row, from_=1, to=32, width=4, textvariable=self.parallel)
        spin.pack(side='left', padx=8)
        check = ttk.Checkbutton(row, text='下载后自动解压', variable=self.extract)
        check.pack(side='left')
        self.editable.extend([spin, check])

        account = ttk.LabelFrame(left, text='03  Nexus 账户', padding=12)
        account.pack(fill='x', pady=(12, 0))
        ttk.Label(account, text='nexusmods_session Cookie（仅保存在本机）').pack(anchor='w')
        cookie_entry = ttk.Entry(account, textvariable=self.cookie, show='●')
        cookie_entry.pack(fill='x', pady=(4, 6))
        self.editable.append(cookie_entry)
        ttk.Label(account, text='从浏览器开发者工具的 Cookies 中复制该值。\n浏览器授权不会自动填写此 Cookie。', foreground='#64748b').pack(anchor='w')
        row = ttk.Frame(account)
        row.pack(fill='x', pady=(8, 0))
        self.login_button = ttk.Button(row, text='浏览器登录 / 验证', command=lambda: self.start('login'))
        self.login_button.pack(side='left')
        self.editable.append(self.login_button)
        ttk.Label(row, textvariable=self.auth_status).pack(side='left', padx=8)

        ttk.Label(right, text='下载状态', font=('Microsoft YaHei UI', 15, 'bold')).pack(anchor='w')
        ttk.Label(right, textvariable=self.status, wraplength=470).pack(anchor='w', pady=(7, 12))
        self.progress = ttk.Progressbar(right, maximum=100)
        self.progress.pack(fill='x')
        ttk.Label(right, textvariable=self.amount).pack(anchor='w', pady=(7, 5))
        ttk.Label(right, textvariable=self.summary).pack(anchor='w', pady=(0, 14))
        table = ttk.Frame(right)
        table.pack(fill='both', expand=True)
        self.tasks = ttk.Treeview(table, columns=('name', 'progress', 'speed'), show='headings', height=5)
        for key, title, width in [('name', '当前文件 / 状态', 260), ('progress', '进度', 70), ('speed', '速度', 95)]:
            self.tasks.heading(key, text=title)
            self.tasks.column(key, width=width, minwidth=60, stretch=key == 'name')
        scroll = ttk.Scrollbar(table, orient='vertical', command=self.tasks.yview)
        self.tasks.configure(yscrollcommand=scroll.set)
        self.tasks.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        ttk.Label(right, text='运行日志', font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor='w', pady=(16, 6))
        self.logs = scrolledtext.ScrolledText(right, height=8, width=24, wrap='word', state='disabled', bg='#e9eef2', relief='flat', padx=8, pady=8, font=('Microsoft YaHei UI', 9))
        self.logs.pack(fill='both', expand=True)
        actions = ttk.Frame(root, padding=(18, 8, 18, 10))
        actions.grid(row=2, column=0, sticky='ew')
        for column in range(4):
            actions.columnconfigure(column, weight=1, uniform='actions')
        self.actions = actions
        open_button = ttk.Button(actions, text='打开下载目录', command=self.open_folder)
        open_button.grid(row=0, column=0, sticky='ew', padx=(0, 6))
        save = ttk.Button(actions, text='保存设置', command=self.save)
        save.grid(row=0, column=1, sticky='ew', padx=3)
        self.editable.append(save)
        self.stop_button = ttk.Button(actions, text='停止', state='disabled', command=self.stop)
        self.stop_button.grid(row=0, column=2, sticky='ew', padx=3)
        self.start_button = ttk.Button(actions, text='开始下载', style='Accent.TButton', command=lambda: self.start('download'))
        self.start_button.grid(row=0, column=3, sticky='ew', padx=(6, 0))
        self.action_buttons = (open_button, save, self.stop_button, self.start_button)
        self.credit = ttk.Label(actions, text='GUI by Ayulog · 基于 Samxel/nexus-downloader', foreground='#64748b')
        self.credit.grid(row=1, column=0, columnspan=4, sticky='w', pady=(5, 0))
        root.minsize(max(600, self.left.winfo_reqwidth() + 54), 420)

    def reflow(self, event=None):
        width = self.canvas.winfo_width()
        self.root.minsize(max(600, self.left.winfo_reqwidth() + 54), 420)
        self.heading.configure(wraplength=max(1, self.root.winfo_width() - 48))
        if hasattr(self, 'action_buttons'):
            self.credit.configure(wraplength=max(1, self.root.winfo_width() - 48))
            compact = self.root.winfo_width() < sum(button.winfo_reqwidth() for button in self.action_buttons) + 60
            columns = 2 if compact else 4
            for column in range(4):
                self.actions.columnconfigure(column, weight=1 if column < columns else 0, uniform='actions' if column < columns else '')
            for index, button in enumerate(self.action_buttons):
                button.grid_configure(row=index // columns, column=index % columns, padx=3, pady=2)
            self.credit.grid_configure(row=2 if compact else 1, columnspan=columns)
        breakpoint = max(860, self.left.winfo_reqwidth() + self.right.winfo_reqwidth() + 54)
        stacked = width < breakpoint
        if stacked != self.stacked:
            self.stacked = stacked
            self.left.grid(row=0, column=0, sticky='nsew', padx=(0, 0 if stacked else 18))
            self.right.grid(row=1 if stacked else 0, column=0 if stacked else 1,
                            sticky='nsew', pady=(18 if stacked else 0, 0))
            self.body.columnconfigure(0, weight=1)
            self.body.columnconfigure(1, weight=0 if stacked else 1)
            self.body.rowconfigure(0, weight=1)
            self.body.rowconfigure(1, weight=1 if stacked else 0)
            self.canvas.yview_moveto(0)
        self.canvas.itemconfigure(self.body_window, width=width)
        self.root.after_idle(self.fit_body)

    def fit_body(self, event=None):
        height = max(self.canvas.winfo_height(), self.body.winfo_reqheight())
        self.canvas.itemconfigure(self.body_window, height=height)
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), height))

    def scroll_body(self, event):
        # Text fields and the file table retain their own scrolling behavior.
        if isinstance(event.widget, (tk.Text, ttk.Treeview)):
            return
        if self.canvas.yview() != (0.0, 1.0) and event.delta:
            steps = -int(event.delta / 120) or (-1 if event.delta > 0 else 1)
            self.canvas.yview_scroll(steps, 'units')
            return 'break'

    def import_links(self):
        path = filedialog.askopenfilename(filetypes=[('文本文件', '*.txt'), ('所有文件', '*.*')])
        if path:
            try:
                text = Path(path).read_text(encoding='utf-8-sig')
                self.links.insert('end', '\n' + text)
            except (OSError, UnicodeError) as exc:
                messagebox.showerror('无法导入', str(exc), parent=self.root)

    def browse(self):
        path = filedialog.askdirectory()
        if path:
            self.folder.set(path)

    def persist(self):
        save_settings(self.config_path, cookie=self.cookie.get(), download_dir=self.folder.get(),
                      parallel=int(self.parallel.get()), extract=self.extract.get())

    def save(self):
        try:
            self.persist()
            self.status.set('设置已保存')
        except (OSError, ValueError, KeyError) as exc:
            messagebox.showerror('无法保存', str(exc), parent=self.root)

    def open_folder(self):
        try:
            if not self.folder.get().strip():
                raise ValueError('请先选择下载目录。')
            path = self.base / self.folder.get().strip()
            path.mkdir(parents=True, exist_ok=True)
            os.startfile(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror('无法打开目录', str(exc), parent=self.root)

    def set_busy(self, busy):
        for widget in self.editable:
            widget.configure(state='disabled' if busy else 'normal')
        self.start_button.configure(state='disabled' if busy else 'normal')
        self.stop_button.configure(state='normal' if busy else 'disabled')

    def start(self, mode):
        if self.process is not None:
            return
        try:
            if mode == 'download':
                links = parse_links(self.links.get('1.0', 'end'))
                if not self.cookie.get().strip():
                    raise ValueError('请先填写 nexusmods_session Cookie；浏览器授权不能替代此 Cookie。')
            self.persist()
            if mode == 'download':
                self.mod_path.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(self.mod_path, '\n'.join(links) + '\n')
            process = subprocess.Popen(worker_command(self.base, mode),
                                       cwd=self.base, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except (OSError, ValueError, KeyError) as exc:
            messagebox.showerror('无法开始', str(exc), parent=self.root)
            return
        self.process = process
        self.result = None
        self.mode = mode
        self.progress['value'] = 0
        self.tasks.delete(*self.tasks.get_children())
        self.summary.set('成功 0    跳过 0    失败 0')
        self.amount.set('等待下载')
        self.auth_status.set('正在验证…')
        self.status.set('正在启动后台…')
        self.logs.configure(state='normal')
        self.logs.delete('1.0', 'end')
        self.logs.configure(state='disabled')
        self.set_busy(True)
        threading.Thread(target=self.read_events, args=(process,), daemon=True).start()

    def read_events(self, process):
        try:
            for line in process.stdout:
                try:
                    self.events.put(json.loads(line))
                except json.JSONDecodeError:
                    self.events.put({'type': 'error', 'message': '后台输出格式异常。'})
            code = process.wait()
        finally:
            process.stdout.close()
        self.events.put({'type': 'exit', 'code': code})

    def log(self, text):
        cookie = self.cookie.get().strip()
        if cookie:
            text = text.replace(cookie, '[hidden]')
        self.logs.configure(state='normal')
        self.logs.insert('end', text + '\n')
        if int(self.logs.index('end-1c').split('.')[0]) > 500:
            self.logs.delete('1.0', '101.0')
        self.logs.see('end')
        self.logs.configure(state='disabled')

    @staticmethod
    def size(value):
        for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
            if value < 1024 or unit == 'TB':
                return f'{value:.1f} {unit}'
            value /= 1024

    def handle(self, event):
        kind = event.get('type')
        if kind in ('log', 'error'):
            self.log(event.get('message', ''))
        elif kind == 'state':
            state = event['state']
            if state == 'authenticated':
                self.auth_status.set('授权已验证')
            elif state == 'authenticating':
                self.status.set('正在验证授权；如浏览器打开，请在浏览器中完成登录。')
            elif state == 'running':
                self.status.set('正在扫描与下载…')
        elif kind == 'snapshot':
            stats = event['stats']
            self.summary.set(f"成功 {stats['downloaded']}    跳过 {stats['skipped']}    失败 {stats['failed']}")
            self.amount.set(f"已传输 {self.size(stats['bytes'])} · 扫描 {stats['scanned']}/{stats['total']} 个 MOD")
            total = max(stats['todo_bytes'], stats['bytes'])
            self.progress['value'] = min(100, stats['bytes'] / total * 100) if total else 0
            self.tasks.delete(*self.tasks.get_children())
            for task in event['tasks']:
                percent = f"{min(100, task['completed'] / task['total'] * 100):.0f}%" if task['total'] else '未知'
                name = task['name'] + (' · ' + task['status'] if task['status'] else '')
                self.tasks.insert('', 'end', values=(name, percent, self.size(task['speed']) + '/s'))
        elif kind == 'result':
            self.result = event['state']
        elif kind == 'exit':
            self.process.stdin.close()
            self.process = None
            self.set_busy(False)
            state = self.result if event['code'] == 0 else 'failed'
            if state == 'done':
                self.status.set('授权验证完成；下载仍需填写 Cookie。' if self.mode == 'login' else '下载完成')
                if self.mode == 'download':
                    self.progress['value'] = 100
            elif state == 'stopped':
                self.status.set('已停止 · 临时下载已清理')
            else:
                self.status.set('操作失败或部分文件失败，请查看日志。')
                if self.auth_status.get() != '授权已验证':
                    self.auth_status.set('授权未通过')
            self.tasks.delete(*self.tasks.get_children())
            if self.closing:
                self.root.destroy()

    def poll(self):
        for _ in range(100):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            self.handle(event)
            if self.closing and self.process is None:
                return
        self.after_id = self.root.after(100, self.poll)

    def stop(self):
        if self.process is not None:
            try:
                self.process.stdin.write('stop\n')
                self.process.stdin.flush()
            except (OSError, ValueError):
                pass
            self.stop_button.configure(state='disabled')
            self.status.set('正在停止…等待当前网络请求或解压结束，并清理临时文件。')

    def close(self):
        if self.process is not None:
            self.closing = True
            self.stop()
        else:
            self.root.after_cancel(self.after_id)
            self.root.destroy()


def main():
    root = tk.Tk()
    try:
        App(root)
    except Exception as exc:
        messagebox.showerror('启动失败', f'无法加载界面（{type(exc).__name__}）。\n请检查 config.toml，或运行 Setup-GUI.cmd。', parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == '__main__':
    main()
