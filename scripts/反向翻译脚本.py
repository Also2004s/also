#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反向翻译脚本 - 将中文INI/Template文件转换回英文
功能：
1. 读取翻译库，构建反向映射（中文->英文）
2. 递归遍历指定目录下的所有.ini和.template文件
3. 将中文内容翻译回英文
4. 保持原有目录结构输出翻译后的文件

使用方法：
    python 反向翻译脚本.py [输入目录] [输出目录]
    
    默认输入目录: . (当前目录/项目根目录)
    默认输出目录: 反向翻译结果/
    
    示例:
    python 反向翻译脚本.py . 英文结果/
    python 反向翻译脚本.py 翻译结果/中文 英文输出/
"""

import os
import re
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Set


class ReverseTranslationLibrary:
    """反向翻译库类，用于构建中文->英文的映射"""
    
    def __init__(self, lib_path: str = "scripts/翻译库.txt"):
        self.lib_path = lib_path
        # 反向映射表：中文 -> 英文
        self.translations: Dict[str, str] = {}
        self.section_translations: Dict[str, str] = {}
        self.value_translations: Dict[str, str] = {}
        self.load_library()
    
    def load_library(self):
        """加载翻译库文件并构建反向映射"""
        if not os.path.exists(self.lib_path):
            # 尝试其他路径
            alt_paths = [
                "翻译库.txt",
                "../scripts/翻译库.txt",
                "../../scripts/翻译库.txt",
                "scripts/翻译库.txt"
            ]
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    self.lib_path = alt_path
                    break
            else:
                print(f"警告: 翻译库文件不存在: {self.lib_path}")
                print("将使用默认路径继续，但没有翻译对照")
                return
        
        with open(self.lib_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析翻译库，构建反向映射
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 解析 [key] = [value] 格式的Section翻译
            section_match = re.match(r'^\[(.+?)\]\s*=\s*\[(.+?)\]$', line)
            if section_match:
                eng = section_match.group(1).strip()
                chn = section_match.group(2).strip()
                # 反向映射：中文 -> 英文
                self.section_translations[chn] = eng
                continue
            
            # 解析 key = value 格式的翻译
            if '=' in line:
                parts = line.split('=', 1)
                eng = parts[0].strip()
                chn = parts[1].strip()
                
                # 区分key翻译和value翻译，构建反向映射
                if eng in ['true', 'false', 'TRUE', 'FALSE', 'True', 'False',
                          'LAND', 'WATER', 'HOVER', 'AIR', 'OVER_CLIFF',
                          'AUTO', 'NONE']:
                    self.value_translations[chn] = eng
                else:
                    self.translations[chn] = eng
    
    def get_translation(self, key: str) -> str:
        """获取中文key对应的英文翻译"""
        return self.translations.get(key, key)
    
    def get_section_translation(self, section: str) -> str:
        """获取中文Section名称对应的英文"""
        return self.section_translations.get(section, section)
    
    def get_value_translation(self, value: str) -> str:
        """获取中文value对应的英文"""
        return self.value_translations.get(value, value)


class ReverseTranslator:
    """反向翻译器：中文 -> 英文"""
    
    def __init__(self, library: ReverseTranslationLibrary):
        self.lib = library
        self.stats = {
            'files_processed': 0,
            'files_skipped': 0,
            'lines_translated': 0,
            'keys_translated': 0,
            'sections_translated': 0
        }
        # 定义要处理的文件扩展名
        self.valid_extensions: Set[str] = {'.ini', '.template'}
        
        # 预编译正则表达式以提高性能
        self._compile_translation_patterns()
    
    def _compile_translation_patterns(self):
        """预编译翻译用的正则表达式模式"""
        # 缓存排序后的键列表（按长度降序，避免短词替换长词的一部分）
        self.sorted_keys = sorted(
            [k for k in self.lib.translations.keys() if k not in self.lib.translations.values()],
            key=len, 
            reverse=True
        )
        
        # 预编译正则表达式模式
        self.compiled_patterns = {}
        for chn_key in self.sorted_keys:
            pattern = r'\b' + re.escape(chn_key) + r'\b'
            self.compiled_patterns[chn_key] = re.compile(pattern)
    
    def is_valid_file(self, file_path: Path) -> bool:
        """检查文件是否是有效的可翻译文件"""
        return file_path.suffix.lower() in self.valid_extensions
    
    def translate_file(self, input_path: str, output_path: str) -> bool:
        """反向翻译单个文件（中文->英文）"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"  [FAIL] 读取失败: {input_path} - {e}")
            self.stats['files_skipped'] += 1
            return False
        
        translated_lines = []
        has_translation = False
        
        for line in lines:
            translated_line = self.translate_line(line)
            translated_lines.append(translated_line)
            if translated_line != line:
                has_translation = True
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:  # 只有在有目录路径时才创建
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.writelines(translated_lines)
        except Exception as e:
            print(f"  [FAIL] 写入失败: {output_path} - {e}")
            self.stats['files_skipped'] += 1
            return False
        
        self.stats['files_processed'] += 1
        print(f"  [OK] 已反向翻译: {input_path} -> {output_path}")
        return True
    
    def translate_line(self, line: str) -> str:
        """反向翻译单行内容（中文->英文）"""
        original = line
        
        # 移除行尾的换行符（保留空格缩进）
        line_content = line.rstrip('\n\r')
        
        # 跳过空行和纯注释行
        stripped = line_content.strip()
        if not stripped or stripped.startswith('#'):
            return line_content + '\n' if line.endswith('\n') else line_content
        
        # 处理Section行 [section_name]
        section_match = re.match(r'^(\s*)\[([^\]]+)\](\s*)$', line_content)
        if section_match:
            indent = section_match.group(1)
            section_name = section_match.group(2)
            trailing = section_match.group(3)
            
            # 检查是否是带注释的section
            comment = ''
            if '#' in section_name:
                parts = section_name.split('#', 1)
                section_name = parts[0].strip()
                comment = '#' + parts[1]
            
            # 反向翻译section名称（中文->英文）
            translated_section = self.lib.get_section_translation(section_name)
            if translated_section != section_name:
                self.stats['sections_translated'] += 1
            
            return f"{indent}[{translated_section}]{trailing}{comment}\n"
        
        # 处理键值对 key: value 或 key = value
        kv_match = re.match(r'^(\s*)([^:=#\[]+?)([:=])(.+?)(\s*)$', line_content)
        if kv_match:
            indent = kv_match.group(1)
            key = kv_match.group(2).strip()
            separator = kv_match.group(3)
            value = kv_match.group(4).strip()
            trailing = kv_match.group(5)
            
            # 分离注释
            comment = ''
            if '#' in value:
                parts = value.split('#', 1)
                value = parts[0].strip()
                comment = ' #' + parts[1]
            
            # 反向翻译key（中文->英文）
            translated_key = self.lib.get_translation(key)
            if translated_key != key:
                self.stats['keys_translated'] += 1
            
            # 反向翻译特定的value
            translated_value = self.translate_value(value)
            if translated_value != value:
                self.stats['lines_translated'] += 1
            
            return f"{indent}{translated_key}{separator}{translated_value}{comment}\n"
        
        # 对于不匹配任何模式的行，确保有换行符
        return line_content + '\n' if line.endswith('\n') else line_content
    
    def translate_value(self, value: str) -> str:
        """反向翻译value值（中文->英文）"""
        # 处理已翻译的布尔值
        if value in ['真', '假']:
            return self.lib.get_value_translation(value)
        
        # 处理已翻译的移动类型
        if value in ['陆地', '水面', '跨悬崖和水面', '空中', '跨悬崖', '两栖']:
            return self.lib.get_value_translation(value)
        
        # 处理特殊值
        if value in ['自动', '无']:
            return self.lib.get_value_translation(value)
        
        # 反向翻译value中出现的中文标识符（变量名、函数名等）
        # 使用预编译的正则表达式模式以提高性能
        translated_value = value
        for chn_key in self.sorted_keys:
            eng_key = self.lib.translations[chn_key]
            
            # 使用预编译的正则表达式
            pattern = self.compiled_patterns[chn_key]
            if pattern.search(translated_value):
                translated_value = pattern.sub(eng_key, translated_value)
                self.stats['lines_translated'] += 1
        
        return translated_value
    
    def translate_directory(self, input_dir: str, output_dir: str, 
                           exclude_dirs: List[str] = None, exclude_files: List[str] = None):
        """反向翻译整个目录下的所有有效文件"""
        input_path = Path(input_dir)
        
        if not input_path.exists():
            print(f"错误: 输入目录不存在: {input_dir}")
            return
        
        # 默认排除的目录
        if exclude_dirs is None:
            exclude_dirs = ['.git', '.vscode', '__pycache__', 'scripts']
        
        if exclude_files is None:
            exclude_files = []
        
        # 获取所有有效文件
        all_files = []
        for ext in self.valid_extensions:
            all_files.extend(input_path.rglob(f"*{ext}"))
        
        # 过滤掉排除的目录中的文件
        valid_files = []
        for file_path in all_files:
            # 检查是否在排除目录中
            should_exclude = False
            for exclude_dir in exclude_dirs:
                if exclude_dir in file_path.parts:
                    should_exclude = True
                    break
            
            # 检查文件名是否在排除列表中
            if file_path.name in exclude_files:
                should_exclude = True
            
            if not should_exclude:
                valid_files.append(file_path)
        
        if not valid_files:
            print(f"警告: 在 {input_dir} 中未找到.ini或.template文件")
            return
        
        print(f"\n找到 {len(valid_files)} 个待反向翻译文件")
        print("=" * 60)
        
        for file_path in valid_files:
            # 计算相对路径
            rel_path = file_path.relative_to(input_path)
            output_file = Path(output_dir) / rel_path
            
            self.translate_file(str(file_path), str(output_file))
        
        print("=" * 60)
        print(f"反向翻译完成!")
        print(f"  处理文件数: {self.stats['files_processed']}")
        print(f"  跳过文件数: {self.stats['files_skipped']}")
        print(f"  Section翻译: {self.stats['sections_translated']}")
        print(f"  Key翻译: {self.stats['keys_translated']}")


def main():
    """主函数"""
    # 获取命令行参数
    if len(sys.argv) >= 2:
        input_dir = sys.argv[1]
    else:
        input_dir = "."
    
    if len(sys.argv) >= 3:
        output_dir = sys.argv[2]
    else:
        # 默认输出到输入目录，覆盖原文件
        output_dir = input_dir
    
    print("=" * 60)
    print("反向翻译脚本 - 中文INI/Template文件转英文工具")
    print("=" * 60)
    print(f"输入目录: {os.path.abspath(input_dir)}")
    print(f"输出目录: {os.path.abspath(output_dir)}")
    
    # 加载翻译库 - 尝试多个可能的位置
    lib_paths = [
        "scripts/翻译库.txt",
        "翻译库.txt",
        os.path.join(os.path.dirname(__file__), "翻译库.txt"),
        os.path.join(input_dir, "scripts/翻译库.txt"),
    ]
    
    lib_path = None
    for path in lib_paths:
        if os.path.exists(path):
            lib_path = path
            break
    
    if lib_path is None:
        print(f"\n警告: 未找到翻译库文件，将创建空翻译库")
        lib_path = "scripts/翻译库.txt"
    
    print(f"\n加载翻译库: {lib_path}")
    library = ReverseTranslationLibrary(lib_path)
    print(f"  已加载 {len(library.translations)} 个反向key映射")
    print(f"  已加载 {len(library.section_translations)} 个反向section映射")
    print(f"  已加载 {len(library.value_translations)} 个反向value映射")
    
    # 创建翻译器并执行反向翻译
    translator = ReverseTranslator(library)
    translator.translate_directory(input_dir, output_dir)
    
    print("\n" + "=" * 60)
    if input_dir == output_dir:
        print("反向翻译完成！所有文件已直接覆盖更新")
    else:
        print("反向翻译完成！结果已保存到:", os.path.abspath(output_dir))


if __name__ == "__main__":
    main()
