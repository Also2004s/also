import os
import sys
import re

# 设置输出编码
sys.stdout.reconfigure(encoding='utf-8')

root_dir = '.'
meta_dir = 'scripts/元/人机的玩笑'


def parse_diff_report(diff_file_path):
    """解析自动触发差异报告，提取每个节的差异信息"""
    sections = {}
    
    try:
        with open(diff_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f'读取差异报告失败: {e}')
        return sections
    
    # 找到"一眼看差异"部分
    start_marker = '【一眼看差异'
    end_marker = '【逻辑等价'
    
    start_pos = content.find(start_marker)
    end_pos = content.find(end_marker)
    
    if start_pos == -1:
        print('未找到差异部分标记')
        return sections
    
    if end_pos == -1:
        diff_content = content[start_pos:]
    else:
        diff_content = content[start_pos:end_pos]
    
    # 解析差异项
    item_pattern = r'【\d+】(.+?)\s*\[([^\]]+)\]'
    matches = list(re.finditer(item_pattern, diff_content))
    
    for i, match in enumerate(matches):
        file_path = match.group(1).strip()
        section_name = match.group(2).strip()
        start = match.end()
        
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(diff_content)
        
        block = diff_content[start:end]
        
        # 提取 missing 和 added
        missing_start = block.find('原始有而转换后缺少:')
        added_start = block.find('转换后新增:')
        
        missing = None
        added = None
        
        if missing_start != -1:
            if added_start != -1:
                missing = block[missing_start + len('原始有而转换后缺少:'):added_start].strip()
            else:
                missing = block[missing_start + len('原始有而转换后缺少:'):].strip()
        
        if added_start != -1:
            added = block[added_start + len('转换后新增:'):].strip()
        
        # 清理多行文本
        if missing:
            missing = ' '.join(missing.split())
        if added:
            added = ' '.join(added.split())
        
        # 只保存有实际差异的项
        if (missing and missing != '无') or (added and added != '无'):
            key = f'{file_path}\\{section_name}'
            sections[key] = {
                'file': file_path,
                'section': section_name,
                'missing': missing if missing and missing != '无' else None,
                'added': added if added and added != '无' else None
            }
    
    return sections


def extract_sections(lines):
    """提取ini文件中的所有节及其内容"""
    sections = {}
    current_section = None
    current_content = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            if current_section:
                sections[current_section] = current_content
            current_section = stripped[1:-1]
            current_content = [line]
        elif current_section:
            current_content.append(line)
    
    if current_section:
        sections[current_section] = current_content
    
    return sections


def extract_auto_trigger_and_requirement(section_lines):
    """从节内容中提取自动触发和需要条件"""
    auto_trigger = None
    required_condition = None
    auto_trigger_is_true = False
    auto_trigger_is_false = False
    
    for line in section_lines:
        stripped = line.strip()
        
        # 检查自动触发:真
        if re.match(r'自动触发\s*:\s*真', stripped, re.IGNORECASE):
            auto_trigger_is_true = True
        
        # 检查自动触发:假
        if re.match(r'自动触发\s*:\s*假', stripped, re.IGNORECASE):
            auto_trigger_is_false = True
        
        # 提取自动触发:if
        match = re.search(r'自动触发\s*:\s*if\s+(.+)', stripped, re.IGNORECASE)
        if match:
            auto_trigger = match.group(1).strip()
        
        # 提取需要条件:if
        match = re.search(r'需要条件\s*:\s*if\s+(.+)', stripped, re.IGNORECASE)
        if match:
            required_condition = match.group(1).strip()
    
    return auto_trigger, required_condition, auto_trigger_is_true, auto_trigger_is_false


def get_all_files(base_path):
    files = []
    for root, dirs, filenames in os.walk(base_path):
        for f in filenames:
            rel_path = os.path.relpath(os.path.join(root, f), base_path)
            files.append(rel_path)
    return set(files)


def analyze_conversion_difference(meta_auto, meta_required, root_required):
    """
    分析转换差异的类型
    返回: {
        'type': 'simple' | 'logic_deformed' | 'complex',
        'removed': [],  # 被移除的条件（子串列表）
        'added': [],    # 被添加的条件（子串列表）
        'correct_form': str,  # 正确的形式
        'issue': str    # 问题描述
    }
    """
    result = {
        'type': 'simple',
        'removed': [],
        'added': [],
        'correct_form': None,
        'issue': None
    }
    
    # 构建原始完整逻辑：自动触发条件 AND 需要条件
    original_full = None
    if meta_auto and meta_required:
        original_full = f"({meta_auto}) and ({meta_required})"
    elif meta_auto:
        original_full = meta_auto
    elif meta_required:
        original_full = meta_required
    
    if not original_full or not root_required:
        return result
    
    # 清理空格用于比较
    orig_norm = original_full.replace(' ', '')
    root_norm = root_required.replace(' ', '')
    
    # 如果完全相同，无差异
    if orig_norm == root_norm:
        return result
    
    # 检查是否是简单子串包含关系
    # 情况1：原始条件被整体包含在当前条件中（添加了额外条件）
    if orig_norm in root_norm:
        # 找出添加的部分
        added_part = root_required.replace(original_full, '').strip()
        if added_part.startswith('and '):
            added_part = added_part[4:].strip()
        result['type'] = 'simple'
        result['added'] = [added_part] if added_part else []
        return result
    
    # 情况2：当前条件被整体包含在原始条件中（移除了部分条件）
    if root_norm in orig_norm:
        removed_part = original_full.replace(root_required, '').strip()
        if removed_part.startswith('and '):
            removed_part = removed_part[4:].strip()
        result['type'] = 'simple'
        result['removed'] = [removed_part] if removed_part else []
        return result
    
    # 情况3：检查是否是逻辑变形（or/and 优先级问题）
    # 这种情况通常表现为：原始条件包含 or，但当前条件错误地将 and 条件附加到最后
    
    # 检查原始自动触发是否包含 or
    has_or_in_auto = bool(meta_auto and re.search(r'\s+or\s+', meta_auto, re.IGNORECASE))
    
    if has_or_in_auto and meta_required:
        # 可能的逻辑变形：自动触发条件中的 or 分支没有分别与需要条件结合
        # 例如：(A or B) and C 被错误写成 A or B and C
        
        # 尝试检测是否当前条件只是把需要条件简单附加到最后
        # 正确的转换应该是：(A or B) and C = A and C or B and C
        # 错误的转换可能是：A or B and C
        
        # 简化判断：如果原始自动触发有or，且需要条件只有一个简单条件
        # 检查当前条件是否只是简单地将需要条件附加到末尾
        
        req_norm = meta_required.replace(' ', '')
        
        # 检查是否当前条件以需要条件结尾（简单附加）
        if root_norm.endswith(req_norm):
            # 可能是逻辑变形
            result['type'] = 'logic_deformed'
            result['issue'] = '逻辑变形：or/and 优先级错误，需要条件没有正确与or分支结合'
            
            # 计算正确的形式
            # (A or B or C) and D 应该展开为 A and D or B and D or C and D
            auto_conds = re.split(r'\s+or\s+', meta_auto, flags=re.IGNORECASE)
            correct_parts = []
            for cond in auto_conds:
                cond = cond.strip()
                if cond.startswith('(') and cond.endswith(')'):
                    cond = cond[1:-1]
                correct_parts.append(f"({cond} and {meta_required})")
            result['correct_form'] = ' or '.join(correct_parts)
            
            return result
    
    # 默认情况：简单差异分析
    result['type'] = 'complex'
    return result


def main():
    # 首先解析差异报告
    diff_report_path = 'scripts/数据集/自动触发差异报告.txt'
    print(f'正在解析差异报告: {diff_report_path}')
    
    diff_sections = parse_diff_report(diff_report_path)
    print(f'从差异报告中解析出 {len(diff_sections)} 个有差异的节')
    
    # 分类结果
    # 第一组：自动触发为真，条件正确（假差异）
    auto_true_correct = []
    
    # 第二组：自动触发为真，简单条件差异（添加/移除子条件）
    auto_true_simple_diff = []
    
    # 第三组：自动触发为真，逻辑变形（or/and优先级问题）
    auto_true_logic_deformed = []
    
    # 第四组：自动触发不为真但有真实差异
    auto_not_true_with_diff = []
    
    # 第五组：在差异报告中但找不到对应节
    not_found_in_files = []
    
    # 处理差异报告中的每个节
    for key, diff_info in diff_sections.items():
        file_path = diff_info['file']
        section_name = diff_info['section']
        
        root_path = os.path.join(root_dir, file_path)
        meta_path = os.path.join(meta_dir, file_path)
        
        # 检查文件是否存在
        if not os.path.exists(root_path) or not os.path.exists(meta_path):
            not_found_in_files.append({
                'file': file_path,
                'section': section_name,
                'reason': '文件不存在'
            })
            continue
        
        try:
            with open(root_path, 'r', encoding='utf-8', errors='ignore') as rf:
                root_lines = rf.readlines()
            with open(meta_path, 'r', encoding='utf-8', errors='ignore') as mf:
                meta_lines = mf.readlines()
        except Exception as e:
            not_found_in_files.append({
                'file': file_path,
                'section': section_name,
                'reason': f'读取失败: {e}'
            })
            continue
        
        root_sections_dict = extract_sections(root_lines)
        meta_sections_dict = extract_sections(meta_lines)
        
        # 检查节是否存在
        if section_name not in root_sections_dict or section_name not in meta_sections_dict:
            not_found_in_files.append({
                'file': file_path,
                'section': section_name,
                'reason': '节不存在'
            })
            continue
        
        root_section = root_sections_dict[section_name]
        meta_section = meta_sections_dict[section_name]
        
        # 提取条件
        root_auto, root_required, root_is_true, root_is_false = extract_auto_trigger_and_requirement(root_section)
        meta_auto, meta_required, meta_is_true, meta_is_false = extract_auto_trigger_and_requirement(meta_section)
        
        # 构建条目
        item = {
            'file': file_path,
            'section': section_name,
            'missing': diff_info['missing'],
            'added': diff_info['added'],
            'root_auto': root_auto,
            'root_required': root_required,
            'root_is_true': root_is_true,
            'meta_auto': meta_auto,
            'meta_required': meta_required,
            'meta_is_true': meta_is_true
        }
        
        # 如果当前自动触发不为真，分到第四组
        if not root_is_true:
            auto_not_true_with_diff.append(item)
            continue
        
        # 当前自动触发为真，分析差异类型
        diff_analysis = analyze_conversion_difference(meta_auto, meta_required, root_required)
        item['diff_analysis'] = diff_analysis
        
        if diff_analysis['type'] == 'simple':
            if not diff_analysis['removed'] and not diff_analysis['added']:
                # 无实际差异
                auto_true_correct.append(item)
            else:
                auto_true_simple_diff.append(item)
        elif diff_analysis['type'] == 'logic_deformed':
            auto_true_logic_deformed.append(item)
        else:
            auto_true_simple_diff.append(item)
    
    print(f'\n分析结果:')
    print(f'  自动触发为真，条件正确（假差异）: {len(auto_true_correct)} 个')
    print(f'  自动触发为真，简单条件差异: {len(auto_true_simple_diff)} 个')
    print(f'  自动触发为真，逻辑变形: {len(auto_true_logic_deformed)} 个')
    print(f'  自动触发不为真需转换: {len(auto_not_true_with_diff)} 个')
    print(f'  找不到对应文件/节: {len(not_found_in_files)} 个')
    
    # 生成逻辑条件分析报告
    with open('scripts/数据集/逻辑条件分析报告.txt', 'w', encoding='utf-8') as out:
        out.write(f'=== 逻辑条件分析报告 ===\n')
        out.write(f'对比目录: 项目根目录 vs scripts/元/人机的玩笑\n')
        out.write(f'差异报告中的总差异节数: {len(diff_sections)}\n')
        out.write(f'=' * 80 + '\n\n')
        
        # 第一组：条件正确（假差异）
        if auto_true_correct:
            out.write(f'=== 第一组：条件正确（共{len(auto_true_correct)}个）===\n')
            out.write(f'说明：差异报告误判，实际条件已正确转换\n')
            out.write(f'结论：这些节**无需修改**\n\n')
            
            for i, item in enumerate(auto_true_correct, 1):
                out.write(f'【{i}】{item["file"]} [{item["section"]}]\n')
                out.write(f'  ✓ 条件已正确转换\n\n')
        
        # 第二组：简单条件差异
        out.write(f'=== 第二组：自动触发为真，简单条件差异（共{len(auto_true_simple_diff)}个）===\n')
        out.write(f'说明：这些节已设置"自动触发:真"，但"需要条件"有简单添加或移除\n')
        out.write(f'操作：根据添加/移除的条件修正\n\n')
        
        if auto_true_simple_diff:
            for i, item in enumerate(auto_true_simple_diff, 1):
                out.write(f'【{i}】{item["file"]} [{item["section"]}]\n')
                
                if item['meta_is_true']:
                    out.write(f'  原始自动触发: 真\n')
                elif item['meta_auto']:
                    out.write(f'  原始自动触发: if {item["meta_auto"]}\n')
                else:
                    out.write(f'  原始自动触发: （无）\n')
                
                if item['meta_required']:
                    out.write(f'  原始需要条件: if {item["meta_required"]}\n')
                
                out.write(f'  当前自动触发: 真\n')
                out.write(f'  当前需要条件: if {item["root_required"] if item["root_required"] else "（无）"}\n')
                
                diff = item['diff_analysis']
                out.write(f'  ⚠️ 移除的条件:\n')
                if diff and diff.get('removed'):
                    for cond in diff['removed']:
                        out.write(f'    → {cond}\n')
                else:
                    out.write(f'    → 无\n')
                
                out.write(f'  ⚠️ 添加的条件:\n')
                if diff and diff.get('added'):
                    for cond in diff['added']:
                        out.write(f'    → {cond}\n')
                else:
                    out.write(f'    → 无\n')
                
                out.write('\n')
        else:
            out.write('（无）\n\n')
        
        # 第三组：逻辑变形
        out.write(f'=== 第三组：自动触发为真，逻辑变形（共{len(auto_true_logic_deformed)}个）===\n')
        out.write(f'说明：这些节已设置"自动触发:真"，但or/and优先级错误，导致逻辑不等价\n')
        out.write(f'操作：需要按正确形式重写"需要条件"\n\n')
        
        if auto_true_logic_deformed:
            for i, item in enumerate(auto_true_logic_deformed, 1):
                out.write(f'【{i}】{item["file"]} [{item["section"]}]\n')
                
                if item['meta_is_true']:
                    out.write(f'  原始自动触发: 真\n')
                elif item['meta_auto']:
                    out.write(f'  原始自动触发: if {item["meta_auto"]}\n')
                else:
                    out.write(f'  原始自动触发: （无）\n')
                
                if item['meta_required']:
                    out.write(f'  原始需要条件: if {item["meta_required"]}\n')
                
                out.write(f'  当前自动触发: 真\n')
                out.write(f'  当前需要条件: if {item["root_required"] if item["root_required"] else "（无）"}\n')
                
                diff = item['diff_analysis']
                if diff and diff.get('issue'):
                    out.write(f'  ❌ 问题: {diff["issue"]}\n')
                
                if diff and diff.get('correct_form'):
                    out.write(f'  ✅ 正确形式: if {diff["correct_form"]}\n')
                
                out.write('\n')
        else:
            out.write('（无）\n\n')
        
        # 第四组：自动触发不为真
        out.write(f'=== 第四组：未转换（共{len(auto_not_true_with_diff)}个）===\n')
        out.write(f'说明：这些节仍使用if条件形式，未转换为"自动触发:真"\n')
        out.write(f'操作：需要转换\n\n')
        
        if auto_not_true_with_diff:
            for i, item in enumerate(auto_not_true_with_diff, 1):
                out.write(f'【{i}】{item["file"]} [{item["section"]}]\n')
                
                if item['meta_is_true']:
                    out.write(f'  原始自动触发: 真\n')
                elif item['meta_auto']:
                    out.write(f'  原始自动触发: if {item["meta_auto"]}\n')
                else:
                    out.write(f'  原始自动触发: （无）\n')
                
                if item['meta_required']:
                    out.write(f'  原始需要条件: if {item["meta_required"]}\n')
                
                if item['root_is_true']:
                    out.write(f'  当前自动触发: 真\n')
                elif item['root_auto']:
                    out.write(f'  当前自动触发: if {item["root_auto"]}\n')
                else:
                    out.write(f'  当前自动触发: （无）\n')
                
                if item['root_required']:
                    out.write(f'  当前需要条件: if {item["root_required"]}\n')
                
                # 给出建议
                if item['meta_auto'] and item['meta_required']:
                    # 检查自动触发是否包含or
                    if re.search(r'\s+or\s+', item['meta_auto'], re.IGNORECASE):
                        # 需要展开为：(A and C) or (B and C)
                        auto_conds = re.split(r'\s+or\s+', item['meta_auto'], flags=re.IGNORECASE)
                        correct_parts = []
                        for cond in auto_conds:
                            cond = cond.strip()
                            correct_parts.append(f"{cond} and {item['meta_required']}")
                        combined = ' or '.join(correct_parts)
                        out.write(f'  💡 建议: 自动触发:真, 需要条件:if {combined}\n')
                    else:
                        combined = f"({item['meta_auto']}) and ({item['meta_required']})"
                        out.write(f'  💡 建议: 自动触发:真, 需要条件:if {combined}\n')
                elif item['meta_auto']:
                    out.write(f'  💡 建议: 自动触发:真, 需要条件:if {item["meta_auto"]}\n')
                elif item['meta_required']:
                    out.write(f'  💡 建议: 自动触发:真, 需要条件:if {item["meta_required"]}\n')
                
                out.write('\n')
        else:
            out.write('（无）\n\n')
        
        # 未找到的文件/节
        if not_found_in_files:
            out.write(f'=== 未找到的文件/节（共{len(not_found_in_files)}个）===\n\n')
            for i, item in enumerate(not_found_in_files, 1):
                out.write(f'【{i}】{item["file"]} [{item["section"]}] - {item["reason"]}\n')
            out.write('\n')
        
        # 总结
        out.write('=' * 80 + '\n')
        out.write('总结:\n')
        out.write(f'  - 条件正确（无需修改）: {len(auto_true_correct)} 个\n')
        out.write(f'  - 简单条件差异: {len(auto_true_simple_diff)} 个\n')
        out.write(f'  - 逻辑变形（需重写）: {len(auto_true_logic_deformed)} 个\n')
        out.write(f'  - 未转换: {len(auto_not_true_with_diff)} 个\n')
        out.write(f'  - 找不到文件/节: {len(not_found_in_files)} 个\n')
    
    print(f'\n逻辑条件分析报告已保存到 scripts/数据集/逻辑条件分析报告.txt')


if __name__ == '__main__':
    main()
