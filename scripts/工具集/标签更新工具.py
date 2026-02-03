# -*- coding: utf-8 -*-
"""
标签更新工具
根据全单位数据集更新所有作战单位的标签
"""

import os
import re
import sys
from pathlib import Path


# 设置控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def parse_dataset(file_path: str) -> dict:
    """
    解析全单位数据集文件，提取单位名称和标签映射
    
    Args:
        file_path: 数据集文件路径
        
    Returns:
        dict: 单位名称到标签列表的映射
    """
    unit_tags = {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用正则表达式匹配单位块
    # 格式: 【编号. 单位名称】 和 下一行的 - 标签: 标签1, 标签2, ...
    # 使用 (.*?) 而不是 (.+?) 以便匹配空标签
    pattern = r'【\d+\.\s*([^】]+)】.*?\n\s*- 标签:\s*(.*?)(?=\n\s*【|\n\s*战力:|\n\s*对地战力:|\n\s*$|\n\s*-{3,})'
    
    matches = re.findall(pattern, content, re.DOTALL)
    
    for unit_name, tags_str in matches:
        unit_name = unit_name.strip()
        # 解析标签列表，支持中文逗号和英文逗号
        # 先替换中文逗号为英文逗号
        tags_str = tags_str.replace('，', ',')
        # 按逗号分割并过滤空字符串
        tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        unit_tags[unit_name] = tags
    
    return unit_tags


def find_ini_files(directory: str) -> list:
    """
    遍历目录查找所有INI文件
    
    Args:
        directory: 要遍历的目录
        
    Returns:
        list: 所有INI文件的路径列表
    """
    ini_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.ini'):
                ini_files.append(os.path.join(root, file))
    
    return ini_files


def update_unit_tags(ini_file: str, unit_tags: dict) -> bool:
    """
    更新INI文件的tags字段
    
    Args:
        ini_file: INI文件路径
        unit_tags: 单位名称到标签列表的映射
        
    Returns:
        bool: 是否进行了更新
    """
    with open(ini_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找name字段
    name_pattern = r'^name:(.+)$'
    name_match = re.search(name_pattern, content, re.MULTILINE)
    
    if not name_match:
        return False
    
    unit_name = name_match.group(1).strip()
    
    # 查找数据集是否有该单位的标签
    if unit_name not in unit_tags:
        return False
    
    new_tags = ','.join(unit_tags[unit_name])
    
    # 查找并更新tags字段
    tags_pattern = r'^tags:.+$'
    
    if re.search(tags_pattern, content, re.MULTILINE):
        # 替换现有的tags行
        new_content = re.sub(tags_pattern, f'tags:{new_tags}', content, flags=re.MULTILINE)
    else:
        # 在name行后添加tags行
        name_line = name_match.group(0)
        new_content = content.replace(name_line, f'{name_line}\ntags:{new_tags}')
    
    # 写入文件
    with open(ini_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True


def main():
    """主函数"""
    # 路径配置
    base_dir = Path(__file__).parent.parent
    dataset_file = base_dir / '数据集' / '全单位数据集.txt'
    project_dir = base_dir.parent  # 整个项目文件夹
    units_dir = project_dir
    
    print("=" * 60)
    print("标签更新工具")
    print("=" * 60)
    
    # 解析数据集
    print(f"\n正在解析数据集: {dataset_file}")
    unit_tags = parse_dataset(str(dataset_file))
    print(f"解析完成，共找到 {len(unit_tags)} 个单位")
    
    # 显示一些解析结果用于调试
    print("\n解析结果示例:")
    for i, (name, tags) in enumerate(list(unit_tags.items())[:5]):
        print(f"  [{name}]: {tags}")
    if len(unit_tags) > 5:
        print(f"  ... 共 {len(unit_tags)} 个单位")
    
    # 查找INI文件
    print(f"\n正在搜索INI文件: {units_dir}")
    ini_files = find_ini_files(str(units_dir))
    print(f"找到 {len(ini_files)} 个INI文件")
    
    # 更新标签
    updated_count = 0
    not_found_count = 0
    
    print("\n开始更新标签...")
    for ini_file in ini_files:
        if update_unit_tags(ini_file, unit_tags):
            relative_path = os.path.relpath(ini_file, project_dir)
            updated_count += 1
            print(f"[OK] {relative_path}")
        else:
            # 检查是否因为找不到name而跳过
            with open(ini_file, 'r', encoding='utf-8') as f:
                content = f.read()
            name_match = re.search(r'^name:(.+)$', content, re.MULTILINE)
            if name_match:
                unit_name = name_match.group(1).strip()
                if unit_name not in unit_tags:
                    not_found_count += 1
    
    # 统计结果
    print("\n" + "=" * 60)
    print("更新完成!")
    print(f"  - 成功更新: {updated_count} 个文件")
    print(f"  - 未找到匹配: {not_found_count} 个文件")
    print(f"  - 总计处理: {len(ini_files)} 个文件")
    print("=" * 60)


if __name__ == '__main__':
    main()
