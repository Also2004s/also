#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键查重工具
合并功能：
    1. 翻译库查重 - 检测翻译库文件中的重复项（英文键重复 + 中文值重复）
    2. 项目查重 - 检测项目中已翻译内容与翻译库的重复

使用方法：
    python 一键查重.py [选项]

    选项：
        --mode all       全部查重（默认）
        --mode lib       仅翻译库查重
        --mode project   仅项目查重
        --output FILE    输出结果到指定文件
        --quiet          静默模式
        --strict         严格模式（Section和Key同名也算重复）
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar


# 设置 Windows 终端 UTF-8 编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


@dataclass
class TranslationStats:
    """翻译统计信息"""
    files_processed: int = 0
    files_skipped: int = 0
    lines_translated: int = 0
    keys_translated: int = 0
    sections_translated: int = 0

    def merge(self, other: TranslationStats) -> None:
        """合并另一个统计对象"""
        self.files_processed += other.files_processed
        self.files_skipped += other.files_skipped
        self.lines_translated += other.lines_translated
        self.keys_translated += other.keys_translated
        self.sections_translated += other.sections_translated

    def __str__(self) -> str:
        return (
            f"  处理文件数: {self.files_processed}\n"
            f"  跳过文件数: {self.files_skipped}\n"
            f"  Section翻译: {self.sections_translated}\n"
            f"  Key翻译: {self.keys_translated}"
        )


@dataclass
class TranslationLog:
    """翻译记录类 - 记录所有被翻译的内容"""
    section_translations: list[dict] = field(default_factory=list)
    key_translations: list[dict] = field(default_factory=list)
    value_translations: list[dict] = field(default_factory=list)
    text_translations: list[dict] = field(default_factory=list)
    
    # 查重相关
    lib_duplicate_keys: dict = field(default_factory=dict)
    lib_duplicate_values: dict = field(default_factory=dict)
    
    OUTPUT_DIR: ClassVar[str] = "scripts/数据集"
    
    def log_section_translation(self, chinese: str, english: str, file_path: str) -> None:
        """记录Section翻译"""
        self.section_translations.append({
            "chinese": chinese,
            "english": english,
            "file": file_path
        })
    
    def log_key_translation(self, chinese: str, english: str, file_path: str) -> None:
        """记录Key翻译"""
        self.key_translations.append({
            "chinese": chinese,
            "english": english,
            "file": file_path
        })
    
    def log_value_translation(self, chinese: str, english: str, file_path: str) -> None:
        """记录Value翻译"""
        self.value_translations.append({
            "chinese": chinese,
            "english": english,
            "file": file_path
        })
    
    def log_text_translation(self, chinese: str, english: str, file_path: str) -> None:
        """记录文本翻译"""
        self.text_translations.append({
            "chinese": chinese,
            "english": english,
            "file": file_path
        })
    
    def log_lib_duplicate_keys(self, duplicates: dict) -> None:
        """记录翻译库英文键重复"""
        self.lib_duplicate_keys = duplicates
    
    def log_lib_duplicate_values(self, duplicates: dict) -> None:
        """记录翻译库中文值重复"""
        self.lib_duplicate_values = duplicates
    
    def save_to_file(self) -> None:
        """保存所有记录到文件"""
        output_path = Path(self.OUTPUT_DIR)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存翻译记录
        all_translations: list[dict] = []
        
        for item in self.section_translations:
            all_translations.append({
                "type": "section",
                "source": item["chinese"],
                "target": item["english"],
                "file": item["file"]
            })
        
        for item in self.key_translations:
            all_translations.append({
                "type": "key",
                "source": item["chinese"],
                "target": item["english"],
                "file": item["file"]
            })
        
        for item in self.value_translations:
            all_translations.append({
                "type": "value",
                "source": item["chinese"],
                "target": item["english"],
                "file": item["file"]
            })
        
        for item in self.text_translations:
            all_translations.append({
                "type": "text",
                "source": item["chinese"],
                "target": item["english"],
                "file": item["file"]
            })
        
        json_path = output_path / "查重记录.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_translations, f, ensure_ascii=False, indent=2)
        
        # 生成报告
        self._generate_report(output_path)
        
        print(f"\n查重记录已保存到: {output_path}")
        print(f"  - JSON记录: {json_path}")
    
    def _generate_report(self, output_path: Path) -> None:
        """生成查重报告"""
        stats_content = f"""# 查重报告
===================================

## 统计概览
- Section翻译次数: {len(self.section_translations)}
- Key翻译次数: {len(self.key_translations)}
- Value翻译次数: {len(self.value_translations)}
- 文本翻译次数: {len(self.text_translations)}
- 总查重次数: {len(self.section_translations) + len(self.key_translations) + len(self.value_translations) + len(self.text_translations)}

===================================
## 翻译库查重结果
===================================

### 英文键重复
"""
        if self.lib_duplicate_keys:
            for key in sorted(self.lib_duplicate_keys.keys(), key=lambda x: self.lib_duplicate_keys[x][0]):
                lines = self.lib_duplicate_keys[key]
                stats_content += f"- 键: {key}\n  出现位置: 第 {', '.join(map(str, lines))} 行\n"
        else:
            stats_content += "✓ 未发现重复的英文键\n"
        
        stats_content += f"""
### 中文值重复
"""
        if self.lib_duplicate_values:
            for value in sorted(self.lib_duplicate_values.keys()):
                entries = self.lib_duplicate_values[value]
                stats_content += f"- 中文值: {value}\n  对应英文键:\n"
                for key, line_num, entry_type in sorted(entries, key=lambda x: x[1]):
                    stats_content += f"    - [{entry_type}] {key} (第{line_num}行)\n"
        else:
            stats_content += "✓ 未发现重复的中文值\n"
        
        if len(self.section_translations) + len(self.key_translations) + len(self.value_translations) + len(self.text_translations) + len(self.lib_duplicate_keys) + len(self.lib_duplicate_values) > 0:
            stats_content += "\n\n⚠️  具有查重内容，请审核\n"
        else:
            stats_content += "\n\n✓ 无查重内容，可进行翻译\n"
        
        stats_content += f"""
===================================
项目查重结果
===================================

### Section翻译 ({len(self.section_translations)}项)
"""
        for item in self.section_translations[:50]:  # 只显示前50项
            stats_content += f"- [{item['chinese']}] -> [{item['english']}] ({item['file']})\n"
        if len(self.section_translations) > 50:
            stats_content += f"\n  ... 还有 {len(self.section_translations) - 50} 项未显示\n"
        
        stats_content += f"""
### Key翻译 ({len(self.key_translations)}项)
"""
        for item in self.key_translations[:50]:
            stats_content += f"- {item['chinese']} -> {item['english']} ({item['file']})\n"
        if len(self.key_translations) > 50:
            stats_content += f"\n  ... 还有 {len(self.key_translations) - 50} 项未显示\n"
        
        stats_content += f"""
### Value翻译 ({len(self.value_translations)}项)
"""
        for item in self.value_translations[:50]:
            stats_content += f"- {item['chinese']} -> {item['english']} ({item['file']})\n"
        if len(self.value_translations) > 50:
            stats_content += f"\n  ... 还有 {len(self.value_translations) - 50} 项未显示\n"
        
        stats_content += f"""
### 文本翻译 ({len(self.text_translations)}项)
"""
        for item in self.text_translations[:50]:
            stats_content += f"- {item['chinese']} -> {item['english']} ({item['file']})\n"
        if len(self.text_translations) > 50:
            stats_content += f"\n  ... 还有 {len(self.text_translations) - 50} 项未显示\n"
        
        stats_content += f"""
===================================
"""
        
        stats_path = output_path / "查重报告.txt"
        with open(stats_path, 'w', encoding='utf-8') as f:
            f.write(stats_content)


class TranslationLibraryChecker:
    """翻译库查重类"""
    
    LIB_PATHS: ClassVar[list[str]] = [
        "scripts/翻译库.txt",
        "翻译库.txt",
        "../scripts/翻译库.txt",
        "../../scripts/翻译库.txt"
    ]
    
    def __init__(self, lib_path: str | None = None) -> None:
        self.lib_path = lib_path
        self._find_library_path()
    
    def _find_library_path(self) -> str | None:
        """查找翻译库文件路径"""
        if self.lib_path and os.path.exists(self.lib_path):
            return self.lib_path
        
        for path in self.LIB_PATHS:
            if os.path.exists(path):
                self.lib_path = path
                return path
        return None
    
    def check_duplicates(self, ignore_section_key_duplicate=True):
        """检查翻译库文件中的重复项
        
        Args:
            ignore_section_key_duplicate: 是否忽略 Section 和 Key 之间的重复（默认True）
        
        Returns:
            (duplicate_keys, duplicate_values, total_keys)
        """
        if not self.lib_path:
            print("警告: 翻译库文件不存在")
            return {}, {}, 0
        
        # 存储所有键及其出现的行号和类型
        key_entries = defaultdict(list)
        # 存储所有中文值及其对应的英文键
        value_to_keys = defaultdict(list)
        
        with open(self.lib_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 匹配模式
        section_pattern = re.compile(r'^\s*\[([^\]]+)\]\s*=\s*\[([^\]]+)\]')
        key_pattern = re.compile(r'^\s*([^#\s\[][^=]*)\s*=')
        
        for line_num, line in enumerate(lines, 1):
            line = line.rstrip()
            
            # 跳过空行和纯注释行
            if not line or line.strip().startswith('#'):
                continue
            
            # 尝试匹配 Section 格式
            section_match = section_pattern.match(line)
            if section_match:
                key = section_match.group(1).strip()
                value = section_match.group(2).strip()
                key_entries[key].append((line_num, 'Section'))
                value_to_keys[value].append((key, line_num, 'Section'))
                continue
            
            # 尝试匹配普通键值对
            key_match = key_pattern.match(line)
            if key_match:
                key = key_match.group(1).strip()
                if '=' in line:
                    value_part = line.split('=', 1)[1].strip()
                    if key and not key.startswith('#'):
                        key_entries[key].append((line_num, 'Key'))
                        value_to_keys[value_part].append((key, line_num, 'Key'))
        
        # 找出重复的键
        duplicate_keys = {}
        for key, entries in key_entries.items():
            if len(entries) > 1:
                if ignore_section_key_duplicate:
                    types = set(e[1] for e in entries)
                    if len(types) == 2 and len(entries) == 2:
                        continue
                duplicate_keys[key] = [e[0] for e in entries]
        
        # 找出重复的中文值
        duplicate_values = {}
        for value, entries in value_to_keys.items():
            if len(entries) > 1:
                if ignore_section_key_duplicate and len(entries) == 2:
                    types = set(e[2] for e in entries)
                    if len(types) == 2:
                        continue
                duplicate_values[value] = entries
        
        return duplicate_keys, duplicate_values, len(key_entries)


class ReverseTranslationLibrary:
    """反向翻译库类，构建中文->英文的映射"""
    
    SPECIAL_VALUES: ClassVar[set[str]] = {
        'true', 'false', 'TRUE', 'FALSE', 'True', 'False',
        'LAND', 'WATER', 'HOVER', 'AIR', 'OVER_CLIFF', 'OVER_CLIFF_WATER',
        'AUTO', 'NONE'
    }
    
    LIB_PATHS: ClassVar[list[str]] = [
        "scripts/翻译库.txt",
        "翻译库.txt",
        "../scripts/翻译库.txt",
        "../../scripts/翻译库.txt"
    ]
    
    def __init__(self, lib_path: str | None = None) -> None:
        self.lib_path = lib_path
        self.translations: dict[str, str] = {}
        self.section_translations: dict[str, str] = {}
        self.value_translations: dict[str, str] = {}
        self._sorted_keys: list[str] = []
        self._compiled_patterns: dict[str, re.Pattern] = {}
        
        self._load_library()
        self._compile_patterns()
    
    def _find_library_path(self) -> str | None:
        if self.lib_path and os.path.exists(self.lib_path):
            return self.lib_path
        
        for path in self.LIB_PATHS:
            if os.path.exists(path):
                return path
        return None
    
    def _load_library(self) -> None:
        found_path = self._find_library_path()
        
        if not found_path:
            print(f"警告: 翻译库文件不存在，将使用默认路径继续")
            self.lib_path = self.LIB_PATHS[0]
            return
        
        self.lib_path = found_path
        
        try:
            content = Path(found_path).read_text(encoding='utf-8')
        except Exception as e:
            print(f"警告: 读取翻译库失败: {e}")
            return
        
        section_pattern = re.compile(r'^\[(.+?)\]\s*=\s*\[(.+?)\]$')
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if (match := section_pattern.match(line)):
                eng, chn = match.group(1).strip(), match.group(2).strip()
                self.section_translations[chn] = eng
                continue
            
            if '=' in line:
                eng, chn = (part.strip() for part in line.split('=', 1))
                
                if eng in self.SPECIAL_VALUES:
                    self.value_translations[chn] = eng
                else:
                    self.translations[chn] = eng
    
    def _compile_patterns(self) -> None:
        valid_keys = [
            k for k in self.translations.keys()
            if k not in self.translations.values()
        ]
        self._sorted_keys = sorted(valid_keys, key=len, reverse=True)
        
        self._compiled_patterns = {
            key: re.compile(r'\b' + re.escape(key) + r'\b')
            for key in self._sorted_keys
        }
    
    def get_translation(self, key: str) -> str:
        return self.translations.get(key, key)
    
    def get_section_translation(self, section: str) -> str:
        return self.section_translations.get(section, section)
    
    def get_value_translation(self, value: str) -> str:
        return self.value_translations.get(value, value)
    
    def translate_in_text(self, text: str) -> str:
        result = text
        for key in self._sorted_keys:
            if self._compiled_patterns[key].search(result):
                result = self._compiled_patterns[key].sub(
                    self.translations[key], result
                )
        return result
    
    @property
    def is_loaded(self) -> bool:
        return bool(self.translations or self.section_translations or self.value_translations)


class ReverseTranslator:
    """反向翻译器：中文 -> 英文"""
    
    VALID_EXTENSIONS: ClassVar[set[str]] = {'.ini', '.template'}
    DEFAULT_EXCLUDES: ClassVar[set[str]] = {'.git', '.vscode', '__pycache__', 'scripts'}
    
    SECTION_PATTERN: ClassVar[re.Pattern] = re.compile(r'^(\s*)\[([^\]]+)\](\s*)$')
    KV_PATTERN: ClassVar[re.Pattern] = re.compile(r'^(\s*)([^:=#\[]+?)([:=])(.*?)(\s*)$')
    
    def __init__(self, library: ReverseTranslationLibrary, log: TranslationLog | None = None) -> None:
        self.lib = library
        self.stats = TranslationStats()
        self.log = log or TranslationLog()
        self._current_file = ""
    
    def translate_file(self, input_path: Path, output_path: Path) -> bool:
        self._current_file = str(input_path)
        
        try:
            content = input_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"  [FAIL] 读取失败: {input_path} - {e}")
            self.stats.files_skipped += 1
            return False
        
        lines = content.split('\n')
        translated_lines: list[str] = []
        file_stats = TranslationStats()
        
        for line in lines:
            translated_line = self._translate_line(line, file_stats)
            translated_lines.append(translated_line)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            output_path.write_text('\n'.join(translated_lines), encoding='utf-8')
        except Exception as e:
            print(f"  [FAIL] 写入失败: {output_path} - {e}")
            self.stats.files_skipped += 1
            return False
        
        self.stats.merge(file_stats)
        self.stats.files_processed += 1
        return True
    
    def _translate_line(self, line: str, stats: TranslationStats) -> str:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            return line
        
        if (match := self.SECTION_PATTERN.match(line)):
            return self._translate_section_line(match, stats)
        
        if (match := self.KV_PATTERN.match(line)):
            return self._translate_kv_line(match, stats)
        
        return line
    
    def _translate_section_line(self, match: re.Match, stats: TranslationStats) -> str:
        indent, section_name, trailing = match.groups()
        
        comment = ''
        if '#' in section_name:
            section_name, comment_part = section_name.split('#', 1)
            section_name = section_name.strip()
            comment = '#' + comment_part
        
        original_section = section_name
        
        translated_section = self.lib.get_section_translation(section_name)
        if translated_section != section_name:
            stats.sections_translated += 1
            self.log.log_section_translation(section_name, translated_section, self._current_file)
            return f"{indent}[{translated_section}]{trailing}{comment}"
        
        if '_' in section_name:
            translated = self._translate_prefixed_section(section_name, stats)
            if translated != section_name:
                self.log.log_section_translation(section_name, translated, self._current_file)
                return f"{indent}[{translated}]{trailing}{comment}"
        
        return f"{indent}[{section_name}]{trailing}{comment}"
    
    def _translate_prefixed_section(self, section_name: str, stats: TranslationStats) -> str:
        parts = section_name.split('_', 1)
        if len(parts) != 2:
            return section_name
        
        prefix, suffix = parts
        
        translated_prefix = self.lib.get_section_translation(prefix)
        if translated_prefix == prefix:
            return section_name
        
        result = f"{translated_prefix}_{suffix}"
        self.log.log_section_translation(section_name, result, self._current_file)
        return result
    
    def _translate_kv_line(self, match: re.Match, stats: TranslationStats) -> str:
        indent, key, separator, value, trailing = match.groups()
        key = key.strip()
        value = value.strip()
        
        comment = ''
        if '#' in value:
            value, comment_part = value.split('#', 1)
            value = value.strip()
            comment = ' #' + comment_part
        
        translated_key = self.lib.get_translation(key)
        if translated_key != key:
            stats.keys_translated += 1
            self.log.log_key_translation(key, translated_key, self._current_file)
        
        translated_value = self._translate_value(value, stats)
        
        return f"{indent}{translated_key}{separator}{translated_value}{comment}"
    
    def _translate_value(self, value: str, stats: TranslationStats) -> str:
        if ',' in value:
            parts = [part.strip() for part in value.split(',')]
            translated_parts = []
            for part in parts:
                translated_part = self._translate_single_value(part, stats)
                translated_parts.append(translated_part)
            return ', '.join(translated_parts)
        
        return self._translate_single_value(value, stats)
    
    def _translate_single_value(self, value: str, stats: TranslationStats) -> str:
        translated = self.lib.get_value_translation(value)
        if translated != value:
            self.log.log_value_translation(value, translated, self._current_file)
            return translated
        
        original = value
        result = self.lib.translate_in_text(value)
        if result != original:
            self.log.log_text_translation(original, result, self._current_file)
        return result
    
    def translate_directory(
        self,
        input_dir: str,
        output_dir: str,
        exclude_dirs: set[str] | None = None,
        exclude_files: set[str] | None = None
    ) -> None:
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        if not input_path.exists():
            print(f"错误: 输入目录不存在: {input_dir}")
            return
        
        exclude_dirs = exclude_dirs or self.DEFAULT_EXCLUDES
        exclude_files = exclude_files or set()
        
        valid_files = self._collect_files(input_path, exclude_dirs, exclude_files)
        
        if not valid_files:
            print(f"警告: 在 {input_dir} 中未找到.ini或.template文件")
            return
        
        print(f"\n找到 {len(valid_files)} 个待查重文件")
        print("=" * 60)
        
        for file_path in valid_files:
            rel_path = file_path.relative_to(input_path)
            self.translate_file(file_path, output_path / rel_path)
        
        print("=" * 60)
        print("项目查重完成!")
        print(self.stats)
    
    def _collect_files(
        self,
        input_path: Path,
        exclude_dirs: set[str],
        exclude_files: set[str]
    ) -> list[Path]:
        valid_files: list[Path] = []
        
        for ext in self.VALID_EXTENSIONS:
            for file_path in input_path.rglob(f"*{ext}"):
                if any(excluded in file_path.parts for excluded in exclude_dirs):
                    continue
                if file_path.name in exclude_files:
                    continue
                valid_files.append(file_path)
        
        return sorted(valid_files)


class UnifiedChecker:
    """统一查重工具类"""
    
    def __init__(self) -> None:
        self.lib_checker = None
        self.translator = None
        self.translation_log = TranslationLog()
    
    def check_library(self, lib_path: str = "scripts/翻译库.txt", strict: bool = False) -> tuple:
        """检查翻译库重复"""
        print("\n" + "=" * 60)
        print("翻译库查重")
        print("=" * 60)
        
        self.lib_checker = TranslationLibraryChecker(lib_path)
        ignore_section_key_duplicate = not strict
        
        duplicate_keys, duplicate_values, total_keys = self.lib_checker.check_duplicates(ignore_section_key_duplicate)
        
        # 记录到日志
        self.translation_log.log_lib_duplicate_keys(duplicate_keys)
        self.translation_log.log_lib_duplicate_values(duplicate_values)
        
        print(f"\n总翻译项数: {total_keys}")
        print(f"英文键重复项: {len(duplicate_keys)}")
        print(f"中文值重复项: {len(duplicate_values)}")
        
        has_duplicates = False
        
        if duplicate_keys:
            has_duplicates = True
            print("\n" + "=" * 60)
            print("发现重复的英文键:")
            print("=" * 60)
            
            for key in sorted(duplicate_keys.keys(), key=lambda x: duplicate_keys[x][0]):
                lines = duplicate_keys[key]
                print(f"\n  键: {key}")
                print(f"  出现位置: 第 {', '.join(map(str, lines))} 行")
        
        if duplicate_values:
            has_duplicates = True
            print("\n" + "=" * 60)
            print("发现重复的中文值（不同英文键对应相同中文）:")
            print("=" * 60)
            
            for value in sorted(duplicate_values.keys()):
                entries = duplicate_values[value]
                print(f"\n  中文值: {value}")
                print(f"  对应英文键:")
                for key, line_num, entry_type in sorted(entries, key=lambda x: x[1]):
                    print(f"    - [{entry_type}] {key} (第{line_num}行)")
        
        if not has_duplicates:
            print("\n✓ 未发现任何重复项！")
        
        print("\n" + "=" * 60)
        print("翻译库查重完成")
        print("=" * 60)
        
        return duplicate_keys, duplicate_values, total_keys
    
    def check_project(self, input_dir: str = ".", output_dir: str = "scripts/数据集/还原后") -> TranslationStats:
        """检查项目重复"""
        print("\n" + "=" * 60)
        print("项目查重")
        print("=" * 60)
        print(f"输入目录: {os.path.abspath(input_dir)}")
        
        # 加载翻译库
        library = ReverseTranslationLibrary()
        
        if not library.is_loaded:
            print("\n警告: 翻译库未加载或为空，可能没有翻译效果")
        else:
            print(f"\n加载翻译库: {library.lib_path}")
            print(f"  已加载 {len(library.translations)} 个反向key映射")
            print(f"  已加载 {len(library.section_translations)} 个反向section映射")
            print(f"  已加载 {len(library.value_translations)} 个反向value映射")
        
        # 创建翻译器
        self.translator = ReverseTranslator(library, self.translation_log)
        self.translator.translate_directory(input_dir, output_dir)
        
        return self.translator.stats
    
    def run_all(self, lib_path: str = "scripts/翻译库.txt", input_dir: str = ".", output_dir: str = "scripts/数据集/还原后", strict: bool = False) -> None:
        """执行全部查重"""
        print("=" * 60)
        print("一键查重工具")
        print("=" * 60)
        print(f"翻译库: {lib_path}")
        print(f"项目目录: {os.path.abspath(input_dir)}")
        if strict:
            print("[严格模式] Section和Key同名也会被视为重复")
        
        # 翻译库查重
        self.check_library(lib_path, strict)
        
        # 项目查重
        self.check_project(input_dir, output_dir)
        
        # 保存记录
        self.translation_log.save_to_file()
        
        print("\n" + "=" * 60)
        print("一键查重完成！")
        print("=" * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='一键查重工具 - 合并翻译库查重和项目查重')
    parser.add_argument('--mode', choices=['all', 'lib', 'project'], default='all',
                        help='查重模式: all=全部, lib=仅翻译库, project=仅项目 (默认: all)')
    parser.add_argument('--lib', default='scripts/翻译库.txt',
                        help='翻译库文件路径 (默认: scripts/翻译库.txt)')
    parser.add_argument('--input', '-i', default='.',
                        help='项目输入目录 (默认: 当前目录)')
    parser.add_argument('--output', '-o', default='scripts/数据集/还原后',
                        help='项目查重输出目录 (默认: scripts/数据集/还原后)')
    parser.add_argument('--output-file', default='scripts/数据集/查重报告.txt',
                        help='查重报告输出路径 (默认: scripts/数据集/查重报告.txt)')
    parser.add_argument('--quiet', '-q', action='store_true', help='静默模式')
    parser.add_argument('--strict', action='store_true', help='严格模式，Section和Key同名也算重复')
    args = parser.parse_args()
    
    checker = UnifiedChecker()
    
    if args.mode == 'all':
        checker.run_all(args.lib, args.input, args.output, args.strict)
    elif args.mode == 'lib':
        duplicate_keys, duplicate_values, total_keys = checker.check_library(args.lib, args.strict)
        # 导出报告
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("翻译库查重报告\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"总翻译项数: {total_keys}\n")
            f.write(f"英文键重复项: {len(duplicate_keys)}\n")
            f.write(f"中文值重复项: {len(duplicate_values)}\n")
            
            if duplicate_keys:
                f.write("\n" + "=" * 60 + "\n")
                f.write("发现重复的英文键:\n")
                f.write("=" * 60 + "\n")
                for key in sorted(duplicate_keys.keys(), key=lambda x: duplicate_keys[x][0]):
                    lines = duplicate_keys[key]
                    f.write(f"\n  键: {key}\n")
                    f.write(f"  出现位置: 第 {', '.join(map(str, lines))} 行\n")
            
            if duplicate_values:
                f.write("\n" + "=" * 60 + "\n")
                f.write("发现重复的中文值:\n")
                f.write("=" * 60 + "\n")
                for value in sorted(duplicate_values.keys()):
                    entries = duplicate_values[value]
                    f.write(f"\n  中文值: {value}\n")
                    for key, line_num, entry_type in sorted(entries, key=lambda x: x[1]):
                        f.write(f"    - [{entry_type}] {key} (第{line_num}行)\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("查重完成\n")
            f.write("=" * 60 + "\n")
        
        if not args.quiet:
            print(f"\n报告已导出到: {args.output_file}")
    elif args.mode == 'project':
        stats = checker.check_project(args.input, args.output)
        checker.translation_log.save_to_file()


if __name__ == '__main__':
    main()
