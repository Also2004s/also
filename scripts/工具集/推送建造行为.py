import os
import re
import shutil

def parse_building_actions_file(file_path):
    """解析建造行为集文件，返回按文件路径分组的数据"""
    file_data = {}
    current_file = None
    current_section = None
    current_content = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip()
            
            # 检测文件分隔符
            if line.startswith('================================================================================'):
                continue
            elif line.startswith('文件: '):
                if current_file and current_section:
                    if current_file not in file_data:
                        file_data[current_file] = {}
                    if current_section not in file_data[current_file]:
                        file_data[current_file][current_section] = []
                    file_data[current_file][current_section].append(current_content)
                
                current_file = line[4:].strip()
                current_section = None
                current_content = []
            elif line.startswith('【') and line.endswith('】'):
                if current_file and current_section and current_content:
                    if current_file not in file_data:
                        file_data[current_file] = {}
                    if current_section not in file_data[current_file]:
                        file_data[current_file][current_section] = []
                    file_data[current_file][current_section].append(current_content)
                
                current_section = line[1:-1]
                current_content = []
            elif line.startswith('  [') and line.endswith(']'):
                if current_content:
                    current_content.append(line)
            elif line.startswith('    ') and current_content:
                current_content.append(line)
    
    # 处理最后一个文件的数据
    if current_file and current_section and current_content:
        if current_file not in file_data:
            file_data[current_file] = {}
        if current_section not in file_data[current_file]:
            file_data[current_file][current_section] = []
        file_data[current_file][current_section].append(current_content)
    
    return file_data

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

def write_ini_file(file_path, sections):
    """将节和内容写入INI文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        for section, content in sections.items():
            f.write(f'[{section}]\n')
            for line in content:
                f.write(f'{line}\n')
            f.write('\n')

def merge_sections(existing_sections, new_sections_data):
    """合并新节数据到现有节中，重复的节用新数据覆盖"""
    merged_sections = existing_sections.copy()
    
    for section_name, section_contents in new_sections_data.items():
        # 如果节已存在，先删除旧的
        if section_name in merged_sections:
            del merged_sections[section_name]
        
        # 添加新的节内容
        for content in section_contents:
            merged_sections[section_name] = content
    
    return merged_sections

def main():
    building_actions_file = 'scripts/数据集/建造行为集.txt'
    root_dir = '.'
    
    # 解析建造行为集文件
    print("正在解析建造行为集文件...")
    building_data = parse_building_actions_file(building_actions_file)
    
    if not building_data:
        print("错误：未能从建造行为集文件中解析到任何数据")
        return
    
    print(f"成功解析到 {len(building_data)} 个文件的建造行为数据")
    
    # 处理每个文件
    processed_files = 0
    updated_files = 0
    
    for file_path, sections_data in building_data.items():
        # 检查文件是否存在
        full_path = os.path.join(root_dir, file_path)
        if not os.path.exists(full_path):
            print(f"警告：文件不存在，跳过 - {file_path}")
            continue
        
        # 备份原文件
        backup_path = full_path + '.backup'
        shutil.copy2(full_path, backup_path)
        
        try:
            # 读取现有文件
            existing_sections = parse_ini_file(full_path)
            
            # 合并新数据
            merged_sections = merge_sections(existing_sections, sections_data)
            
            # 写回文件
            write_ini_file(full_path, merged_sections)
            
            processed_files += 1
            updated_files += 1
            print(f"已更新：{file_path}")
            
        except Exception as e:
            print(f"错误：处理文件 {file_path} 时出错 - {str(e)}")
            # 如果出错，恢复备份
            shutil.copy2(backup_path, full_path)
    
    print(f"\n处理完成！")
    print(f"总共处理文件：{processed_files}")
    print(f"成功更新文件：{updated_files}")

if __name__ == '__main__':
    main()