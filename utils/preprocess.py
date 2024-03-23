import os
import subprocess
from multiprocessing import Pool

def _gat_absolute_path(path: str) -> str:
    """
    return absolute path

    Args:
        path (str): path to the file
    
    Returns:
        str: absolute path
    """
    cur_dir = os.path.dirname(__file__)
    download_path = os.path.join(os.path.dirname(cur_dir), path)
    
    return download_path


def arxiv_latex_cleaner_pre(path: str) -> None:
    """
    using arxiv-latex-cleane 
    from googleresearch (https://github.com/google-research/arxiv-latex-cleaner)
    to do preprocess

    Args:
        path (str): path to the file containing the latex code
    
    """
    subprocess.Popen(f"arxiv_latex_cleaner \"{path}\"", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"PID {os.getpid()} done.")
    return None
    

if __name__ == "__main__":
    paper_dirs = []
    multiple_results = []
    download_abs_path = _gat_absolute_path("downloads")
    disciplines = os.listdir(download_abs_path)
    for discipline in disciplines:
        path_ = os.path.join(download_abs_path, discipline)
        for paper_dir in os.listdir(path_):
            paper_dirs.append(os.path.join(path_, paper_dir))
    with Pool(processes=5) as pool:
        for path in paper_dirs:
            multiple_results.append(pool.apply_async(arxiv_latex_cleaner_pre, args=(path,)))
    
        for res in multiple_results:
            res.get() 

