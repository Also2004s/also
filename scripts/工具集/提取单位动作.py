import os
import re

def parse_ini_file(file_path):
    """解析INI文件，返回所有节和内容"""
    sections = {}
    current_section = None
    current_content = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                if current_section is not None:
                    sections[current_section] = current_content
                current_section = line[1:-1]
                current_content = []
            else:
                if line and current_section is not None:
                    current_content.append(line)
    
    if current_section is not None:
        sections[current_section] = current_content
    
    return sections

def get_build_units_from_section(content):
    """从节内容中提取可建造单位的名称"""
    units = []
    for line in content:
        if line.startswith('canBuild_') and '_name:' in line:
            unit_name = line.split('_name:')[1].strip()
            if unit_name:
                units.append(unit_name)
    return units

def get_build_units_from_core_section(sections):
    """从[核心]节中提取可建造单位的名称"""
    units = []
    core_section = sections.get('核心', [])
    for line in core_section:
        if line.startswith('canBuild_') and '_name:' in line:
            unit_name = line.split('_name:')[1].strip()
            if unit_name:
                units.append(unit_name)
    return units

def get_build_units_from_build_sections(sections):
    """从[可建造]节中提取可建造单位的名称"""
    units = []
    for section_name, content in sections.items():
        if section_name.startswith('可建造'):
            for line in content:
                if line.startswith('name:'):
                    unit_name = line.split('name:')[1].strip()
                    if unit_name:
                        units.append(unit_name)
    return units

def get_build_units_from_build_section_content(content):
    """从[可建造]节内容中提取可建造单位的名称"""
    units = []
    for line in content:
        if line.startswith('name:'):
            unit_name = line.split('name:')[1].strip()
            if unit_name:
                units.append(unit_name)
    return units

def has_production_unit(content):
    """检查节内容中是否包含生产单位"""
    for line in content:
        if line.startswith('生产单位:'):
            return True
    return False

def has_queue_action(content):
    """检查节内容中是否包含将单位加入队列的动作"""
    for line in content:
        if '也添加进队列:' in line:
            return True
    return False

def has_queue_trigger(content):
    """检查节内容中是否包含队列触发条件"""
    for line in content:
        if '也添加进队列:' in line or '也执行队列或需执行条件:' in line:
            return True
    return False

def find_queue_related_actions(sections, queue_actions):
    """查找与队列相关的动作"""
    queue_related = {}
    queue_names = set()
    
    # 收集所有队列名称
    for section_name, content in queue_actions:
        for line in content:
            if '也添加进队列:' in line:
                queue_name = line.split('也添加进队列:')[1].strip()
                queue_names.add(queue_name)
    
    # 查找与队列相关的动作
    for section_name, content in sections.items():
        if section_name.startswith('隐藏行动'):
            # 检查是否是队列动作本身
            if any(sec == section_name for sec, _ in queue_actions):
                continue
                
            # 检查是否包含队列名称
            section_content_str = '\n'.join(content)
            for queue_name in queue_names:
                if queue_name in section_content_str:
                    if queue_name not in queue_related:
                        queue_related[queue_name] = []
                    queue_related[queue_name].append((section_name, content))
                    break
    
    return queue_related

def find_all_ini_files(root_dir):
    """查找所有INI文件"""
    ini_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.ini'):
                ini_files.append(os.path.join(root, file))
    return ini_files

def main():
    root_dir = '.'
    output_file = 'scripts/数据集/建造行为集.txt'
    
    # 按文件分类存储数据
    file_data = {}
    
    # 查找所有INI文件
    ini_files = find_all_ini_files(root_dir)
    
    for file_path in ini_files:
        rel_path = os.path.relpath(file_path, root_dir)
        sections = parse_ini_file(file_path)
        
        # 初始化该文件的数据
        file_data[rel_path] = {
            'build_units': [],
            'actions': [],
            'hidden_actions': [],
            'queue_actions': []
        }
        
        # 获取核心节内容
        core_section = sections.get('核心', [])
        
        # 提取可建造单位的节
        for section, content in sections.items():
            build_units = get_build_units_from_section(content)
            if build_units:
                # 检查是否包含可建造: setRally
                has_setrally = False
                for line in content:
                    if line.startswith('可建造:') and 'setRally' in line:
                        has_setrally = True
                        break
                
                # 如果不包含可建造: setRally，则添加该节
                if not has_setrally:
                    file_data[rel_path]['build_units'].append((section, content))
        
        # 从[核心]节提取可建造单位（避免重复）
        core_build_units = get_build_units_from_core_section(sections)
        if core_build_units:
            # 检查是否已经添加过[核心]节
            if not any(sec == '核心' for sec, _ in file_data[rel_path]['build_units']):
                file_data[rel_path]['build_units'].append(('核心', core_section))
        
        # 从[可建造]节提取可建造单位（避免重复）
        build_sections_units = get_build_units_from_build_sections(sections)
        if build_sections_units:
            for section_name, content in sections.items():
                if section_name.startswith('可建造'):
                    # 检查是否已经添加过该节
                    if not any(sec == section_name for sec, _ in file_data[rel_path]['build_units']):
                        # 检查是否包含name:repair、name:reclaim或name:setRally
                        has_special_units = False
                        for line in content:
                            if line.startswith('name:') and ('repair' in line or 'reclaim' in line or 'setRally' in line):
                                has_special_units = True
                                break
                        
                        # 如果不包含特殊单位，则添加该节
                        if not has_special_units:
                            file_data[rel_path]['build_units'].append((section_name, content))
        
        # 提取有生产单位的[行动]和[隐藏行动]的完整节内容
        for section, content in sections.items():
            if has_production_unit(content):
                if section.startswith('行动'):
                    file_data[rel_path]['actions'].append((section, content))
                elif section.startswith('隐藏行动'):
                    if has_queue_action(content):
                        file_data[rel_path]['queue_actions'].append((section, content))
                    else:
                        file_data[rel_path]['hidden_actions'].append((section, content))
        
        # 提取包含队列触发条件但没有生产单位的隐藏行动
        for section, content in sections.items():
            if section.startswith('隐藏行动') and not has_production_unit(content) and has_queue_trigger(content):
                # 检查是否已经添加过该节
                if not any(sec == section for sec, _ in file_data[rel_path]['queue_actions']):
                    file_data[rel_path]['queue_actions'].append((section, content))
        
        # 查找与队列相关的动作
        queue_related = find_queue_related_actions(sections, file_data[rel_path]['queue_actions'])
        file_data[rel_path]['queue_related'] = queue_related
    
    # 写入汇总文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for file_path, data in file_data.items():
            # 如果该文件没有任何相关数据，跳过
            if not any(data.values()):
                continue
            
            f.write("=" * 80 + "\n")
            f.write(f"文件: {file_path}\n")
            f.write("=" * 80 + "\n\n")
            
            # 可建造单位
            if data['build_units']:
                f.write("【可建造】\n")
                for section, content in data['build_units']:
                    f.write(f"  [{section}]\n")
                    # 根据节名判断使用哪种提取方法
                    if section.startswith('可建造'):
                        build_units = get_build_units_from_build_section_content(content)
                        # 显示可建造节的完整内容
                        for line in content:
                            f.write(f"    {line}\n")
                    else:
                        build_units = get_build_units_from_section(content)
                        for unit in build_units:
                            f.write(f"    可建造: {unit}\n")
                f.write("\n")
            
            # 行动
            if data['actions']:
                f.write("【行动】\n")
                for section, content in data['actions']:
                    f.write(f"  [{section}]\n")
                    for line in content:
                        f.write(f"    {line}\n")
                f.write("\n")
            
            # 隐藏行动
            if data['hidden_actions']:
                f.write("【隐藏行动】\n")
                for section, content in data['hidden_actions']:
                    f.write(f"  [{section}]\n")
                    for line in content:
                        f.write(f"    {line}\n")
                f.write("\n")
            
            # 队列行动
            if data['queue_actions']:
                f.write("【将生产单位加入队列的隐藏行动】\n")
                for section, content in data['queue_actions']:
                    f.write(f"  [{section}]\n")
                    for line in content:
                        f.write(f"    {line}\n")
                f.write("\n")
            
            # 相关动作
            if data.get('queue_related'):
                f.write("【相关动作】\n")
                for queue_name, related_actions in data['queue_related'].items():
                    for related_section, related_content in related_actions:
                        f.write(f"  [{related_section}]\n")
                        for line in related_content:
                            f.write(f"    {line}\n")
                f.write("\n")
    
    print(f"汇总完成，结果已保存到: {output_file}")
    print(f"总共处理了 {len(ini_files)} 个INI文件")

if __name__ == '__main__':
    main()
