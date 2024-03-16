import os

if __name__ == "__main__":
    cur_dir = os.path.dirname(__file__)
    download_path = os.path.join(os.path.dirname(cur_dir), 'downloads')
    
    print(len(os.listdir(download_path)))

