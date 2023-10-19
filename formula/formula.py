# encoding: utf-8

# 本脚本实现了快速构建grobid和latex源码公式数据集功能
# 其中包括以下几个步骤
# 1. 获取待处理pdf以及tex文件路径
# 2. 使用Grobid解析pdf，得到xml文件
# 3. 清洗xml文件及清洗tex文件
# 4. 建立对应关系
# 5. 构建data pair

import os 
import shutil
import argparse
import json
from grobid_client.grobid_client import GrobidClient
from grobid_parser import GParser
import xml.etree.ElementTree as ET
import re
import time
from datasketch import MinHash, MinHashLSH
from tqdm import tqdm

context_len = 70
simliarity_threshold = 0.65

# 顺序清洗
def clean_tex(tex_file_path):
    # 异常处理
    try:
        with open(tex_file_path,'r') as fp:
            data = fp.read()
    except UnicodeDecodeError:
        print("Unable to decode the file with UTF-8 encoding.")
        return [] # 直接返回一个空列表
    # tex中的公式源码list
    equation_latex_list = []
    # 去掉注释
    clean_data = re.sub(r'(?<!\\)%.*', '', data)
    # 提取公式
    pattern = [r'(\\begin{equation}(.*?)\\end{equation})',
                   r'(\\begin{align}.*?\\end{align})',
                   r'(\\begin{math}(.*?)\\end{math})',
                   r'(\$\$.+?\$\$)',
                   r'((?<!\$)\$[^\$]+\$(?!\$))',
                   r'(\\\[.*?\\\])',
                   r'(\\\(.*?\\\))']
    for pattern_ in pattern:
        pattern = re.compile(pattern_, re.DOTALL)
        matches = pattern.finditer(clean_data)
        for match in matches:
            start = match.start()
            end = match.end()
            content = match.group(1) # 公式
            pre_txt =  clean_data[start-context_len:start] if start>=context_len else clean_data[:end]# 取前后context_len个character
            post_txt = clean_data[end:end+context_len]
            full_txt = pre_txt+ content + post_txt
            equation_latex_list.append({"pre_txt":pre_txt, "equation_txt":content, "post_txt":post_txt, "full_txt":full_txt})
    # [{"pre_txt":Pre_Formula_Text1$Formula1$, "equation_txt":$Formula1$, "post_txt":$Formula1$Post_Formula_Text1, "full_txt":Full_Text1}, {...}, ...] 
    return equation_latex_list

def clean_xml(pdf_parser, pdf_path, xml_path):
    # xml中的公式ocr list
    equation_xml_list = []
    pdf_name = os.path.basename(pdf_path)
    pdf_parser.pdf_name = pdf_name
    tree = ET.parse(xml_path)
    root = tree.getroot()
    result = pdf_parser.parse_all(root, pdf_name, f"{pdf_name.strip('.pdf')}.json")
    body = result['body']
    pre_txt = ""
    post_txt = ""
    for index, el in enumerate(body):
        if el['el_type'] == "formula":
            # 跳过当前值
            i_forward = 1
            i_backward = 1
            # 前向寻找
            while len(pre_txt)<=context_len:# equation前面的character在context_len个以内
                if "txt" not in body[index - i_forward]:
                    i_forward += 1
                    continue
                elif "tail" in body[index - i_forward]:# 包含"tail"
                    txt = body[index - i_forward]['txt'] + body[index - i_forward]['tail']
                else:
                    txt = body[index - i_forward]['txt']
                pre_txt = txt + pre_txt
                i_forward += 1
            # 后向寻找
            while len(post_txt)<=context_len:# equation前面的character在context_len个以内
                if "txt" not in body[index + i_backward]:
                    i_backward += 1
                    continue
                elif "tail" in body[index + i_backward]:# 包含"tail"
                    txt = body[index + i_backward]['txt'] + body[index + i_backward]['tail']
                else:
                    txt = body[index + i_backward]['txt']
                post_txt = post_txt + txt
                i_backward += 1
            equation_txt = el['txt']
            pre_txt = pre_txt[-context_len:]
            post_txt = post_txt[:context_len]
            full_txt = pre_txt + equation_txt + post_txt
            equation_xml_list.append({"pre_txt":pre_txt, "equation_txt":equation_txt, "post_txt":post_txt, "full_txt":full_txt})
            # 恢复初始态
            pre_txt = ""
            post_txt = ""
            i_forward = 1
            i_backward = 1
    # [{"pre_txt":Pre_Formula_Text1$Formula1$, "equation_txt":$Formula1$, "post_txt":$Formula1$Post_Formula_Text1, "full_txt":Full_Text1}, {...}, ...] 
    return equation_xml_list


# 创建一个 MinHash 对象
def create_minhash(data):
    minhash = MinHash(num_perm=128)  # num_perm 是哈希函数的数量，可以根据需要调整
    for d in data:
        minhash.update(d.encode('utf8'))
    return minhash

def make_dir_if_not_exist(folder):
  if not os.path.exists(folder):
    os.makedirs(folder)

def main():  # pragma no cover
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="FORMULA DATASET GENERATION",
    )
    # 添加命令行参数
    parser.add_argument('--source_data_path', type=str, help='实际数据集位置设置, 所有数据的父路径')
    parser.add_argument('--pdf_work_dir', type=str,  default="./tmp/pdfs/", help='将数据集中的pdf拉到本地的本地pdf路径')
    parser.add_argument('--tex_work_dir', type=str, default="./tmp/tex/", help='将数据集中的tex拉到本地的本地tex路径')
    parser.add_argument('--xml_work_dir', type=str, default="./tmp/xmls/", help='Grobid解析xml输出路径')
    parser.add_argument('--output_path_jsons', default="./tmp/jsons/", type=str, help='输出json的路径')
    parser.add_argument('--parse_imgs', type=bool, default=False, help='是否解析图、表、公式图片')

    # 解析命令行参数
    args = parser.parse_args()

    # 访问命令行参数的值
    source_data_path = args.source_data_path # 根据实际数据集位置设置，所有数据的父路径
    pdf_work_dir = args.pdf_work_dir
    tex_work_dir = args.tex_work_dir
    xml_work_dir = args.xml_work_dir
    output_path_jsons = args.output_path_jsons
    parse_imgs = args.parse_imgs


    # 寻找用于解析的pdf文件以及tex文件路径
    dir_paths = [os.path.join(source_data_path, f) 
                for f in os.listdir(source_data_path) 
                if os.path.isdir(os.path.join(source_data_path, f))]# 找到包含pdf，tex文件的路径
    workfile_path_tuple_list = []# 存储数据路径，如：[(pdf1_path,tex1_paths),(pdf2_path,tex2_paths),...]
    for path in dir_paths:
        pdf_path = None
        tex_paths = []
        for f in os.listdir(path):
            if f.endswith('.pdf') and bool(re.match(r'\d+\.\d+\.pdf', f)):# 这个地方我们只取符合arxiv的doi的pdf
                pdf_path = os.path.join(path, f)
            elif f.endswith('.tex'): # 一个source文件里可能会有好几个.tex文件，全找！
                tex_paths.append(os.path.join(path, f))
        if pdf_path is not None and len(tex_paths) != 0:
            workfile_path_tuple_list.append((pdf_path, tex_paths))
        else:
            continue
                
    # 由于不能直接对原数据集进行写入操作，这里把数据集中的论文拉到本地
    print("正在把数据拉到本地...")
    for (pdf_path, tex_paths) in tqdm(workfile_path_tuple_list):
        make_dir_if_not_exist(pdf_work_dir)
        shutil.copy(pdf_path, os.path.join(pdf_work_dir, os.path.basename(pdf_path)))
        for tex_path in tex_paths:  
            make_dir_if_not_exist(os.path.join(tex_work_dir,f"{os.path.basename(pdf_path).strip('.pdf')}"))
            shutil.copy(tex_path, os.path.join(tex_work_dir, os.path.basename(pdf_path).strip('.pdf'), os.path.basename(tex_path)))

    # 使用Grobid进行pdf解析，得到tex文件
    client = GrobidClient(config_path='./config.json')# Grobid配置文件
    print('Grobid正在解析，请等待...')
    client.process("processFulltextDocument", 
                input_path=pdf_work_dir, 
                output=xml_work_dir,
                n=20,
                include_raw_citations=True, 
                include_raw_affiliations=True, 
                tei_coordinates=True, 
                force=False, 
                segment_sentences=True,
                verbose=False)

    print('解析完毕！')

    # 将tmp路径下的pdf,xml以及tex路径加到workfile_path_tuple_list_new中
    workfile_path_tuple_list_new = []# [(pdf1_path,tex1_paths,xml1_path),(pdf2_path,tex2_paths,xml2_path),...]
    for (pdf_path,tex_paths) in workfile_path_tuple_list:
        base_name_pdf = os.path.basename(pdf_path)
        # Grobid解析成功才计入
        if base_name_pdf.strip('.pdf') + '.tei.xml' in os.listdir(xml_work_dir):
            workfile_path_tuple_list_new.append((os.path.join(pdf_work_dir, base_name_pdf),
                                                 [os.path.join(tex_work_dir, base_name_pdf.strip('.pdf'), os.path.basename(tex_path)) for tex_path in tex_paths],
                                                 os.path.join(xml_work_dir, f"{base_name_pdf.strip('.pdf')}.tei.xml")))
    # 接下来是清洗工作
    # 清洗xml和tex
    # 实例化一个用于解析的类Parser
    pdf_parser = GParser(pdf_name="",# pdf的名字
                        input_path=pdf_work_dir,# 输入pdf所在文件夹
                        output_path_xmls=xml_work_dir,# 存储xml所在文件夹
                        output_path_jsons=output_path_jsons,# 存储json所在文件夹
                        parse_imgs=parse_imgs)# 是否解析图片、表格、公式图片

    # data pair list
    data_pair_list = []
    print("正在清洗xml和tex，构建数据集...")
    t0 = time.time()
    for index, (pdf_path,tex_paths,xml_path) in enumerate(tqdm(workfile_path_tuple_list_new)):
        t1 = time.time()
        print(f"正在清洗{os.path.basename(pdf_path)}...")
        equation_xml_list = []
        equation_latex_list = []
        # xml公式list
        equation_xml_list += clean_xml(pdf_parser, pdf_path, xml_path)    
        # tex公式list
        for tex_path in tex_paths:
            equation_latex_list += clean_tex(tex_path)

        equation_xml_list_new = [item["full_txt"] for item in equation_xml_list]
        equation_latex_list_new = [item["full_txt"] for item in equation_latex_list]

        # 文本匹配形成pair
        # 创建 MinHash 对象并插入到 LSH 中
        lsh = MinHashLSH(threshold=0, num_perm=128)  # threshold 是相似度阈值，可以根据需要调整
        for idx, sentence in enumerate(equation_latex_list_new):
            # 去除无关信息会使相似性分数更加显著
            sentence = sentence.replace('\\begin{equation}','')
            sentence = sentence.replace('\\end{equation}','')
            sentence = sentence.replace('\\begin{align}','')
            sentence = sentence.replace('\\end{align}','') 
            sentence = sentence.replace('\(','') 
            sentence = sentence.replace('\)','')   
            sentence = sentence.replace('\[','') 
            sentence = sentence.replace('\]','')  
            sentence = sentence.replace('$','') 
            sentence = sentence.replace('\\begin{math}','')   
            sentence = sentence.replace('\\end{math}','')   
            minhash = create_minhash(list(sentence))
            lsh.insert(idx, minhash)
        for query_id, query_origin in enumerate(equation_xml_list_new):
            # 查找相似的集合
            query_minhash = create_minhash(list(query_origin))
            results = lsh.query(query_minhash)
            # 输出最大相似度分数及对应的（xml, latex）对
            max_simlilarity = 0
            max_sim_latex = None
            max_sim_latex_id = 0
            for result in results:
                minhash = create_minhash(list(equation_latex_list_new[result]))
                jaccard_similarity = query_minhash.jaccard(minhash)
                if jaccard_similarity >= max_simlilarity:# 得到最大相似性的xml-latex公式对
                    max_simlilarity = jaccard_similarity
                    max_sim_latex_id = result
                    max_sim_latex = equation_latex_list_new[result]
            if max_simlilarity>=simliarity_threshold:
                xml_data = equation_xml_list[query_id]
                latex_data = equation_latex_list[max_sim_latex_id]
                data_pair_list.append({"dirty_data": xml_data, "clean_data":latex_data, "similarity_score": max_simlilarity})
        t2 = time.time()
        print(f"{os.path.basename(pdf_path)}解析时间：%6.3fs"%(t2-t1))
        if (index+1) % 10 == 0:
            print(f"执行到第{index+1}个pdf，保存一次数据。")
            with open('./dataset.json','w') as fp:
                json.dump(data_pair_list, fp, indent=4)
    # 保存最后一次数据
    with open('./dataset.json','w') as fp:
        json.dump(data_pair_list, fp, indent=4)
    t4 = time.time()
    total_time = t4 - t0
    hours, remainder = divmod(total_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    print(f"总共用时: {int(hours)} 小时, {int(minutes)} 分钟, {seconds:.2f} 秒")
if __name__ == "__main__":  # pragma no cover
    main()
