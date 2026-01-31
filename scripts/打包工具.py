#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RWMOD 打包工具
将项目文件打包为铁锈战争 MOD 格式 (.rwmod)

使用方法:
    python 打包工具.py
    
固定输出:
    文件名: 人机的玩笑.rwmod
    路径: D:/Users/Documents/MuMu共享文件夹/X/rustedWarfare/units

排除的文件夹:
    - scripts
    - .vscode
    - .git
    - __pycache__
    - 翻译结果
    - 测试翻译输出
"""

import os
import sys
import zipfile
from pathlib import Path
from datetime import datetime


def create_rwmod(output_file="mod.rwmod", source_dir="."):
    """
    创建 rwmod 文件
    
    Args:
        output_file: 输出文件名，默认 mod.rwmod
        source_dir: 源目录，默认当前目录
    """
    # 确保输出文件名以 .rwmod 结尾
    if not output_file.endswith('.rwmod'):
        output_file += '.rwmod'
    
    # 排除的文件夹和文件
    exclude_dirs = {
        'scripts',
        '.vscode',
        '.git',
        '__pycache__',
        '翻译结果',
        '测试翻译输出',
    }
    
    exclude_files = {
        '.gitignore',
        '.nomedia',
        output_file,  # 排除输出文件本身
    }
    
    source_path = Path(source_dir).resolve()
    output_path = source_path / output_file
    
    print("=" * 60)
    print("RWMOD 打包工具")
    print("=" * 60)
    print(f"源目录: {source_path}")
    print(f"输出文件: {output_path}")
    print("-" * 60)
    
    # 收集要打包的文件
    files_to_pack = []
    total_size = 0
    
    for root, dirs, files in os.walk(source_path):
        root_path = Path(root)
        
        # 排除指定文件夹
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            # 排除指定文件
            if file in exclude_files:
                continue
            
            file_path = root_path / file
            
            # 跳过隐藏文件（以.开头的文件）
            if file.startswith('.'):
                continue
            
            # 计算相对路径
            try:
                rel_path = file_path.relative_to(source_path)
                file_size = file_path.stat().st_size
                files_to_pack.append((file_path, rel_path, file_size))
                total_size += file_size
            except (ValueError, OSError):
                continue
    
    if not files_to_pack:
        print("错误: 没有找到可打包的文件")
        return False
    
    print(f"找到 {len(files_to_pack)} 个文件，总大小: {format_size(total_size)}")
    print("-" * 60)
    
    # 创建 ZIP 文件（rwmod 就是 ZIP 格式）
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for idx, (file_path, rel_path, file_size) in enumerate(files_to_pack, 1):
                # 显示进度
                progress = (idx / len(files_to_pack)) * 100
                print(f"\r打包进度: [{idx}/{len(files_to_pack)}] {progress:.1f}% - {rel_path}", end='', flush=True)
                
                # 将文件添加到 ZIP
                zf.write(file_path, rel_path)
        
        print()  # 换行
        print("-" * 60)
        
        # 显示结果
        output_size = output_path.stat().st_size
        compression_ratio = ((total_size - output_size) / total_size) * 100 if total_size > 0 else 0
        
        print("打包完成!")
        print(f"  输出文件: {output_path}")
        print(f"  原始大小: {format_size(total_size)}")
        print(f"  打包大小: {format_size(output_size)}")
        print(f"  压缩率: {compression_ratio:.1f}%")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n错误: 打包失败 - {e}")
        # 如果失败，删除不完整的输出文件
        if output_path.exists():
            output_path.unlink()
        return False


def format_size(size_bytes):
    """格式化文件大小显示"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def main():
    """主函数"""
    # 固定输出文件名和路径
    output_file = "人机的玩笑.rwmod"
    source_dir = "."
    output_dir = "D:/Users/Documents/MuMu共享文件夹/X/rustedWarfare/units"
    
    # 确保输出目录存在
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 完整的输出文件路径
    full_output_file = str(output_path / output_file)
    
    # 执行打包
    success = create_rwmod(full_output_file, source_dir)
    
    if success:
        print("\n提示: 将 .rwmod 文件放入铁锈战争的 mods 文件夹即可使用")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
