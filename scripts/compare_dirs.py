import os
import filecmp
import sys
import difflib

# 设置输出编码
sys.stdout.reconfigure(encoding='utf-8')

root_dir = '.'
meta_dir = 'scripts/元/人机的玩笑'

def get_all_files(base_path):
    files = []
    for root, dirs, filenames in os.walk(base_path):
        for f in filenames:
            rel_path = os.path.relpath(os.path.join(root, f), base_path)
            files.append(rel_path)
    return set(files)

root_files = get_all_files(root_dir)
meta_files = get_all_files(meta_dir)

common_files = root_files & meta_files

# 只对比 .ini 和 .template 文件
valid_extensions = ('.ini', '.template')
filtered_files = [f for f in common_files if f.endswith(valid_extensions)]

print(f'找到 {len(filtered_files)} 个需要对比的 .ini/.template 文件')

different_files = []
same_files = []

for f in sorted(filtered_files):
    root_path = os.path.join(root_dir, f)
    meta_path = os.path.join(meta_dir, f)
    
    if os.path.exists(root_path) and os.path.exists(meta_path):
        if filecmp.cmp(root_path, meta_path, shallow=False):
            same_files.append(f)
        else:
            different_files.append(f)

print(f'内容相同: {len(same_files)} 个')
print(f'内容不同: {len(different_files)} 个')

# 生成详细差异报告
with open('scripts/diff_report.txt', 'w', encoding='utf-8') as out:
    out.write(f'=== 文件差异详细报告 ===\n')
    out.write(f'对比目录: 项目根目录 vs scripts/元/人机的玩笑\n')
    out.write(f'共 {len(different_files)} 个文件有差异\n')
    out.write('=' * 80 + '\n\n')
    
    for f in different_files:
        root_path = os.path.join(root_dir, f)
        meta_path = os.path.join(meta_dir, f)
        
        out.write(f'\n{"=" * 80}\n')
        out.write(f'文件: {f}\n')
        out.write(f'{"=" * 80}\n\n')
        
        try:
            with open(root_path, 'r', encoding='utf-8', errors='ignore') as rf:
                root_content = rf.read()
            with open(meta_path, 'r', encoding='utf-8', errors='ignore') as mf:
                meta_content = mf.read()
            
            # 去除空行进行比较
            root_lines = [line for line in root_content.split('\n') if line.strip()]
            meta_lines = [line for line in meta_content.split('\n') if line.strip()]
            
            diff = difflib.unified_diff(
                meta_lines, root_lines,
                fromfile=f'scripts/元/人机的玩笑/{f}',
                tofile=f'{f}',
                lineterm=''
            )
            diff_text = '\n'.join(diff)
            if diff_text.strip():
                out.write(diff_text + '\n')
            else:
                out.write('(内容完全相同)\n')
        except Exception as e:
            out.write(f'读取文件出错: {e}\n')

print(f'详细差异报告已保存到 scripts/diff_report.txt')
