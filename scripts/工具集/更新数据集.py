#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据单位战力数据.csv生成完整的全单位数据集.txt
"""

import csv
from pathlib import Path

def calculate_power(hp, shield, attack_range, move_speed, damage):
    """计算战力"""
    if damage == 0:
        # 无攻击力单位只计算生存力
        C = (hp + shield * 1.2) * 1.44 * (move_speed * 0.2 + 0.8)
        Y = C * 0.012
        return max(int(Y), 1)
    
    A = max(attack_range * 0.55, 100)
    B = A * damage * 0.012
    C = (hp + shield * 1.2) * 1.44 * (move_speed * 0.2 + 0.8)
    Y = (B + C) * 0.012
    return max(int(Y), 1)


def get_combat_level(power):
    """根据战力获取作战等级 C1-C10"""
    if power >= 250:
        return 'C10'
    elif power >= 200:
        return 'C9'
    elif power >= 150:
        return 'C8'
    elif power >= 120:
        return 'C7'
    elif power >= 100:
        return 'C6'
    elif power >= 80:
        return 'C5'
    elif power >= 50:
        return 'C4'
    elif power >= 30:
        return 'C3'
    elif power >= 20:
        return 'C2'
    elif power >= 10:
        return 'C1'
    else:
        return 'C1'  # 战力低于10的也归为C1

def main():
    # 读取CSV
    csv_path = Path('scripts/数据集/单位战力数据.csv')
    if not csv_path.exists():
        print(f"错误: 找不到 {csv_path}")
        return
    
    units = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            unit = {
                'name': row['名称'],
                'category': row['分类'],
                'hp': int(row['血量']) if row['血量'] else 0,
                'shield': int(row['护盾']) if row['护盾'] else 0,
                'range': int(row['攻击范围']) if row['攻击范围'] else 0,
                'speed': float(row['移速']) if row['移速'] else 0,
                'damage': int(row['伤害量']) if row['伤害量'] else 0,
                'air_damage': int(row['对空伤害量']) if row['对空伤害量'] else 0,
                'ground_power': int(row['对地战力']) if row['对地战力'] else 0,
                'air_power': int(row['对空战力']) if row['对空战力'] else 0,
                'tags': row['标签'],
            }
            units.append(unit)
    
    # 按分类分组
    categories = {}
    for unit in units:
        cat = unit['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(unit)
    
    # 生成报告
    lines = []
    lines.append("=" * 80)
    lines.append("                           完整战力计算报告")
    lines.append("=" * 80)
    lines.append("")
    lines.append("【公式说明】")
    lines.append("  基础战力 = (max(攻击范围×0.55, 100) × 伤害量 × 0.012 + (血量+护盾×1.2) × 1.44 × (移速×0.2+0.8)) × 0.012")
    lines.append("  对空战力 = (max(攻击范围×0.55, 100) × 对空伤害量 × 0.012 + (血量+护盾×1.2) × 1.44 × (移速×0.2+0.8)) × 0.012")
    lines.append("")
    
    # 按分类输出
    category_names = {
        '陆军': '陆军单位',
        '海军': '海军单位',
        '空军': '空军单位',
        '建筑': '建筑物',
        '其他': '其他单位'
    }
    
    idx = 1
    for cat_key, cat_name in category_names.items():
        if cat_key not in categories:
            continue
        
        lines.append("=" * 80)
        lines.append(f"                          {cat_name}")
        lines.append("=" * 80)
        lines.append("")
        
        # 按战力排序
        cat_units = sorted(categories[cat_key], key=lambda x: x['ground_power'], reverse=True)
        
        for unit in cat_units:
            # 如果有"对地"标签，添加C等级
            tags = unit['tags']
            if '对地' in tags:
                level = get_combat_level(unit['ground_power'])
                # 检查是否已有C标签，如果有则不再添加，只保留第一个
                existing_c_tag = None
                for c_level in ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10']:
                    if c_level in tags:
                        existing_c_tag = c_level
                        break
                if existing_c_tag is None:  # 没有C标签时才添加
                    tags = f"{tags}, {level}" if tags else level
            
            lines.append(f"【{idx}. {unit['name']}】")
            if cat_key == '建筑':
                lines.append(f"  - 伤害量: {unit['damage']} | 血量: {unit['hp']} | 攻击范围: {unit['range']}")
            else:
                lines.append(f"  - 伤害量: {unit['damage']} | 血量: {unit['hp']} | 护盾: {unit['shield']} | 攻击范围: {unit['range']} | 移速: {unit['speed']}")
            lines.append(f"  - 标签: {tags};")
            if unit['air_damage'] > 0:
                lines.append(f"  对地战力: {unit['ground_power']} | 对空战力: {unit['air_power']}")
            else:
                lines.append(f"  战力: {unit['ground_power']}")
            lines.append("")
            idx += 1
    
    # 战力排行榜
    lines.append("=" * 80)
    lines.append("                          完整战力排名")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"{'排名':<8}{'单位名称':<20}{'分类':<10}{'伤害':<8}{'血量':<8}{'战力':<8}")
    lines.append("-" * 80)
    
    all_units = sorted(units, key=lambda x: x['ground_power'], reverse=True)
    for rank, unit in enumerate(all_units[:50], 1):
        lines.append(f"{rank:<8}{unit['name']:<20}{unit['category']:<10}{unit['damage']:<8}{unit['hp']:<8}{unit['ground_power']:<8}")
    
    lines.append("")
    lines.append("=" * 80)
    lines.append("                              统计汇总")
    lines.append("=" * 80)
    lines.append("")
    
    for cat_key, cat_name in category_names.items():
        if cat_key in categories:
            count = len(categories[cat_key])
            lines.append(f"{cat_name}: {count}个")
    
    lines.append("")
    lines.append(f"总计: {len(units)}个单位")
    lines.append("")
    lines.append("=" * 80)
    
    # 保存文件
    output_path = Path('scripts/数据集/全单位数据集.txt')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✓ 已生成完整数据集: {output_path}")
    print(f"  总计: {len(units)}个单位")
    for cat_key, cat_name in category_names.items():
        if cat_key in categories:
            print(f"  - {cat_name}: {len(categories[cat_key])}个")

if __name__ == '__main__':
    main()
