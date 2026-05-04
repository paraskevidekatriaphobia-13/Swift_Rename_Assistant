import os
import json
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime
from pathlib import Path
import sys

# 設定ファイルの保存先
CONFIG_FILE = "swift_rename_assistant_config.json"

class SwiftRenameAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("Swift Rename Assistant")
        
        # --- ウィンドウサイズの設定 ---
        window_width = 900  # 少し横幅を広げました
        window_height = 700 # 小さすぎず、はみ出さない絶妙なライン
        
        # 画面の幅と高さを取得
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 真ん中に表示するための座標を計算
        center_x = int((screen_width - window_width) / 2)
        center_y = int((screen_height - window_height) / 5)

        # サイズと位置を同時に設定 ("幅x高さ+X座標+Y座標")
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        
        # 最小サイズも設定（これ以上小さくならないように）
        self.root.minsize(750, 550)
        
        # --- アイコン設定（.exe内部のリソースを参照する設定） ---
        try:
            # 実行ファイル自身（.exe）に埋め込まれたアイコンを参照
            self.root.iconbitmap(default=sys.executable)
        except:
            # 開発中（.pyで実行中）やエラー時のためのバックアップ
            try:
                self.root.iconbitmap("rounded-image.ico")
            except:
                pass

        # --- ここに追記！見た目のルール（スタイル）を決める ---
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)

        # --- 変数管理 ---
        self.folder_path = tk.StringVar()
        self.rename_mode = tk.StringVar(value="add")
        self.sort_mode = tk.StringVar(value="名前順")
        self.custom_name = tk.StringVar()
        
        # 詳細設定用
        self.dup_avoid_mode = tk.StringVar(value="auto")
        self.dup_custom_str = tk.StringVar(value="(copy)")
        self.confirm_mode = tk.StringVar(value="confirm")
        self.seq_pos = tk.StringVar(value="後に付加")
        self.digits = tk.IntVar(value=0)
        self.start_num = tk.IntVar(value=1) # 開始番号
        self.exclude_exts = tk.StringVar(value="ini, db, tmp") # 除外拡張子
        self.remove_text = tk.StringVar()
        self.replace_from = tk.StringVar()
        self.replace_to = tk.StringVar()
        self.save_config_var = tk.BooleanVar(value=True)

        # 内部データ
        self.preview_data = []
        self.undo_list = []

        # 実行ファイル名の特定（自分自身をリネーム対象から除外するため）
        self.my_name = os.path.basename(sys.executable if getattr(sys, 'frozen', False) else __file__)

        self.load_config()
        self.setup_ui()
        self.update_ui_states()

    def setup_ui(self):
        # メインコンテナ（全体の余白を調整）
        container = tk.Frame(self.root, padx=10, pady=5)
        container.pack(fill="both", expand=True)

        # --- 1. フォルダ選択 ---
        f_select_frame = tk.LabelFrame(container, text="フォルダ選択", padx=5, pady=2)
        f_select_frame.pack(fill="x", pady=2)
        tk.Entry(f_select_frame, textvariable=self.folder_path, state="readonly").pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(f_select_frame, text="参照...", command=self.select_folder).pack(side="right")

        # --- 2. 基本設定 ---
        basic_frame = tk.LabelFrame(container, text="基本設定", padx=5, pady=5)
        basic_frame.pack(fill="x", pady=2)

        row1 = tk.Frame(basic_frame)
        row1.pack(fill="x")
        tk.Label(row1, text="並び順:").pack(side="left")
        ttk.Combobox(row1, textvariable=self.sort_mode, values=["名前順", "更新日時順"], state="readonly", width=12).pack(side="left", padx=5)
        
        tk.Label(row1, text=" モード:").pack(side="left")
        tk.Radiobutton(row1, text="連番追加", variable=self.rename_mode, value="add", command=self.update_ui_states).pack(side="left")
        tk.Radiobutton(row1, text="名称変更+連番", variable=self.rename_mode, value="replace", command=self.update_ui_states).pack(side="left")

        self.name_entry_frame = tk.Frame(basic_frame, pady=2)
        self.name_entry_frame.pack(fill="x")
        tk.Label(self.name_entry_frame, text="変更後の名称:").pack(side="left")
        self.ent_custom_name = tk.Entry(self.name_entry_frame, textvariable=self.custom_name)
        self.ent_custom_name.pack(side="left", fill="x", expand=True, padx=5)

        # --- 3. アコーディオン詳細設定 ---
        self.adv_btn = tk.Button(container, text="▼ 詳細設定を開く", relief="flat", fg="blue", command=self.toggle_advanced)
        self.adv_btn.pack(pady=2)

        self.adv_frame = tk.Frame(container, padx=10, pady=5, relief="groove", bd=1)

        # 詳細設定内の配置 (Grid)
        tk.Label(self.adv_frame, text="重複回避:").grid(row=0, column=0, sticky="w")
        tk.Checkbutton(self.adv_frame, text="自動(1)", variable=self.dup_avoid_mode, onvalue="auto", offvalue="custom", command=self.update_ui_states).grid(row=0, column=1, sticky="w")
        tk.Checkbutton(self.adv_frame, text="指定文字:", variable=self.dup_avoid_mode, onvalue="custom", offvalue="auto", command=self.update_ui_states).grid(row=0, column=2, sticky="w")
        self.ent_dup_custom = tk.Entry(self.adv_frame, textvariable=self.dup_custom_str, width=10)
        self.ent_dup_custom.grid(row=0, column=3, sticky="w")

        tk.Label(self.adv_frame, text="確認設定:").grid(row=1, column=0, sticky="w", pady=5)
        tk.Radiobutton(self.adv_frame, text="実行前に確認", variable=self.confirm_mode, value="confirm").grid(row=1, column=1, sticky="w")
        tk.Radiobutton(self.adv_frame, text="概要を表示", variable=self.confirm_mode, value="summary").grid(row=1, column=2, sticky="w")
        tk.Radiobutton(self.adv_frame, text="確認なし", variable=self.confirm_mode, value="none").grid(row=1, column=3, sticky="w")

        tk.Label(self.adv_frame, text="連番位置:").grid(row=2, column=0, sticky="w")
        ttk.Combobox(self.adv_frame, textvariable=self.seq_pos, values=["前に付加", "後に付加"], state="readonly", width=10).grid(row=2, column=1, sticky="w")
        tk.Label(self.adv_frame, text=" 桁数(0=なし):").grid(row=2, column=2, sticky="w")
        tk.Spinbox(self.adv_frame, from_=0, to=10, textvariable=self.digits, width=5).grid(row=2, column=3, sticky="w")
        tk.Label(self.adv_frame, text=" 開始番号:").grid(row=2, column=4, sticky="w")
        tk.Spinbox(self.adv_frame, from_=0, to=9999, textvariable=self.start_num, width=7).grid(row=2, column=5, sticky="w")

        tk.Label(self.adv_frame, text="除外拡張子:").grid(row=3, column=0, sticky="w", pady=5)
        tk.Entry(self.adv_frame, textvariable=self.exclude_exts, width=15).grid(row=3, column=1, sticky="w")
        tk.Label(self.adv_frame, text=" 文字削除:").grid(row=3, column=2, sticky="w")
        tk.Entry(self.adv_frame, textvariable=self.remove_text, width=10).grid(row=3, column=3, sticky="w")
        
        tk.Label(self.adv_frame, text=" 置換:").grid(row=3, column=4, sticky="w")
        replace_f = tk.Frame(self.adv_frame)
        replace_f.grid(row=3, column=5, sticky="w")
        tk.Entry(replace_f, textvariable=self.replace_from, width=5).pack(side="left")
        tk.Label(replace_f, text="→").pack(side="left")
        tk.Entry(replace_f, textvariable=self.replace_to, width=5).pack(side="left")

        tk.Checkbutton(self.adv_frame, text="この設定を保存する", variable=self.save_config_var).grid(row=4, column=0, columnspan=2, sticky="w", pady=5)

        # --- 4. プレビューエリア（スクロール対応） ---
        tk.Button(container, text="プレビュー更新", command=self.preview, bg="#f0f0f0").pack(fill="x", pady=2)
        
        tree_frame = tk.Frame(container)
        tree_frame.pack(fill="both", expand=True) 

        self.tree = ttk.Treeview(tree_frame, columns=("old", "arrow", "new"), show="headings", height=5)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.heading("old", text="現在のファイル名")
        self.tree.heading("arrow", text="")
        self.tree.heading("new", text="変更後のファイル名")
        self.tree.column("old", width=250)
        self.tree.column("arrow", width=30, anchor="center")
        self.tree.column("new", width=250)

        # --- 5. 実行エリア ---
        action_frame = tk.Frame(container, pady=5)
        action_frame.pack(fill="x", side="bottom")

        self.btn_undo = tk.Button(action_frame, text="<< 元に戻す", command=self.undo, state="disabled", width=12)
        self.btn_undo.pack(side="left", padx=5)

        self.btn_run = tk.Button(action_frame, text="一括リネーム実行", command=self.execute, bg="#4CAF50", fg="white", font=("", 10, "bold"))
        self.btn_run.pack(side="right", fill="x", expand=True, padx=5)

    # --- ロジック部 ---

    def toggle_advanced(self):
        if self.adv_frame.winfo_viewable():
            self.adv_frame.pack_forget()
            self.adv_btn.config(text="▼ 詳細設定を開く")
        else:
            self.adv_frame.pack(after=self.adv_btn, fill="x", pady=5)
            self.adv_btn.config(text="▲ 詳細設定を閉じる")

    def update_ui_states(self):
        if self.rename_mode.get() == "replace":
            self.ent_custom_name.config(state="normal", bg="white")
        else:
            self.ent_custom_name.config(state="disabled", bg="#f0f0f0")

        if self.dup_avoid_mode.get() == "custom":
            self.ent_dup_custom.config(state="normal")
        else:
            self.ent_dup_custom.config(state="disabled")

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.folder_path.set(path)
            self.preview()

    def generate_new_name(self, filename, index, used_names):
        p = Path(filename)
        name = p.stem
        ext = p.suffix

        # 1. 置換と削除
        rem = self.remove_text.get()
        if rem: name = name.replace(rem, "")
        
        rep_f = self.replace_from.get()
        rep_t = self.replace_to.get()
        if rep_f: name = name.replace(rep_f, rep_t)

        # 2. 連番生成（開始番号を反映）
        d = self.digits.get()
        current_num = index + self.start_num.get() - 1
        num_str = str(current_num).zfill(d) if d > 0 else str(current_num)

        # 3. メインリネーム
        if self.rename_mode.get() == "add":
            if self.seq_pos.get() == "前に付加":
                name = f"{num_str}_{name}"
            else:
                name = f"{name}_{num_str}"
        else:
            base = self.custom_name.get() or datetime.now().strftime("%Y%m%d")
            if self.seq_pos.get() == "前に付加":
                name = f"{num_str}_{base}"
            else:
                name = f"{base}_{num_str}"

        full_new = name + ext
        
        # 4. 重複回避
        count = 1
        temp_name = name
        while full_new in used_names or os.path.exists(os.path.join(self.folder_path.get(), full_new)):
            suffix = f"({count})" if self.dup_avoid_mode.get() == "auto" else f"{self.dup_custom_str.get()}{count}"
            full_new = f"{temp_name}{suffix}{ext}"
            count += 1
        
        return full_new

    def preview(self):
        folder = self.folder_path.get()
        if not folder: return
        
        for item in self.tree.get_children(): self.tree.delete(item)
        self.preview_data.clear()

        # 除外設定をリスト化
        exclude_list = [e.strip().lower() for e in self.exclude_exts.get().split(",") if e.strip()]

        try:
            raw_files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
            
            # ブラックリストによるフィルタリング
            files = []
            for f in raw_files:
                if f == self.my_name: continue # 自分自身
                if f.lower() in ["desktop.ini", "thumbs.db"]: continue # システムファイル
                if any(f.lower().endswith(f".{ext}") for ext in exclude_list): continue # 指定拡張子
                files.append(f)

            if self.sort_mode.get() == "名前順":
                files.sort()
            else:
                files.sort(key=lambda x: os.path.getmtime(os.path.join(folder, x)))

            used_names = set()
            for i, f in enumerate(files, 1):
                new_name = self.generate_new_name(f, i, used_names)
                self.tree.insert("", "end", values=(f, "→", new_name))
                self.preview_data.append((f, new_name))
                used_names.add(new_name)
        except Exception as e:
            messagebox.showerror("エラー", f"リスト取得失敗: {e}")

    def execute(self):
        if not self.preview_data:
            messagebox.showwarning("注意", "リネーム対象がありません")
            return

        mode_text = self.confirm_mode.get()
        if mode_text != "none":
            if mode_text == "summary":
                msg = f"以下の設定で {len(self.preview_data)} 件を変更します。\n\n" \
                      f"・開始番号: {self.start_num.get()}\n" \
                      f"・並び順: {self.sort_mode.get()}\n" \
                      f"・モード: {'名称変更' if self.rename_mode.get()=='replace' else '連番追加'}\n" \
                      f"・重複回避: {'自動(1)' if self.dup_avoid_mode.get()=='auto' else 'カスタム'}\n\n" \
                      f"実行しますか？"
            else:
                msg = f"{len(self.preview_data)} 件をリネームします。よろしいですか？"
            
            if not messagebox.askyesno("実行確認", msg): return

        folder = self.folder_path.get()
        new_undo_list = []
        success = 0

        for old, new in self.preview_data:
            if old == new: continue
            old_p = os.path.join(folder, old)
            new_p = os.path.join(folder, new)
            try:
                os.rename(old_p, new_p)
                new_undo_list.append((old_p, new_p))
                success += 1
            except Exception as e:
                print(f"Error renaming {old}: {e}")

        self.undo_list = new_undo_list
        if self.undo_list:
            self.btn_undo.config(state="normal", bg="#ffeb3b")

        if self.save_config_var.get(): self.save_config()
        
        messagebox.showinfo("完了", f"{success} 件のリネームが完了しました。")
        self.preview()

    def undo(self):
        if not self.undo_list: return
        if not messagebox.askyesno("Undo", "前回の操作を元に戻しますか？"): return

        success = 0
        for old_p, new_p in reversed(self.undo_list):
            try:
                os.rename(new_p, old_p)
                success += 1
            except: pass
        
        self.undo_list = []
        self.btn_undo.config(state="disabled", bg="#f0f0f0")
        messagebox.showinfo("Undo完了", f"{success} 件を元に戻しました。")
        self.preview()

    def save_config(self):
        config = {
            "sort_mode": self.sort_mode.get(),
            "rename_mode": self.rename_mode.get(),
            "digits": self.digits.get(),
            "start_num": self.start_num.get(),
            "exclude_exts": self.exclude_exts.get(),
            "confirm_mode": self.confirm_mode.get(),
            "seq_pos": self.seq_pos.get(),
            "dup_avoid": self.dup_avoid_mode.get(),
            "save_config": self.save_config_var.get()
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except: pass

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    c = json.load(f)
                    self.sort_mode.set(c.get("sort_mode", "名前順"))
                    self.rename_mode.set(c.get("rename_mode", "add"))
                    self.digits.set(c.get("digits", 0))
                    self.start_num.set(c.get("start_num", 1))
                    self.exclude_exts.set(c.get("exclude_exts", "ini, db, tmp"))
                    self.confirm_mode.set(c.get("confirm_mode", "confirm"))
                    self.seq_pos.set(c.get("seq_pos", "後に付加"))
                    self.dup_avoid_mode.set(c.get("dup_avoid", "auto"))
                    self.save_config_var.set(c.get("save_config", True))
            except: pass

if __name__ == "__main__":
    # --- ここに追加！ ---
    import ctypes
    try:
        # Windowsに「このアプリは高解像度（DPI）に対応してるよ！」と伝えます
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass # Windows以外（Macなど）で動かした時のためのエラー回避
    # ------------------
    root = tk.Tk()
    app = SwiftRenameAssistant(root)
    root.mainloop()