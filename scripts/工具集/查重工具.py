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

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar


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
    """翻译记录类 - 记录所有被翻译的中文内容"""
    # 记录各类翻译内容
    section_translations: list[dict] = field(default_factory=list)
    key_translations: list[dict] = field(default_factory=list)
    value_translations: list[dict] = field(default_factory=list)
    text_translations: list[dict] = field(default_factory=list)
    
    # 输出目录
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
    
    def save_to_file(self) -> None:
        """保存翻译记录到文件"""
        output_path = Path(self.OUTPUT_DIR)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存所有翻译记录到一个文件
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
        
        # 写入JSON文件
        json_path = output_path / "查重记录.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_translations, f, ensure_ascii=False, indent=2)
        
        # 写入统计信息
        stats_content = f"""# 查重报告
====================================

## 统计概览
- Section翻译次数: {len(self.section_translations)}
- Key翻译次数: {len(self.key_translations)}
- Value翻译次数: {len(self.value_translations)}
- 文本翻译次数: {len(self.text_translations)}
- 总翻译次数: {len(all_translations)}

## 各类翻译详情

### Section翻译 ({len(self.section_translations)}项)
"""
        for item in self.section_translations:
            stats_content += f"- [{item['chinese']}] -> [{item['english']}] ({item['file']})\n"
        
        stats_content += f"""
### Key翻译 ({len(self.key_translations)}项)
"""
        for item in self.key_translations:
            stats_content += f"- {item['chinese']} -> {item['english']} ({item['file']})\n"
        
        stats_content += f"""
### Value翻译 ({len(self.value_translations)}项)
"""
        for item in self.value_translations:
            stats_content += f"- {item['chinese']} -> {item['english']} ({item['file']})\n"
        
        stats_content += f"""
### 文本翻译 ({len(self.text_translations)}项)
"""
        for item in self.text_translations:
            stats_content += f"- {item['chinese']} -> {item['english']} ({item['file']})\n"
        
        stats_path = output_path / "查重报告.txt"
        with open(stats_path, 'w', encoding='utf-8') as f:
            f.write(stats_content)
        
        print(f"\n查重记录已保存到: {output_path}")
        print(f"  - JSON记录: {json_path}")
        print(f"  - 报告文件: {stats_path}")


class ReverseTranslationLibrary:
    """
    反向翻译库类，构建中文->英文的映射

    功能:
        与TranslationLibrary相反，构建中文到英文的反向映射
        用于将已翻译的中文INI文件转换回英文

    与正向翻译的区别:
        - 正向: 读取 [english] = [中文]，建立 eng->chn 映射
        - 反向: 读取 [english] = [中文]，建立 chn->eng 映射（反向）

    使用场景:
        将已经翻译成中文的INI文件还原为英文，方便版本对比或更新
    """

    # 原始英文特殊值（用于识别哪些value需要特殊处理）
    SPECIAL_VALUES: ClassVar[set[str]] = {
        'true', 'false', 'TRUE', 'FALSE', 'True', 'False',
        'LAND', 'WATER', 'HOVER', 'AIR', 'OVER_CLIFF', 'OVER_CLIFF_WATER',
        'AUTO', 'NONE'
    }

    # 翻译库可能的路径
    LIB_PATHS: ClassVar[list[str]] = [
        "scripts/翻译库.txt",
        "翻译库.txt",
        "../scripts/翻译库.txt",
        "../../scripts/翻译库.txt"
    ]

    def __init__(self, lib_path: str | None = None) -> None:
        self.lib_path = lib_path
        # 反向映射表：中文 -> 英文
        self.translations: dict[str, str] = {}
        self.section_translations: dict[str, str] = {}
        self.value_translations: dict[str, str] = {}
        self._sorted_keys: list[str] = []
        self._compiled_patterns: dict[str, re.Pattern] = {}

        self._load_library()
        self._compile_patterns()

    def _find_library_path(self) -> str | None:
        """查找翻译库文件路径"""
        if self.lib_path and os.path.exists(self.lib_path):
            return self.lib_path

        for path in self.LIB_PATHS:
            if os.path.exists(path):
                return path
        return None

    def _load_library(self) -> None:
        """加载翻译库文件并构建反向映射"""
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

        # Section 翻译的正则
        section_pattern = re.compile(r'^\[(.+?)\]\s*=\s*\[(.+?)\]$')

        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # 解析 [key] = [value] 格式的Section翻译
            if (match := section_pattern.match(line)):
                eng, chn = match.group(1).strip(), match.group(2).strip()
                # 反向映射：中文 -> 英文
                self.section_translations[chn] = eng
                continue

            # 解析 key = value 格式的翻译
            if '=' in line:
                eng, chn = (part.strip() for part in line.split('=', 1))

                # 区分key翻译和value翻译，构建反向映射
                if eng in self.SPECIAL_VALUES:
                    self.value_translations[chn] = eng
                else:
                    self.translations[chn] = eng

    def _compile_patterns(self) -> None:
        """预编译正则表达式模式以提高性能"""
        # 过滤掉英文key，避免重复替换
        valid_keys = [
            k for k in self.translations.keys()
            if k not in self.translations.values()
        ]
        # 按长度降序排序，避免短词替换长词的一部分
        self._sorted_keys = sorted(valid_keys, key=len, reverse=True)

        self._compiled_patterns = {
            key: re.compile(r'\b' + re.escape(key) + r'\b')
            for key in self._sorted_keys
        }

    def get_translation(self, key: str) -> str:
        """获取中文key对应的英文翻译"""
        return self.translations.get(key, key)

    def get_section_translation(self, section: str) -> str:
        """获取中文Section名称对应的英文"""
        return self.section_translations.get(section, section)

    def get_value_translation(self, value: str) -> str:
        """获取中文value对应的英文"""
        return self.value_translations.get(value, value)

    def translate_in_text(self, text: str, stats: TranslationStats | None = None) -> str:
        """在文本中反向翻译所有匹配的中文key"""
        result = text
        for key in self._sorted_keys:
            if self._compiled_patterns[key].search(result):
                result = self._compiled_patterns[key].sub(
                    self.translations[key], result
                )
                if stats:
                    stats.lines_translated += 1
        return result

    @property
    def is_loaded(self) -> bool:
        """检查是否成功加载了翻译数据"""
        return bool(self.translations or self.section_translations or self.value_translations)


class ReverseTranslator:
    """
    反向翻译器：中文 -> 英文

    功能:
        将中文INI文件翻译回英文
        逻辑与INITranslator类似，但使用反向映射（中文->英文）

    与正向翻译器的区别:
        - 使用 ReverseTranslationLibrary（中文->英文映射）
        - 不需要处理 global_resource_XX 特殊规则（因为已经翻译成中文了）
        - 其他处理逻辑完全相同

    使用场景:
        当需要将已翻译的中文版本还原为英文时（如对比原版、更新版本等）
    """

    VALID_EXTENSIONS: ClassVar[set[str]] = {'.ini', '.template'}
    DEFAULT_EXCLUDES: ClassVar[set[str]] = {'.git', '.vscode', '__pycache__', 'scripts'}

    # 预编译的正则表达式（与正向翻译器相同）
    SECTION_PATTERN: ClassVar[re.Pattern] = re.compile(r'^(\s*)\[([^\]]+)\](\s*)$')
    KV_PATTERN: ClassVar[re.Pattern] = re.compile(r'^(\s*)([^:=#\[]+?)([:=])(.*?)(\s*)$')

    def __init__(self, library: ReverseTranslationLibrary, log: TranslationLog | None = None) -> None:
        self.lib = library
        self.stats = TranslationStats()
        self.log = log or TranslationLog()
        self._current_file = ""  # 当前正在处理的文件路径

    def translate_file(self, input_path: Path, output_path: Path) -> bool:
        """反向翻译单个文件（中文->英文）"""
        # 设置当前处理的文件路径（相对路径）
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

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            output_path.write_text('\n'.join(translated_lines), encoding='utf-8')
        except Exception as e:
            print(f"  [FAIL] 写入失败: {output_path} - {e}")
            self.stats.files_skipped += 1
            return False

        self.stats.merge(file_stats)
        self.stats.files_processed += 1
        print(f"  [OK] 已反向翻译: {input_path}")
        return True

    def _translate_line(self, line: str, stats: TranslationStats) -> str:
        """反向翻译单行内容（中文->英文）"""
        # 跳过空行和纯注释行
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            return line

        # 处理Section行 [section_name]
        if (match := self.SECTION_PATTERN.match(line)):
            return self._translate_section_line(match, stats)

        # 处理键值对 key: value 或 key = value
        if (match := self.KV_PATTERN.match(line)):
            return self._translate_kv_line(match, stats)

        return line

    def _translate_section_line(self, match: re.Match, stats: TranslationStats) -> str:
        """
        反向翻译Section行（中文 -> 英文）

        处理流程（按优先级）:
            1. 处理带#注释的section（分离注释部分）
            2. 尝试完整section名称匹配（在反向映射中查找）
            3. 处理带下划线的section（分割前缀和后缀，只翻译前缀）
            4. 以上都不匹配则原样返回

        Args:
            match: 正则匹配结果，groups: (缩进, section名称, 尾部空白)
            stats: 统计对象，用于记录翻译数量

        Returns:
            反向翻译后的section行字符串

        示例:
            [全局_资源] -> [global_resource]          （完整匹配）
            [隐藏动作_陆军协防] -> [hiddenAction_陆军协防]  （前缀翻译）

        注意:
            与正向翻译不同，反向翻译不需要处理 global_resource_XX 特殊规则
            因为这些section已经被翻译成中文格式了
        """
        indent, section_name, trailing = match.groups()

        # 处理带注释的section
        comment = ''
        if '#' in section_name:
            section_name, comment_part = section_name.split('#', 1)
            section_name = section_name.strip()
            comment = '#' + comment_part

        original_section = section_name

        # 1. 首先尝试完整section匹配（如 [全局_资源] -> [global_resource]）
        # 在反向映射中查找：中文 -> 英文
        translated_section = self.lib.get_section_translation(section_name)
        if translated_section != section_name:
            stats.sections_translated += 1
            # 记录翻译
            self.log.log_section_translation(section_name, translated_section, self._current_file)
            return f"{indent}[{translated_section}]{trailing}{comment}"

        # 2. 处理带下划线的section名称（如 [隐藏动作_陆军协防]）
        # 分割前缀和后缀，只翻译前缀部分（中文前缀 -> 英文前缀）
        if '_' in section_name:
            translated = self._translate_prefixed_section(section_name, stats)
            if translated != section_name:
                # 记录翻译
                self.log.log_section_translation(section_name, translated, self._current_file)
                return f"{indent}[{translated}]{trailing}{comment}"

        return f"{indent}[{section_name}]{trailing}{comment}"

    def _translate_prefixed_section(self, section_name: str, stats: TranslationStats) -> str:
        """
        反向翻译带前缀的section名称（如 隐藏动作_陆军协防 -> hiddenAction_陆军协防）

        功能:
            将section名称按下划线分割为前缀和后缀，只翻译前缀部分
            前缀从中文翻译回英文，后缀保持原样

        Args:
            section_name: section名称（不含方括号），如 "隐藏动作_陆军协防"
            stats: 统计对象（暂未使用，保持接口一致性）

        Returns:
            反向翻译后的section名称，如 "hiddenAction_陆军协防"
            如果前缀没有对应的英文翻译，则返回原名称

        注意:
            - 与正向翻译逻辑相同，只是映射方向相反（中文->英文）
            - 需要在翻译库中有反向映射（如 [hiddenAction] = [隐藏动作] 会被反向解析）
        """
        # 分割前缀和后缀（只分割一次，保留后续所有内容）
        parts = section_name.split('_', 1)
        if len(parts) != 2:
            return section_name

        prefix, suffix = parts

        # 在反向映射中查找前缀的翻译（中文前缀 -> 英文前缀）
        translated_prefix = self.lib.get_section_translation(prefix)
        if translated_prefix == prefix:
            # 前缀没有对应的翻译，返回原值不变
            return section_name

        # 找到了前缀翻译，组合成新名称（后缀保持原样）
        result = f"{translated_prefix}_{suffix}"
        # 记录翻译（记录完整section）
        self.log.log_section_translation(section_name, result, self._current_file)
        return result

    def _translate_kv_line(self, match: re.Match, stats: TranslationStats) -> str:
        """翻译键值对行"""
        indent, key, separator, value, trailing = match.groups()
        key = key.strip()
        value = value.strip()

        # 分离注释
        comment = ''
        if '#' in value:
            value, comment_part = value.split('#', 1)
            value = value.strip()
            comment = ' #' + comment_part

        # 反向翻译key
        translated_key = self.lib.get_translation(key)
        if translated_key != key:
            stats.keys_translated += 1
            # 记录key翻译
            self.log.log_key_translation(key, translated_key, self._current_file)

        # 反向翻译value
        translated_value = self._translate_value(value, stats)

        return f"{indent}{translated_key}{separator}{translated_value}{comment}"

    def _translate_value(self, value: str, stats: TranslationStats) -> str:
        """反向翻译value值（中文->英文）"""
        # 处理逗号分隔的多个值
        if ',' in value:
            parts = [part.strip() for part in value.split(',')]
            translated_parts = []
            changed = False
            for part in parts:
                translated_part = self._translate_single_value(part, stats)
                if translated_part != part:
                    changed = True
                translated_parts.append(translated_part)
            if changed:
                stats.lines_translated += 1
            return ', '.join(translated_parts)

        # 单值翻译
        return self._translate_single_value(value, stats)

    def _translate_single_value(self, value: str, stats: TranslationStats) -> str:
        """翻译单个value值"""
        # 首先检查是否在value_translations中
        translated = self.lib.get_value_translation(value)
        if translated != value:
            # 记录value翻译
            self.log.log_value_translation(value, translated, self._current_file)
            return translated

        # 反向翻译value中出现的中文标识符
        original = value
        result = self.lib.translate_in_text(value, stats)
        if result != original:
            # 记录文本翻译
            self.log.log_text_translation(original, result, self._current_file)
        return result

    def translate_directory(
        self,
        input_dir: str,
        output_dir: str,
        exclude_dirs: set[str] | None = None,
        exclude_files: set[str] | None = None
    ) -> None:
        """反向翻译整个目录下的所有有效文件"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)

        if not input_path.exists():
            print(f"错误: 输入目录不存在: {input_dir}")
            return

        exclude_dirs = exclude_dirs or self.DEFAULT_EXCLUDES
        exclude_files = exclude_files or set()

        # 获取所有有效文件
        valid_files = self._collect_files(input_path, exclude_dirs, exclude_files)

        if not valid_files:
            print(f"警告: 在 {input_dir} 中未找到.ini或.template文件")
            return

        print(f"\n找到 {len(valid_files)} 个待反向翻译文件")
        print("=" * 60)

        for file_path in valid_files:
            rel_path = file_path.relative_to(input_path)
            self.translate_file(file_path, output_path / rel_path)

        print("=" * 60)
        print(f"反向翻译完成!")
        print(self.stats)

    def _collect_files(
        self,
        input_path: Path,
        exclude_dirs: set[str],
        exclude_files: set[str]
    ) -> list[Path]:
        """收集所有需要翻译的文件"""
        valid_files: list[Path] = []

        for ext in self.VALID_EXTENSIONS:
            for file_path in input_path.rglob(f"*{ext}"):
                # 检查是否在排除目录中
                if any(excluded in file_path.parts for excluded in exclude_dirs):
                    continue
                # 检查文件名是否在排除列表中
                if file_path.name in exclude_files:
                    continue
                valid_files.append(file_path)

        return sorted(valid_files)


def main() -> None:
    """主函数"""
    input_dir = sys.argv[1] if len(sys.argv) >= 2 else "."
    output_dir = sys.argv[2] if len(sys.argv) >= 3 else "scripts/数据集/还原后"

    print("=" * 60)
    print("反向翻译脚本 - 中文INI/Template文件转英文工具")
    print("=" * 60)
    print(f"输入目录: {os.path.abspath(input_dir)}")
    print(f"输出目录: {os.path.abspath(output_dir)}")

    # 加载翻译库
    library = ReverseTranslationLibrary()

    if not library.is_loaded:
        print("\n警告: 翻译库未加载或为空，可能没有翻译效果")
    else:
        print(f"\n加载翻译库: {library.lib_path}")
        print(f"  已加载 {len(library.translations)} 个反向key映射")
        print(f"  已加载 {len(library.section_translations)} 个反向section映射")
        print(f"  已加载 {len(library.value_translations)} 个反向value映射")

    # 创建翻译记录器
    translation_log = TranslationLog()
    
    # 创建翻译器并执行反向翻译
    translator = ReverseTranslator(library, translation_log)
    translator.translate_directory(input_dir, output_dir)
    
    # 保存翻译记录
    translation_log.save_to_file()

    print("\n" + "=" * 60)
    if input_dir == output_dir:
        print("反向翻译完成！所有文件已直接覆盖更新")
    else:
        print(f"反向翻译完成！结果已保存到: {os.path.abspath(output_dir)}")


if __name__ == "__main__":
    main()
