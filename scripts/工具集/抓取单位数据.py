#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取所有单位数据脚本
遍历所有.ini文件，提取单位的全部属性并计算战力
排除HP、护盾、伤害量都为0的单位
"""

import os
import re
from pathlib import Path
from collections import defaultdict


def parse_ini_file(filepath):
    """解析单个ini文件，提取单位完整数据"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"读取文件失败 {filepath}: {e}")
        return None

    data = {
        'file_path': str(filepath),
        'name': '',
        'max_hp': '0',
        'attack_range': '0',
        'move_speed': '0',
        'tags': '',
        'shield': '0',
        'damage': '0',
        'air_damage': '0',
        'category': '其他'
    }

    # 提取name
    name_match = re.search(r'^name[:：]\s*(.+)$', content, re.MULTILINE)
    if name_match:
        data['name'] = name_match.group(1).strip()
    else:
        return None

    # 提取生命值
    hp_match = re.search(r'^(?:生命值|maxHp)[:：]\s*(\d+)', content, re.MULTILINE | re.IGNORECASE)
    if hp_match:
        data['max_hp'] = hp_match.group(1)

    # 提取护盾值
    shield_match = re.search(r'^(?:护盾|护盾值|shield)[:：]\s*(\d+)', content, re.MULTILINE | re.IGNORECASE)
    if shield_match:
        data['shield'] = shield_match.group(1)

    # 提取攻击范围
    attack_section = re.search(r'\[攻击\](.*?)(?=\[|\Z)', content, re.DOTALL | re.IGNORECASE)
    if attack_section:
        attack_content = attack_section.group(1)
        range_match = re.search(r'^(?:攻击距离|maxAttackRange)[:：]\s*(\d+)', attack_content, re.MULTILINE | re.IGNORECASE)
        if range_match:
            data['attack_range'] = range_match.group(1)

    # 提取移动速度
    move_section = re.search(r'\[运动\](.*?)(?=\[|\Z)', content, re.DOTALL | re.IGNORECASE)
    if move_section:
        move_content = move_section.group(1)
        speed_match = re.search(r'^(?:移动速度|moveSpeed)[:：]\s*([\d.]+)', move_content, re.MULTILINE | re.IGNORECASE)
        if speed_match:
            data['move_speed'] = speed_match.group(1)

    # 提取标签
    tags_match = re.search(r'^tags[:：]\s*(.+)$', content, re.MULTILINE)
    if tags_match:
        data['tags'] = tags_match.group(1).strip()

    # 提取对地伤害量（优先匹配"对地伤害量"，如果没有则匹配单独的"伤害量"）
    # 使用负向前瞻来避免匹配"对空伤害量"
    damage_match = re.search(r'(?:对地伤害量|directDamage|(?<!对空)伤害量)[:=]\s*-?(\d+)', content, re.IGNORECASE)
    if damage_match:
        data['damage'] = damage_match.group(1)

    # 提取对空伤害量
    air_damage_match = re.search(r'(?:对空伤害量|airDamage)[:=]\s*-?(\d+)', content, re.IGNORECASE)
    if air_damage_match:
        data['air_damage'] = air_damage_match.group(1)

    # 判断分类
    tags = data['tags'].lower()
    filepath_lower = str(filepath).lower()
    if '建筑' in tags or 'building' in tags:
        data['category'] = '建筑'
    elif '海' in tags or 'naval' in tags or 'sea' in filepath_lower:
        data['category'] = '海军'
    elif '空' in tags or 'air' in tags or 'fly' in filepath_lower:
        data['category'] = '空军'
    elif '地' in tags or 'land' in tags or '陆军' in filepath_lower:
        data['category'] = '陆军'
    else:
        data['category'] = '其他'

    return data


def is_valid_unit(unit):
    """检查单位是否有效（HP、护盾、伤害量都大于0）"""
    try:
        hp = float(unit['max_hp']) if unit['max_hp'] else 0
        shield = float(unit['shield']) if unit['shield'] else 0
        damage = float(unit['damage']) if unit['damage'] else 0
        # 排除HP、护盾、伤害量都为0的单位
        return not (hp == 0 and shield == 0 and damage == 0)
    except:
        return False


def calculate_power(unit):
    """计算战力（完整公式）"""
    try:
        hp = float(unit['max_hp']) if unit['max_hp'] else 0
        shield = float(unit['shield']) if unit['shield'] else 0
        attack_range = float(unit['attack_range']) if unit['attack_range'] else 0
        move_speed = float(unit['move_speed']) if unit['move_speed'] else 0
        damage = float(unit['damage']) if unit['damage'] else 0
        air_damage = float(unit['air_damage']) if unit['air_damage'] else 0

        # 战力公式
        # A = max(攻击范围×0.55, 100)
        A = max(attack_range * 0.55, 100)
        # B = A × 伤害量 × 0.012
        B = A * damage * 0.012
        # C = (最大血量+护盾×1.2) × 1.44 × (移速×0.2+0.8)
        C = (hp + shield * 1.2) * 1.44 * (move_speed * 0.2 + 0.8)
        # Y = (B + C) × 0.012
        Y = (B + C) * 0.012
        # 战力 = int(max(Y, 1))
        ground_power = int(max(Y, 1))

        # 对空战力
        if air_damage > 0:
            B_air = A * air_damage * 0.012
            Y_air = (B_air + C) * 0.012
            air_power = int(max(Y_air, 1))
        else:
            air_power = 0

        return ground_power, air_power
    except:
        return 0, 0


def scan_all_units(base_path):
    """扫描所有单位文件"""
    base_path = Path(base_path)
    all_units = []

    scan_dirs = [
        '作战单位',
        '建筑',
        '建造单位',
        '空中单位',
        '定制单位',
        '机制/开局/辉光'
    ]

    for dir_name in scan_dirs:
        target_dir = base_path / dir_name
        if not target_dir.exists():
            continue

        print(f"扫描目录: {dir_name}")

        for ini_file in target_dir.rglob('*.ini'):
            if '模块' in ini_file.name:
                continue

            data = parse_ini_file(ini_file)
            if data and is_valid_unit(data):
                # 计算战力
                ground_power, air_power = calculate_power(data)
                data['ground_power'] = ground_power
                data['air_power'] = air_power
                all_units.append(data)

    return all_units


def pad_string(s, width, align='left'):
    """统一字符串格式化，处理中英文宽度"""
    s = str(s)
    cn_chars = sum(1 for c in s if ord(c) > 127)
    real_len = len(s) + cn_chars
    if align == 'left':
        return s + ' ' * max(0, width - real_len)
    else:
        return ' ' * max(0, width - real_len) + s


def generate_report(units, output_path):
    """生成分类报告"""
    categories = defaultdict(list)
    for unit in units:
        categories[unit['category']].append(unit)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("╔" + "=" * 98 + "╗\n")
        f.write("║" + " " * 40 + "单位战力计算报告" + " " * 42 + "║\n")
        f.write("╚" + "=" * 98 + "╝\n\n")

        # 公式说明
        f.write("【战力计算公式】\n")
        f.write("  基础战力 = (max(攻击范围×0.55, 100) × 伤害量 × 0.012 + (血量+护盾×1.2) × 1.44 × (移速×0.2+0.8)) × 0.012\n")
        f.write("  对空战力 = (max(攻击范围×0.55, 100) × 对空伤害量 × 0.012 + (血量+护盾×1.2) × 1.44 × (移速×0.2+0.8)) × 0.012\n")
        f.write("  排除条件: HP、护盾、伤害量 都为0的单位\n\n")

        # 总览表格
        f.write("┌──────────────┬──────────┐\n")
        f.write("│  统计分类    │  数量    │\n")
        f.write("├──────────────┼──────────┤\n")
        total = len(units)
        for category in ['陆军', '海军', '空军', '建筑', '其他']:
            if category in categories:
                count = len(categories[category])
                f.write(f"│  {pad_string(category + '单位', 8, 'left')}    │  {count:>4} 个 │\n")
        f.write("├──────────────┼──────────┤\n")
        f.write(f"│  {'合计':8}    │  {total:>4} 个 │\n")
        f.write("└──────────────┴──────────┘\n\n")

        # 定义列宽
        COL_WIDTHS = {
            'idx': 5,
            'name': 18,
            'hp': 8,
            'shield': 8,
            'damage': 8,
            'range': 8,
            'speed': 8,
            'ground': 10,
            'air': 10,
            'tags': 22
        }

        # 按分类输出
        for category in ['陆军', '海军', '空军', '建筑', '其他']:
            if category not in categories:
                continue

            cat_units = categories[category]

            f.write("┌" + "─" * 98 + "┐\n")
            f.write("│" + " " * 45 + f"【{category}单位】" + " " * (37 - len(category)) + "│\n")
            f.write("├" + "─" * 98 + "┤\n")

            header = (f"│{pad_string('序号', COL_WIDTHS['idx'], 'center')}│"
                     f"{pad_string('名称', COL_WIDTHS['name'], 'center')}│"
                     f"{pad_string('血量', COL_WIDTHS['hp'], 'center')}│"
                     f"{pad_string('护盾', COL_WIDTHS['shield'], 'center')}│"
                     f"{pad_string('伤害', COL_WIDTHS['damage'], 'center')}│"
                     f"{pad_string('射程', COL_WIDTHS['range'], 'center')}│"
                     f"{pad_string('移速', COL_WIDTHS['speed'], 'center')}│"
                     f"{pad_string('对地战力', COL_WIDTHS['ground'], 'center')}│"
                     f"{pad_string('对空战力', COL_WIDTHS['air'], 'center')}│"
                     f"{pad_string('标签', COL_WIDTHS['tags'], 'center')}│")
            f.write(header + "\n")
            f.write("├" + "─" * 98 + "┤\n")

            cat_units_sorted = sorted(cat_units, key=lambda x: x['ground_power'], reverse=True)

            for idx, unit in enumerate(cat_units_sorted, 1):
                name_display = unit['name'][:9] if len(unit['name']) > 9 else unit['name']
                tags_display = unit['tags'][:11] if len(unit['tags']) > 11 else unit['tags']

                row = (f"│{pad_string(str(idx), COL_WIDTHS['idx'], 'right')}│"
                      f"{pad_string(name_display, COL_WIDTHS['name'], 'left')}│"
                      f"{pad_string(unit['max_hp'], COL_WIDTHS['hp'], 'right')}│"
                      f"{pad_string(unit['shield'], COL_WIDTHS['shield'], 'right')}│"
                      f"{pad_string(unit['damage'], COL_WIDTHS['damage'], 'right')}│"
                      f"{pad_string(unit['attack_range'], COL_WIDTHS['range'], 'right')}│"
                      f"{pad_string(unit['move_speed'], COL_WIDTHS['speed'], 'right')}│"
                      f"{pad_string(str(unit['ground_power']), COL_WIDTHS['ground'], 'right')}│"
                      f"{pad_string(str(unit['air_power']), COL_WIDTHS['air'], 'right')}│"
                      f"{pad_string(tags_display, COL_WIDTHS['tags'], 'left')}│")
                f.write(row + "\n")

            f.write("└" + "─" * 98 + "┘\n\n")

        # 战力排行榜
        f.write("┌" + "─" * 62 + "┐\n")
        f.write("│" + " " * 20 + "【战力排行榜 TOP 50】" + " " * 21 + "│\n")
        f.write("├" + "─" * 62 + "┤\n")

        rank_widths = {'rank': 5, 'name': 18, 'cat': 8, 'ground': 10, 'air': 10}
        rank_header = (f"│{pad_string('排名', rank_widths['rank'], 'center')}│"
                      f"{pad_string('名称', rank_widths['name'], 'center')}│"
                      f"{pad_string('分类', rank_widths['cat'], 'center')}│"
                      f"{pad_string('对地战力', rank_widths['ground'], 'center')}│"
                      f"{pad_string('对空战力', rank_widths['air'], 'center')}│")
        f.write(rank_header + "\n")
        f.write("├" + "─" * 62 + "┤\n")

        sorted_units = sorted(units, key=lambda x: x['ground_power'], reverse=True)

        for idx, unit in enumerate(sorted_units[:50], 1):
            name_display = unit['name'][:9] if len(unit['name']) > 9 else unit['name']
            row = (f"│{pad_string(str(idx), rank_widths['rank'], 'center')}│"
                  f"{pad_string(name_display, rank_widths['name'], 'left')}│"
                  f"{pad_string(unit['category'], rank_widths['cat'], 'center')}│"
                  f"{pad_string(str(unit['ground_power']), rank_widths['ground'], 'right')}│"
                  f"{pad_string(str(unit['air_power']), rank_widths['air'], 'right')}│")
            f.write(row + "\n")

        f.write("└" + "─" * 62 + "┘\n\n")
        f.write("报告生成完成 | 总计 " + str(len(units)) + " 个有效单位（已排除HP、护盾、伤害都为0的单位）\n")

    print(f"\n报告已保存到: {output_path}")


def main():
    script_dir = Path(__file__).parent
    # 脚本的父目录是 scripts，项目根目录是 scripts 的父目录
    base_path = script_dir.parent.parent

    print("开始抓取单位数据...")
    print(f"项目路径: {base_path}\n")
    print("正在扫描并过滤单位（排除HP、护盾、伤害都为0的单位）...\n")

    all_units = scan_all_units(base_path)

    print(f"\n=================================")
    print(f"共找到 {len(all_units)} 个有效单位")
    print(f"  陆军: {sum(1 for u in all_units if u['category'] == '陆军')} 个")
    print(f"  海军: {sum(1 for u in all_units if u['category'] == '海军')} 个")
    print(f"  空军: {sum(1 for u in all_units if u['category'] == '空军')} 个")
    print(f"  建筑: {sum(1 for u in all_units if u['category'] == '建筑')} 个")
    print(f"  其他: {sum(1 for u in all_units if u['category'] == '其他')} 个")
    print(f"=================================\n")

    # CSV格式
    csv_file = script_dir.parent / '数据集' / '单位战力数据.csv'
    with open(csv_file, 'w', encoding='utf-8-sig') as f:
        f.write("名称,分类,血量,护盾,攻击范围,移速,伤害量,对空伤害量,对地战力,对空战力,标签,文件路径\n")
        for unit in all_units:
            f.write(f"{unit['name']},{unit['category']},{unit['max_hp']},{unit['shield']},"
                   f"{unit['attack_range']},{unit['move_speed']},{unit['damage']},{unit['air_damage']},"
                   f"{unit['ground_power']},{unit['air_power']},"
                   f"\"{unit['tags']}\",\"{unit['file_path']}\"\n")

    print(f"CSV数据已保存到: {csv_file}")


if __name__ == '__main__':
    main()