# -*- coding: utf-8 -*-
"""
批量重命名 v1.0 — 剪辑素材批量重命名工具
=========================================
痛点：剪辑素材来自多个设备/来源，命名混乱（IMG_0001.MOV, DSC_0023.MP4...），
      手动逐个改名费时且易出错。

功能：
  - 选择文件夹，列出所有文件
  - 设置命名模板：前缀 + 序号（起始值/位数/步长可调） + 后缀
  - 实时预览新文件名
  - 执行批量重命名
  - 支持撤销（记录旧名→新名映射，可一键还原）

依赖：仅使用 Python 标准库。
"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime

# ============================================================================
# 配色与常量
# ============================================================================
COLOR_BG = "#1e1e2e"
COLOR_CARD = "#2a2a3c"
COLOR_ACCENT = "#ec4899"          # 粉色强调
COLOR_ACCENT_HOVER = "#db2777"
COLOR_TEXT = "#e0e0e0"
COLOR_TEXT_SECONDARY = "#a0a0b0"
COLOR_ENTRY_BG = "#3a3a4c"
COLOR_GREEN = "#4ade80"
COLOR_WARN = "#fbbf24"


# ============================================================================
# 主程序
# ============================================================================

class BatchRenamerApp:
    """批量重命名 v1.0"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("批量重命名 v1.0")
        self.root.geometry("580x460")
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BG)

        self.folder: str | None = None
        self.files: list[str] = []               # 原始文件名列表
        self.rename_map: dict[str, str] = {}      # {旧名: 新名}
        self.undo_history: list[dict] = []        # 撤销历史 [{旧绝对路径: 新绝对路径}, ...]

        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=COLOR_BG, foreground=COLOR_TEXT, font=("微软雅黑", 9))
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT)
        style.configure("Card.TLabelframe", background=COLOR_CARD, foreground=COLOR_ACCENT)
        style.configure("Card.TLabelframe.Label", background=COLOR_CARD, foreground=COLOR_ACCENT,
                        font=("微软雅黑", 10, "bold"))
        style.configure("Accent.TButton", background=COLOR_ACCENT, foreground="#ffffff",
                        borderwidth=0, font=("微软雅黑", 9, "bold"))
        style.map("Accent.TButton", background=[("active", COLOR_ACCENT_HOVER)])
        style.configure("Secondary.TButton", background="#444466", foreground=COLOR_TEXT, borderwidth=0)
        style.map("Secondary.TButton", background=[("active", "#555577")])

    def _build_ui(self):
        pad = {"padx": 8, "pady": 2}

        # ---- 文件夹选择 ----
        frm_folder = ttk.LabelFrame(self.root, text="选择文件夹", style="Card.TLabelframe")
        frm_folder.pack(fill=tk.X, **pad, pady=(8, 4))

        row = tk.Frame(frm_folder, bg=COLOR_CARD)
        row.pack(fill=tk.X, padx=6, pady=4)
        ttk.Button(row, text="选择文件夹", command=self._on_select_folder,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 6))
        self.lbl_folder = tk.Label(row, text="未选择", bg=COLOR_CARD, fg=COLOR_TEXT_SECONDARY,
                                    font=("微软雅黑", 8), anchor=tk.W)
        self.lbl_folder.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ---- 命名模板 ----
        frm_tpl = ttk.LabelFrame(self.root, text="命名模板", style="Card.TLabelframe")
        frm_tpl.pack(fill=tk.X, **pad)

        inner = tk.Frame(frm_tpl, bg=COLOR_CARD)
        inner.pack(fill=tk.X, padx=6, pady=4)

        # 前缀
        tk.Label(inner, text="前缀：", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.prefix_var = tk.StringVar(value="素材_")
        tk.Entry(inner, textvariable=self.prefix_var, width=12, bg=COLOR_ENTRY_BG,
                fg=COLOR_TEXT, insertbackground=COLOR_TEXT, relief=tk.FLAT,
                font=("Consolas", 9)).grid(row=0, column=1, sticky=tk.W, padx=(4, 12))

        # 序号起始
        tk.Label(inner, text="起始序号：", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=0, column=2, sticky=tk.W, pady=2)
        self.start_var = tk.IntVar(value=1)
        tk.Spinbox(inner, from_=0, to=9999, textvariable=self.start_var, width=5,
                   bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, buttonbackground=COLOR_CARD,
                   relief=tk.FLAT, font=("Consolas", 9)).grid(row=0, column=3, sticky=tk.W, padx=(4, 12))

        # 位数
        tk.Label(inner, text="位数：", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=0, column=4, sticky=tk.W, pady=2)
        self.digits_var = tk.IntVar(value=3)
        tk.Spinbox(inner, from_=1, to=8, textvariable=self.digits_var, width=4,
                   bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, buttonbackground=COLOR_CARD,
                   relief=tk.FLAT, font=("Consolas", 9)).grid(row=0, column=5, sticky=tk.W, padx=(4, 12))

        # 步长
        tk.Label(inner, text="步长：", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=0, column=6, sticky=tk.W, pady=2)
        self.step_var = tk.IntVar(value=1)
        tk.Spinbox(inner, from_=1, to=100, textvariable=self.step_var, width=4,
                   bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, buttonbackground=COLOR_CARD,
                   relief=tk.FLAT, font=("Consolas", 9)).grid(row=0, column=7, sticky=tk.W, padx=(4, 12))

        # 后缀
        tk.Label(inner, text="后缀：", bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.suffix_var = tk.StringVar()
        tk.Entry(inner, textvariable=self.suffix_var, width=12, bg=COLOR_ENTRY_BG,
                fg=COLOR_TEXT, insertbackground=COLOR_TEXT, relief=tk.FLAT,
                font=("Consolas", 9)).grid(row=1, column=1, sticky=tk.W, padx=(4, 12))

        # 模板预览
        tk.Label(inner, text="示例：", bg=COLOR_CARD, fg=COLOR_TEXT_SECONDARY,
                font=("微软雅黑", 8)).grid(row=1, column=2, sticky=tk.W, columnspan=2)
        self.lbl_sample = tk.Label(inner, text="素材_001.ext", bg=COLOR_CARD, fg=COLOR_ACCENT,
                                    font=("Consolas", 9))
        self.lbl_sample.grid(row=1, column=4, sticky=tk.W, columnspan=4, padx=(4, 0))

        # 绑定更新预览
        for var in (self.prefix_var, self.start_var, self.digits_var, self.step_var, self.suffix_var):
            if isinstance(var, tk.StringVar):
                var.trace_add("write", lambda *a: self._on_template_change())
            else:
                var.trace_add("write", lambda *a: self._on_template_change())

        # ---- 文件列表 & 预览 ----
        frm_list = ttk.LabelFrame(self.root, text="文件列表 & 重命名预览", style="Card.TLabelframe")
        frm_list.pack(fill=tk.BOTH, expand=True, **pad, pady=(4, 2))

        list_inner = tk.Frame(frm_list, bg=COLOR_CARD)
        list_inner.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        self.listbox = tk.Listbox(list_inner, height=8, bg=COLOR_ENTRY_BG, fg=COLOR_TEXT,
                                   font=("Consolas", 9), selectbackground=COLOR_ACCENT,
                                   selectforeground="#ffffff", relief=tk.FLAT)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = tk.Scrollbar(list_inner, orient=tk.VERTICAL, command=self.listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=sb.set)

        # ---- 按钮行 ----
        btn_frame = tk.Frame(self.root, bg=COLOR_BG)
        btn_frame.pack(fill=tk.X, **pad, pady=(2, 4))

        self.btn_rename = ttk.Button(btn_frame, text="执行重命名", command=self._on_rename,
                                      style="Accent.TButton", state="disabled")
        self.btn_rename.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_undo = ttk.Button(btn_frame, text="撤销重命名", command=self._on_undo,
                                    style="Secondary.TButton", state="disabled")
        self.btn_undo.pack(side=tk.LEFT, padx=(0, 6))

        self.lbl_status = tk.Label(btn_frame, text="", bg=COLOR_BG, fg=COLOR_TEXT_SECONDARY,
                                    font=("微软雅黑", 8))
        self.lbl_status.pack(side=tk.LEFT)

    # ------------------------------------------------------------------
    def _on_select_folder(self):
        """选择文件夹并列出文件"""
        folder = filedialog.askdirectory(title="选择包含素材的文件夹")
        if not folder:
            return

        self.folder = folder
        self.lbl_folder.config(text=folder, fg=COLOR_TEXT)

        # 列出所有文件（排除隐藏、系统、子目录）
        self.files = []
        try:
            for entry in sorted(os.listdir(folder)):
                full = os.path.join(folder, entry)
                if os.path.isfile(full) and not entry.startswith("."):
                    self.files.append(entry)
        except PermissionError:
            pass

        self._refresh_preview()
        self.btn_rename.configure(state="normal" if self.files else "disabled")
        self.lbl_status.config(
            text=f"共 {len(self.files)} 个文件" if self.files else "文件夹为空",
            fg=COLOR_GREEN if self.files else COLOR_WARN,
        )

    # ------------------------------------------------------------------
    def _on_template_change(self):
        """模板参数变更时更新预览"""
        if self.files:
            self._refresh_preview()

    def _build_new_name(self, index: int, ext: str) -> str:
        """根据模板构建新文件名"""
        prefix = self.prefix_var.get()
        start = self.start_var.get()
        digits = self.digits_var.get()
        step = self.step_var.get()
        suffix = self.suffix_var.get()

        num = start + index * step
        num_str = str(num).zfill(digits)
        return f"{prefix}{num_str}{suffix}{ext}"

    def _refresh_preview(self):
        """刷新文件列表预览"""
        self.listbox.delete(0, tk.END)
        self.rename_map.clear()

        if not self.files:
            return

        for i, fname in enumerate(self.files):
            stem, ext = os.path.splitext(fname)
            new_name = self._build_new_name(i, ext)
            self.rename_map[fname] = new_name
            self.listbox.insert(tk.END, f"  {fname:35s} → {new_name}")

        # 更新示例
        sample_ext = os.path.splitext(self.files[0])[1] if self.files else ".ext"
        sample = self._build_new_name(0, sample_ext)
        self.lbl_sample.config(text=sample)

    # ------------------------------------------------------------------
    def _on_rename(self):
        """执行批量重命名"""
        if not self.rename_map:
            return

        # 检查是否有重名冲突
        new_names = list(self.rename_map.values())
        if len(new_names) != len(set(new_names)):
            # 找出冲突项
            from collections import Counter
            conflicts = [n for n, c in Counter(new_names).items() if c > 1]
            messagebox.showerror("重名冲突",
                f"以下新文件名存在重复，请调整模板参数：\n" +
                "\n".join(f"  {c}" for c in conflicts[:10]))
            return

        # 检查是否与已存在的文件冲突
        conflicts_existing = []
        for old, new in self.rename_map.items():
            new_path = os.path.join(self.folder, new)
            old_path = os.path.join(self.folder, old)
            if os.path.exists(new_path) and new_path != old_path:
                conflicts_existing.append(new)

        if conflicts_existing:
            if not messagebox.askyesno("文件覆盖确认",
                f"以下 {len(conflicts_existing)} 个新文件名已存在，将被覆盖：\n" +
                "\n".join(f"  {c}" for c in conflicts_existing[:10]) +
                f"\n{'...' if len(conflicts_existing) > 10 else ''}\n\n确定继续？"):
                return

        # 执行重命名（先全部改为临时名避免冲突，再改为目标名）
        temp_prefix = f"_ren_temp_{datetime.now().strftime('%H%M%S%f')}_"
        step1_map = {}  # 旧绝对路径 → 临时绝对路径
        step2_map = {}  # 临时绝对路径 → 新绝对路径

        try:
            # 第一步：全部改为临时名
            for old_name, new_name in self.rename_map.items():
                old_path = os.path.join(self.folder, old_name)
                temp_name = temp_prefix + old_name
                temp_path = os.path.join(self.folder, temp_name)
                os.rename(old_path, temp_path)
                step1_map[old_path] = temp_path

            # 第二步：临时名改为目标名
            for old_name, new_name in self.rename_map.items():
                old_path = os.path.join(self.folder, old_name)
                temp_path = step1_map[old_path]
                new_path = os.path.join(self.folder, new_name)
                os.rename(temp_path, new_path)
                step2_map[temp_path] = new_path

            # 记录撤销信息
            self.undo_history.append({
                "folder": self.folder,
                "mapping": {new_name: old_name for old_name, new_name in self.rename_map.items()},
            })

            self.lbl_status.config(
                text=f"重命名完成：{len(self.rename_map)} 个文件",
                fg=COLOR_GREEN,
            )
            self.btn_undo.configure(state="normal")
            messagebox.showinfo("完成", f"已成功重命名 {len(self.rename_map)} 个文件。\n可使用「撤销重命名」一键还原。")

            # 刷新列表
            self.files = sorted(list(self.rename_map.values()))
            self._refresh_preview()

        except OSError as e:
            messagebox.showerror("重命名失败", f"操作出错：{e}\n\n请检查是否有文件正在被使用。")
            self.lbl_status.config(text="重命名失败，请检查后重试", fg="red")
            # 尝试回滚已执行的步骤
            self._rollback_step1(step1_map)

    def _rollback_step1(self, step1_map: dict):
        """回滚第一步（临时名改回原名）"""
        for old_path, temp_path in step1_map.items():
            try:
                if os.path.exists(temp_path):
                    os.rename(temp_path, old_path)
            except OSError:
                pass

    def _on_undo(self):
        """撤销最近一次重命名"""
        if not self.undo_history:
            return

        record = self.undo_history.pop()
        folder = record["folder"]
        mapping = record["mapping"]

        try:
            success = 0
            failed = 0
            for current_name, original_name in mapping.items():
                cur_path = os.path.join(folder, current_name)
                orig_path = os.path.join(folder, original_name)
                try:
                    if os.path.exists(cur_path):
                        # 如果目标路径已存在，先临时改名
                        if os.path.exists(orig_path):
                            tmp = orig_path + f".undo_{datetime.now().strftime('%H%M%S%f')}"
                            os.rename(orig_path, tmp)
                            os.rename(cur_path, orig_path)
                            os.rename(tmp, cur_path)
                        else:
                            os.rename(cur_path, orig_path)
                        success += 1
                except OSError:
                    failed += 1

            self.lbl_status.config(
                text=f"撤销完成：{success} 成功" + (f"，{failed} 失败" if failed else ""),
                fg=COLOR_GREEN if not failed else COLOR_WARN,
            )

            if not self.undo_history:
                self.btn_undo.configure(state="disabled")

            # 刷新
            self.files = sorted(list(mapping.values()))
            self._refresh_preview()

        except Exception as e:
            messagebox.showerror("撤销失败", str(e))


# ============================================================================
# 入口
# ============================================================================

def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    BatchRenamerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
