"""
Credits to fantastic work at https://github.com/google-research/arxiv-latex-cleaner
"""

import os
import subprocess
from multiprocessing import Pool
import regex
import numpy

# Fix for Windows: Even if '\' (os.sep) is the standard way of making paths on
# Windows, it interferes with regular expressions. We just change os.sep to '/'
# and os.path.join to a version using '/' as Windows will handle it the right
# way.
if os.name == 'nt':
  global old_os_path_join

  def new_os_join(path, *args):
    res = old_os_path_join(path, *args)
    res = res.replace('\\', '/')
    return res

  old_os_path_join = os.path.join

  os.sep = '/'
  os.path.join = new_os_join

def _get_absolute_path(path: str) -> str:
    """
    Return absolute path

    Args:
        path (str): path to the file
    
    Returns:
        str: absolute path
    """
    cur_dir = os.path.dirname(__file__)
    absolute_path = os.path.join(os.path.dirname(cur_dir), path)
    
    return absolute_path

def _list_all_files(in_folder):
  """
  Return all files' full path in a list
  """
  to_consider = [
      os.path.join(path, name)
      for path, _, files in os.walk(in_folder)
      for name in files
  ]
  return to_consider

def _read_file_content(file_path):
  """
  Return file contents in string
  """
  with open(file_path, 'r', encoding='ISO-8859-1') as fp: # not using utf-8 to avoid UnicodeDecodeError
    contents = fp.read()
    return contents

def arxiv_latex_cleaner_pre(path: str) -> None:
    """
    Using arxiv-latex-cleane 
    from googleresearch (https://github.com/google-research/arxiv-latex-cleaner)
    to do preprocess

    Args:
        path (str): path to the file containing the latex code
    
    """
    subprocess.Popen(f"arxiv_latex_cleaner \"{path}\"", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"PID {os.getpid()} done.")
    return None



def check_main_tex(in_folder: str):
   """
   Check which .tex file is the main file,
   we are using dumb match method now, do not know if any problem will occur in the future.

   Args:
        in_folder(str): the folder where your latex codes all lie in

   Returns:
        main_tex_name: path to main .tex file
   """
   main_tex_name = []
   file_names = _list_all_files(in_folder)
   select_tex_files = [file_name for file_name in file_names if file_name.endswith(".tex")]
   for file_name in select_tex_files:
      tex = _read_file_content(file_name)
      if "\\begin{document}" in tex and "\\end{document}" in tex:
         main_tex_name.append(file_name)
   assert len(main_tex_name) == 1, "There are more than one main .tex file in the folder."
   return main_tex_name[0]



def find_input_tex(in_tex: str):
   """
   Find \\input{.*} in input tex strings so that we can replace them with original tex text.

   Args:
        in_tex(str): all tex text in the .tex file

   Returns:
        list of .tex files
   """
   pattern = r"\\input{(.*)}"
   p = regex.compile(pattern)
   finds = p.findall(in_tex)
   return finds
   
def insert_input_tex(in_tex_path: str) -> None:
   """
   Find \\input{.*} in input tex files and substitute them with contents within corresponding .tex files
   +
   Rewrite in_tex_path contents

   Args:
        in_tex_path(str): path to .tex file where \\input{.*} may exist

   Returns:
        None
   """
   with open(in_tex_path, "r", encoding='ISO-8859-1') as f:
      in_tex = f.read()
   finds = find_input_tex(in_tex) # matched patterns
   for find in finds:
      insert_tex_path = os.path.join(os.path.dirname(in_tex_path), find+'.tex') # HACK: believe input files are .tex files
      insert_tex_content = _read_file_content(insert_tex_path)
      in_tex = in_tex.replace(f"\\input{{{find}}}", insert_tex_content)
   with open(in_tex_path, "w", encoding='ISO-8859-1') as f:
      f.write(in_tex)

def insert_input_tex_completely(in_tex_path: str) -> None:
   """
   In case of those needed to be inserted .tex file need to be inserted.

   Args:
        in_tex_path(str): path to .tex file where \\input{.*} may exist

   Returns:
        None
   """
   while True:
    with open(in_tex_path, "r", encoding='ISO-8859-1') as f:
        in_tex = f.read()
    finds = find_input_tex(in_tex) # matched patterns
    if len(finds) == 0:
        break
    else:
        insert_input_tex(in_tex_path)
      
      
   


# for pre-cleaning the latex code directory, removing unused files and commets in the .tex files.
# if __name__ == "__main__":
#     paper_dirs = []
#     multiple_results = []
#     download_abs_path = _get_absolute_path("downloads")
#     disciplines = os.listdir(download_abs_path)
#     for discipline in disciplines:
#         path_ = os.path.join(download_abs_path, discipline)
#         for paper_dir in os.listdir(path_):
#             paper_dirs.append(os.path.join(path_, paper_dir))
#     with Pool(processes=5) as pool:
#         for path in paper_dirs:
#             multiple_results.append(pool.apply_async(arxiv_latex_cleaner_pre, args=(path,)))
    
#         for res in multiple_results:
#             res.get() 


if __name__ == "__main__":
    paper_dirs = []
    download_abs_path = _get_absolute_path("downloads")
    disciplines = os.listdir(download_abs_path)
    for discipline in disciplines:
       path_ = os.path.join(download_abs_path, discipline)
       for paper_dir in os.listdir(path_):
          if paper_dir.endswith("_arXiv"):
            paper_dirs.append(os.path.join(path_, paper_dir))
    # for path in paper_dirs:
    #     print(check_main_tex(path))
    insert_input_tex_completely(check_main_tex(paper_dirs[3]))

