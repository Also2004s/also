#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译库查重工具
检测翻译库文件中的重复项（英文键重复 + 中文值重复）
"""

import re
import sys
from collections import defaultdict

# 设置 Windows 终端 UTF-8 编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def check_duplicates(file_path, ignore_section_key_duplicate=True):
    """检查翻译库文件中的重复项
    
    Args:
        file_path: 翻译库文件路径
        ignore_section_key_duplicate: 是否忽略 Section 和 Key 之间的重复（默认True）
    """
    
    # 存储所有键及其出现的行号和类型: {key: [(line_num, type), ...]}
    key_entries = defaultdict(list)
    # 存储所有中文值及其对应的英文键
    value_to_keys = defaultdict(list)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 匹配模式:
    # [section] = [中文]  或  key = 中文
    section_pattern = re.compile(r'^\s*\[([^\]]+)\]\s*=\s*\[([^\]]+)\]')
    key_pattern = re.compile(r'^\s*([^#\s\[][^=]*)\s*=')
    
    for line_num, line in enumerate(lines, 1):
        line = line.rstrip()
        
        # 跳过空行和纯注释行
        if not line or line.strip().startswith('#'):
            continue
        
        # 尝试匹配 Section 格式 [xxx] = [yyy]
        section_match = section_pattern.match(line)
        if section_match:
            key = section_match.group(1).strip()
            value = section_match.group(2).strip()
            key_entries[key].append((line_num, 'Section'))
            value_to_keys[value].append((key, line_num, 'Section'))
            continue
        
        # 尝试匹配普通键值对 key = value
        key_match = key_pattern.match(line)
        if key_match:
            key = key_match.group(1).strip()
            # 获取等号后面的值
            if '=' in line:
                value_part = line.split('=', 1)[1].strip()
                # 过滤掉纯注释或特殊情况
                if key and not key.startswith('#'):
                    key_entries[key].append((line_num, 'Key'))
                    value_to_keys[value_part].append((key, line_num, 'Key'))
    
    # 找出重复的键
    duplicate_keys = {}
    for key, entries in key_entries.items():
        if len(entries) > 1:
            if ignore_section_key_duplicate:
                # 检查是否只有 Section 和 Key 各出现一次（不算重复）
                types = set(e[1] for e in entries)
                if len(types) == 2 and len(entries) == 2:
                    # 一个是Section，一个是Key，不算重复，跳过
                    continue
            # 是真正的重复
            duplicate_keys[key] = [e[0] for e in entries]
    
    # 找出重复的中文值（多个英文对应同一个中文）
    duplicate_values = {}
    for value, entries in value_to_keys.items():
        if len(entries) > 1:
            if ignore_section_key_duplicate and len(entries) == 2:
                # 检查是否是 Section 和 Key 一对一的情况
                types = set(e[2] for e in entries)
                if len(types) == 2:
                    # 一个是Section，一个是Key，不算重复，跳过
                    continue
            # 是真正的重复
            duplicate_values[value] = entries
    
    return duplicate_keys, duplicate_values, len(key_entries)

def export_results(duplicate_keys, duplicate_values, total_keys, output_file):
    """将查重结果导出到文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("翻译库查重报告\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"总翻译项数: {total_keys}\n")
        f.write(f"英文键重复项: {len(duplicate_keys)}\n")
        f.write(f"中文值重复项: {len(duplicate_values)}\n")
        
        has_duplicates = False
        
        # 导出英文键重复
        if duplicate_keys:
            has_duplicates = True
            f.write("\n" + "=" * 60 + "\n")
            f.write("发现重复的英文键:\n")
            f.write("=" * 60 + "\n")
            
            for key in sorted(duplicate_keys.keys(), key=lambda x: duplicate_keys[x][0]):
                lines = duplicate_keys[key]
                f.write(f"\n  键: {key}\n")
                f.write(f"  出现位置: 第 {', '.join(map(str, lines))} 行\n")
        
        # 导出中文值重复
        if duplicate_values:
            has_duplicates = True
            f.write("\n" + "=" * 60 + "\n")
            f.write("发现重复的中文值（不同英文键对应相同中文）:\n")
            f.write("=" * 60 + "\n")
            
            for value in sorted(duplicate_values.keys()):
                entries = duplicate_values[value]
                f.write(f"\n  中文值: {value}\n")
                f.write(f"  对应英文键:\n")
                for key, line_num, entry_type in sorted(entries, key=lambda x: x[1]):
                    f.write(f"    - [{entry_type}] {key} (第{line_num}行)\n")
        
        if not has_duplicates:
            f.write("\n✓ 未发现任何重复项！\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("查重完成\n")
        f.write("=" * 60 + "\n")

def main():
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='翻译库查重工具 - 检测英文键和中文值的重复')
    parser.add_argument('file', nargs='?', default='scripts/翻译库.txt', help='翻译库文件路径 (默认: scripts/翻译库.txt)')
    parser.add_argument('-o', '--output', help='导出结果到指定文件')
    parser.add_argument('-q', '--quiet', action='store_true', help='静默模式，不输出到控制台')
    parser.add_argument('--strict', action='store_true', help='严格模式，Section和Key同名也算重复')
    args = parser.parse_args()
    
    file_path = args.file
    ignore_section_key_duplicate = not args.strict
    
    if not args.quiet:
        print("=" * 60)
        print("翻译库查重工具")
        print("=" * 60)
        if not ignore_section_key_duplicate:
            print("[严格模式] Section和Key同名也会被视为重复")
    
    try:
        duplicate_keys, duplicate_values, total_keys = check_duplicates(file_path, ignore_section_key_duplicate)
    except FileNotFoundError:
        print(f"错误: 找不到文件 '{file_path}'")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
    
    if not args.quiet:
        print(f"\n总翻译项数: {total_keys}")
        print(f"英文键重复项: {len(duplicate_keys)}")
        print(f"中文值重复项: {len(duplicate_values)}")
        
        has_duplicates = False
        
        # 显示英文键重复
        if duplicate_keys:
            has_duplicates = True
            print("\n" + "=" * 60)
            print("发现重复的英文键:")
            print("=" * 60)
            
            # 按行号排序输出
            for key in sorted(duplicate_keys.keys(), key=lambda x: duplicate_keys[x][0]):
                lines = duplicate_keys[key]
                print(f"\n  键: {key}")
                print(f"  出现位置: 第 {', '.join(map(str, lines))} 行")
        
        # 显示中文值重复（不同英文对应相同中文）
        if duplicate_values:
            has_duplicates = True
            print("\n" + "=" * 60)
            print("发现重复的中文值（不同英文键对应相同中文）:")
            print("=" * 60)
            
            # 按中文值排序
            for value in sorted(duplicate_values.keys()):
                entries = duplicate_values[value]
                print(f"\n  中文值: {value}")
                print(f"  对应英文键:")
                for key, line_num, entry_type in sorted(entries, key=lambda x: x[1]):
                    print(f"    - [{entry_type}] {key} (第{line_num}行)")
        
        if not has_duplicates:
            print("\n✓ 未发现任何重复项！")
        
        print("\n" + "=" * 60)
        print("查重完成")
        print("=" * 60)
    
    # 导出到文件
    if args.output:
        export_results(duplicate_keys, duplicate_values, total_keys, args.output)
        if not args.quiet:
            print(f"\n结果已导出到: {args.output}")

if __name__ == '__main__':
    main()
