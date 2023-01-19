## Paper Spider

- A tool to quickly crawl papers from mainstream vision-related conferences, such as CVPR, ECCV and ICLR, etc.
- Supports multi-process acceleration.
- Support for supplementary material crawling.
- ...

## Get Started

#### Installation

- Python >= 3.8
- pip install -r requirements.txt

#### Example

Now if you wanna get all 2022 CVPR papers,  you should:

1. change home_page and target_prefix_page;
2. Initialize instance, like CVPR_spider().

```python
if __name__ == "__main__":
    home_page = "https://openaccess.thecvf.com/CVPR2022?day=all"
    target_prefix_page = "https://openaccess.thecvf.com/"
    cvpr_spider = CVPR_spider(home_page=home_page, target_prefix_page=target_prefix_page)
    cvpr_spider()
```

#### Progress

- **Done:**

1. Support for CVPR, ECCV, ICLR, ICML.
2. Supports multi-process acceleration.
3. Support for supplementary material crawling.

- **To do**

1. Support for AAAI, ACM MM, ICCV, NeurlPS.
2. PDF merge between the main text and supplementary material.
