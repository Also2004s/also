#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单位性能占用计算脚本
用于计算铁锈战争Mod中每个单位的性能占用
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class UnitData:
    """单位数据类"""
    name: str = ""
    file_path: str = ""
    
    # 继承关系
    inherited_templates: List[str] = field(default_factory=list)
    
    # 性能指标
    path_point_action_types: int = 0  # 添加路径点动作类型数量
    clear_all_waypoints: int = 0  # 清除所有路径点数量
    set_unit_memory: int = 0  # 设置单位内存数量
    logic_resource_count: int = 0  # 用逻辑设置资源数量
    
    # 自动触发隐藏行动
    auto_trigger_actions: int = 0  # 自动触发的隐藏行动数量
    auto_trigger_conditions: int = 0  # 自动触发条件数量
    
    # 非自动触发隐藏行动
    non_auto_trigger_actions: int = 0  # 非自动触发的隐藏行动数量
    non_auto_trigger_conditions: int = 0  # 非自动触发条件数量
    
    # 触发间隔
    trigger_interval_frames: int = 60  # 自动触发间隔（帧），默认60帧
    trigger_check_rate: int = 1  # 自动触发检查率（帧），默认1帧
    
    # 原始值（用于显示）
    raw_interval: str = "60帧(默认)"
    raw_check_rate: str = "每1帧(默认)"


class UnitPerformanceCalculator:
    """单位性能占用计算器"""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.units: Dict[str, UnitData] = {}
        self.template_cache: Dict[str, str] = {}  # 模板缓存
        
    def scan_all_units(self):
        """扫描所有单位文件"""
        unit_extensions = {'.ini', '.lua'}
        skip_patterns = {'数据集', '__pycache__', '.git', 'scripts'}
        
        for root, dirs, files in os.walk(self.workspace_root):
            # 跳过不需要的目录
            dirs[:] = [d for d in dirs if not any(skip in d for skip in skip_patterns)]
            
            for file in files:
                if os.path.splitext(file)[1].lower() in unit_extensions:
                    file_path = os.path.join(root, file)
                    # 跳过模板文件和通用模块
                    if '.template' in file or '模版' in file:
                        continue
                    self.parse_unit_file(file_path)
    
    def parse_unit_file(self, file_path: str):
        """解析单个单位文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            return
        
        unit_data = UnitData()
        unit_data.file_path = file_path
        
        # 提取单位名称
        name_match = re.search(r'\[核心\]\s*name:(.+)', content)
        if name_match:
            unit_data.name = name_match.group(1).strip()
        else:
            # 使用文件名作为名称
            unit_data.name = Path(file_path).stem
        
        # 解析继承关系
        unit_data.inherited_templates = self.parse_inheritance(content, file_path)
        
        # 合并模板内容
        merged_content = self.merge_templates(content, unit_data.inherited_templates, file_path)
        
        # 解析性能指标
        self.parse_performance_metrics(merged_content, unit_data)
        
        # 存储单位数据
        key = f"{unit_data.name}_{file_path}"
        self.units[key] = unit_data
    
    def parse_inheritance(self, content: str, file_path: str) -> List[str]:
        """解析继承关系"""
        templates = []
        
        # 1. 解析复制与:xxx.ini的继承关系（支持多个模板，逗号分隔）
        copy_match = re.search(r'复制与:\s*(.+)', content)
        if copy_match:
            template_path = copy_match.group(1).strip()
            # 处理多个模板（逗号分隔）
            for tpl in template_path.split(','):
                tpl = tpl.strip()
                if tpl:
                    templates.append(tpl)
        
        # 2. 向上递归查找template文件，找到第一个就停止
        current_dir = os.path.dirname(file_path)
        found_template = False
        
        while current_dir and current_dir.startswith(str(self.workspace_root)):
            if found_template:
                break
                
            # 检查.template文件
            template_file = os.path.join(current_dir, '.template')
            if os.path.exists(template_file):
                templates.append(template_file)
                found_template = True
                break
            
            # 检查all-units.template文件
            all_template = os.path.join(current_dir, 'all-units.template')
            if os.path.exists(all_template):
                templates.append(all_template)
                found_template = True
                break
            
            # 移动到上级目录
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                break
            current_dir = parent_dir
        
        return templates
    
    def merge_templates(self, content: str, templates: List[str], file_path: str) -> str:
        """合并模板内容"""
        merged = content
        
        for template in templates:
            template_content = self.get_template_content(template, file_path)
            if template_content:
                merged += "\n" + template_content
        
        return merged
    
    def get_template_content(self, template: str, source_file: str) -> str:
        """获取模板文件内容"""
        if not template:
            return ""
        
        # 检查缓存
        cache_key = f"{template}_{source_file}"
        if cache_key in self.template_cache:
            return self.template_cache[cache_key]
        
        template_content = ""
        full_path = None
        
        # 处理绝对路径或ROOT:前缀
        if template.startswith('ROOT:'):
            template_path = template[5:]
            full_path = os.path.join(self.workspace_root, template_path)
        elif template.startswith('/'):
            full_path = os.path.join(self.workspace_root, template[1:])
        elif os.path.isabs(template):
            full_path = template
        else:
            # 相对路径 - 先尝试同目录
            source_dir = os.path.dirname(source_file)
            
            # 如果模板路径包含目录分隔符，直接拼接
            if '/' in template or '\\' in template:
                full_path = os.path.join(source_dir, template)
            else:
                # 可能是同目录的模板文件（不带路径）
                # 尝试多种可能的文件名
                source_ext = os.path.splitext(source_file)[1]
                template_name = os.path.splitext(template)[0] if template.endswith(('.ini', '.template')) else template
                
                # 优先查找同目录下的文件
                potential_paths = [
                    os.path.join(source_dir, template),  # 原始名称
                    os.path.join(source_dir, f"{template_name}.ini"),
                    os.path.join(source_dir, f"{template_name}.template"),
                ]
                
                for path in potential_paths:
                    if os.path.exists(path):
                        full_path = path
                        break
                
                # 如果没找到，尝试从源文件所在目录向上查找
                if not full_path or not os.path.exists(full_path):
                    # 检查模板是否在源文件目录树中
                    check_dir = source_dir
                    while check_dir and check_dir.startswith(str(self.workspace_root)):
                        potential = os.path.join(check_dir, template)
                        if os.path.exists(potential):
                            full_path = potential
                            break
                        parent = os.path.dirname(check_dir)
                        if parent == check_dir:
                            break
                        check_dir = parent
        
        if full_path and os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                self.template_cache[cache_key] = template_content
            except (UnicodeDecodeError, FileNotFoundError):
                pass
        
        return template_content
    
    def parse_performance_metrics(self, content: str, unit_data: UnitData):
        """解析性能指标"""
        
        # 1. 解析自动触发间隔
        # 格式: 自动触发间隔:2s 或 自动触发间隔:120 或 自动触发间隔:每8帧
        interval_match = re.search(r'自动触发间隔:\s*(.+)', content)
        if interval_match:
            raw_interval = interval_match.group(1).strip()
            unit_data.raw_interval = raw_interval
            unit_data.trigger_interval_frames = self.parse_interval(raw_interval)
        
        # 2. 解析自动触发检查率
        # 格式: 自动触发检查率:每8帧
        check_rate_match = re.search(r'自动触发检查率:\s*(.+)', content)
        if check_rate_match:
            raw_check_rate = check_rate_match.group(1).strip()
            unit_data.raw_check_rate = raw_check_rate
            unit_data.trigger_check_rate = self.parse_check_rate(raw_check_rate)
        
        # 3. 解析添加路径点动作类型
        path_point_matches = re.findall(r'添加路径点动作类型:', content)
        unit_data.path_point_action_types = len(path_point_matches)
        
        # 4. 解析清除所有路径点
        clear_waypoint_matches = re.findall(r'清除所有路径点:', content)
        unit_data.clear_all_waypoints = len(clear_waypoint_matches)
        
        # 5. 解析设置单位内存
        memory_matches = re.findall(r'设置单位内存:', content)
        unit_data.set_unit_memory = len(memory_matches)
        
        # 6. 解析隐藏行动
        action_sections = re.findall(r'\[隐藏行动[^\]]*\]', content)
        
        for action_section in action_sections:
            # 找到该行动块的内容范围
            section_start = content.find(action_section)
            next_section = content.find('[', section_start + 1)
            if next_section == -1:
                section_content = content[section_start:]
            else:
                section_content = content[section_start:next_section]
            
            # 判断是否自动触发（支持"自动触发:真"或"自动触发:if"格式）
            is_auto_trigger = '自动触发:真' in section_content or '自动触发:if' in section_content
            
            # 解析自动触发条件数量
            if is_auto_trigger:
                auto_cond_match = re.search(r'自动触发:\s*if\s+(.+)', section_content)
                if auto_cond_match:
                    conditions = auto_cond_match.group(1)
                    # 统计条件变量（排除 if/and/or 关键字，只保留实际条件）
                    keywords = {'if', 'and', 'or'}
                    cond_vars = [v for v in re.findall(r'\b[A-Za-z0-9_]+\b', conditions) if v.lower() not in keywords]
                    unit_data.auto_trigger_conditions += len(cond_vars)
            
            # 判断是否需要条件
            has_condition = '需要条件:' in section_content
            
            # 解析需要条件数量
            if has_condition:
                cond_match = re.search(r'需要条件:\s*if\s+(.+)', section_content)
                if cond_match:
                    conditions = cond_match.group(1)
                    # 统计条件变量（排除 if/and/or 关键字，只保留实际条件）
                    keywords = {'if', 'and', 'or'}
                    cond_vars = [v for v in re.findall(r'\b[A-Za-z0-9_]+\b', conditions) if v.lower() not in keywords]
                    unit_data.non_auto_trigger_conditions += len(cond_vars)
            
            # 判断是否用逻辑设置资源
            has_logic_resource = '用逻辑设置资源:' in section_content or '用逻辑添加资源:' in section_content
            
            # 统计逻辑设置资源数量
            if has_logic_resource:
                resource_matches = re.findall(r'(?:用逻辑设置资源|用逻辑添加资源):(.+)', section_content)
                for match in resource_matches:
                    # 计算资源设置的数量（通过逗号分隔）
                    resources = match.split(',')
                    unit_data.logic_resource_count += len(resources)
            
            if is_auto_trigger:
                unit_data.auto_trigger_actions += 1
            else:
                unit_data.non_auto_trigger_actions += 1
    
    def parse_interval(self, raw_interval: str) -> int:
        """解析自动触发间隔"""
        raw = raw_interval.strip().lower()
        
        # 帧格式: "120" 或 "120帧"
        frame_match = re.match(r'^(\d+)\s*帧?$', raw)
        if frame_match:
            return int(frame_match.group(1))
        
        # 时间格式: "2s" 或 "2.0s" 或 "0.4s"
        time_match = re.match(r'^([\d.]+)\s*s$', raw)
        if time_match:
            seconds = float(time_match.group(1))
            # 2秒 = 120帧，所以60帧/秒
            return int(seconds * 60)
        
        # 默认60帧
        return 60
    
    def parse_check_rate(self, raw_check_rate: str) -> int:
        """解析自动触发检查率"""
        raw = raw_check_rate.strip().lower()
        
        # 格式: "每8帧"
        match = re.match(r'^每(\d+)\s*帧?$', raw)
        if match:
            return int(match.group(1))
        
        # 默认1帧（每帧检查）
        return 1
    
    def calculate_performance_score(self, unit_data: UnitData) -> float:
        """计算性能占用分数"""
        # 新公式:
        # (添加路径点动作类型数量*3 + 清除所有路径点*3 + 设置单位内存*10 + 用逻辑设置资源数量*8 + 
        # 自动触发的隐藏行动数量*(0.1+自动触发条件数量*0.025+需要条件数量*0.01) + 
        # 非自动触发的隐藏行动数量*(0.01+需要条件数量*0.01)) / (自动触发间隔/60)
        
        # 避免除零
        if unit_data.trigger_interval_frames <= 0:
            return 0.0
        
        # 计算自动触发部分的贡献
        auto_trigger_contribution = unit_data.auto_trigger_actions * (
            0.1 + unit_data.auto_trigger_conditions * 0.025 + unit_data.non_auto_trigger_conditions * 0.01
        )
        
        # 计算非自动触发部分的贡献
        non_auto_trigger_contribution = unit_data.non_auto_trigger_actions * (
            0.01 + unit_data.non_auto_trigger_conditions * 0.01
        )
        
        # 总和
        total = (
            unit_data.path_point_action_types * 3 +
            unit_data.clear_all_waypoints * 3 +
            unit_data.set_unit_memory * 10 +
            unit_data.logic_resource_count * 8 +
            auto_trigger_contribution +
            non_auto_trigger_contribution
        )
        
        # 除以间隔（转换为60帧基准）
        score = total / (unit_data.trigger_interval_frames / 60)
        
        return round(score, 2)
    
    def check_divisibility(self, unit_data: UnitData) -> Tuple[bool, str]:
        """检查整除性"""
        # 默认检查率为1帧（每帧检查）
        check_rate = unit_data.trigger_check_rate if unit_data.trigger_check_rate > 0 else 1
        
        if unit_data.trigger_interval_frames % check_rate == 0:
            return True, "正常"
        else:
            return False, "错误"
    
    def generate_report(self, output_file: str = None):
        """生成分析报告"""
        results = []
        errors = []
        total_score = 0.0
        
        for key, unit_data in self.units.items():
            score = self.calculate_performance_score(unit_data)
            is_valid, status = self.check_divisibility(unit_data)
            
            total_score += score
            
            result = {
                'name': unit_data.name,
                'path_actions': unit_data.path_point_action_types,
                'clear_waypoints': unit_data.clear_all_waypoints,
                'set_memory': unit_data.set_unit_memory,
                'logic_resources': unit_data.logic_resource_count,
                'auto_trigger_actions': unit_data.auto_trigger_actions,
                'auto_trigger_conditions': unit_data.auto_trigger_conditions,
                'non_auto_trigger_actions': unit_data.non_auto_trigger_actions,
                'non_auto_trigger_conditions': unit_data.non_auto_trigger_conditions,
                'trigger_interval': unit_data.raw_interval,
                'check_rate': unit_data.raw_check_rate,
                'performance_score': score,
                'status': status,
                'file_path': unit_data.file_path
            }
            results.append(result)
            
            if not is_valid:
                errors.append({
                    'name': unit_data.name,
                    'interval': unit_data.raw_interval,
                    'check_rate': unit_data.raw_check_rate
                })
        
        # 生成报告文本
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("单位性能占用分析报告")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"扫描单位数量: {len(self.units)}")
        report_lines.append(f"总路径点动作类型数: {sum(u.path_point_action_types for u in self.units.values())}")
        report_lines.append(f"总清除路径点次数: {sum(u.clear_all_waypoints for u in self.units.values())}")
        report_lines.append(f"总设置单位内存次数: {sum(u.set_unit_memory for u in self.units.values())}")
        report_lines.append(f"总逻辑设置资源数: {sum(u.logic_resource_count for u in self.units.values())}")
        report_lines.append(f"总自动触发隐藏行动数: {sum(u.auto_trigger_actions for u in self.units.values())}")
        report_lines.append(f"总自动触发条件数: {sum(u.auto_trigger_conditions for u in self.units.values())}")
        report_lines.append(f"总非自动触发隐藏行动数: {sum(u.non_auto_trigger_actions for u in self.units.values())}")
        report_lines.append(f"总非自动触发条件数: {sum(u.non_auto_trigger_conditions for u in self.units.values())}")
        report_lines.append(f"总性能占用分数: {total_score:.2f}")
        report_lines.append("")
        
        # 整除性错误
        if errors:
            report_lines.append("=" * 80)
            report_lines.append(f"整除性错误 (共{len(errors)}个)")
            report_lines.append("=" * 80)
            for error in errors:
                report_lines.append(f"\n{error['name']}:")
                report_lines.append(f"  - 间隔({error['interval']})不能被检查率({error['check_rate']})整除")
            report_lines.append("")
        
        # 详细列表
        report_lines.append("=" * 80)
        report_lines.append("单位详细性能分析")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"{'单位名称':<6} {'路径':<6} {'清路径':<6} {'内存':<6} {'逻辑':<6} {'自动':<6} {'条':<4} {'非自':<6} {'条':<4} {'占用':<10} {'状态':<6}")
        report_lines.append("-" * 100)
        
        # 按性能分数排序
        sorted_results = sorted(results, key=lambda x: x['performance_score'], reverse=True)
        
        for r in sorted_results:
            report_lines.append(
                f"{r['name']:<6} "
                f"{r['path_actions']:<6} "
                f"{r['clear_waypoints']:<6} "
                f"{r['set_memory']:<6} "
                f"{r['logic_resources']:<6} "
                f"{r['auto_trigger_actions']:<6} "
                f"{r['auto_trigger_conditions']:<4} "
                f"{r['non_auto_trigger_actions']:<6} "
                f"{r['non_auto_trigger_conditions']:<4} "
                f"{r['performance_score']:<10.2f} "
                f"{r['status']:<6}"
            )
        
        report_lines.append("")
        
        # 继承关系
        report_lines.append("=" * 80)
        report_lines.append("模板继承关系")
        report_lines.append("=" * 80)
        
        for key, unit_data in self.units.items():
            if unit_data.inherited_templates:
                report_lines.append(f"\n{unit_data.name}:")
                for template in unit_data.inherited_templates:
                    report_lines.append(f"  继承: {template}")
        
        report = "\n".join(report_lines)
        
        # 输出到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report

    def analyze_top_unit_score_source(self):
        """分析性能占用第一的单位的分数来源"""
        if not self.units:
            return ""
        
        # 找出性能占用第一的单位
        top_unit = None
        top_score = -1
        for key, unit_data in self.units.items():
            score = self.calculate_performance_score(unit_data)
            if score > top_score:
                top_score = score
                top_unit = unit_data
        
        if not top_unit:
            return ""
        
        analysis_lines = []
        analysis_lines.append("\n" + "=" * 80)
        analysis_lines.append("性能占用第一单位详细分析")
        analysis_lines.append("=" * 80)
        analysis_lines.append(f"\n单位名称: {top_unit.name}")
        analysis_lines.append(f"文件路径: {top_unit.file_path}")
        analysis_lines.append(f"性能分数: {top_score:.2f}")
        analysis_lines.append(f"自动触发间隔: {top_unit.raw_interval} ({top_unit.trigger_interval_frames}帧)")
        analysis_lines.append(f"自动触发检查率: {top_unit.raw_check_rate} (每{top_unit.trigger_check_rate}帧)")
        
        if top_unit.inherited_templates:
            analysis_lines.append("\n继承模板:")
            for template in top_unit.inherited_templates:
                analysis_lines.append(f"  - {template}")
        
        # 详细分解分数来源
        analysis_lines.append("\n分数来源分解:")
        
        # 1. 路径点动作类型贡献
        path_contribution = top_unit.path_point_action_types * 3
        analysis_lines.append(f"  添加路径点动作类型: {top_unit.path_point_action_types}个 × 3 = {path_contribution:.2f}")
        
        # 2. 清除路径点贡献
        clear_contribution = top_unit.clear_all_waypoints * 3
        analysis_lines.append(f"  清除所有路径点: {top_unit.clear_all_waypoints}个 × 3 = {clear_contribution:.2f}")
        
        # 3. 设置内存贡献
        memory_contribution = top_unit.set_unit_memory * 10
        analysis_lines.append(f"  设置单位内存: {top_unit.set_unit_memory}个 × 10 = {memory_contribution:.2f}")
        
        # 4. 逻辑设置资源贡献
        logic_contribution = top_unit.logic_resource_count * 8
        analysis_lines.append(f"  用逻辑设置资源: {top_unit.logic_resource_count}个 × 8 = {logic_contribution:.2f}")
        
        # 5. 自动触发隐藏行动贡献
        if top_unit.auto_trigger_actions > 0:
            auto_base = 0.1
            auto_cond = top_unit.auto_trigger_conditions * 0.025
            auto_non_cond = top_unit.non_auto_trigger_conditions * 0.01
            auto_per_action = auto_base + auto_cond + auto_non_cond
            auto_total = top_unit.auto_trigger_actions * auto_per_action
            analysis_lines.append(f"\n  自动触发隐藏行动: {top_unit.auto_trigger_actions}个")
            analysis_lines.append(f"    - 基础值: {auto_base}")
            analysis_lines.append(f"    - 自动触发条件×0.025: {top_unit.auto_trigger_conditions} × 0.025 = {auto_cond:.4f}")
            analysis_lines.append(f"    - 需要条件×0.01: {top_unit.non_auto_trigger_conditions} × 0.01 = {auto_non_cond:.4f}")
            analysis_lines.append(f"    - 每行动贡献: {auto_per_action:.4f}")
            analysis_lines.append(f"    - 自动触发总贡献: {auto_total:.4f}")
        
        # 6. 非自动触发隐藏行动贡献
        if top_unit.non_auto_trigger_actions > 0:
            non_auto_base = 0.02
            non_auto_cond = top_unit.non_auto_trigger_conditions * 0.01
            non_auto_per_action = non_auto_base + non_auto_cond
            non_auto_total = top_unit.non_auto_trigger_actions * non_auto_per_action
            analysis_lines.append(f"\n  非自动触发隐藏行动: {top_unit.non_auto_trigger_actions}个")
            analysis_lines.append(f"    - 基础值: {non_auto_base}")
            analysis_lines.append(f"    - 需要条件×0.01: {top_unit.non_auto_trigger_conditions} × 0.01 = {non_auto_cond:.4f}")
            analysis_lines.append(f"    - 每行动贡献: {non_auto_per_action:.4f}")
            analysis_lines.append(f"    - 非自动触发总贡献: {non_auto_total:.4f}")
        
        # 7. 间隔除数
        divisor = top_unit.trigger_interval_frames / 60
        analysis_lines.append(f"\n  间隔除数: {top_unit.trigger_interval_frames}帧 / 60 = {divisor:.4f}")
        
        # 汇总
        pre_divisor_total = (
            path_contribution +
            clear_contribution +
            memory_contribution +
            logic_contribution +
            top_unit.auto_trigger_actions * (0.1 + top_unit.auto_trigger_conditions * 0.05 + top_unit.non_auto_trigger_conditions * 0.01) +
            top_unit.non_auto_trigger_actions * (0.02 + top_unit.non_auto_trigger_conditions * 0.01)
        )
        analysis_lines.append(f"\n总贡献(除间隔前): {pre_divisor_total:.4f}")
        analysis_lines.append(f"最终分数: {pre_divisor_total:.4f} / {divisor:.4f} = {top_score:.2f}")
        
        return "\n".join(analysis_lines)

    def analyze_test_file(self):
        """分析测试文件 scripts/元/测试文件.ini"""
        test_file = os.path.join(self.workspace_root, 'scripts', '元', '测试文件.ini')
        
        if not os.path.exists(test_file):
            return ""
        
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return ""
        
        # 解析测试文件
        unit_data = UnitData()
        unit_data.name = "测试文件"
        unit_data.file_path = test_file
        self.parse_performance_metrics(content, unit_data)
        
        score = self.calculate_performance_score(unit_data)
        
        analysis_lines = []
        analysis_lines.append("\n" + "=" * 80)
        analysis_lines.append("测试文件详细分析")
        analysis_lines.append("=" * 80)
        analysis_lines.append(f"\n文件路径: {test_file}")
        analysis_lines.append(f"\n解析结果:")
        analysis_lines.append(f"  - 自动触发隐藏行动: {unit_data.auto_trigger_actions}个")
        analysis_lines.append(f"  - 自动触发条件: {unit_data.auto_trigger_conditions}个")
        analysis_lines.append(f"  - 非自动触发隐藏行动: {unit_data.non_auto_trigger_actions}个")
        analysis_lines.append(f"  - 需要条件: {unit_data.non_auto_trigger_conditions}个")
        analysis_lines.append(f"  - 添加路径点动作类型: {unit_data.path_point_action_types}个")
        analysis_lines.append(f"  - 清除所有路径点: {unit_data.clear_all_waypoints}次")
        analysis_lines.append(f"  - 设置单位内存: {unit_data.set_unit_memory}个")
        analysis_lines.append(f"  - 用逻辑设置资源: {unit_data.logic_resource_count}个")
        analysis_lines.append(f"\n性能分数: {score:.2f}")
        
        analysis_lines.append("\n分数来源分解:")
        
        # 1. 路径点动作类型贡献
        path_contribution = unit_data.path_point_action_types * 3
        analysis_lines.append(f"  添加路径点动作类型: {unit_data.path_point_action_types}个 × 3 = {path_contribution:.2f}")
        
        # 2. 清除路径点贡献
        clear_contribution = unit_data.clear_all_waypoints * 3
        analysis_lines.append(f"  清除所有路径点: {unit_data.clear_all_waypoints}个 × 3 = {clear_contribution:.2f}")
        
        # 3. 设置内存贡献
        memory_contribution = unit_data.set_unit_memory * 10
        analysis_lines.append(f"  设置单位内存: {unit_data.set_unit_memory}个 × 10 = {memory_contribution:.2f}")
        
        # 4. 逻辑设置资源贡献
        logic_contribution = unit_data.logic_resource_count * 8
        analysis_lines.append(f"  用逻辑设置资源: {unit_data.logic_resource_count}个 × 8 = {logic_contribution:.2f}")
        
        # 5. 自动触发隐藏行动贡献
        if unit_data.auto_trigger_actions > 0:
            auto_base = 0.1
            auto_cond = unit_data.auto_trigger_conditions * 0.025
            auto_non_cond = unit_data.non_auto_trigger_conditions * 0.01
            auto_per_action = auto_base + auto_cond + auto_non_cond
            auto_total = unit_data.auto_trigger_actions * auto_per_action
            analysis_lines.append(f"\n  自动触发隐藏行动: {unit_data.auto_trigger_actions}个")
            analysis_lines.append(f"    - 基础值: {auto_base}")
            analysis_lines.append(f"    - 自动触发条件×0.025: {unit_data.auto_trigger_conditions} × 0.025 = {auto_cond:.4f}")
            analysis_lines.append(f"    - 需要条件×0.01: {unit_data.non_auto_trigger_conditions} × 0.01 = {auto_non_cond:.4f}")
            analysis_lines.append(f"    - 每行动贡献: {auto_per_action:.4f}")
            analysis_lines.append(f"    - 自动触发总贡献: {auto_total:.4f}")
        
        # 6. 非自动触发隐藏行动贡献
        if unit_data.non_auto_trigger_actions > 0:
            non_auto_base = 0.01
            non_auto_cond = unit_data.non_auto_trigger_conditions * 0.01
            non_auto_per_action = non_auto_base + non_auto_cond
            non_auto_total = unit_data.non_auto_trigger_actions * non_auto_per_action
            analysis_lines.append(f"\n  非自动触发隐藏行动: {unit_data.non_auto_trigger_actions}个")
            analysis_lines.append(f"    - 基础值: {non_auto_base}")
            analysis_lines.append(f"    - 需要条件×0.01: {unit_data.non_auto_trigger_conditions} × 0.01 = {non_auto_cond:.4f}")
            analysis_lines.append(f"    - 每行动贡献: {non_auto_per_action:.4f}")
            analysis_lines.append(f"    - 非自动触发总贡献: {non_auto_total:.4f}")
        
        # 间隔除数
        divisor = unit_data.trigger_interval_frames / 60
        analysis_lines.append(f"\n  间隔除数: {unit_data.trigger_interval_frames}帧 / 60 = {divisor:.4f}")
        
        # 汇总
        pre_divisor_total = (
            path_contribution +
            clear_contribution +
            memory_contribution +
            logic_contribution +
            unit_data.auto_trigger_actions * (0.1 + unit_data.auto_trigger_conditions * 0.025 + unit_data.non_auto_trigger_conditions * 0.01) +
            unit_data.non_auto_trigger_actions * (0.01 + unit_data.non_auto_trigger_conditions * 0.01)
        )
        analysis_lines.append(f"\n总贡献(除间隔前): {pre_divisor_total:.4f}")
        analysis_lines.append(f"最终分数: {pre_divisor_total:.4f} / {divisor:.4f} = {score:.2f}")
        
        return "\n".join(analysis_lines)


def main():
    """主函数"""
    # 自动检测工作目录
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    calculator = UnitPerformanceCalculator(workspace_root)
    
    print("正在扫描单位文件...")
    calculator.scan_all_units()
    
    print(f"扫描完成，共发现 {len(calculator.units)} 个单位")
    
    # 生成报告
    output_path = os.path.join(workspace_root, 'scripts', '数据集', '单位性能占用.txt')
    report = calculator.generate_report(output_path)
    
    # 分析性能占用第一的单位
    analysis = calculator.analyze_top_unit_score_source()
    print(analysis)
    
    # 分析测试文件
    test_analysis = calculator.analyze_test_file()
    print(test_analysis)
    
    # 将分析结果追加到报告
    if output_path:
        with open(output_path, 'a', encoding='utf-8') as f:
            f.write(analysis)
            f.write(test_analysis)
    
    print(f"\n报告已生成: {output_path}")
    print(f"\n总性能占用分数: {sum(calculator.calculate_performance_score(u) for u in calculator.units.values()):.2f}")


if __name__ == "__main__":
    main()
