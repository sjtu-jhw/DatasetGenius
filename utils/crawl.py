# crwal pdfs and source from arxiv
from pathlib import Path
import requests
import os
import tarfile
import subprocess
from bs4 import  BeautifulSoup
import re
from rich.progress import Progress
import random
import shutil

BASE_URL_ABS = 'https://arxiv.org/abs/'
BASE_URL_PDF = 'https://arxiv.org/pdf/'
BASE_URL_SOURCE = 'https://arxiv.org/e-print/'


def get_doi(path: Path):
    """
    Get papers' doi from a file where the doi information lies in.

    Args:
        path(Path): path to doi information.

    Return:
        A list of doi
    """
    with open(path, 'r') as fp:
        lines = fp.readlines()
    doi_list = []
    for line in lines:
        line = line.strip()
        if line.endswith(".pdf"):
            doi_list.append(line[:-4])
    return doi_list

def gat_paper_info(doi: str):
    """
    Parse paper infomation via doi

    Args:
        doi(str): paper doi
    
    Returns:
        A dict of paper info
    """
    info = {}
    url = BASE_URL_ABS + doi
    s = requests.session()
    response = s.get(url)
    soup = BeautifulSoup(response.content, 'xml')

    title = soup.find("h1",attrs={"class":"title mathjax"})
    if title is None:
        title = ""
    else:
        title = title.text[6:]

    category = soup.find("span", attrs={'class' : 'primary-subject'})
    if category is None:
        category = ""
    else:
        category = re.sub(r'\(.*\)', "", category.text).strip()

    info['title'] = title    
    info['category'] = category
    info['doi'] = doi
    return info

def download_pdf(doi: str, dest: Path):
    """
    Download pdf to outdir

    Args:
        doi(str): paper doi in arxiv
        dest(Path): path to save pdf file

    Returns:
        A string describes downloading status
    """
    if dest.suffix == "pdf": # TODO: 1304.2432 will be recognized as a file, but it is a dir actually, how to fix this bug?
        raise ValueError("outdir should not be a file")
    os.makedirs(dest, exist_ok=True)

    if doi.endswith(".pdf"):
        dest = dest / doi
    else:
        doi = doi + ".pdf"
        dest = dest / doi
    if dest.is_file():
        return f"Download {doi} finished. File already exists."
    else:
        url = BASE_URL_PDF + doi[:-4]
        # session代表某一次连接
        s = requests.session()
        response = s.get(url)
        with open(dest, 'wb') as fp:
            fp.write(response.content)
        return f"Download {doi} finished."

def download_source(doi: str, dest: Path):
    """
    Download source to outdir

    Args:
        doi(str): paper doi in arxiv
        dest(Path): path to save pdf file

    Returns:
        A string describes downloading status
    """
    if dest.suffix == "pdf": # TODO: 1304.2432 will be recognized as a file, but it is a dir actually, how to fix this bug?
        raise ValueError("outdir should not be a file")
    os.makedirs(dest, exist_ok=True)

    if doi.endswith(".pdf"):
        doi = doi[:-4]
        doi = doi + ".tar.gz"
        dest = dest / doi 
    else:
        doi = doi + ".tar.gz"
        dest = dest / doi
    _dest = dest.parent / dest.name[:-7]
    if _dest.is_dir() or dest.is_file():
        return f"Download {doi} finished. File already exists/unzipped."
    else:
        url = BASE_URL_SOURCE + doi[:-7]
        # session代表某一次连接
        s = requests.session()
        response = s.get(url)
        with open(dest, 'wb') as fp:
            fp.write(response.content)
        return f"Download {doi} finished."
    
def extract_gz(infile: Path, dest: Path):
    """
    Extract .gz file

    Args:
        infile(Path): input file path of .ter.gz
        dest(Path): path to extract to

    Returns:
        A string describes extracting status
    """
    os.makedirs(dest, exist_ok=True)

    # unzip .gz file via 7z using subprocess
    try:
        s = subprocess.Popen(['7z', 'x', f'{infile.absolute()}', f'-o{dest.absolute()}'], stdout=subprocess.DEVNULL)
        s.wait() # wait until finish. Important!
        return f"Extract {infile.name} finished."
    except Exception as e:
        raise Exception(f"Failed to extract {infile.name}") from e


# extract .tar.gz
def extract_tar_gz(infile: Path, dest: Path):
    """
    Extract .tar.gz file

    Args:
        infile(Path): input file path of .ter.gz
        dest(Path): path to extract to

    Returns:
        A string describes extracting status
    """
    os.makedirs(dest, exist_ok=True)
    if (len(os.listdir(dest)) != 0) and not (len(os.listdir(dest)) == 1 and os.listdir(dest)[0].endswith(".pdf")): # when _extract_dir is empty and _extract_dir has one element but is a pdf, we extract                    
        return f"{dest.name} is already extrated."
    try:
        tar = tarfile.open(infile)
        tar.extractall(dest)
        tar.close()
        os.remove(infile)
        return f"Extract {infile.name} finished."
    except Exception as e1:
        try:
            gz_name = infile.parent / infile.name.replace(".tar.gz", ".gz")
            os.rename(infile, gz_name)
            extract_gz(gz_name, dest)
            os.remove(gz_name)
            return f"Extract {gz_name.name} finished."
        except Exception as e2:  
            raise Exception(f"Extract {infile.stem} failed. {e1}, {e2}")
    
  



if __name__ == "__main__":
    download_base_dir = Path("./downloads/")
    request_num = 1000 # first get this number papers, not too much for fear of explosion of my memory
    doi_list = get_doi(Path("E:/projects/vscode/2024spring/DatasetGenius/doi.txt"))
    random_doi_list = random.sample(doi_list, request_num) # random choose for diversity

    with Progress() as progress:
        task = progress.add_task("[red]Downloading...", total=request_num)
        for doi in random_doi_list:
            info = gat_paper_info(doi)
            category = info["category"]
            dest = download_base_dir / category
            print(download_source(doi, dest))
            print(download_pdf(doi, dest / doi))
            print(extract_tar_gz(dest / f'{doi}.tar.gz', dest / doi)) # after extract the source files are deleted
            if len(os.listdir(dest / doi)) == 1:
               shutil.rmtree(dest / doi)
            progress.update(task, advance=1)




