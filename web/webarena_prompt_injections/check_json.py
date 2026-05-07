import json

# 读取文件
with open(r'd:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections\configs\experiment_config.merged_all.json', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 第7125行（索引7124）
target_line_idx = 7124
line = lines[target_line_idx]

# 简单分析：找到instruction开始的位置
idx = line.find('instruction')
if idx != -1:
    print('instruction字段起始位置:', idx)
    # 从instruction的值开始提取
    quote_pos = line.find('"', idx + 11)
    if quote_pos != -1:
        start_pos = quote_pos + 1
        # 找到下一个未转义的引号
        pos = start_pos
        while pos < len(line):
            if line[pos] == '"' and (pos == 0 or line[pos-1] != '\\'):
                break
            pos += 1
        print(f'instruction值从位置{start_pos}到{pos}')
        print('值的内容（前500字符）:')
        print(repr(line[start_pos:min(pos, start_pos+500)]))
        print()
        print('第338列附近的内容:')
        col_338 = 337  # 0-based
        print(repr(line[max(0, col_338-30):col_338+30]))
