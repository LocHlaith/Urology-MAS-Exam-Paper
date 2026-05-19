import json
import os

# 考点映射表
TEST_POINTS = {
    1: "尿液检查-血尿", 2: "尿液检查-蛋白尿", 3: "尿液检查-管型尿",
    4: "肾小球疾病-概述", 5: "肾小球疾病-急性肾小球肾炎", 6: "肾小球疾病-急进性肾小球肾炎",
    7: "肾小球疾病-慢性肾小球肾炎", 8: "肾小球疾病-肾病综合征", 9: "肾小球疾病-IgA肾病",
    10: "肾间质疾病-急性间质性肾炎", 11: "尿路感染-概述", 12: "尿路感染-急性肾盂肾炎",
    13: "尿路感染-慢性肾盂肾炎", 14: "尿路感染-急性膀胱炎", 15: "尿路感染-无症状细菌尿",
    16: "男性生殖系统感染-前列腺炎", 17: "男性生殖系统感染-附睾炎", 18: "泌尿、男性生殖系统结核-泌尿系统结核",
    19: "泌尿、男性生殖系统结核-男性生殖系统结核", 20: "尿路结石-概述", 21: "尿路结石-上尿路结石",
    22: "尿路结石-膀胱结石", 23: "泌尿、男性生殖系统肿瘤-肾肿瘤（肾癌、肾母细胞瘤、肾血管平滑肌脂肪瘤）",
    24: "泌尿、男性生殖系统肿瘤-尿路上皮肿瘤（膀胱肿瘤，肾盂、输尿管癌）", 25: "泌尿、男性生殖系统肿瘤-前列腺癌",
    26: "泌尿、男性生殖系统肿瘤-睾丸肿瘤", 27: "泌尿、男性生殖系统肿瘤-阴茎癌", 28: "泌尿系统梗阻-概论",
    29: "泌尿系统梗阻-肾积水", 30: "泌尿系统梗阻-良性前列腺增生", 31: "泌尿系统梗阻-尿潴留",
    32: "泌尿系统外伤-肾外伤", 33: "泌尿系统外伤-膀胱外伤", 34: "泌尿系统外伤-前尿道外伤",
    35: "泌尿系统外伤-后尿道外伤", 36: "泌尿、男性生殖系统先天性畸形及其他疾病-隐睾",
    37: "泌尿、男性生殖系统先天性畸形及其他疾病-鞘膜积液", 38: "泌尿、男性生殖系统先天性畸形及其他疾病-精索静脉曲张",
    39: "肾功能不全-急性肾损伤（急性肾衰竭）", 40: "肾功能不全-慢性肾脏病（慢性肾衰竭）"
}

def generate_statistics():
    files_to_read = [
        "new_bank_a1.json",
        "new_bank_a2.json",
        "new_bank_a3.json",
        "new_bank_a4.json",
        "new_bank_b.json",
        "new_bank_x.json"
    ]
    
    q_types = ['A1', 'A2', 'A3', 'A4', 'B', 'X']
    
    # 初始化各个考点的统计字典
    stats_by_tp = {tp: {qt: 0 for qt in q_types} for tp in TEST_POINTS.keys()}
    for tp in stats_by_tp:
        stats_by_tp[tp]['Total'] = 0
        
    # 初始化全题库去重总计字典
    grand_total = {qt: 0 for qt in q_types}
    grand_total['Total'] = 0

    # 遍历读取文件
    for file in files_to_read:
        if not os.path.exists(file):
            print(f"提示：未找到文件 {file}，已跳过。")
            continue
            
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            for item in data:
                q_type = item.get('type', '未知')
                
                # 1. 计入全题库去重总计 (每道题只算1次)
                if q_type in grand_total:
                    grand_total[q_type] += 1
                    grand_total['Total'] += 1
                
                # 2. 计入各个考点统计 (如果一道题有多个考点，则分别计入)
                tps = item.get('test_point', [])
                for tp in tps:
                    if tp in stats_by_tp and q_type in stats_by_tp[tp]:
                        stats_by_tp[tp][q_type] += 1
                        stats_by_tp[tp]['Total'] += 1

    # 写入统计结果到 txt 文件
    output_file = "statistics_for_test_point.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("泌尿外科专科题库 —— 考点与题型分布统计\n")
        f.write("=" * 70 + "\n\n")
        
        # 写入每个考点的明细
        for tp, name in TEST_POINTS.items():
            s = stats_by_tp[tp]
            f.write(f"考点 {tp}：{name}\n")
            # 使用固定宽度排版，确保在纯文本中对齐
            f.write(f"  A1: {s['A1']:<3} | A2: {s['A2']:<3} | A3: {s['A3']:<3} | A4: {s['A4']:<3} | B: {s['B']:<3} | X: {s['X']:<3} | 本考点总计: {s['Total']}\n")
            f.write("-" * 70 + "\n")
            
        # 写入全题库真实总计
        f.write("\n" + "=" * 70 + "\n")
        f.write("【全题库去重总计】（注：跨考点的题目在此处只计算一次）\n")
        f.write(f"  A1型题：{grand_total['A1']} 题\n")
        f.write(f"  A2型题：{grand_total['A2']} 题\n")
        f.write(f"  A3型题：{grand_total['A3']} 题\n")
        f.write(f"  A4型题：{grand_total['A4']} 题\n")
        f.write(f"  B 型题：{grand_total['B']} 题\n")
        f.write(f"  X 型题：{grand_total['X']} 题\n")
        f.write("-" * 30 + "\n")
        f.write(f"  总题目数：{grand_total['Total']} 题\n")
        f.write("=" * 70 + "\n")

    print(f"\n统计完成！已成功导出至：{output_file}")

if __name__ == "__main__":
    generate_statistics()
