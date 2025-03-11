import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from itertools import product
import threading
import queue
import re
import sys
import random
from collections import defaultdict

# -------------------- 基础函数 --------------------
def load_original_combinations(file_path):
    """加载原始组合数据"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return set(line.strip() for line in file)

def save_results(file_path, results):
    """保存结果到文件"""
    with open(file_path, 'w', encoding='utf-8') as file:
        for combo in results:
            file.write(combo + '\n')

# -------------------- 自定义控件 --------------------
class StyledCheckbutton(tk.Checkbutton):
    """带样式更新的复选框"""
    def __init__(self, master, text, variable, style_callback, **kwargs):
        super().__init__(master, text=text, variable=variable, **kwargs)
        self.variable = variable
        self.style_callback = style_callback
        self.configure(command=self.update_style, bg="white")

    def update_style(self):
        """动态更新样式"""
        self.style_callback(self["text"], self.variable.get())

# -------------------- 常规过滤窗口 --------------------
class BasicFilterWindow(tk.Toplevel):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.title("常规过滤")
        self.geometry("680x700")
        self.configure(bg="#f0f0f0")
        
        self.grab_set()
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.filtered_data = list(app.new_combinations)
        self.current_page = 1
        self.page_size = 20
        self.total_pages = 0
        
        self.create_widgets()
        self.update_count()

    def create_widgets(self):
        condition_frame = ttk.LabelFrame(self, text="常规过滤条件")
        condition_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=10)
        
        conditions = [
            ("胜场数", 5, 7), ("平场数", 4, 6), ("负场数", 3, 6),
            ("连胜", 1, 5), ("连平", 1, 3), ("连负", 1, 3),
            ("胜平连号", 2, 8), ("胜负连号", 2, 8), ("平负连号", 0, 7)
        ]
        
        self.condition_vars = []
        self.min_combos = []
        self.max_combos = []
        for idx, (label, d_min, d_max) in enumerate(conditions):
            row_frame = ttk.Frame(condition_frame)
            row_frame.pack(fill=tk.X, pady=3, padx=5)
            
            var = tk.IntVar(value=1 if idx < 3 else 0)
            ttk.Checkbutton(row_frame, variable=var).pack(side=tk.LEFT, padx=5)
            self.condition_vars.append(var)
            
            ttk.Label(row_frame, text=label, width=12).pack(side=tk.LEFT)
            
            min_combo = ttk.Combobox(
                row_frame, 
                values=[str(i) for i in range(15)],
                width=4, 
                state="readonly"
            )
            min_combo.set(str(d_min))
            min_combo.pack(side=tk.LEFT)
            self.min_combos.append(min_combo)
            
            ttk.Label(row_frame, text=" ≤ 值 ≤ ").pack(side=tk.LEFT)
            
            max_combo = ttk.Combobox(
                row_frame,
                values=[str(i) for i in range(15)],
                width=4,
                state="readonly"
            )
            max_combo.set(str(d_max))
            max_combo.pack(side=tk.LEFT)
            self.max_combos.append(max_combo)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="开始过滤", command=self.start_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="下一步", command=self.open_position_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="上一步", command=self.back_to_mystic).pack(side=tk.LEFT, padx=5)  # 新增按钮
        ttk.Button(btn_frame, text="返回", command=self.on_close).pack(side=tk.LEFT, padx=5)

        result_frame = ttk.LabelFrame(self, text="过滤结果")
        result_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=10)
        
        self.result_text = tk.Text(result_frame, height=12, width=70, 
                                 font=('Consolas', 9), wrap=tk.NONE)
        vsb = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_text.yview)
        hsb = ttk.Scrollbar(result_frame, orient="horizontal", command=self.result_text.xview)
        self.result_text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.result_text.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)
        
        page_frame = ttk.Frame(self)
        page_frame.pack(pady=5)
        self.prev_btn = ttk.Button(page_frame, text="◀", width=3, command=self.prev_page)
        self.page_label = ttk.Label(page_frame, text="0/0")
        self.next_btn = ttk.Button(page_frame, text="▶", width=3, command=self.next_page)
        self.count_label = ttk.Label(page_frame, text="共0条")
        
        self.prev_btn.pack(side=tk.LEFT)
        self.page_label.pack(side=tk.LEFT, padx=5)
        self.next_btn.pack(side=tk.LEFT)
        self.count_label.pack(side=tk.LEFT, padx=10)
        ttk.Button(page_frame, text="保存结果", command=self.save_results).pack(side=tk.LEFT, padx=10)

    def start_filter(self):
        active_conditions = []
        for i in range(9):
            if self.condition_vars[i].get():
                try:
                    min_val = int(self.min_combos[i].get())
                    max_val = int(self.max_combos[i].get())
                    if min_val > max_val:
                        messagebox.showerror("错误", "最小值不能大于最大值")
                        return
                    active_conditions.append( (i, min_val, max_val) )
                except ValueError:
                    messagebox.showerror("错误", "请输入有效数字")
                    return
        
        if not active_conditions:
            messagebox.showwarning("提示", "请至少选择一个条件")
            return
        
        filtered = []
        for combo in self.app.new_combinations:
            win_count = combo.count('3')
            draw_count = combo.count('1')
            lose_count = combo.count('0')
            
            win_streak = max(len(m) for m in re.findall(r'3+', combo)) if '3' in combo else 0
            draw_streak = max(len(m) for m in re.findall(r'1+', combo)) if '1' in combo else 0
            lose_streak = max(len(m) for m in re.findall(r'0+', combo)) if '0' in combo else 0
            
            win_draw = self.calc_mixed_streak(combo, {'3','1'})
            win_lose = self.calc_mixed_streak(combo, {'3','0'})
            draw_lose = self.calc_mixed_streak(combo, {'1','0'})
            
            valid = True
            for cond_id, min_v, max_v in active_conditions:
                value = [
                    win_count, draw_count, lose_count,
                    win_streak, draw_streak, lose_streak,
                    win_draw, win_lose, draw_lose
                ][cond_id]
                if not (min_v <= value <= max_v):
                    valid = False
                    break
            if valid:
                filtered.append(combo)
        
        self.filtered_data = filtered
        self.current_page = 1
        self.total_pages = max(1, (len(filtered) + self.page_size -1) // self.page_size)
        self.update_page_controls()
        self.show_current_page()
        self.update_count()
        messagebox.showinfo("完成", f"过滤后剩余{len(filtered)}条")

    def calc_mixed_streak(self, combo, chars):
        max_len = current = 0
        for c in combo:
            if c in chars:
                current += 1
                max_len = max(max_len, current)
            else:
                current = 0
        return max_len

    def update_page_controls(self):
        self.prev_btn["state"] = "normal" if self.current_page > 1 else "disabled"
        self.next_btn["state"] = "normal" if self.current_page < self.total_pages else "disabled"
        self.page_label["text"] = f"{self.current_page}/{self.total_pages}"

    def show_current_page(self):
        start = (self.current_page-1)*self.page_size
        end = start + self.page_size
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "\n".join(self.filtered_data[start:end]))

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_page_controls()
            self.show_current_page()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_page_controls()
            self.show_current_page()

    def update_count(self):
        self.count_label.config(text=f"共{len(self.filtered_data)}条")

    def save_results(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt")]
        )
        if path:
            save_results(path, self.filtered_data)
            messagebox.showinfo("成功", f"已保存{len(self.filtered_data)}条结果")

    def open_position_filter(self):
        PositionFilterWindow(self.master, self.app, self.filtered_data)
        self.destroy()
    
    def back_to_mystic(self):
        self.app.deiconify()
        MysticFilterWindow(
            self.master, 
            self.app,
            self.app.sorted_combinations,
            callback=lambda: BasicFilterWindow(self.master, self.app)
        )
        self.destroy()
    
    def on_close(self):
        self.app.deiconify()
        self.destroy()

# -------------------- 定位过滤窗口 --------------------
class PositionFilterWindow(tk.Toplevel):
    def __init__(self, master, app, data):
        super().__init__(master)
        self.app = app
        self.original_data = data.copy()
        self.filtered_data = data.copy()
        self.title("定位过滤")
        self.geometry("900x800")
        
        self.grab_set()
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.position_vars = []
        self.create_widgets()
        self.show_results()
        
    def create_widgets(self):
        # 上半部分：条件设置
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左侧：位置复选框
        left_frame = ttk.LabelFrame(top_frame, text="位置条件设置")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # 创建14个位置的复选框
        for pos in range(14):
            row_frame = ttk.Frame(left_frame)
            row_frame.pack(fill=tk.X, pady=2)
            ttk.Label(row_frame, text=f"第{pos+1}位:", width=6).pack(side=tk.LEFT)
            vars = []
            for char in ['3', '1', '0']:
                var = tk.IntVar()
                cb = ttk.Checkbutton(row_frame, text=char, variable=var)
                cb.pack(side=tk.LEFT, padx=2)
                vars.append(var)
            self.position_vars.append(vars)

        # 中间：按钮
        mid_frame = ttk.Frame(top_frame)
        mid_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        btn_frame = ttk.Frame(mid_frame)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="添加条件", command=self.add_condition).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="删除选中", command=self.remove_condition).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="全部删除", command=self.clear_conditions).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="导出条件", command=self.export_conditions).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="导入条件", command=self.import_conditions).pack(fill=tk.X, pady=2)

        # 右侧：条件列表
        right_frame = ttk.LabelFrame(top_frame, text="已添加的条件")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self.condition_list = tk.Listbox(right_frame, height=15, width=25, selectmode=tk.SINGLE)
        scroll = ttk.Scrollbar(right_frame, command=self.condition_list.yview)
        self.condition_list.configure(yscrollcommand=scroll.set)
        self.condition_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 下半部分：过滤结果
        bottom_frame = ttk.LabelFrame(self, text="过滤结果")
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.result_info = ttk.Label(bottom_frame, text="匹配结果：0条")
        self.result_info.pack(pady=5)

        self.result_text = tk.Text(bottom_frame, height=15, width=50, font=('Consolas', 9))
        scroll_result = ttk.Scrollbar(bottom_frame, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scroll_result.set)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_result.pack(side=tk.RIGHT, fill=tk.Y)

        # 控制区域
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, pady=10)

        self.filter_type = tk.IntVar(value=1)
        ttk.Radiobutton(control_frame, text="保留匹配项", variable=self.filter_type, value=1).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(control_frame, text="过滤匹配项", variable=self.filter_type, value=0).pack(side=tk.LEFT, padx=5)

        action_frame = ttk.Frame(control_frame)
        action_frame.pack(side=tk.RIGHT, padx=10)
        ttk.Button(action_frame, text="执行过滤", command=self.apply_filter).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="保存结果", command=self.save_results).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="重置数据", command=self.reset_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="返回上一步", command=self.back_to_basic).pack(side=tk.LEFT, padx=2)

    def add_condition(self):
        position_options = []
        for pos_vars in self.position_vars:
            selected = []
            for i, var in enumerate(pos_vars):
                if var.get():
                    selected.append(['3', '1', '0'][i])
            if not selected:
                selected.append('#')
            position_options.append(selected)
        
        conditions = []
        for combo in product(*position_options):
            condition = ''.join(combo)
            conditions.append(condition.replace('#', '#'))
        
        existing = set(self.condition_list.get(0, tk.END))
        for cond in conditions:
            if cond not in existing:
                self.condition_list.insert(tk.END, cond)

    def remove_condition(self):
        selection = self.condition_list.curselection()
        if selection:
            self.condition_list.delete(selection[0])

    def clear_conditions(self):
        self.condition_list.delete(0, tk.END)

    def export_conditions(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt")]
        )
        if path:
            with open(path, 'w') as f:
                f.write("\n".join(self.condition_list.get(0, tk.END)))
            messagebox.showinfo("成功", "条件已导出")

    def import_conditions(self):
        path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt")])
        if path:
            try:
                with open(path, 'r') as f:
                    conditions = [line.strip() for line in f if line.strip()]
                self.condition_list.delete(0, tk.END)
                for cond in conditions:
                    if len(cond) == 14 and all(c in "310#" for c in cond):
                        self.condition_list.insert(tk.END, cond)
                messagebox.showinfo("成功", f"已导入{len(conditions)}条条件")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {str(e)}")

    def apply_filter(self):
        conditions = self.condition_list.get(0, tk.END)
        if not conditions:
            messagebox.showwarning("提示", "请先添加过滤条件")
            return
        
        filtered = []
        for combo in self.original_data:
            match = any(
                all(c == '#' or combo[i] == c for i, c in enumerate(cond))
                for cond in conditions if len(cond) == 14
            )
            if (self.filter_type.get() == 1 and match) or \
               (self.filter_type.get() == 0 and not match):
                filtered.append(combo)
        
        self.filtered_data = filtered
        self.show_results()
        messagebox.showinfo("完成", f"过滤后剩余{len(filtered)}条")

    def show_results(self):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "\n".join(self.filtered_data))
        self.result_info.config(text=f"匹配结果：{len(self.filtered_data)}条")

    def save_results(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt")]
        )
        if path:
            save_results(path, self.filtered_data)
            messagebox.showinfo("成功", f"已保存{len(self.filtered_data)}条结果")

    def reset_data(self):
        self.filtered_data = self.original_data.copy()
        self.show_results()

    def back_to_basic(self):
        self.app.new_combinations = set(self.filtered_data)
        self.app.sorted_combinations = sorted(self.filtered_data)
        self.app.deiconify()
        self.app.show_main_page()
        self.destroy()

    def on_close(self):
        self.back_to_basic()

# -------------------- 玄学过滤窗口（修复版）--------------------
class MysticFilterWindow(tk.Toplevel):
    def __init__(self, master, app, data, callback):
        super().__init__(master)
        self.app = app
        self.original_data = list(data)
        self.filtered_data = list(data)
        self.callback = callback
        self.title("玄学过滤 - 智能优化版")
        self.geometry("1400x900")  # 加宽窗口解决显示问题
        self.configure(bg="#f0f0f0")
        
        # 初始化分页参数
        self.current_page = 1
        self.page_size = 20
        self.total_pages = 0
        
        # 统计数据和权重
        self.stats = self.calculate_statistics()
        self.position_weights = self.get_position_weights()
        
        self.create_widgets()
        self.update_page_controls()
        self.show_current_page()
        self.update_count()
        
        # 事件绑定
        self.strength.bind("<Motion>", self.show_strength_tip)
        self.tolerance.bind("<Motion>", self.show_tolerance_tip)

    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧控制面板
        control_frame = ttk.LabelFrame(main_frame, text="智能参数设置")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        self.create_controls(control_frame)
        
        # 右侧结果展示
        result_frame = ttk.LabelFrame(main_frame, text="过滤结果（共{}条原始数据）".format(len(self.original_data)))
        result_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.create_results(result_frame)

    def create_controls(self, parent):
        param_frame = ttk.Frame(parent)
        param_frame.pack(pady=5)

        # 参数输入组件
        ttk.Label(param_frame, text="锚定场次:").grid(row=0, column=0, sticky="e")
        self.anchor_count = ttk.Combobox(param_frame, values=list(range(1,15)), state="readonly", width=5)
        self.anchor_count.set("5")
        self.anchor_count.grid(row=0, column=1, padx=5)
        ttk.Label(param_frame, text="个高频位置").grid(row=0, column=2)

        ttk.Label(param_frame, text="最大容错:").grid(row=1, column=0, sticky="e")
        self.tolerance = ttk.Combobox(param_frame, values=list(range(0,6)), state="readonly", width=5)
        self.tolerance.set("3")
        self.tolerance.grid(row=1, column=1, padx=5)
        ttk.Label(param_frame, text="加权容错值").grid(row=1, column=2)

        ttk.Label(param_frame, text="收缩强度:").grid(row=2, column=0, sticky="e")
        self.strength = ttk.Scale(param_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=150)
        self.strength.set(50)
        self.strength.grid(row=2, column=1, columnspan=2)

        # 统计图表区域
        chart_frame = ttk.Frame(parent)
        chart_frame.pack(pady=10)
        
        self.stats_chart = tk.Canvas(chart_frame, width=400, height=150, bg='white')
        self.stats_chart.pack(side=tk.LEFT)
        self.draw_frequency_chart()
        
        chart_help = """
        【位置频率直方图】
        柱子高度表示各位置出现'3'或'1'的概率
        颜色说明：
        🔴 红色：高频位置（推荐锚定）
        🟢 绿色：中频位置
        🔵 蓝色：低频位置
        建议优先选择红色区域位置进行锚定
        """
        ttk.Label(chart_frame, text=chart_help, wraplength=250).pack(side=tk.LEFT, padx=10)

        # 操作按钮
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="执行智能过滤", command=self.start_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="推荐参数", command=self.suggest_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="随机预览", command=self.preview_filter).pack(side=tk.LEFT, padx=5)

        # 参数说明
        help_frame = ttk.LabelFrame(parent, text="参数说明")
        help_frame.pack(fill=tk.X)
        helps = [
            ("🔒 锚定场次", "强制要求选定的N个高频位置必须为3/1"),
            ("🛡️ 最大容错", "允许出现0的总权重值（后卫位置0的影响更大）"),
            ("📉 收缩强度", "向左←保留更少但更优质的组合\n向右→保留更多备选组合")
        ]
        for text, desc in helps:
            frame = ttk.Frame(help_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=text, width=12).pack(side=tk.LEFT)
            ttk.Label(frame, text=desc).pack(side=tk.LEFT)

    def create_results(self, parent):
        # 结果文本框
        self.result_text = tk.Text(parent, height=25, width=60, 
                                 font=('Consolas', 9), wrap=tk.NONE)
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.result_text.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.result_text.xview)
        self.result_text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.result_text.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # 分页控制
        page_frame = ttk.Frame(parent)
        page_frame.grid(row=2, column=0, pady=5)
        self.prev_btn = ttk.Button(page_frame, text="◀", command=self.prev_page)
        self.page_label = ttk.Label(page_frame, text="0/0")
        self.next_btn = ttk.Button(page_frame, text="▶", command=self.next_page)
        self.count_label = ttk.Label(page_frame, text="共0条")
        
        self.prev_btn.pack(side=tk.LEFT)
        self.page_label.pack(side=tk.LEFT, padx=5)
        self.next_btn.pack(side=tk.LEFT)
        self.count_label.pack(side=tk.LEFT, padx=10)
        
        # 操作按钮
        action_frame = ttk.Frame(parent)
        action_frame.grid(row=3, column=0, pady=5)
        ttk.Button(action_frame, text="确认继续", command=self.on_close).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="返回上一步", command=self.back_to_basic).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="重置数据", command=self.reset_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="跳过此步", command=self.skip_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="保存结果", command=self.save_results).pack(side=tk.LEFT, padx=5)

    def save_results(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt")]
        )
        if path:
            save_results(path, self.filtered_data)
            messagebox.showinfo("成功", f"已保存{len(self.filtered_data)}条结果")
            
    def calculate_statistics(self):
        stats = defaultdict(lambda: defaultdict(int))
        for combo in self.original_data:
            for idx, c in enumerate(combo):
                if c in ['3','1']:
                    stats['position'][idx] += 1
            for i in range(len(combo)-2):
                stats['patterns'][combo[i:i+3]] += 1
        return stats

    def draw_frequency_chart(self):
        self.stats_chart.delete("all")
        max_freq = max(self.stats['position'].values()) or 1
        
        # 绘制坐标轴
        self.stats_chart.create_line(30, 20, 30, 130, width=2)
        self.stats_chart.create_line(30, 130, 380, 130, width=2)
        
        bar_width = 20
        x = 40
        for pos in range(14):
            height = (self.stats['position'][pos]/max_freq)*100
            color = "#%02x%02x%02x" % (
                int(255 - height*2),
                int(height*2),
                50
            )
            self.stats_chart.create_rectangle(
                x, 130-height, x+bar_width, 130,
                fill=color, outline=''
            )
            self.stats_chart.create_text(x+bar_width/2, 140, text=str(pos+1))
            x += bar_width + 5
        
        self.stats_chart.create_text(200, 145, text="← 位置编号（1-14） →", anchor=tk.CENTER)
        self.stats_chart.create_text(30, 15, text="频率% →", anchor=tk.NW)

    def start_filter(self):
        try:
            anchor_num = int(self.anchor_count.get())
            max_tolerance = float(self.tolerance.get())
            strength = self.strength.get()
            
            # 智能锚定
            anchors = self.select_anchor_fields(anchor_num)
            filtered = [c for c in self.original_data 
                       if all(c[idx] in ['3','1'] for idx in anchors)]
            
            # 动态容错
            filtered = self.apply_tolerance(filtered, max_tolerance)
            
            # 智能收缩
            if filtered:
                filtered = self.smart_shrink(filtered, strength)
            
            self.filtered_data = filtered
            self.current_page = 1
            self.total_pages = max(1, (len(filtered) + self.page_size - 1) // self.page_size)
            self.update_page_controls()
            self.show_current_page()
            self.update_count()
            messagebox.showinfo("完成", f"过滤后剩余：{len(filtered)}条")
            
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def select_anchor_fields(self, num):
        sorted_pos = sorted(self.stats['position'].items(), key=lambda x:x[1], reverse=True)
        return [x[0] for x in sorted_pos[:num]]

    def apply_tolerance(self, data, max_tolerance):
        return [c for c in data if 
               sum(self.position_weights[idx] for idx,ch in enumerate(c) if ch == '0') <= max_tolerance]

    def get_position_weights(self):
        return {
            0:0.8, 1:0.9, 2:1.0, 3:1.1, 
            4:0.7, 5:0.8, 6:0.9, 7:1.0,
            8:0.6, 9:0.7, 10:0.5, 11:0.6,
            12:0.4, 13:0.5
        }

    def smart_shrink(self, data, strength):
        scored = []
        for combo in data:
            score = 0
            # 模式得分
            for i in range(len(combo)-2):
                score += self.stats['patterns'].get(combo[i:i+3], 0)
            # 位置得分
            score += sum(self.stats['position'][idx] for idx, c in enumerate(combo) if c in ['3','1'])
            scored.append( (combo, score) )
        
        scored.sort(key=lambda x:x[1], reverse=True)
        keep_count = max(1, int(len(scored)*strength/100))
        return [x[0] for x in scored[:keep_count]]

    def suggest_params(self):
        total = len(self.original_data)
        suggest_tolerance = min(4, int(total**0.5))
        suggest_strength = max(30, 100 - int(total/100))
        
        self.tolerance.set(suggest_tolerance)
        self.strength.set(suggest_strength)
        messagebox.showinfo("参数推荐", f"推荐参数：\n容错次数：{suggest_tolerance}\n收缩强度：{suggest_strength}%")

    def reset_data(self):
        self.filtered_data = self.original_data.copy()
        self.current_page = 1
        self.total_pages = max(1, (len(self.filtered_data) + self.page_size - 1) // self.page_size)
        self.update_page_controls()
        self.show_current_page()
        self.update_count()
        messagebox.showinfo("重置完成", "已恢复初始数据")

    def back_to_basic(self):
        self.app.deiconify()
        self.destroy()

    def skip_step(self):
        self.app.new_combinations = set(self.original_data)
        self.callback()
        self.destroy()

    def update_page_controls(self):
        self.prev_btn["state"] = "normal" if self.current_page > 1 else "disabled"
        self.next_btn["state"] = "normal" if self.current_page < self.total_pages else "disabled"
        self.page_label["text"] = f"{self.current_page}/{self.total_pages}"

    def show_current_page(self):
        start = (self.current_page-1)*self.page_size
        end = start + self.page_size
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "\n".join(self.filtered_data[start:end]))

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_page_controls()
            self.show_current_page()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_page_controls()
            self.show_current_page()

    def update_count(self):
        self.count_label.config(text=f"共{len(self.filtered_data)}条")

    def preview_filter(self):
        if self.filtered_data:
            sample = random.sample(self.filtered_data, min(5, len(self.filtered_data)))
            messagebox.showinfo("预览", "\n".join(sample))

    def on_close(self):
        self.app.new_combinations = set(self.filtered_data)
        self.app.sorted_combinations = sorted(self.filtered_data)
        if self.callback:
            self.callback()
        self.destroy()

    def show_strength_tip(self, event):
        value = self.strength.get()
        tip_text = f"收缩强度：{value}%\n"
        tip_text += "← 严格筛选（保留前{}条）\n→ 宽松筛选（保留前{}条）".format(
            int(len(self.filtered_data)*0.3),
            int(len(self.filtered_data)*0.8)
        )
        self.show_tooltip(tip_text)

    def show_tolerance_tip(self, event):
        tip_text = "容错权重说明：\n"
        tip_text += "• 前锋位置（1-5）：0.8\n"
        tip_text += "• 中场位置（6-10）：1.0\n"
        tip_text += "• 后卫位置（11-14）：1.2"
        self.show_tooltip(tip_text)

    def show_tooltip(self, text):
        x, y = self.winfo_pointerxy()
        tip = tk.Toplevel(self)
        tip.wm_overrideredirect(True)
        tip.geometry(f"+{x+10}+{y+10}")
        ttk.Label(tip, text=text, background="#FFFFE0", borderwidth=1, relief="solid").pack()
        self.after(1500, tip.destroy)

# -------------------- 主程序 --------------------
class CombinationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("组合生成器 v5.0")
        self.geometry("900x1080")
        self.configure(bg="#f0f0f0")
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        
        self.original_combinations = set()
        self.new_combinations = set()
        self.sorted_combinations = []
        self.checkbox_vars = []
        self.checkboxes = []
        self.stop_event = threading.Event()
        self.progress_queue = queue.Queue()
        self.current_page = 1
        self.page_size = 20
        self.total_pages = 0
        
        self.create_widgets()
        self.setup_styles()
        self.after(100, self.process_queue)
        
        exit_btn = ttk.Button(self, text="退出程序", command=self.quit_app)
        exit_btn.pack(side=tk.BOTTOM, pady=10)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=6, font=('微软雅黑', 10))
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=('微软雅黑', 9))

    def create_widgets(self):
        file_frame = ttk.Frame(self)
        file_frame.pack(pady=10, fill=tk.X, padx=10)
        
        ttk.Button(file_frame, text="导入数据源", command=self.load_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="导入模板", command=self.load_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="清空选项", command=self.clear_checkboxes).pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(self, text="已加载组合：0")
        self.status_label.pack(pady=5)
        
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(pady=5, fill=tk.BOTH, expand=True, padx=10)
        
        self.canvas = tk.Canvas(canvas_frame, bg="white", highlightthickness=0, height=250)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0,0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        for pos in range(14):
            row_frame = ttk.Frame(self.scrollable_frame)
            row_frame.pack(fill=tk.X, padx=10, pady=3)
            
            ttk.Label(row_frame, text=f"第 {pos+1} 位：", width=8).pack(side=tk.LEFT)
            
            var_3 = tk.IntVar()
            var_1 = tk.IntVar()
            var_0 = tk.IntVar()
            
            cb_3 = StyledCheckbutton(row_frame, text="3", variable=var_3,
                                   style_callback=lambda t,s,p=pos,i=0: self.safe_style_update(t,s,p,i))
            cb_1 = StyledCheckbutton(row_frame, text="1", variable=var_1,
                                   style_callback=lambda t,s,p=pos,i=1: self.safe_style_update(t,s,p,i))
            cb_0 = StyledCheckbutton(row_frame, text="0", variable=var_0,
                                   style_callback=lambda t,s,p=pos,i=2: self.safe_style_update(t,s,p,i))
            
            for cb in [cb_3, cb_1, cb_0]:
                cb.pack(side=tk.LEFT, padx=3)
            
            self.checkbox_vars.append( (var_3, var_1, var_0) )
            self.checkboxes.append( (cb_3, cb_1, cb_0) )
        
        self.progress = ttk.Progressbar(self, orient="horizontal", length=500, mode="determinate")
        self.progress.pack(pady=10)
        
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(pady=10)
        
        self.start_btn = ttk.Button(ctrl_frame, text="开始生成", command=self.start_generation)
        self.cancel_btn = ttk.Button(ctrl_frame, text="取消", state="disabled", command=self.cancel_generation)
        self.next_btn = ttk.Button(ctrl_frame, text="下一步", command=self.open_filter_window)
        
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        self.next_btn.pack(side=tk.LEFT, padx=5)
        
        self.result_text = tk.Text(self, height=6, width=70, font=('Consolas', 9))
        self.result_text.pack(pady=10, fill=tk.BOTH, expand=True, padx=10)
        
        page_frame = ttk.Frame(self)
        page_frame.pack(pady=5)
        
        self.prev_page_btn = ttk.Button(page_frame, text="◀", width=3, command=self.prev_main_page)
        self.page_label_main = ttk.Label(page_frame, text="0/0")
        self.next_page_btn = ttk.Button(page_frame, text="▶", width=3, command=self.next_main_page)
        self.count_label_main = ttk.Label(page_frame, text="共0条")
        ttk.Button(page_frame, text="清空结果", command=self.clear_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(page_frame, text="保存结果", command=self.save_file).pack(side=tk.LEFT, padx=5)
        
        self.prev_page_btn.pack(side=tk.LEFT)
        self.page_label_main.pack(side=tk.LEFT)
        self.next_page_btn.pack(side=tk.LEFT)
        self.count_label_main.pack(side=tk.LEFT, padx=10)

    def safe_style_update(self, text, state, position, index):
        if position < len(self.checkboxes) and index < 3:
            self.update_checkbox_style(text, state, position, index)
    
    def update_checkbox_style(self, text, state, pos, idx):
        colors = {"3":"red", "1":"#006400", "0":"blue"}
        checkbox = self.checkboxes[pos][idx]
        checkbox.configure(
            fg=colors[text] if state else "#666666",
            font=('Arial',9,'bold' if state else 'normal')
        )
    
    def clear_checkboxes(self):
        for var_3, var_1, var_0 in self.checkbox_vars:
            var_3.set(0)
            var_1.set(0)
            var_0.set(0)
        for pos in range(14):
            for idx in range(3):
                self.update_checkbox_style(["3","1","0"][idx], 0, pos, idx)
    
    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt")])
        if path:
            self.original_combinations = load_original_combinations(path)
            self.status_label.config(text=f"已加载组合：{len(self.original_combinations)}")
            messagebox.showinfo("成功", "数据源加载完成")
    
    def load_template(self):
        path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt")])
        if not path: return
        
        try:
            with open(path) as f:
                templates = [line.strip() for line in f if line.strip()]
            
            if not templates:
                messagebox.showerror("错误", "模板文件为空")
                return
            
            for template in templates:
                if len(template) != 14 or any(c not in '310' for c in template):
                    messagebox.showerror("错误", "模板必须为14位且只包含3/1/0")
                    return
            
            position_digits = [set() for _ in range(14)]
            for template in templates:
                for idx, c in enumerate(template):
                    position_digits[idx].add(c)
            
            for pos in range(14):
                var_3, var_1, var_0 = self.checkbox_vars[pos]
                var_3.set(1 if '3' in position_digits[pos] else 0)
                var_1.set(1 if '1' in position_digits[pos] else 0)
                var_0.set(1 if '0' in position_digits[pos] else 0)
                
                self.update_checkbox_style("3", var_3.get(), pos, 0)
                self.update_checkbox_style("1", var_1.get(), pos, 1)
                self.update_checkbox_style("0", var_0.get(), pos, 2)
            
            messagebox.showinfo("成功", f"已导入{len(templates)}个模板")
        
        except Exception as e:
            messagebox.showerror("错误", f"模板加载失败：{str(e)}")
    
    def start_generation(self):
        if not self.original_combinations:
            messagebox.showwarning("错误", "请先导入数据源")
            return
        
        self.start_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.next_btn.config(state="disabled")
        self.stop_event.clear()
        
        threading.Thread(target=self.generate_combinations, daemon=True).start()
    
    def generate_combinations(self):
        try:
            self.new_combinations.clear()
            selected = []
            
            for pos in range(14):
                var_3, var_1, var_0 = self.checkbox_vars[pos]
                options = []
                if var_3.get(): options.append('3')
                if var_1.get(): options.append('1')
                if var_0.get(): options.append('0')
                selected.append(options if options else ['3','1','0'])
            
            total = len(self.original_combinations)
            processed = 0
            
            for batch in self.chunked_list(list(self.original_combinations), 100):
                if self.stop_event.is_set():
                    break
                
                for combo in batch:
                    parts = []
                    for idx, char in enumerate(combo):
                        parts.append(selected[idx])
                    
                    for variation in product(*parts):
                        new_combo = ''.join(variation)
                        if new_combo not in self.original_combinations:
                            self.new_combinations.add(new_combo)
                    
                    processed += 1
                    self.progress_queue.put(('progress', processed/total*100))
                
                self.progress_queue.put(('partial', len(self.new_combinations)))
            
            self.sorted_combinations = sorted(self.new_combinations)
            self.total_pages = (len(self.sorted_combinations) + self.page_size -1) // self.page_size
            self.progress_queue.put(('done', len(self.new_combinations)))
        
        except Exception as e:
            self.progress_queue.put(('error', str(e)))
    
    def chunked_list(self, lst, size):
        for i in range(0, len(lst), size):
            yield lst[i:i+size]
    
    def process_queue(self):
        try:
            while True:
                msg_type, data = self.progress_queue.get_nowait()
                
                if msg_type == 'progress':
                    self.progress['value'] = data
                elif msg_type == 'partial':
                    self.result_text.delete(1.0, tk.END)
                    self.result_text.insert(tk.END, f"已生成 {data} 条新组合...\n")
                elif msg_type == 'done':
                    self.progress['value'] = 100
                    self.current_page = 1
                    self.total_pages = max(1, (data + self.page_size -1) // self.page_size)
                    self.page_label_main.config(text=f"{self.current_page}/{self.total_pages}")
                    self.count_label_main.config(text=f"共{data}条")
                    self.show_main_page()
                    self.next_btn.config(state="normal")
                    messagebox.showinfo("完成", f"生成完成，共{data}条新组合")
                elif msg_type == 'error':
                    messagebox.showerror("错误", data)
                
                self.update()
        
        except queue.Empty:
            pass
        
        self.after(100, self.process_queue)
    
    def show_main_page(self):
        start = (self.current_page -1) * self.page_size
        end = start + self.page_size
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "\n".join(self.sorted_combinations[start:end]))
    
    def prev_main_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.page_label_main.config(text=f"{self.current_page}/{self.total_pages}")
            self.show_main_page()
    
    def next_main_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.page_label_main.config(text=f"{self.current_page}/{self.total_pages}")
            self.show_main_page()
    
    def cancel_generation(self):
        self.stop_event.set()
        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        messagebox.showinfo("提示", "操作已取消")
    
    def save_file(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt")]
        )
        if path:
            save_results(path, self.new_combinations)
            messagebox.showinfo("成功", "结果已保存")
    
    def open_filter_window(self):
        if not self.original_combinations:
            messagebox.showwarning("提示", "请先导入数据源")
            return
        
        if not self.new_combinations:
            self.new_combinations = self.original_combinations.copy()
            self.sorted_combinations = sorted(self.new_combinations)
        
        self.withdraw()
        MysticFilterWindow(
            self, 
            self, 
            self.new_combinations,
            callback=lambda: BasicFilterWindow(self, self)
        )
    
    def clear_results(self):
        self.result_text.delete(1.0, tk.END)
        self.new_combinations.clear()
        self.sorted_combinations.clear()
        self.current_page = 1
        self.total_pages = 0
        self.page_label_main.config(text="0/0")
        self.count_label_main.config(text="共0条")
        self.next_btn.config(state="disabled")
    
    def quit_app(self):
        self.stop_event.set()
        self.destroy()
        sys.exit(0)

if __name__ == '__main__':
    app = CombinationApp()
    app.mainloop()