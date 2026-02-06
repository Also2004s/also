#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动触发逻辑差异分析工具

功能：
    对比原始和转换后的自动触发逻辑，精准显示最小差异单元
    而不是显示整个表达式让用户自己找差异

对比逻辑：
    原始逻辑 = 自动触发条件 ∧ 需要条件
    转换后逻辑 = 需要条件（自动触发固定为"真"）
"""

import os
import re
import sys
from pathlib import Path
from typing import Set, Tuple, List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class BoolExpr:
    """布尔表达式节点"""
    raw: str  # 原始文本
    op: Optional[str] = None  # 操作符: 'and', 'or', 'not', 'atom'
    children: List['BoolExpr'] = field(default_factory=list)
    
    def __hash__(self):
        return hash(self.raw)
    
    def __eq__(self, other):
        if isinstance(other, BoolExpr):
            return self.raw.strip() == other.raw.strip()
        return False
    
    def __repr__(self):
        return f"BoolExpr({self.op}: {self.raw[:50]}...)"


def tokenize_logic(text: str) -> List[str]:
    """分词逻辑表达式"""
    text = text.strip()
    tokens = []
    i = 0
    
    # 定义操作符（按长度降序，避免部分匹配）
    operators = ['∧', '∨', '∧ not', '∨ not', 'not ', '(', ')', '<=', '>=', '<', '>', '==', '!=', '=']
    
    while i < len(text):
        # 跳过空白
        if text[i].isspace():
            i += 1
            continue
        
        # 检查操作符
        matched = False
        for op in operators:
            if text[i:].startswith(op):
                tokens.append(op.strip())
                i += len(op)
                matched = True
                break
        
        if matched:
            continue
        
        # 读取原子表达式（括号内的内容或普通文本）
        if text[i] == '(':
            # 匹配括号
            depth = 1
            j = i + 1
            while j < len(text) and depth > 0:
                if text[j] == '(':
                    depth += 1
                elif text[j] == ')':
                    depth -= 1
                j += 1
            tokens.append(text[i:j])
            i = j
        else:
            # 读取到下一个操作符或括号
            j = i
            while j < len(text):
                if text[j] in '()∧∨' or text[j:].startswith('not '):
                    break
                j += 1
            if j > i:
                tokens.append(text[i:j].strip())
            i = j
    
    return [t for t in tokens if t]


def parse_logic(text: str) -> BoolExpr:
    """解析布尔表达式为树结构"""
    text = text.strip()
    
    # 去除外层括号
    while text.startswith('(') and text.endswith(')'):
        inner = text[1:-1].strip()
        # 检查括号是否匹配
        depth = 0
        valid = True
        for c in inner:
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            if depth < 0:
                valid = False
                break
        if valid and depth == 0:
            text = inner
        else:
            break
    
    # 检查是否是 not 表达式
    if text.startswith('not '):
        inner = text[4:].strip()
        child = parse_logic(inner)
        return BoolExpr(raw=text, op='not', children=[child])
    
    # 分词
    tokens = tokenize_logic(text)
    if not tokens:
        return BoolExpr(raw=text, op='atom')
    
    # 查找顶层的 ∨ (or)
    depth = 0
    for i, token in enumerate(tokens):
        if token == '(':
            depth += 1
        elif token == ')':
            depth -= 1
        elif token == '∨' and depth == 0:
            left = ''.join(tokens[:i]).strip()
            right = ''.join(tokens[i+1:]).strip()
            left_expr = parse_logic(left)
            right_expr = parse_logic(right)
            return BoolExpr(raw=text, op='or', children=[left_expr, right_expr])
    
    # 查找顶层的 ∧ (and)
    depth = 0
    for i, token in enumerate(tokens):
        if token == '(':
            depth += 1
        elif token == ')':
            depth -= 1
        elif token == '∧' and depth == 0:
            left = ''.join(tokens[:i]).strip()
            right = ''.join(tokens[i+1:]).strip()
            left_expr = parse_logic(left)
            right_expr = parse_logic(right)
            return BoolExpr(raw=text, op='and', children=[left_expr, right_expr])
    
    # 原子表达式
    return BoolExpr(raw=text, op='atom')


def get_all_atoms(expr: BoolExpr) -> Set[str]:
    """获取表达式中所有原子条件"""
    atoms = set()
    
    def traverse(e: BoolExpr):
        if e.op == 'atom':
            atoms.add(e.raw.strip())
        else:
            for child in e.children:
                traverse(child)
    
    traverse(expr)
    return atoms


def find_differences(original: BoolExpr, converted: BoolExpr) -> Tuple[Set[str], Set[str]]:
    """
    找出两个表达式之间的最小差异
    
    返回: (只在原始中存在的原子条件, 只在转换后中存在的原子条件)
    """
    original_atoms = get_all_atoms(original)
    converted_atoms = get_all_atoms(converted)
    
    only_in_original = original_atoms - converted_atoms
    only_in_converted = converted_atoms - original_atoms
    
    return only_in_original, only_in_converted


def normalize_condition(text: str) -> str:
    """规范化条件文本，用于比较"""
    # 去除多余空白
    text = ' '.join(text.split())
    # 统一引号
    text = text.replace('"', '').replace("'", '')
    # 去除括号差异
    text = text.strip('()')
    return text.strip()


def smart_diff(original_text: str, converted_text: str) -> Tuple[List[str], List[str]]:
    """
    智能差异分析
    
    返回: (移除的条件列表, 新增的条件列表)
    """
    # 解析表达式
    original_expr = parse_logic(original_text)
    converted_expr = parse_logic(converted_text)
    
    # 获取原子条件
    only_in_original, only_in_converted = find_differences(original_expr, converted_expr)
    
    # 进一步处理，识别结构性变化
    # 例如：原始是 (A ∧ B) ∨ (A ∧ C) 转换后是 A ∧ (B ∨ C)
    
    removed = sorted(only_in_original)
    added = sorted(only_in_converted)
    
    return removed, added


def extract_logic_from_report(report_path: str) -> List[Dict]:
    """从现有报告中提取逻辑对比数据"""
    if not os.path.exists(report_path):
        return []
    
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    results = []
    
    # 匹配每个节的差异
    # 格式：【数字】文件路径 [节名]
    section_pattern = r'【\d+】([^\[]+)\[([^\]]+)\]'
    
    # 匹配差异内容
    diff_pattern = r'原始有而转换后缺少:\s*(.+?)(?=\s*转换后新增:|$)'
    add_pattern = r'转换后新增:\s*(.+?)(?=\s*【|\Z)'
    
    # 按节分割
    parts = re.split(r'(?=【\d+】)', content)
    
    for part in parts:
        section_match = re.search(section_pattern, part)
        if not section_match:
            continue
        
        file_path = section_match.group(1).strip()
        section_name = section_match.group(2).strip()
        
        # 提取原始和转换后的逻辑
        original_match = re.search(r'原始有而转换后缺少:\s*(.+?)(?=\s*转换后新增:|$)', part, re.DOTALL)
        converted_match = re.search(r'转换后新增:\s*(.+?)(?=\s*【|\Z)', part, re.DOTALL)
        
        if original_match and converted_match:
            original_logic = original_match.group(1).strip().replace('\n', ' ')
            converted_logic = converted_match.group(1).strip().replace('\n', ' ')
            
            results.append({
                'file': file_path,
                'section': section_name,
                'original': original_logic,
                'converted': converted_logic
            })
    
    return results


def generate_precise_diff_report(logic_data: List[Dict], output_path: str):
    """生成精准的差异报告"""
    lines = []
    lines.append("=" * 80)
    lines.append("自动触发逻辑差异精准分析报告")
    lines.append("=" * 80)
    lines.append("")
    lines.append("检查逻辑:")
    lines.append("  原始逻辑 = 自动触发条件 ∧ 需要条件")
    lines.append("  转换后逻辑 = 需要条件（自动触发固定为'真'）")
    lines.append("")
    lines.append("=" * 80)
    lines.append("")
    
    for i, item in enumerate(logic_data, 1):
        file_path = item['file']
        section_name = item['section']
        original = item['original']
        converted = item['converted']
        
        # 计算差异
        removed, added = smart_diff(original, converted)
        
        # 如果没有实质差异，跳过
        if not removed and not added:
            continue
        
        lines.append(f"【{i}】{file_path} [{section_name}]")
        lines.append("")
        
        if removed:
            lines.append("  ❌ 移除的条件:")
            for cond in removed:
                lines.append(f"     - {cond}")
            lines.append("")
        
        if added:
            lines.append("  ✅ 新增的条件:")
            for cond in added:
                lines.append(f"     + {cond}")
            lines.append("")
        
        # 显示原始完整逻辑（可选，用于参考）
        lines.append("  📋 原始完整逻辑:")
        lines.append(f"     {original[:200]}{'...' if len(original) > 200 else ''}")
        lines.append("")
        lines.append("  📋 转换后完整逻辑:")
        lines.append(f"     {converted[:200]}{'...' if len(converted) > 200 else ''}")
        lines.append("")
        lines.append("-" * 80)
        lines.append("")
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return '\n'.join(lines)


def main():
    """主函数"""
    # 输入输出路径
    input_report = 'scripts/数据集/自动触发差异报告.txt'
    output_report = 'scripts/数据集/自动触发差异精准报告.txt'
    
    print("=" * 60)
    print("自动触发逻辑差异精准分析")
    print("=" * 60)
    
    # 检查输入文件
    if not os.path.exists(input_report):
        print(f"错误: 找不到输入报告: {input_report}")
        sys.exit(1)
    
    print(f"\n读取原始报告: {input_report}")
    
    # 提取逻辑数据
    logic_data = extract_logic_from_report(input_report)
    print(f"提取了 {len(logic_data)} 个节的逻辑数据")
    
    # 生成精准报告
    print("\n正在分析差异...")
    report_content = generate_precise_diff_report(logic_data, output_report)
    
    # 输出摘要
    print("\n" + "=" * 60)
    print("分析完成!")
    print(f"报告已保存: {output_report}")
    
    # 显示前3个示例
    print("\n" + "=" * 60)
    print("差异示例 (前3个):")
    print("=" * 60)
    
    count = 0
    for item in logic_data[:3]:
        removed, added = smart_diff(item['original'], item['converted'])
        if removed or added:
            count += 1
            print(f"\n【{count}】{item['file']} [{item['section']}]")
            
            if removed:
                print("  ❌ 移除:")
                for cond in list(removed)[:2]:  # 最多显示2个
                    print(f"     - {cond[:80]}{'...' if len(cond) > 80 else ''}")
            
            if added:
                print("  ✅ 新增:")
                for cond in list(added)[:2]:  # 最多显示2个
                    print(f"     + {cond[:80]}{'...' if len(cond) > 80 else ''}")
    
    if count == 0:
        print("\n没有发现实质性差异")


if __name__ == "__main__":
    main()
