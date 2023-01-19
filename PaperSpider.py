import numpy as np
import requests,bs4
from concurrent.futures import ProcessPoolExecutor
import time
import os
import io
from PyPDF2 import PdfMerger  
import contextlib
from tqdm import tqdm

# selenium: for some openreview web, such as ICLR, NeurlPS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains


class Spider():
    def __init__(self, work_root="./", name="Spider", num_workers=5):
        self.url_list = []
        self.name = name 
        self.root = work_root
        self.num_workers = num_workers
        self.target_dir = os.path.join(self.root, self.name)

    def get_name(self):
        return self.name
    
    def get_pdf_list_file(self):
        pass

    def get_idx_to_paper_file(self):
        pass

    def get_pdf(self, unit):
        if len(unit) == 2:
            title, paper_link = unit[0], unit[1]
        elif len(unit) == 3:
            title, paper_link, supp_link = unit[0], unit[1], unit[2]
        target_paper_dir = os.path.join(self.target_dir, "paper")
        if not os.path.exists(target_paper_dir):
            os.mkdir(target_paper_dir)
        save_path = os.path.join(target_paper_dir, title)
        if os.path.exists(save_path+".pdf"):
            print(" Exists...",save_path)
            pass
        else:
            self.get_file_from_url(paper_link=paper_link, save_path=save_path)
            if len(unit) == 3 and supp_link is not None:
                save_supp_path = os.path.join(target_paper_dir, 'supp_'+title)
                self.get_file_from_url(paper_link=supp_link, save_path=save_supp_path)

    def get_file_from_url(self, paper_link, save_path):
        send_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
            "Connection": "keep-alive",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "cookie": "OJSSID=lmv39p08rj7chjsi5sqpunoejb",
        }
        req = requests.get(paper_link, headers=send_headers)  
        bytes_io = io.BytesIO(req.content)  
        with open(save_path + ".pdf", 'wb') as file:
            file.write(bytes_io.getvalue())  
            print("***Saved", save_path)
        time.sleep(1)
        return bytes_io

    def single_spider(self):
        for unit in self.url_list:
            self.get_pdf(unit)

    def thread_spider(self):
        process_pool = ProcessPoolExecutor(max_workers = self.num_workers)
        process_pool.map(self.get_pdf, self.url_list)

    def spider(self, mode="single", is_merge=False):
        start = time.time()
        # get_target_pdf_list_file
        self.get_pdf_list_file()
        end = time.time()
        print("Stage I: get pdf list file finish! Time Consume: {:3f}".format(end - start))

        # get_target_idx_to_paper_file
        start = end
        self.get_idx_to_paper_file()
        end = time.time()
        print("Stage II: get idx_to_paper file finish! Time Consume: {:3f}".format(end - start))

        # start spider
        start = end
        if mode == 'single':
            self.single_spider()
        elif mode == "thread":
            self.thread_spider()
        end = time.time()
        print("Finish! Time Consume: {:3f}".format(end - start))

        # test
        if is_merge:
            self.pdf_merge()
    

    # test
    def pdf_merge(self):
        paper_dir = os.path.join(self.target_dir, "paper")
        merge_paper_dir = os.path.join(self.target_dir, "paper_merge")
        if not os.path.exists(merge_paper_dir):
            os.mkdir(merge_paper_dir)
        files_list = os.listdir(paper_dir)
        for file_name in files_list:
            if "supp" in file_name:
                target_merge_path = os.path.join(merge_paper_dir, file_name.split("_")[-1])
                with contextlib.ExitStack() as stack:
                    merger = PdfMerger()
                    fs = [stack.enter_context(open(pdf,'rb')) for pdf in [os.path.join(paper_dir, file_name), os.path.join(paper_dir, file_name.split("_")[-1])]]
                    for f in fs: 
                        merger.append(f)
                    with open(target_merge_path,'wb') as new_file:
                        merger.write(new_file)
    
    def __call__(self, mode='single', is_merge=False):
        return self.spider(mode=mode, is_merge=is_merge)



class CVPR_spider(Spider):
    def __init__(self, home_page, target_prefix_page, work_root="./", name="CVPR", num_workers=5):
        super(CVPR_spider, self).__init__(work_root=work_root, name=name, num_workers=num_workers)
        self.home_page = home_page
        self.target_prefix_page = target_prefix_page
        self.target_dir = os.path.join(self.root, self.name)
        if not os.path.exists(self.target_dir):
            os.mkdir(self.target_dir)
        self.target_file_name = os.path.join(self.target_dir, self.get_name() + "_pdf_list.txt")
        self.target_idx_to_paper_name = os.path.join(self.target_dir, self.get_name() + "_idx_to_paper.txt")

    def get_pdf_list_file(self):
        f = open(self.target_file_name, 'w+')
        response = requests.get(url=self.home_page)
        if response.content:
            soup = bs4.BeautifulSoup(response.text, features="lxml")
            ele_list = soup.select("dd")
            for ele in ele_list:
                if 'pdf' in ele.text or 'supp' in ele.text:
                    href = ele.findAll("a")
                    if "pdf" in href[0].text:
                        paper = href[0].get('href')
                        f.write(self.target_prefix_page + paper[1:] + "\n")
                    if "supp" in href[1].text:
                        supp = href[1].get('href') 
                        f.write(self.target_prefix_page + supp[1:] + "\n")
                    f.write("\n")
        f.close()

    def get_idx_to_paper_file(self):
        index = open(self.target_idx_to_paper_name,"w+")
        url_list = []
        with open(self.target_file_name,"r") as fpdf:
            paper = None
            supp = None
            paper_cnt = 0
            for line in fpdf.readlines():
                if line == "\n":
                    paper_cnt += 1
                    title =  " ".join(paper.split("/")[-1].split("_")[1:-3])
                    index.write(str(paper_cnt) +" "+title+"\n")
                    self.url_list.append((str(paper_cnt), paper, supp))
                    paper = None
                    supp = None
                elif paper is None: 
                    paper = line.strip()
                else:
                    supp = line.strip()
            index.close()


class ECCV_spider(Spider):
    def __init__(self, home_page, target_prefix_page, work_root="./", name="ECCV", num_workers=5):
        super(ECCV_spider, self).__init__(work_root=work_root, name=name, num_workers=num_workers)
        self.home_page = home_page
        self.title_list = []
        self.target_prefix_page = target_prefix_page
        self.target_dir = os.path.join(self.root, self.name)
        if not os.path.exists(self.target_dir):
            os.mkdir(self.target_dir)
        self.target_file_name = os.path.join(self.target_dir, self.get_name() + "_pdf_list.txt")
        self.target_idx_to_paper_name = os.path.join(self.target_dir, self.get_name() + "_idx_to_paper.txt")

    def get_pdf_list_file(self):
        f = open(self.target_file_name, 'w+', encoding='utf-8')
        response = requests.get(url=self.home_page)
        if response.content:
            soup = bs4.BeautifulSoup(response.text, features="lxml")

            tit_list = soup.select("dt")
            for tit in tit_list:
                title = tit.find("a").text
                self.title_list.append(title.strip())
                ## by hand 
                if "Video Dialog As Conversation about Objects Living in Space-Time" in title:
                    break

            ele_list = soup.select("dd")
            title_cnt = 0

            for idx, ele in enumerate(ele_list):
                if title_cnt == len(self.title_list):
                    break
                if 'pdf' in ele.text or 'supp' in ele.text:
                    href = ele.findAll("a")
                    f.write("###"+ self.title_list[title_cnt] + "\n")
                    if "pdf" in href[0].text:
                        paper = href[0].get('href')
                        f.write(self.target_prefix_page + paper[:] + "\n")
                    if "supp" in href[1].text:
                        supp = href[1].get('href')
                        if not str(supp).endswith("zip"):
                            f.write(self.target_prefix_page + supp[:] + "\n") 
                    elif len(href) > 2 and "supp" in href[2].text:
                        supp = href[2].get('href')
                        if not str(supp).endswith("zip"):
                            f.write(self.target_prefix_page + supp[:] + "\n") 
                    f.write("\n")
                    title_cnt += 1
        f.close()

    def get_idx_to_paper_file(self):
        index = open(self.target_idx_to_paper_name,"w+", encoding='utf-8')
        url_list = []
        with open(self.target_file_name,"r", encoding='utf-8') as fpdf:
            paper = None
            supp = None
            title = None
            paper_cnt = 0
            for line in fpdf.readlines():
                if line == "\n":
                    paper_cnt += 1
                    index.write(str(paper_cnt) +" "+title+"\n")
                    self.url_list.append((str(paper_cnt), paper, supp))
                    paper = None
                    supp = None
                elif line.startswith("###"):
                    title = line.strip()[3:]
                elif paper is None: 
                    paper = line.strip()
                else:
                    supp = line.strip()
            index.close()
        

class ICLR_spider(Spider):
    def __init__(self, home_page, target_prefix_page, work_root="./", name="ICLR", num_workers=5):
        super(ICLR_spider, self).__init__(work_root=work_root, name=name, num_workers=num_workers)
        self.home_page = home_page
        self.target_prefix_page = target_prefix_page
        self.target_dir = os.path.join(self.root, self.name)
        if not os.path.exists(self.target_dir):
            os.mkdir(self.target_dir)
        self.target_file_name = os.path.join(self.target_dir, self.get_name() + "_pdf_list.txt")
        self.target_idx_to_paper_name = os.path.join(self.target_dir, self.get_name() + "_idx_to_paper.txt")

    def get_pdf_list_file(self):
        f = open(self.target_file_name, 'w+', encoding='utf-8')
        path = "/snap/bin/chromium.chromedriver"
        driver = webdriver.Chrome(path)
        driver.get(self.home_page)
        crawl_id = self.home_page.split("#")[-1]
        cond = EC.presence_of_element_located((By.XPATH, '//*[@id="'+ crawl_id + '"]/ul/li[1]'))
        WebDriverWait(driver, 10000).until(cond)
        # by hand
        for page in tqdm(range(1, 19)):
            elems = driver.find_elements(By.XPATH,'//*[@id="'+ crawl_id + '"]/ul/li')
            for i, elem in enumerate(elems):
                title_ele = elem.find_element(By.XPATH,'./h4/a[1]')
                paper_link = elem.find_element(By.XPATH,'./h4/a[2]').get_attribute('href')
                title = title_ele.text.strip()
                f.write('###' + title + "\n")
                f.write(paper_link + "\n")
                f.write("\n")
            try:
                target = driver.find_element(By.XPATH, '//*[@id="'+ crawl_id + '"]/nav/ul/li[13]/a').click()
                time.sleep(4) # NOTE: increase sleep time if needed
                cond = EC.presence_of_element_located((By.XPATH, '//*[@id="'+ crawl_id + '"]/ul/li[1]'))
                WebDriverWait(driver, 10000).until(cond)
            except:
                print("Crawl Finish!")
                break
        f.close()

    def get_idx_to_paper_file(self):
        index = open(self.target_idx_to_paper_name,"w+", encoding='utf-8')
        url_list = []
        with open(self.target_file_name,"r", encoding='utf-8') as fpdf:
            paper = None
            title = None
            paper_cnt = 0
            for line in fpdf.readlines():
                if line == "\n":
                    paper_cnt += 1
                    index.write(str(paper_cnt) +" "+title+"\n")
                    self.url_list.append((str(paper_cnt), paper))
                    paper = None
                elif line.startswith("###"):
                    title = line.strip()[3:]
                elif paper is None: 
                    paper = line.strip()
            index.close()

class AAAI_spider(Spider):
    def __init__(self, home_page, target_prefix_page, work_root="./", name="AAAI", num_workers=5):
        super(AAAI_spider, self).__init__(work_root=work_root, name=name, num_workers=num_workers)
        self.home_page = home_page
        self.target_prefix_page = target_prefix_page
        self.target_dir = os.path.join(self.root, self.name)
        if not os.path.exists(self.target_dir):
            os.mkdir(self.target_dir)
        self.target_file_name = os.path.join(self.target_dir, self.get_name() + "_pdf_list.txt")
        self.target_idx_to_paper_name = os.path.join(self.target_dir, self.get_name() + "_idx_to_paper.txt")

    def get_pdf_list_file(self):
        f = open(self.target_file_name, 'w+', encoding='utf-8')
        send_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
            "Connection": "keep-alive",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        }
        response = requests.get(url=self.home_page, headers=send_headers)
        if response.content:
            soup = bs4.BeautifulSoup(response.text, features="lxml")
            ele_list = soup.select('ul.publ-list')
            # by hand
            target_list = []
            for idx in tqdm([2]):
                ele = ele_list[idx]
                papers_info = ele.select("li.entry.inproceedings")
                for paper in papers_info:
                    title = paper.select_one(".title").text
                    paper_from_link = paper.select_one("div.head").find('a').get('href')
                    paper_response = requests.get(paper_from_link, headers=send_headers)
                    if paper_response.content:
                        paper_soup = bs4.BeautifulSoup(paper_response.text, features='lxml')
                        paper_link = paper_soup.select_one("a.obj_galley_link.pdf").get('href')
                        f.write('###' + title.strip() + "\n")
                        f.write(self.target_prefix_page + paper_link + "\n")
                        f.write("\n")
        f.close()

    def get_idx_to_paper_file(self):
        index = open(self.target_idx_to_paper_name,"w+", encoding='utf-8')
        url_list = []
        with open(self.target_file_name,"r", encoding='utf-8') as fpdf:
            paper = None
            title = None
            paper_cnt = 0
            for line in fpdf.readlines():
                if line == "\n":
                    paper_cnt += 1
                    index.write(str(paper_cnt) +" "+title+"\n")
                    self.url_list.append((str(paper_cnt), paper))
                    paper = None
                elif line.startswith("###"):
                    title = line.strip()[3:]
                elif paper is None: 
                    paper = line.strip()
            index.close()

class ICML_spider(Spider):
    def __init__(self, home_page, target_prefix_page, work_root="./", name="ICML", num_workers=5):
        super(ICML_spider, self).__init__(work_root=work_root, name=name, num_workers=num_workers)
        self.home_page = home_page
        self.target_prefix_page = target_prefix_page
        self.target_dir = os.path.join(self.root, self.name)
        if not os.path.exists(self.target_dir):
            os.mkdir(self.target_dir)
        self.target_file_name = os.path.join(self.target_dir, self.get_name() + "_pdf_list.txt")
        self.target_idx_to_paper_name = os.path.join(self.target_dir, self.get_name() + "_idx_to_paper.txt")

    def get_pdf_list_file(self):
        f = open(self.target_file_name, 'w+', encoding='utf-8')
        response = requests.get(url=self.home_page)
        if response.content:
            soup = bs4.BeautifulSoup(response.text, features="lxml")
            # tit_list = soup.find_all(class_="paper")
            ele_list = soup.select("div.paper")
            for ele in ele_list:
                title = ele.select('p.title')[0].text
                href = ele.select('p.links')[0].findAll('a')[1].get('href')
                f.write('###' + title.strip() + "\n")
                f.write(self.target_prefix_page + href + "\n")
                f.write("\n")
        f.close()

    def get_idx_to_paper_file(self):
        index = open(self.target_idx_to_paper_name,"w+", encoding='utf-8')
        url_list = []
        with open(self.target_file_name,"r", encoding='utf-8') as fpdf:
            paper = None
            title = None
            paper_cnt = 0
            for line in fpdf.readlines():
                if line == "\n":
                    paper_cnt += 1
                    index.write(str(paper_cnt) +" "+title+"\n")
                    self.url_list.append((str(paper_cnt), paper))
                    paper = None
                elif line.startswith("###"):
                    title = line.strip()[3:]
                elif paper is None: 
                    paper = line.strip()
            index.close()


'''
    CVPR home page: https://openaccess.thecvf.com/CVPR2022?day=all
         prefix page: https://openaccess.thecvf.com/
    
    ICLR home page: https://openreview.net/group?id=ICLR.cc/2022/Conference#oral-submissions (oral/spotlight/poster)
         prefix page: https://openreview.net/

    ECCV home page: https://www.ecva.net/papers.php
         prefix page: https://www.ecva.net/

    ICML home page: http://proceedings.mlr.press/v162/
         prefix page: ""

    AAAI (not done) home page: https://dblp.uni-trier.de/db/conf/aaai/aaai2022.html
         prefix page: ""

    Recent Test: 1.18, 2023
    By hand -> Need to check out the webpage of conference to get some parameters manually
        
'''

if __name__ == "__main__":
    home_page = "https://openaccess.thecvf.com/CVPR2022?day=all"
    target_prefix_page = "https://openaccess.thecvf.com/"
    cvpr_spider = ICML_spider(home_page=home_page, target_prefix_page=target_prefix_page)
    cvpr_spider()