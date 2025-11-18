# 2025.11.14_Grok3_modified.py
import os
import subprocess
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple
from PyQt5 import QtWidgets, QtCore, QtGui
import sys
import glob

class FLTSParser:
    def __init__(self, flts_path: str):
        self.flts_path = os.path.abspath(flts_path)
        self.lines = self.read_flts_file()
        self.sections = self.parse_sections()

    def read_flts_file(self) -> List[str]:
        with open(self.flts_path, 'r') as f:
            return f.readlines()

    def parse_sections(self) -> Dict[str, Dict]:
        sections = {}
        current_section = None
        current_subsection = None
        line_idx = 0

        while line_idx < len(self.lines):
            line = self.lines[line_idx].strip()

            major_sections = ['TITLE', 'INSTRUMENTAL AND SIZE BROADENING', 'STRUCTURAL', 'STACKING', 'TRANSITIONS', 'CALCULATION', 'SIMULATION']
            if line in major_sections:
                current_section = line
                sections[current_section] = {'start': line_idx, 'params': {}, 'subsections': {}, 'line_idx_map': {}}
                current_subsection = None
                if current_section == 'TITLE':
                    # Next line is the title text
                    line_idx += 1
                    title_text = self.lines[line_idx].strip()
                    sections[current_section]['params']['Title_Text'] = {
                        'line_idx': line_idx,
                        'values': [title_text]
                    }
                line_idx += 1
                continue

            # STRUCTURAL parsing (keeps track of potential extra next-line for certain params)
            if current_section == 'STRUCTURAL' and (
                line.startswith('Avercell') or line.startswith('SPGR') or
                line.startswith('Cell') or line.startswith('Symm') or
                line.startswith('NLAYERS') or line.startswith('Lwidth')
            ):
                parts = line.split()
                param_key = parts[0]
                values = parts[1:]
                sections[current_section]['params'][param_key] = {
                    'line_idx': line_idx,
                    'values': values
                }

                # check next non-empty line whether it should be treated as an extra line (same logic used elsewhere)
                next_idx = line_idx + 1
                while next_idx < len(self.lines) and self.lines[next_idx].strip() == '':
                    next_idx += 1
                if next_idx < len(self.lines):
                    nxt = self.lines[next_idx].strip()
                    if not nxt.startswith('LAYER') and nxt not in major_sections and not nxt.startswith('!'):
                        sections[current_section]['params'][param_key]['extra_line_idx'] = next_idx
                        sections[current_section]['params'][param_key]['extra_value'] = self.lines[next_idx].rstrip('\n')
                line_idx += 1
                continue

            if current_section == 'STRUCTURAL' and line.startswith('LAYER'):
                current_subsection = line.strip()
                sections[current_section]['subsections'][current_subsection] = {'params': {}, 'start': line_idx}
                line_idx += 1
                while line_idx < len(self.lines) and not self.lines[line_idx].strip().startswith('LAYER') and not self.lines[line_idx].strip() in major_sections:
                    sub_line = self.lines[line_idx].strip()
                    if sub_line.startswith('!Layer symmetry') or sub_line.startswith('LSYM') or sub_line.startswith('!Atom'):
                        line_idx += 1
                        continue
                    elif sub_line.startswith('Atom'):
                        parts = sub_line.split()
                        atom_key = f'Atom_{parts[1]}_{parts[2]}'
                        values = parts[1:]
                        sections[current_section]['subsections'][current_subsection]['params'][atom_key] = {
                            'line_idx': line_idx,
                            'values': values
                        }
                    elif sub_line.startswith('LSYM'):
                        parts = sub_line.split()
                        param_key = parts[0]
                        values = parts[1:]
                        sections[current_section]['subsections'][current_subsection]['params'][param_key] = {
                            'line_idx': line_idx,
                            'values': values
                        }
                    line_idx += 1
                continue

            if current_section == 'INSTRUMENTAL AND SIZE BROADENING':
                if line.startswith('Radiation') or line.startswith('Wavelength') or line.startswith('Aberrations') or line.startswith('Pseudo-Voigt'):
                    parts = line.split()
                    param_key = parts[0]
                    values = parts[1:]
                    sections[current_section]['params'][param_key] = {
                        'line_idx': line_idx,
                        'values': values
                    }

            if current_section == 'TRANSITIONS' and line.startswith('!'):
                subname = line[1:].strip()
                current_subsection = subname
                sections[current_section]['subsections'][current_subsection] = {'params': {}, 'line_idx': line_idx}
                line_idx += 1
                continue

            if current_section == 'TRANSITIONS' and current_subsection:
                if line.startswith('LT') or line.startswith('FW'):
                    parts = line.split()
                    param_key = parts[0]
                    values = parts[1:]
                    sections[current_section]['subsections'][current_subsection]['params'][param_key] = {
                        'line_idx': line_idx,
                        'values': values
                    }
                    line_idx += 1
                    if line_idx < len(self.lines):
                        next_line = self.lines[line_idx].strip()
                        if next_line and all(v == '0.00' for v in next_line.split() if v):
                            line_idx += 1
                            continue
                else:
                    pass
                line_idx += 1
                continue

            if current_section == 'STACKING':
                parts = line.split()
                if not parts:
                    line_idx += 1
                    continue
                token = parts[0]
                # If token is RECURSIVE or INFINITE, capture any values that follow on the same line.
                # (This fixes cases like "INFINITE 1000" so the 1000 is shown in the first-line input.)
                if token in ('RECURSIVE', 'INFINITE'):
                    # capture following tokens on the same line as values (may be empty)
                    following = parts[1:] if len(parts) > 1 else []
                    # if no following values, set values to [''] (so GUI still creates an editable field)
                    values = following if following else ['']
                    sections[current_section]['params'][token] = {
                        'line_idx': line_idx,
                        'values': values,
                        'solo': True
                    }
                    # check next non-empty line for extra value (second-line behaviour)
                    next_idx = line_idx + 1
                    while next_idx < len(self.lines) and self.lines[next_idx].strip() == '':
                        next_idx += 1
                    if next_idx < len(self.lines):
                        nxt = self.lines[next_idx].strip()
                        if nxt not in major_sections and not nxt.startswith('LAYER') and not nxt.startswith('!'):
                            sections[current_section]['params'][token]['extra_line_idx'] = next_idx
                            sections[current_section]['params'][token]['extra_value'] = self.lines[next_idx].rstrip('\n')
                else:
                    # ordinary key-value line
                    param_key = parts[0]
                    values = parts[1:]
                    sections[current_section]['params'][param_key] = {
                        'line_idx': line_idx,
                        'values': values
                    }
                line_idx += 1
                continue

            if current_section == 'CALCULATION' or current_section == 'SIMULATION':
                if line.startswith('POWDER'):
                    parts = line.split()
                    param_key = parts[0]
                    values = parts[1:]
                    sections[current_section]['params'][param_key] = {
                        'line_idx': line_idx,
                        'values': values
                    }

            line_idx += 1

        return sections

    def update_parameter(self, section: str, subsection: str, param_key: str, value_idx: int, new_value: str):
        if subsection:
            param_data = self.sections[section]['subsections'][subsection]['params'][param_key]
        else:
            param_data = self.sections[section]['params'][param_key]
        
        line_idx = param_data['line_idx']
        values = param_data.get('values', [])
        while len(values) <= value_idx:
            values.append('')
        values[value_idx] = new_value

        # Aberrations 只更新本行的三个数值
        if section == 'INSTRUMENTAL AND SIZE BROADENING' and param_key == 'Aberrations':
            # 只保留前3个数值
            values = values[:3]
            param_data['values'] = values
            new_line = 'Aberrations ' + ' '.join(values) + '\n'
            indentation = len(self.lines[line_idx]) - len(self.lines[line_idx].lstrip())
            self.lines[line_idx] = ' ' * indentation + new_line
            return

        # Pseudo-Voigt 只更新本行的七个参数，保持后续行不变
        if section == 'INSTRUMENTAL AND SIZE BROADENING' and param_key == 'Pseudo-Voigt':
            # 只保留前7个数值和最后的TRIM
            # 例如：Pseudo-Voigt -0.049561 0.031393 0.017370 0.391327 5000 5000 TRIM
            # 只允许编辑这7个数值，TRIM保持不变
            # 如果TRIM被误删，也自动补上
            vals = values[:7]
            # 检查原行是否有TRIM
            orig_line = self.lines[line_idx].rstrip('\n')
            has_trim = orig_line.strip().endswith('TRIM')
            new_line = 'Pseudo-Voigt ' + ' '.join(vals)
            if has_trim or (len(values) > 7 and values[7].upper() == 'TRIM'):
                new_line += ' TRIM'
            else:
                new_line += ' TRIM'
            new_line += '\n'
            indentation = len(self.lines[line_idx]) - len(self.lines[line_idx].lstrip())
            self.lines[line_idx] = ' ' * indentation + new_line
            param_data['values'] = vals + ['TRIM']
            return

        # 对于 TRANSITIONS 下的 LT 和 FW，只更新本行，不动下方内容，并自动删除多余的“0”行
        if section == 'TRANSITIONS' and param_key in ('LT', 'FW'):
            # 更新本行
            new_line = param_key + ' ' + ' '.join(values) + '\n'
            indentation = len(self.lines[line_idx]) - len(self.lines[line_idx].lstrip())
            self.lines[line_idx] = ' ' * indentation + new_line
            param_data['values'] = values
            # 检查下一行是否为单独的“0”，如果是则删除
            next_idx = line_idx + 1
            if next_idx < len(self.lines):
                next_line = self.lines[next_idx].strip()
                if next_line == '0':
                    del self.lines[next_idx]
                    # 删除后需要修正所有行号索引
                    self._shift_line_indices(next_idx, -1)
            return

        # 其他参数的处理逻辑保持不变
        # 第二行写回逻辑（value_idx == 1 表示 second line）
        if value_idx == 1:
            if 'extra_line_idx' in param_data:
                extra_idx = param_data['extra_line_idx']
                indentation = len(self.lines[extra_idx]) - len(self.lines[extra_idx].lstrip())
                self.lines[extra_idx] = ' ' * indentation + new_value + '\n'
                param_data['extra_value'] = new_value
            else:
                insert_at = line_idx + 1
                indentation = len(self.lines[line_idx]) - len(self.lines[line_idx].lstrip())
                self.lines.insert(insert_at, ' ' * indentation + new_value + '\n')
                param_data['extra_line_idx'] = insert_at
                param_data['extra_value'] = new_value
                self._shift_line_indices(insert_at, 1)
            param_data['values'] = values
            return

        param_data['values'] = values
        if param_data.get('solo', False):
            new_line = ' '.join(values) + '\n'
        else:
            new_line = (param_key + ' ' if param_key else '') + ' '.join(values) + '\n'
        indentation = len(self.lines[line_idx]) - len(self.lines[line_idx].lstrip())
        self.lines[line_idx] = ' ' * indentation + new_line
        param_data['values'] = values

    def _shift_line_indices(self, insert_at: int, delta: int):
        for sec_name, sec in self.sections.items():
            if 'start' in sec and sec['start'] >= insert_at:
                sec['start'] += delta
            for pkey, pdata in sec.get('params', {}).items():
                if 'line_idx' in pdata and pdata['line_idx'] >= insert_at:
                    pdata['line_idx'] += delta
                if 'extra_line_idx' in pdata and pdata['extra_line_idx'] >= insert_at:
                    pdata['extra_line_idx'] += delta
            for subname, sub in sec.get('subsections', {}).items():
                if 'start' in sub and sub['start'] >= insert_at:
                    sub['start'] += delta
                for pk, pd in sub.get('params', {}).items():
                    if 'line_idx' in pd and pd['line_idx'] >= insert_at:
                        pd['line_idx'] += delta
                    if 'extra_line_idx' in pd and pd['extra_line_idx'] >= insert_at:
                        pd['extra_line_idx'] += delta

    def write_flts_file(self):
        with open(self.flts_path, 'w') as f:
            f.writelines(self.lines)

def run_faults(flts_path: str):
    dir_path = os.path.dirname(flts_path)
    flts_file = os.path.basename(flts_path)
    original_dir = os.getcwd()
    try:
        if dir_path:
            os.chdir(dir_path)
        else:
            dir_path = original_dir
        subprocess.run(['Faults', flts_file], input='\n', text=True, check=True)
    finally:
        os.chdir(original_dir)

def read_dat_file(dat_path: str) -> Tuple[np.ndarray, np.ndarray]:
    abs_dat_path = os.path.abspath(dat_path)
    with open(abs_dat_path, 'r') as f:
        lines = f.readlines()
    
    params = list(map(float, lines[1].strip().split()))
    start, step, _ = params
    intensities = []
    for line in lines[2:]:
        intensities.extend(map(float, line.strip().split()))
    
    num_points = len(intensities)
    two_theta = np.arange(start, start + num_points * step, step)
    
    return two_theta, np.array(intensities)

class GUI(QtWidgets.QMainWindow):
    def __init__(self, parser: FLTSParser, flts_path: str, dat_path: str):
        super().__init__()
        font = QtGui.QFont("微软雅黑", 12)
        QtWidgets.QApplication.instance().setFont(font)

        self.parser = parser
        self.flts_path = flts_path
        self.dat_path = dat_path
        self.setWindowTitle("Magia_faults_GUI - programmed by WWWYJ")
        self.setStyleSheet("background-color: #333333; color: white;")
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0; }
            QTabBar::tab { background: #555555; color: white; padding: 8px; }
            QTabBar::tab:selected { background: #333333; color: white; }
            QWidget { background: #333333; color: white; }
        """)
        self.layout.addWidget(self.tabs)

        self.entries = {}

        self.create_title_instrumental_tab()
        self.create_structural_tab()
        self.create_stacking_transitions_tab()
        self.create_calculation_tab()

        self.run_button = QtWidgets.QPushButton("Apply & Run")
        self.run_button.setStyleSheet("background-color: #555555; color: white;")
        self.run_button.clicked.connect(self.apply_and_run)
        self.layout.addWidget(self.run_button)

    def create_calculation_tab(self):
        tab = QtWidgets.QWidget()
        vlay = QtWidgets.QVBoxLayout(tab)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        form = QtWidgets.QGridLayout(inner)
        scroll.setWidget(inner)
        vlay.addWidget(scroll)

        row = 0
        calc_section = self.parser.sections.get('SIMULATION', {}).get('params', {})
        powder = calc_section.get('POWDER')
        if powder:
            label = QtWidgets.QLabel("POWDER (2theta_min, 2theta_max, step)")
            label.setStyleSheet("font-weight:bold; color:white;")
            form.addWidget(label, row, 0, 1, 4)
            row += 1
            for i in range(3):
                e = QtWidgets.QLineEdit(powder['values'][i])
                e.setStyleSheet("background-color: #555555; color: white;")
                e.editingFinished.connect(self.make_update_param('SIMULATION', None, 'POWDER', i, e))
                form.addWidget(QtWidgets.QLabel(['2theta_min','2theta_max','step'][i]), row, 0)
                form.addWidget(e, row, 1)
                self.entries[('SIMULATION', None, 'POWDER', i)] = e
                row += 1
            for i in range(3, len(powder['values'])):
                e = QtWidgets.QLineEdit(powder['values'][i])
                e.setReadOnly(True)
                e.setStyleSheet("background-color: #444444; color: #bbbbbb;")
                form.addWidget(QtWidgets.QLabel(f"参数{i+1}"), row, 0)
                form.addWidget(e, row, 1)
                row += 1

        self.tabs.addTab(tab, "CALCULATION")

    def create_title_instrumental_tab(self):
        tab = QtWidgets.QWidget()
        vlay = QtWidgets.QVBoxLayout(tab)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        form = QtWidgets.QGridLayout(inner)
        scroll.setWidget(inner)
        vlay.addWidget(scroll)

        row = 0
        title_section = self.parser.sections.get('TITLE', {})
        if 'params' in title_section and 'Title_Text' in title_section['params']:
            label = QtWidgets.QLabel("TITLE")
            label.setStyleSheet("font-weight:bold; color: white;")
            form.addWidget(label, row, 0, 1, 4)
            row += 1
            tt = title_section['params']['Title_Text']
            entry = QtWidgets.QLineEdit(tt['values'][0])
            entry.setStyleSheet("background-color: #555555; color: white;")
            entry.editingFinished.connect(self.make_update_param('TITLE', None, 'Title_Text', 0, entry))
            form.addWidget(entry, row, 0, 1, 4)
            self.entries[('TITLE', None, 'Title_Text', 0)] = entry
            row += 1

        instr = self.parser.sections.get('INSTRUMENTAL AND SIZE BROADENING', {}).get('params', {})
        if instr:
            label = QtWidgets.QLabel("INSTRUMENTAL AND SIZE BROADENING")
            label.setStyleSheet("font-weight:bold; color: white;")
            form.addWidget(label, row, 0, 1, 6)
            row += 1

            if 'Wavelength' in instr:
                hdr = QtWidgets.QLabel("lambda1    lambda2    ratio")
                hdr.setStyleSheet("color: white;")
                form.addWidget(hdr, row, 1, 1, 3)
                row += 1
                param = instr['Wavelength']
                form.addWidget(QtWidgets.QLabel("Wavelength"), row, 0)
                for i, val in enumerate(param['values']):
                    e = QtWidgets.QLineEdit(val)
                    e.setStyleSheet("background-color: #555555; color: white;")
                    e.editingFinished.connect(self.make_update_param('INSTRUMENTAL AND SIZE BROADENING', None, 'Wavelength', i, e))
                    form.addWidget(e, row, i + 1)
                    self.entries[('INSTRUMENTAL AND SIZE BROADENING', None, 'Wavelength', i)] = e
                row += 1

            if 'Aberrations' in instr:
                hdr = QtWidgets.QLabel("zero    sycos    sysin")
                hdr.setStyleSheet("color: white;")
                form.addWidget(hdr, row, 1, 1, 3)
                row += 1
                param = instr['Aberrations']
                form.addWidget(QtWidgets.QLabel("Aberrations"), row, 0)
                for i, val in enumerate(param['values']):
                    e = QtWidgets.QLineEdit(val)
                    e.setStyleSheet("background-color: #555555; color: white;")
                    e.editingFinished.connect(self.make_update_param('INSTRUMENTAL AND SIZE BROADENING', None, 'Aberrations', i, e))
                    form.addWidget(e, row, i + 1)
                    self.entries[('INSTRUMENTAL AND SIZE BROADENING', None, 'Aberrations', i)] = e
                row += 1

            if 'Pseudo-Voigt' in instr:
                hdr = QtWidgets.QLabel("u    v    w    x    Dg    Dl")
                hdr.setStyleSheet("color: white;")
                form.addWidget(hdr, row, 1, 1, 6)
                row += 1
                param = instr['Pseudo-Voigt']
                form.addWidget(QtWidgets.QLabel("Pseudo-Voigt"), row, 0)
                for i, val in enumerate(param['values']):
                    e = QtWidgets.QLineEdit(val)
                    e.setStyleSheet("background-color: #555555; color: white;")
                    e.editingFinished.connect(self.make_update_param('INSTRUMENTAL AND SIZE BROADENING', None, 'Pseudo-Voigt', i, e))
                    form.addWidget(e, row, i + 1)
                    self.entries[('INSTRUMENTAL AND SIZE BROADENING', None, 'Pseudo-Voigt', i)] = e
                row += 1

        self.tabs.addTab(tab, "TITLE AND INSTRUMENTAL")

    def create_structural_tab(self):
        tab = QtWidgets.QWidget()
        vlay = QtWidgets.QVBoxLayout(tab)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        form = QtWidgets.QGridLayout(inner)
        scroll.setWidget(inner)
        vlay.addWidget(scroll)

        row = 0
        struct = self.parser.sections.get('STRUCTURAL', {})
        params = struct.get('params', {})
        structural_keys = ['Avercell', 'SPGR', 'Cell', 'Symm', 'NLAYERS', 'Lwidth']
        for key in structural_keys:
            if key in params:
                group_box = QtWidgets.QGroupBox(key)
                group_box.setStyleSheet("color:white; font-weight:bold;")
                group_layout = QtWidgets.QVBoxLayout(group_box)

                top_row = QtWidgets.QWidget()
                top_layout = QtWidgets.QHBoxLayout(top_row)
                for i, val in enumerate(params[key]['values']):
                    e = QtWidgets.QLineEdit(val)
                    e.setStyleSheet("background-color: #555555; color: white;")
                    e.editingFinished.connect(self.make_update_param('STRUCTURAL', None, key, i, e))
                    top_layout.addWidget(e)
                    self.entries[('STRUCTURAL', None, key, i)] = e
                group_layout.addWidget(top_row)

                # CHANGED: 取消在 STRUCTURAL 中为 NLAYERS 添加第二行（用户要求）
                # 仅为 Lwidth 保留第二行
                if key == 'Lwidth':
                    second_row = QtWidgets.QWidget()
                    second_layout = QtWidgets.QHBoxLayout(second_row)
                    hint = QtWidgets.QLabel("(second line / extra)")
                    hint.setStyleSheet("color: #bbbbbb;")
                    hint.setFixedWidth(120)
                    second_layout.addWidget(hint)
                    extra_text = params[key].get('extra_value', '')
                    e2 = QtWidgets.QLineEdit(extra_text)
                    e2.setStyleSheet("background-color: #555555; color: white;")
                    e2.editingFinished.connect(self.make_update_param('STRUCTURAL', None, key, 1, e2))
                    second_layout.addWidget(e2)
                    group_layout.addWidget(second_row)
                    self.entries[('STRUCTURAL', None, key, 1)] = e2

                form.addWidget(group_box, row, 0, 1, 6)
                row += 1

        subs = struct.get('subsections', {})
        for subsection, subdata in subs.items():
            hdr = QtWidgets.QLabel(subsection)
            hdr.setStyleSheet("font-weight:bold; color:white;")
            form.addWidget(hdr, row, 0, 1, 6)
            row += 1
            atom_header = QtWidgets.QLabel("name    number    x    y    z    Biso    Occ")
            atom_header.setStyleSheet("color: white;")
            form.addWidget(atom_header, row, 0, 1, 6)
            row += 1
            params = subdata.get('params', {})
            if 'LSYM' in params:
                form.addWidget(QtWidgets.QLabel("LSYM"), row, 0)
                for i, val in enumerate(params['LSYM']['values']):
                    e = QtWidgets.QLineEdit(val)
                    e.setStyleSheet("background-color: #555555; color: white;")
                    e.editingFinished.connect(self.make_update_param('STRUCTURAL', subsection, 'LSYM', i, e))
                    form.addWidget(e, row, i + 1)
                    self.entries[('STRUCTURAL', subsection, 'LSYM', i)] = e
                row += 1
            for param_key, param_data in params.items():
                if param_key.startswith('Atom_'):
                    parts = param_data['values']
                    label = QtWidgets.QLabel(param_key)
                    label.setStyleSheet("color: white;")
                    form.addWidget(label, row, 0)
                    for i, val in enumerate(parts):
                        e = QtWidgets.QLineEdit(val)
                        e.setStyleSheet("background-color: #555555; color: white;")
                        e.editingFinished.connect(self.make_update_param('STRUCTURAL', subsection, param_key, i, e))
                        form.addWidget(e, row, i + 1)
                        self.entries[('STRUCTURAL', subsection, param_key, i)] = e
                    row += 1

        self.tabs.addTab(tab, "STRUCTURAL")

    def create_stacking_transitions_tab(self):
        tab = QtWidgets.QWidget()
        vlay = QtWidgets.QVBoxLayout(tab)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        form = QtWidgets.QGridLayout(inner)
        scroll.setWidget(inner)
        vlay.addWidget(scroll)

        row = 0
        stacking_section = self.parser.sections.get('STACKING', {}).get('params', {})
        form.addWidget(QtWidgets.QLabel("STACKING"), row, 0, 1, 6)
        form.itemAtPosition(row,0).widget().setStyleSheet("font-weight:bold; color:white;")
        row += 1

        # RECURSIVE display (if exists)
        if 'RECURSIVE' in stacking_section:
            form.addWidget(QtWidgets.QLabel("stacking type"), row, 0)
            for i, val in enumerate(stacking_section['RECURSIVE']['values']):
                e = QtWidgets.QLineEdit(val)
                e.setStyleSheet("background-color: #555555; color: white;")
                e.editingFinished.connect(self.make_update_param('STACKING', None, 'RECURSIVE', i, e))
                form.addWidget(e, row, i + 1)
                self.entries[('STACKING', None, 'RECURSIVE', i)] = e
            if 'extra_value' in stacking_section['RECURSIVE']:
                row += 1
                e2 = QtWidgets.QLineEdit(stacking_section['RECURSIVE'].get('extra_value',''))
                e2.setStyleSheet("background-color: #555555; color: white;")
                e2.editingFinished.connect(self.make_update_param('STACKING', None, 'RECURSIVE', 1, e2))
                form.addWidget(QtWidgets.QLabel("(extra)"), row, 0)
                form.addWidget(e2, row, 1, 1, 3)
                self.entries[('STACKING', None, 'RECURSIVE', 1)] = e2
            row += 1

        # INFINITE (number of layers) - CHANGED: ensure it shows two rows (first-line value(s) + second-line input)
        if 'INFINITE' in stacking_section:
            form.addWidget(QtWidgets.QLabel("number of layers"), row, 0)
            # first line values (typical is a single number like 1000)
            for i, val in enumerate(stacking_section['INFINITE']['values']):
                e = QtWidgets.QLineEdit(val)
                e.setStyleSheet("background-color: #555555; color: white;")
                e.editingFinished.connect(self.make_update_param('STACKING', None, 'INFINITE', i, e))
                form.addWidget(e, row, i + 1)
                self.entries[('STACKING', None, 'INFINITE', i)] = e
            row += 1
            # always show a second-line input (empty if no extra_value present)
            extra_inf = stacking_section['INFINITE'].get('extra_value', '')
            e_inf2 = QtWidgets.QLineEdit(extra_inf)
            e_inf2.setStyleSheet("background-color: #555555; color: white;")
            e_inf2.editingFinished.connect(self.make_update_param('STACKING', None, 'INFINITE', 1, e_inf2))
            form.addWidget(QtWidgets.QLabel("(second line / extra)"), row, 0)
            form.addWidget(e_inf2, row, 1, 1, 4)
            self.entries[('STACKING', None, 'INFINITE', 1)] = e_inf2
            row += 1

        trans_section = self.parser.sections.get('TRANSITIONS', {})
        subs = trans_section.get('subsections', {})

        form.addWidget(QtWidgets.QLabel("TRANSITIONS"), row, 0, 1, 8)
        form.itemAtPosition(row,0).widget().setStyleSheet("font-weight:bold; color:white;")
        row += 1

        fw_box = QtWidgets.QGroupBox("Global FW (apply to all FW entries)")
        fw_layout = QtWidgets.QHBoxLayout(fw_box)
        self.global_fw_edits = []
        first_fw_vals = None
        for sname, sdata in subs.items():
            if 'FW' in sdata.get('params', {}):
                first_fw_vals = sdata['params']['FW']['values']
                break
        if first_fw_vals is None:
            first_fw_vals = ['0.00'] * 6
        for i in range(6):
            e = QtWidgets.QLineEdit(first_fw_vals[i] if i < len(first_fw_vals) else '0.00')
            e.setFixedWidth(80)
            e.setStyleSheet("background-color: #666666; color: white;")
            fw_layout.addWidget(e)
            self.global_fw_edits.append(e)
        apply_btn = QtWidgets.QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_global_fw)
        fw_layout.addWidget(apply_btn)
        form.addWidget(fw_box, row, 0, 1, 8)
        row += 1

        for subsection, subdata in subs.items():
            lbl = QtWidgets.QLabel(subsection)
            lbl.setStyleSheet("font-weight:bold; color:white;")
            form.addWidget(lbl, row, 0, 1, 8)
            row += 1
            params = subdata.get('params', {})
            if 'LT' in params:
                form.addWidget(QtWidgets.QLabel("LT"), row, 0)
                for i, val in enumerate(params['LT']['values']):
                    e = QtWidgets.QLineEdit(val)
                    try:
                        is_non_zero = float(val) != 0.0
                    except Exception:
                        is_non_zero = False
                    if is_non_zero:
                        e.setStyleSheet("background-color: #555555; color: red; font-weight: bold;")
                    else:
                        e.setStyleSheet("background-color: #555555; color: white;")
                    e.editingFinished.connect(self.make_update_param('TRANSITIONS', subsection, 'LT', i, e))
                    form.addWidget(e, row, i + 1)
                    self.entries[('TRANSITIONS', subsection, 'LT', i)] = e
                row += 1
            if 'FW' in params:
                form.addWidget(QtWidgets.QLabel("FW"), row, 0)
                for i, val in enumerate(params['FW']['values']):
                    e = QtWidgets.QLineEdit(val)
                    try:
                        is_non_zero = float(val) != 0.0
                    except Exception:
                        is_non_zero = False
                    if is_non_zero:
                        e.setStyleSheet("background-color: #555555; color: red; font-weight: bold;")
                    else:
                        e.setStyleSheet("background-color: #555555; color: white;")
                    e.editingFinished.connect(self.make_update_param('TRANSITIONS', subsection, 'FW', i, e))
                    form.addWidget(e, row, i + 1)
                    self.entries[('TRANSITIONS', subsection, 'FW', i)] = e
                row += 1

        self.tabs.addTab(tab, "STACKING AND TRANSITIONS")

    def apply_global_fw(self):
        vals = [e.text() for e in self.global_fw_edits]
        trans = self.parser.sections.get('TRANSITIONS', {})
        subs = trans.get('subsections', {})
        for subsection, sdata in subs.items():
            params = sdata.get('params', {})
            if 'FW' in params:
                fw_param = params['FW']
                line_idx = fw_param['line_idx']
                # 只更新FW这一行，不动下方的内容
                new_line = 'FW ' + ' '.join(vals) + '\n'
                indentation = len(self.parser.lines[line_idx]) - len(self.parser.lines[line_idx].lstrip())
                self.parser.lines[line_idx] = ' ' * indentation + new_line
                fw_param['values'] = vals
                # 更新界面显示
                for i in range(len(vals)):
                    ent = self.entries.get(('TRANSITIONS', subsection, 'FW', i))
                    if ent:
                        ent.setText(vals[i])
                        try:
                            is_non_zero = float(vals[i]) != 0.0
                        except Exception:
                            is_non_zero = False
                        if is_non_zero:
                            ent.setStyleSheet("background-color: #555555; color: red; font-weight: bold;")
                        else:
                            ent.setStyleSheet("background-color: #555555; color: white;")
        QtWidgets.QMessageBox.information(self, "完成", "已将全局 FW 应用到所有 TRANSITIONS 的 FW 条目。")

    def make_update_param(self, section, subsection, param_key, value_idx, entry):
        def handler():
            new_val = entry.text()
            self.parser.update_parameter(section, subsection, param_key, value_idx, new_val)
            if section == 'TRANSITIONS':
                try:
                    is_non_zero = float(new_val) != 0.0
                except Exception:
                    is_non_zero = False
                if is_non_zero:
                    entry.setStyleSheet("background-color: #555555; color: red; font-weight: bold;")
                else:
                    entry.setStyleSheet("background-color: #555555; color: white; font-weight: normal;")
        return handler

    def apply_and_run(self):
        self.parser.write_flts_file()
        run_faults(self.flts_path)
        dat_files = glob.glob(os.path.join(os.path.dirname(self.flts_path), '*.dat'))
        if not dat_files:
            QtWidgets.QMessageBox.critical(self, "错误", "未找到任何dat文件！")
            return
        latest_dat = max(dat_files, key=os.path.getmtime)
        two_theta, intensities = read_dat_file(latest_dat)
        import matplotlib.pyplot as plt
        plt.figure(facecolor='#333333')
        ax = plt.gca()
        ax.set_facecolor('#333333')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.yaxis.label.set_color('white')
        ax.xaxis.label.set_color('white')
        ax.title.set_color('white')
        plt.plot(two_theta, intensities, color='cyan')
        plt.xlabel('2θ')
        plt.ylabel('Intensity')
        plt.title('Simulated Spectrum')
        plt.grid(True, color='gray')
        plt.show()

def main():
    flts_path = 'Li3YCl6_8layers.flts'  # Replace if needed
    dat_path = 'Li3YCl6_Model1_6.dat'  # Replace if needed
    parser = FLTSParser(flts_path)
    app = QtWidgets.QApplication(sys.argv)
    gui = GUI(parser, parser.flts_path, dat_path)
    gui.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
