# 基于Grobid的PDF解析工具 v0.0.2

## 1. 简介
该脚本用于清洗论文中的公式。

## 2. 代码结构
<pre>
├── tmp/  # 工作文件夹
│   ├── jsons/
│   ├── pdfs/
│   ├── tex/
│   └── xmls/
├── dataset.json  # 清洗示例
├── config.json
├── formula.py  # 清洗脚本
└── README.md
</pre>

## 3. 运行环境
- python版本 ---- 3.10.4

- Grobid版本 ---- 0.7.2

- python包

  - [grobid_client](https://github.com/kermitt2/grobid_client_python)
  - [grobid_parser](https://git.acemap.cn/jihuawei/pdf_parser/tree/grobid_parser_v2)
  - [datasketch](https://pypi.org/project/datasketch/)


## 4. 代码说明
- /formula.py文件给定带解析文件目录直接对其中的公式进行提取，只需指定参数（详细信息请看源码）：

   - `source_data_path`：实际数据集位置设置, 所有数据的父路径

   - `pdf_work_dir`：将数据集中的pdf拉到本地的本地pdf路径

   - `tex_work_dir`：将数据集中的tex拉到本地的本地tex路径

   - `xml_work_dir`：Grobid解析xml输出路径

   - `output_path_figures`：输出figure的路径（目前用不到）

   - `output_path_jsons`：输出json的路径

   - `output_path_mds`：输出markdown的路径

   - `parse_imgs`：是否解析图、表、公式图片

- 数据示例请见/dataset.json
  - 数据结构如下：
   <pre>
   [{
       "dirty_data": { # 脏文本
           "pre_txt": "xxx", # 公式之前的内容
           "equation_txt": "xxx",# 公式内容
           "post_txt": "xxx", # 公式之后的内容
           "full_txt": "xxx" # 全文本
       },
       "clean_data": { # 干净文本
           "pre_txt": "xxx", # 公式之前的内容
           "equation_txt": "xxx",# 公式内容
           "post_txt": "xxx", # 公式之后的内容
           "full_txt": "xxx" # 全文本
       },
       "similarity_score": "xxx" # 相似度打分
    },
   ...
   ]

   </pre>

