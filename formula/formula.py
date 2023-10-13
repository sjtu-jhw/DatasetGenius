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
from datasketch import MinHash, MinHashLSH

# 将tex中的公式tex源码按顺序清洗出来
def clean_tex(tex_file_path):
    with open(tex_file_path,'r') as fp:
        data = fp.read()
    # tex中的公式源码list
    equation_latex_list = []
    # 首先去掉注释部分
    clean_data = re.sub(r'(?<!\\)%.*', '', data)
    # 提取公式部分
    # 使用正则表达式
    # 提取\begin{equation}和\end{align}之间的内容
    equations1 = re.findall(r'(\\begin{equation}.*?\\end{equation})', clean_data, re.DOTALL)
    # 使用正则表达式
    # 提取\begin{align}和\end{equation}之间的内容
    equations2 = re.findall(r'(\\begin{align}.*?\\end{align})', clean_data, re.DOTALL)
    equations = equations1 + equations2
    # 对每个提取出来公式进行进一步清洗
    for equation in equations:
        # 使用正则表达式
        # 删除\label{...}标签
        clean_eq = re.sub(r'\\label\{[^\}]*\}', '', equation)
        # 使用正则表达式
        # 去除多余的换行和空格
        clean_eq = re.sub(r'(\n+|\s+)', ' ', clean_eq)
        equation_latex_list.append(clean_eq)
    return equation_latex_list

# 将xml中的公式源码按顺序清洗出来
def clean_xml(pdf_parser, pdf_path, xml_path):
    # xml中的公式ocr list
    equation_xml_list = []
    pdf_name = os.path.basename(pdf_path)
    pdf_parser.pdf_name = pdf_name
    tree = ET.parse(xml_path)
    root = tree.getroot()
    result = pdf_parser.parse_all(root, pdf_name, f"{pdf_name.strip('.pdf')}.json")
    body = result['body']
    for el in body:
        if el['el_type'] == "formula":
            equation_xml_list.append(el['txt'])
    return equation_xml_list

# 创建一个 MinHash 对象
def create_minhash(data):
    minhash = MinHash(num_perm=128)  # num_perm 是哈希函数的数量，可以根据需要调整
    for d in data:
        minhash.update(d.encode('utf8'))
    return minhash

def main():  # pragma no cover
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="FORMULA DATASET GENERATION",
    )
    # 添加命令行参数
    parser.add_argument('--source_data_path', type=str, help='实际数据集位置设置, 所有数据的父路径')
    parser.add_argument('--pdf_work_dir', type=str,  default="./tmp/pdfs/", help='将数据集中的pdf拉到本地的本地pdf路径')
    parser.add_argument('--tex_work_dir', type=str, default="./tmp/tex/", help='将数据集中的tex拉到本地的本地tex路径')
    parser.add_argument('--xml_work_dir', type=str, default="./tmp/xmls/", help='将数据集中的xml拉到本地的本地xml路径')
    parser.add_argument('--output_path_figures', default="./tmp/figures/", type=str, help='输出figure的路径')
    parser.add_argument('--output_path_jsons', default="./tmp/jsons/", type=str, help='输出json的路径')
    parser.add_argument('--output_path_mds', default="./tmp/mds/", type=str, help='输出markdown的路径')
    parser.add_argument('--parse_imgs', type=bool, default=False, help='是否解析图、表、公式图片')

    # 解析命令行参数
    args = parser.parse_args()

    # 访问命令行参数的值
    source_data_path = args.source_data_path # 根据实际数据集位置设置，所有数据的父路径
    pdf_work_dir = args.pdf_work_dir
    tex_work_dir = args.tex_work_dir
    xml_work_dir = args.xml_work_dir
    output_path_figures = args.output_path_figures
    output_path_jsons = args.output_path_jsons
    output_path_mds = args.output_path_mds
    parse_imgs = args.parse_imgs


    # 寻找用于解析的pdf文件以及tex文件路径
    dir_paths = [os.path.join(source_data_path, f) 
                for f in os.listdir(source_data_path) 
                if os.path.isdir(os.path.join(source_data_path, f))]# 找到包含pdf，tex文件的路径
    workfile_path_tuple_list = []# 存储数据路径，如：[(pdf1_path,tex1_path),(pdf2_path,tex2_path),...]
    for path in dir_paths:
        pdf_path = None
        tex_path = None
        for f in os.listdir(path):
            # 这个地方我人为把pdf加到source文件夹里面了
            # 实际上这里面没有
            if f.endswith('.pdf'):
                pdf_path = os.path.join(path, f)
            # 一个source文件里可能会有好几个.tex文件
            # 需要总结一下主.tex文件的命名规律
            elif f == 'main.tex': 
                tex_path = os.path.join(path, f)
            if pdf_path is not None and tex_path is not None:
                workfile_path_tuple_list.append((pdf_path, tex_path))
                break# 找齐了就跳出循环
                
    # 由于不能直接对原数据集进行写入操作，这里把数据集中的论文拉到本地
    for (pdf_path, tex_path) in workfile_path_tuple_list:
        shutil.copy(pdf_path, pdf_work_dir + os.path.basename(pdf_path))
        shutil.copy(tex_path, tex_work_dir + os.path.basename(pdf_path).strip('.pdf')+'.tex')

    # 使用Grobid进行pdf解析，得到tex文件
    client = GrobidClient(config_path='./config.json')# Grobid配置文件
    print('正在解析，请等待...')
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
    workfile_path_tuple_list_new = []# [(pdf1_path,tex1_path,xml1_path),(pdf2_path,tex2_path,xml2_path),...]
    for (pdf_path,tex_path) in workfile_path_tuple_list:
        base_name_pdf = os.path.basename(pdf_path)
        # Grobid解析成功才计入
        if base_name_pdf.strip('.pdf') + '.tei.xml' in os.listdir(xml_work_dir):
            workfile_path_tuple_list_new.append((os.path.join(pdf_work_dir, base_name_pdf),
                                                 os.path.join(tex_work_dir, f"{base_name_pdf.strip('.pdf')}.tex"),
                                                 os.path.join(xml_work_dir, f"{base_name_pdf.strip('.pdf')}.tei.xml")))
    # 接下来是清洗工作
    # 清洗xml和tex
    # 实例化一个用于解析的类Parser
    pdf_parser = GParser(pdf_name="",# pdf的名字
                        input_path=pdf_work_dir,# 输入pdf所在文件夹
                        output_path_xmls=xml_work_dir,# 存储xml所在文件夹
                        output_path_figures=output_path_figures,# 存储图片所在文件夹，用不上
                        output_path_jsons=output_path_jsons,# 存储json所在文件夹
                        output_path_mds=output_path_mds,# 存储mardkown所在文件夹，用不上
                        parse_imgs=parse_imgs)# 是否解析图片、表格、公式图片

    # data pair list
    data_pair_list = []
    for (pdf_path,tex_path,xml_path) in workfile_path_tuple_list_new:
        # xml公式list
        equation_xml_list = clean_xml(pdf_parser, pdf_path, xml_path)    
        # tex公式list
        equation_latex_list = clean_tex(tex_path)

        # 文本匹配形成pair
        # 创建 MinHash 对象并插入到 LSH 中
        lsh = MinHashLSH(threshold=0, num_perm=128)  # threshold 是相似度阈值，可以根据需要调整
        for idx, sentence in enumerate(equation_xml_list):
            minhash = create_minhash(list(sentence))
            lsh.insert(idx, minhash)
        for query in equation_latex_list:
            # 去除无关信息会使相似性分数更加显著
            query = query.strip('\\begin{equation}').strip('\\end{equation}')
            query = query.strip('\\begin{align}').strip('\\end{align}')
            # 查找相似的集合
            query_minhash = create_minhash(list(query))
            results = lsh.query(query_minhash)
            # 输出最大相似度分数及对应的（xml, latex）对
            max_simlilarity = 0
            max_sim_xml = None
            for result in results:
                minhash = create_minhash(list(equation_xml_list[result]))
                jaccard_similarity = query_minhash.jaccard(minhash)
                if jaccard_similarity >= max_simlilarity:# 得到最大相似性的xml-latex公式对
                    max_simlilarity = jaccard_similarity
                    max_sim_xml = equation_xml_list[result]
            if max_simlilarity >= 0.5:# 只有相似性大于0.5的pair才考虑，可调
                data_pair_list.append((max_sim_xml, query))
    with open('./dataset.json','w') as fp:
        json.dump(data_pair_list, fp, indent=4)
if __name__ == "__main__":  # pragma no cover
    main()
