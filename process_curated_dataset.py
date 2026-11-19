"""Download, validate, deduplicate, and organize curated bovine hard-negative images."""

import os
import sys
import io
import shutil
import csv
import logging
from typing import Dict, List, Tuple
import requests
from PIL import Image
import imagehash

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Curated_Bovine_Pipeline")

# Paths and Constants
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATASET_ROOT = os.path.join(BASE_DIR, "dataset_bovine_hard_negatives")
DIR_TICKS = os.path.join(DATASET_ROOT, "ticks_bovine_hide")
DIR_MUD = os.path.join(DATASET_ROOT, "mud_bovine_coat")
DIR_SNOW = os.path.join(DATASET_ROOT, "snow_bovine_coat")
MANIFEST_PATH = os.path.join(BASE_DIR, "bovine_hard_negatives_index.csv")
MANIFEST_COPY_PATH = os.path.join(DATASET_ROOT, "bovine_hard_negatives_index.csv")

JPEG_QUALITY = 95
PHASH_HAMMING_THRESHOLD = 6
REQUEST_TIMEOUT = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Target Curated URL Lists (255 Unique URLs: 80 Ticks/Flies, 122 Mud, 53 Snow)
CURATED_TICK_URLS = [
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQYMUEr5_Nz6YcYEQKjGdHYuKgRC3j9wxPifqc1-SvIhQ&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQaqn3Un_orAk5S3PQy5aMPoOGsbDpNHCq8eRHwAWtiIw&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSJ3A0IQcfWjGoU7gaZPM6L_e6z3bmuccjSrITuWETwbw&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRo5JMgtxyI7oARAf1Rw8TsnclYQh-s_dFyy9ET0B731g&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRBptTqX82d2jQ7u5Qd1P_6qOiAxQnH92TJT-8ix180Jw&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSyXEwA387nwsVTD5xmIdoio8IKAvjjcG54-tXBiDXKPw&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSzfs6qWPEZKqLEYGzreE0kkqwvhCpRujwXOgXngAq0Qg&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS-Pw8R-DSK9QxMMHijUVf7_84AzOSBuWdzL9T2E93AUw&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRjVabQFdOSYI1NfejnimGFdx0E_YymN6adPrN4FSSxbQ&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRLZebTgRi9OzsUtrWzOwKidcdm_5pp8RI4fop5QRHe_A&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRgc9RQN9Ox5R4Qd4nraexVc2QPteybigeMLCaFm3DmZQ&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSWsIuVOICBCqxVyNQFoJi08uugklPwFeDjqQxc0t_S1w&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSvJ9Xg7wQt0dQL-aaS8LvS_mvnHnU2l0xyWgK2v4XcsA&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRWdekrpwxvKIjtIvY8WR188X0yTHn79HPR7tlWJ_sfmw&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTzzGYh8a7bv5OrEdkbtCtfgrcJibDOL5JLdbPppoGfFA&s=10",
    "https://ars.els-cdn.com/content/image/1-s2.0-S1877959X2100090X-gr2.jpg",
    "https://ars.els-cdn.com/content/image/1-s2.0-S0034528826002754-gr4.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQDTYUF91qcRdwJEM3pJYP7oBCU667b8ZderdVc0Riv8M3jjUAiqq3sHg8W&s=10",
    "https://www.researchgate.net/publication/378858016/figure/fig2/AS:11431281229208784@1710387110792/Ticks-between-the-legs-of-cattle-in-the-group-treated-with-fluralaner-A-Animal-5411-on_Q320.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR_XvJmtjor0lN3zKQ0W65uimbQEWL914ZBxud8-8u7Zw&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQioPJ8GZ5LtsNRU3e-nzv9oyuBFE4ddhyWaZlcFNvfZkOgeNR0VCwRZv4&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSXDnTPJK5fQ1y_vG-_Ag2jWwQbVtWVeTLuYR5qCJKzsggs7j9J-b9Yrt8X&s=10",
    "https://ars.els-cdn.com/content/image/1-s2.0-S0304401723001309-gr5.jpg",
    "https://www.researchgate.net/profile/Mohamad-Ezzedine/publication/317049746/figure/fig1/AS:501646361071616@1496613220295/Ticks-on-mammary-glands-of-cow.png",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRhiPb_et62JxNbX6oL0MiS-xexP4LpgWHpgW9BfAXnI8Gmlw5ZkMNGpKQ&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRfYaxCokLX-On0vh3wzNMI-SVTjVNg655EOa6vQP_iFF6Ri1SHm_5T3Bxs&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSki9QARJGBdymxJkXiAWUpVMbJfTAAfgtgdpioIna7T3eXKwQtVydvSZEv&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcShxHh36LONltC6CJDQSJXa5Md79YD29z4p4uaozWj3aIsG0hDsN-9IP38&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS3qrtB9MSaeDU-tx60a0bm4PDjgul9oGtEdvAGH9CLahYhl2Y7ofCgvWU&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQHSrL_QOlw3jQUHEahXE-KUEbGogLsqhZEJPheibkNLQ&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR_c376xq0M5s9OZVbX3LbV0hH5TM_06ufWwOU1h1bqnfFSsuTJtERUnD78&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSbGxwm_9EhUN0RTV1zhY9igtHNJabaH1sbqXIScWAjNAJfTwrCYgn5TQ&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSl5-GaMJgpULJxHuhaYL3xKLhCXBX17A0GACXf_gv0UonOO5oxrbO7n0b-&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS6-e_sX3E9ScOLbeOXbPo9fvsDAUWZ0M7sUiQ1MRiELg&s=10",
    "https://www.researchgate.net/profile/Ahmed-Wahba-4/publication/327566145/figure/fig1/AS:669518372302856@1536637027758/Clinical-symptoms-of-theileriosis-in-examined-Balady-Friesian-cattle-in-Egypt-a-The_Q320.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRQXI8NRZk74Pm62tugyULRLykL4WIUbMbYN6bnNZsg4sq_Ve0adr3I-Xma&s=10",
    "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/36/Rhipicephalus-appendiculatus-calf-ear.jpg/250px-Rhipicephalus-appendiculatus-calf-ear.jpg?utm_source=en.wikipedia.org&utm_campaign=parser&utm_content=thumbnail",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTSryVTdTVG7ksN2Fx51SJa84d_Gcd4j0vYRw8pQ5QjVHT_GHfhmztMxtc&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTr8ndhJAeFTbmKZ4TPCUBKio89M3Jspw7Y_jd1qGhAtIwKnzV6Lc5sEfs&s=10",
    "https://eu-images.contentstack.com/v3/assets/blt4175b16074920322/blt3ded81637aecd04d/6830799a1103881efe141037/Cattle_surrounded_by_flies_-Linda_Geist-University_of_Missouri.jpg?width=1280&auto=webp&quality=80&disable=upscale",
    "https://i0.wp.com/entomologytoday.org/wp-content/uploads/2018/08/ticks-on-cow-ear.jpg?resize=1000%2C750&ssl=1",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTwokkZMcuLsSSVtIy7S4E80PI9e0yc_jz0FIRKyQ2_lnTgTGV2cLgkA7U&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ0cxm0xwMMbcREzasVCd1CxNNKvfGjhexBXt3bScx3WgOdZaQA24GO49Ef&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSvHlnyd6LLOOIlvgtkl9AsMvIWQXjRz3EJJm8wd1dJldLQk0ReMXdYdBY&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRmIWWFXMMRlYUKpusPPotNMg5ZqEtkTshVC5S2PGuC2TNlmi1M8DdiTtrq&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSUu5HdzytDXv3wmjP-l2oV0pNB-WoWF7msJHGIXJfADRP7tf5DRcwEfb2h&s=10",
    "https://media.springernature.com/m685/springer-static/image/art%3A10.1007%2Fs12639-018-0977-z/MediaObjects/12639_2018_977_Fig1_HTML.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQWiKtuGM02_44-6BwrG81CVhDVbhEcYlIeKScg_xW4IZhvXEp0XqtV8MJ_&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSxs6ZqU2iD3KExhaTR4IM3O94xgMdozfBi5pcnqOyZQa7mwzMY5KsKq_I&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTG_5OLU_dnjsrZeeRnd6RX33yZhhmQu83rfuqvFlQXruDqOdEbWy0KikI&s=10",
    "https://pranisampad.com/wp-content/uploads/2024/05/Ticks-in-cattle-1024x611-1.webp",
    "https://tse1.mm.bing.net/th/id/OIP.XInAGMG4QkgYTE5X0QEbgAHaEK?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
    "https://rurallivingtoday.com/wp-content/uploads/cow-attacked-by-flies.jpg",
    "https://tse1.mm.bing.net/th/id/OIP.I3kjvWcS6hmLeEhpEBXybwHaEX?r=0&pid=ImgDet&w=195&h=114&c=7&dpr=1.3&o=7&rm=3",
    "https://tse1.explicit.bing.net/th/id/OIP.5JEchss_Hijs4HsiSSMtLwHaE8?r=0&pid=ImgDet&w=195&h=130&c=7&dpr=1.3&o=7&rm=3",
    "https://www.shutterstock.com/image-photo/udder-full-flies-260nw-686279443.jpg",
    "https://tse3.mm.bing.net/th/id/OIP.Pv7RnGCkvsqkrdrMl5mxjgHaEm?r=0&w=1003&h=624&rs=1&pid=ImgDetMain&o=7&rm=3",
    "https://thecountrysmallholder.com/wp-content/uploads/shutterstock_1820806.jpg",
    "https://images.ctfassets.net/vo1m91j96iq4/6bso49pvMksyPgIpjrLtUO/7d8797bbe3f72c4d1eb6f9ce5311b554/emergence-triage-cattle-flies.jpg?fl=progressive&fm=jpg&w=600&h=314&fit=fill&f=center",
    "https://eu-images.contentstack.com/v3/assets/bltdd43779342bd9107/blt0e7a348589244d73/638f3fead0a4a3750ab7a15e/0314H1-1396-1540x800.jpg?width=1280&auto=webp&quality=95&format=jpg&disable=upscale",
    "https://tse3.mm.bing.net/th/id/OIP.UbVchzmz7EGQPpjPxi1OWgHaHa?r=0&w=1440&h=1440&rs=1&pid=ImgDetMain&o=7&rm=3",
    "https://th.bing.com/th/id/R.19997bedc21622d459c56a8f1c08e891?rik=KCmHicfawRRkHA&riu=http%3a%2f%2famericancattlemen.com%2fwp-content%2fuploads%2f2025%2f04%2fBattlingFlies.jpg&ehk=4ZEcgNgY7CLP1aiDmOORf5wLg34Uhl8RZJVZpmarxmo%3d&risl=&pid=ImgRaw&r=0",
    "https://tse1.explicit.bing.net/th/id/OIP.6GTlXxEC7aMiEe_7WXCB9QHaFQ?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
    "https://www.altosidigr.com/cms/images/horn%20flies%20on%20cattle.png",
    "https://media.istockphoto.com/id/1418442348/photo/the-rare-white-park-cow.jpg?s=1024x1024&w=is&k=20&c=Eh5ZM6vr28xdRb4JmfdFXP44ZN2ShxA2kXYaGLnod8o=",
    "https://www.shutterstock.com/image-photo/hundreds-flies-bother-cows-on-260nw-686568715.jpg",
    "https://www.mwiah.com/-/media/assets/mwianimalhealth/images/insights-images/flies_on_cow_back.jpg?h=4000&iar=0&w=6000&hash=CBFF1A7805564F53DF7F1E49D3D4350B",
    "https://media.istockphoto.com/id/1341591540/photo/horn-flies-taking-off.jpg?s=612x612&w=0&k=20&c=vyGDYUIn5NJ_05HFlXDirR64-ToVLX9iq1IH7tIEKsA=",
    "https://tse3.mm.bing.net/th/id/OIP.QmPTQAvY904ZwCkpO9SzGAHaH5?r=0&w=850&h=907&rs=1&pid=ImgDetMain&o=7&rm=3",
    "https://tse4.mm.bing.net/th/id/OIP.iy69KmJ4zHuOryC1re1BvAHaE8?r=0&w=1920&h=1280&rs=1&pid=ImgDetMain&o=7&rm=3",
    "https://tse3.mm.bing.net/th/id/OIP.hl7BXstOmdnvB4Z7CHHa-wHaEo?r=0&w=760&h=475&rs=1&pid=ImgDetMain&o=7&rm=3",
    "https://tse2.mm.bing.net/th/id/OIP.woiSPHPSJfA8YiBBrNgkVAHaEL?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
    "https://tse1.explicit.bing.net/th/id/OIP.ErWX3WWWBoFOy-ozUpf2QwHaE6?r=0&rs=1&pid=ImgDet&w=195&h=130&c=7&dpr=1.3&o=7&rm=3",
    "https://th.bing.com/th/id/OIP.1OlOpC_1eOSyLyJt0HjZjQHaE7?r=0&o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3",
    "https://www.mgk.com/wp-content/uploads/2019/06/8.-Picture-Tabanids.jpg",
    "https://th.bing.com/th/id/R.19bc4da86be18f14df3021a2ef038b46?rik=Aihl0uIoPKOEiA&riu=http%3a%2f%2fcranbrooktownsman.com%2fwp-content%2fuploads%2fsites%2f14%2f2017%2f08%2f8198832_web1_HoundsTongue_cow_with_burrs.jpg&ehk=m8h8kRu%2fgaUk8IAjJHUyzMjm8pQZe%2fJMxDjv9a7bOZQ%3d&risl=&pid=ImgRaw&r=0",
    "https://tse1.mm.bing.net/th/id/OIP.Evev92N1LfZWSWm519G_uwHaDt?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
    "https://cdn.farmjournal.com/s3fs-public/C5B51270-8B4C-4404-B509F49FD3D40486.jpg",
    "https://site.extension.uga.edu/evansag/files/2025/05/image-3-1024x532.png",
    "https://www.billpelton.com/media/Horn-flies-Boxler-RESIZED.jpg"
]

CURATED_MUD_URLS = [
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSmyIdBt4yBR4HkV7zWFvgquCqKQ1yLBMIghqWyXCvmURDrZAQA9Kxihojr&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSIKHOGCfUmHswvLsrm0Ast4D9BA4o4RgbjrdOFf5Ln4JgA8VzY_vJR-8YK&s=10",
    "https://c8.alamy.com/comp/RWPAG2/a-dirty-cow-standing-in-mud-thailand-RWPAG2.jpg",
    "https://www.shutterstock.com/image-photo/young-cow-stands-muddy-field-260nw-2852985939.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQGcTD2hc-mINIpZax1H3zWEINxgO-IWFfPKhPr0v3AejrdOo_QQt7MRrzZ&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS7rwBC_yIlgOrY69SyDTdqnaS78YK9nPGc3XmiiZxywUqH9d1UpZ1GgwQY&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS4ZJgrHWJuci4dPwBiubCNlsXJ1zmppSEJryS8wkzUvQP74yEMAbQ1XXY&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQowYK_BO3-U-CoMMEWb2j2m8Z0jPwsDQcrG9XL5U-HZTVcSQ5ibaJXUnGY&s=10",
    "https://thumbs.dreamstime.com/b/cow-walking-muddy-ground-farm-cow-stands-muddy-ground-farm-its-body-partially-covered-mud-477471486.jpg",
    "https://media.istockphoto.com/id/2231870343/photo/dirty-cow-walking-away-in-mud-showing-udder-and-anus.jpg?s=612x612&w=0&k=20&c=1KUciyc3NyZvGt1usTxAras0dddafhXX1sEXNU3r1_M=",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRruvfzqZFVeHpoG_O_UYSe09i39mXPqLkmpqxYvy0-nT8SW2Vgp2VL7L4&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQbzdnV79313xdq3QnnYWwqX_0oWk2WVIf1CjjOJNi0fJFHuAsVKBN6Ybs&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcToKa_qUYsL5FxUl-ZfUpMjz_Z58cZkidCrp3ciHCbHezRUxFZkHJXKN3I&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTwYSUXE4lvzgBaR0W0XtlGa216RNjisd9l9gROp5maaqCwz2DTwurv2XUv&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR171oBmzdEKL9XD042JET1deMzNlKXmKhCwnYzCFjoManJ-6mkYhboa48U&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQvcrRk1Ie_a8XkEzbwyG1Xq0YThtlZvw0dMuNmK1PvGGgCBnV6nlfW1EI&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSr-qQ5MN9DCp0gMBXL80uRnxqpAQTipcZiJV6mAs--wPitFJlxvOjv3d0&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQT4dY2ZN-p1McKi_9NThCyEod3f_vvGlGWDxpSh5aTA98HiotlOCibsYrz&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRNFJBMxPr-nt89PPyiIWomjrEI8RmKAdorBppLQTlWdfRjTG7r_gm8ZCs&s=10",
    "https://www.4wileyfarm.com/uploads/2/8/4/1/28414001/covered-in-mud-1-of-1_orig.jpg",
    "https://media.istockphoto.com/id/2213063864/photo/cows-gather-near-water-trough-in-a-muddy-field-normandy-france.jpg?s=612x612&w=0&k=20&c=MbEWWMiOKIQQUjJklyy6z27YVwP6B7c5v8rrLR5C_H0=",
    "https://thumbs.dreamstime.com/b/cow-standing-muddy-field-daytime-located-patches-mud-scattered-grass-has-yellow-tags-its-ears-477479562.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ2mpgKVTTVu8BaStfgE6v8ObQejIhzBDMfLGVMA1CoyrfhVEoNqMcPTCY&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR9oSi_VHWqx5i2ubNQgxnCfMswze-BfvyyQkQvc8Y6Xg&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSKuJacYsOY888-gWI1yPkxVrLA3ctnZUvvmYpPu7C8sA&s=10",
    "https://www.shutterstock.com/image-photo/closeup-dirty-dairy-cows-udder-600w-2716248727.jpg",
    "https://www.shutterstock.com/image-photo/majestic-brown-cow-lies-comfortably-260nw-2581417379.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRevJi6vc9PeY_HTq1o25NiSQcEykShQ_YNtKO-s54Hz2Ecjgra-5V0cSs&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR1xjztieEK59FMlmfWyZUCRIZBuzXAbKlbbLtGD05R1no9i_C1H8Nj-r4&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTftkaJ5EKfVZkQ2JmWwaMlOLHa_mQigxTMG8ZXw5wkC2bxvuLP6-jWEVTL&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQfXPsFCB1xrEL-eutXPWG36R1dOhH1qr-roxfxwBdHrYg2iuQA1kyy9Tg&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTsYwiVT6wAnKmgeBMcq_TAFfLA1mDkwIfwylo4ilwQSWDrBKxCPYu5ahb0&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSt1W9IqMqazFACjMpC5Ky7wAadVjQt15Y1oAwVikVp6A&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS8yH63Tsf4qm1q8ahgQfoee8mYRCXlKouDAxgrDd4j-oEFbE-BfAg7nmzm&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQYpKIsGpDl0Xj8a_Y7wOZqEEJa_h0ZPTL_2307ujWVRA&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRI1iF9NAmn4g2bwXa1Qu7GGl1WNt-LH457xLvj41OA_FeN9iMenU44rAg&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTal5GyhYcDzvV4GWhThRkCpt9f6HgI1F3JB-4pQWiPJuJ1RI_YhIKe1fwh&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQoqXBnymuyXcc48s0TcZDASb5onxUG2l7Y5hLBF-AjunqqxJOM94RB5cY&s=10",
    "https://c8.alamy.com/comp/EB4BM8/cow-standing-in-mud-devon-uk-EB4BM8.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS7MKLQ1r-ig1_R5vaXt0x4QbLUlRmHj3T8tELQ9lNxrjzjDc4D8TUbPID9&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS4_u09IsjixTEO3bV-uO-PDPxZezZ2-qVc0tkGyDJ493EzG6K09JEpPpc&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTFsJ_q-R61I5bptPzFUi64eWdXStcypvmimcKtFtKxJQ&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTxVpUFOYMZ2PzqgHmJxjsLdHOAmWfapJnCGErTSwCIHeLpNYZO60tlLkCW&s=10",
    "https://eu-images.contentstack.com/v3/assets/blt4175b16074920322/blte312264875fc4073/6485e24fbd47aff32d0a4866/12-26-22_20cattle_20in_20mudGettyImages-940298960.jpg?disable=upscale&width=1200&height=630&fit=crop",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQVwV61Opif-IBmVWVDovfTf2idjwZ90jTRvz46GUDE_4RhD9CLFI8ca6U&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRabPusm65ygP1uEzbIabM-iioz87khAqe1iqfSBpYSRpn42yM_BEyTeiYq&s=10",
    "https://dartmouth.theweektoday.com/sites/default/files/2025/08/field/image/533490062_740490012191249_2227568076624132161_n.jpg",
    "https://thumbs.dreamstime.com/b/cow-walking-mud-farm-daylight-hours-brown-white-markings-walks-muddy-ground-setting-shows-477469151.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSlOOjmk2RI6aC98hDXJw4IhJX_Yvp42ZWPZsGW4-NnM6I8f5R8mRBMZtMw&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR-_MIfuexWN4l-yshZuIWJnFWJ5iNLoMsfFLYawYNA1Wqqdrl-xhUQ0QvC&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSai3DGuoXuf2hP-7UDA9dVZLZSVxOrKBLtyZ20tgufYRog0p_ZBK-94IU&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRenSoHUeAZImHObXOS04dG4EVaSi9Nh-aUO8Q4HxSn2A&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTVIeCSdNUgZuj8djJuyqn2ILeuRoIekWBvGL5XO3qPDI3c_48JK0daG64A&s=10",
    "https://media.gettyimages.com/id/2180517860/photo/african-buffalos-are-standing-on-a-body-covered-in-mud-with-calm-eyes.jpg?s=612x612&w=gi&k=20&c=vOmwrB13Ov3Ci0UygAF5ii4o0Qychv_v2YC3HYYztCk=",
    "https://video.cgtn.com/news/2020-09-10/Why-are-African-buffalos-often-covered-in-mud--TGbfQ8DwvS/video/818bbc24ec4d495a9773eb3c47e4bf7c/818bbc24ec4d495a9773eb3c47e4bf7c.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSY5bkSF0Ar_diUzMll6yfiOitSqmMi11kcvLSf7NNAjbbfRmOc-J1Jb4ap&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSie8wH9GX196WmxXi28lshl-pbJYQmflaBCeoPBeGRhU_rrezD5RV5iu0&s=10",
    "https://media.istockphoto.com/id/2226479971/photo/winter-time-feed.jpg?s=612x612&w=0&k=20&c=1s5J1BDw0ujsDr7LK9NRhy_UVT-qgj7CzW2NYjsUy4A=",
    "https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/7543ed6b-0652-4481-b7ef-260c2143de5d/d18jp50-ca8e009d-03e9-4fbe-8678-13e7a6e57653.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7InBhdGgiOiJcL2ZcLzc1NDNlZDZiLTA2NTItNDQ4MS1iN2VmLTI2MGMyMTQzZGU1ZFwvZDE4anA1MC1jYThlMDA5ZC0wM2U5LTRmYmUtODY3OC0xM2U3YTZlNTc2NTMuanBnIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmZpbGUuZG93bmxvYWQiXX0.hYa_8mYwmWX9vH4aNL1tp9cubOICKqDzdx9-hWPYp3o",
    "https://external-preview.redd.it/bEYQ5xMFBE3B3YtjBLECdn7-xUhJwu9KA04TidZcMPg.png?format=pjpg&auto=webp&s=dbd36a64cbdf597e8cb443537de04de6b5719ada",
    "https://media.istockphoto.com/id/1319403079/video/udder-of-a-black-dirty-cash-cow-grazing-on-a-beautiful-green-meadow-grass-4k.jpg?s=640x640&k=20&c=e-YSprIg_hkigG30tTkgy2ymMssLQVNKO5t88RloZ90=",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTd0OP_THrYNeBqwhhg9YZt_KGSthWLaAAHg4_SrEecb5MlAQMJyR8wCvmH&s=10",
    "https://media.rnztools.nz/rnz/image/upload/s--YjQbtMkz--/t_kt-crop-16x10/w_614/f_auto/q_auto:eco/4M7H59F_Cows_in_mud_at_Southland_farm_one_JPG",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQV6xGA-S0BreU82Y4uhg_MUecMsZFzKjIm1LhX0AH1f-xJE2_ojVlyrPIs&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQrk_uMgCHPAq8vkUz8V_p5EE5nWOx80jHtohAcKsbGZ67RDFWN4ZSM0Is&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRjBgKaSS4w5Pk9AZ3QUxE31IzJauvtINmeBB4bGvLMsQ&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSJJfYTzXglL8cBDg0ws22jdzT1OZEGLCHml0TrXd02AZJW09_vfpxvCinu&s=10",
    "https://www.stuff.co.nz/media/images/9Tzi8ywRz924XE3uHaD6DfGZQfjEdZd7oKlsiR53VLHvSZExpMzuRmKdwHbkL9PkVc5t41aFnqOdCOS2JBAtePtCLXZloCRLeahebYyu8noOrmc5M2%2FQkuLVi0td8Gk%2Fg3RFrS70QvNowGSwu86a5rYZbVPfF4hgfVqPfVIp64nWkLGTRja8L2bXwWSac6AMmvIeFzUugLwP6jQitZ5xfg==",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSXLK_fIsHzZHX6Uirek_fbTrmg4kHZ9p3PO7mSnJDRnA&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRieTC8Hz1WoyMixqPEmSu9fZH8PJeppJGhvQibLKjrQPmeMgSCl0rh8N8&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRLg3v17U4wYVtl9RBYFcKNc1EqyYho5J75wNCqrvTpr63VSXgxCCLCzok&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTeMEONYLIbFC78qlHQWomzTL0E2nsmd0KhWpoOF8b0DfwtRPxa6fLbbuRj&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQpRslMEw72FQpMmU4AVTcFqS6MmfP8dlT0DQ7eWfKDOfVBjH1Kx1GcPdxo&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRwP8eBwr0WOB-N3s4LTWigACPwm4s1adVnQwlZhk4cBjUPRuOU6sag3cA&s=10",
    "https://hips.hearstapps.com/thepioneerwoman/wp-content/uploads/2013/12/snowy1.jpg?crop=0.665079365079365xw:1xh;center,top&resize=1200:*",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTmE7nOpFXRmIjXW2wAVl2zKVgG2PpjtP6QGK3Mosrq3l1PNQ8CcNRXERSD&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQhX4MBBn3RuMmfaC7qktcEtVKZ0z8nJuSiLMT1_WtpafkkMmX79GCF9XSD&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQYZXJct2P2l4qr6bYH9kOIU02YXlBYkqdyD-CsnrQaEyOfro1lHkxHP0w&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSaoEEuzWXuu-VeBMadnmFLWH4DYNtNqAb81tL8NkqhVdZt1wdxgDrOrLo&s=10",
    "https://media.gettyimages.com/id/1194247561/photo/portrait-of-a-scottish-highland-cow-in-the-snow.jpg?s=612x612&w=gi&k=20&c=e0V8ezMxPlVhEbZGg0l6J-rXr8YdQ06UD1itkiEVdBY=",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQbrBizEf9490PuHbHIv2787O0d8XA2h4u3glTVCVbpQlxrpK16b2bm25HR&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQdigiZfRlnTE3nOpr1Z3kDWw2BlrE_8Spnzx82GLR0x_A0wEZiv_pnsrv_&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTJPTHxOXHpG1J3dpPntueM0-j9zZR63V62cQ5vOlfZMnnHNVzA99rFtc_q&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSao-9RjHfLxj_Onj7HU5788Ub3jC8fLTtOJaej8rJArq0YxrpyYTO5H8U9&s=10",
    "https://www.shutterstock.com/image-photo/cattle-freedom-cow-between-mud-260nw-2696751049.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTTK00ps4fp-3ZcMBjFs5lgZyo0xKP0dcMd1IVrOlnt8RR7ZCNH2zNAoDo&s=10",
    "https://www.shutterstock.com/image-photo/group-cows-calf-stand-deep-260nw-2764441593.jpg",
    "https://www.shutterstock.com/image-photo/beef-cows-family-standing-outdoors-260nw-2733566849.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTIbANCtXqZrQ4KrKopGfrKQu3hrJWt_E8jsw-0GGMwCRYmn_W0WLzCjEg&s=10",
    "https://www.stuff.co.nz/media/images/9Tzi8ywRz924XE3uHaD6DfGZQfjEdZd7oKlsiR53VLHvSZExpMzuRmKdwHbkL9PkBI2TuxNfSEQhYhNAKVBK75aUe2BTWtM+YMQBQqGKEiZiIv3BQ9nZCSq9a4ATOWWlcVm%2FlAmNFPusZe8c9Nd%2FB%2Fuj6dxJFTdv2uMTNwVhfKjwexYi8O079U5ftMCjgGmTWI2AwezfxN155pyqm2sFZA==",
    "https://thumbs.dreamstime.com/b/cow-14541397.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSOToFOUhs30RIsDgNLHB1qQT_Gvv041-Qse8bu07F1-RwcvD2dg46_6p8&s=10",
    "https://www.shutterstock.com/image-photo/cow-seen-on-farm-dirt-260nw-2848017279.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQU7_PB4buCyEVrcH2QPMZJwKK4gw6KiqudV6z-ROrGiuyo4YttmfMGY7s&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT2iPqfAzk_B9FVpgSAKULXiFROldWIdk4IFs3w8xibFA9DnBYLRehGBM8&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQWBMWDS9O6PieXGXpiL5Mjty22YugnvIgDpgM_57tlHXgk-jo1tlC4A6w&s=10",
    "https://media.rnztools.nz/rnz/image/upload/s--v8gx4cri--/c_scale,f_auto,q_auto,w_576/v1643365797/4NPPMEL_gallery_image_52030?_a=BACCd2AD",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTwMrVq2U9jH5L2O63oNU_Sx02lexW4zq5kt91L12YRskD74F4idxWufzM&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSAZWEGWyV6NOy58FFeAPxn2fFXHVomPihDPQk9sxQQBA&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRdzopecTPN6Hyt7ZZMjed7RjY-aiN10whBrDYluUYcdLWgYi4V8YiZ1lo&s=10",
    "https://c8.alamy.com/comp/3FKYTH2/charlottetown-prince-edward-island-pei-canadanine-mile-creekblack-and-white-cattlefarm-animallivestockbovinecowfull-bodystanding-in-mudlookin-3FKYTH2.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTK2PgZZ2QchXLFHhiKSiBtegk2jTlr7HTmGzKKmNqUDF_m8Wqp0Vf2Ppc&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQhT7AiPTvbeoegXZYXbtz4sq4RFWkYgXOtMra9PL733QKtYsHN3E7oN7U&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQyH7p1b_WkARqqYXDm3YtxjTW3IFuD2RiYJgmhW2cLVKftyHNvVFyoh3d-&s=10",
    "https://stmaaprodfwsite.blob.core.windows.net/assets/sites/1/2019/08/Stock-living-in-mud-and-their-own-excrement-nz-c-angus-robson.jpg",
    "https://ichef.bbci.co.uk/news/480/cpsprodpb/8f5f/live/15720780-05da-11f1-a351-bb43301b14c5.jpg.webp",
    "https://media.rnztools.nz/rnz/image/upload/s--L_Rny4ZJ--/t_kt-crop-16x10/w_614/f_auto/q_auto:eco/4M7HLV9_Cows_caked_in_mud_at_Southland_property_JPG",
    "https://news.stv.tv/wp-content/uploads/2025/09/e5bb6aee6ed77c7157e140980e3952b8-1756900489.jpeg",
    "https://media.istockphoto.com/id/1138734029/photo/muddy-conditions-for-cattle.jpg?s=612x612&w=0&k=20&c=Go0_werIsLsYQS5TfrE3Cp6N5Wcbw4b_AiSZeGwkvvw=",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT3pD57WIbGc11bjga7cfpksOlcIw-mDyPluYoiaOlS0EQCeWMj76fgd3G7&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcREK2Wip1rsb8l0DvSjFzJIVc9oTMJ5i3zacRlPgtjitL29nXsE3jdb8sQ&s=10",
    "https://thumbs.dreamstime.com/b/agricultural-landscape-muddy-ground-featuring-two-cows-white-brown-coats-partially-covered-mud-tree-foliage-482913877.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSTZR0bTWH96Zr1S5NE35fzrIdzMyo1k_9DtWnUZ5B032hHc822mg1tan0&s=10",
    "https://bloximages.newyork1.vip.townnews.com/feedlotmagazine.com/content/tncms/assets/v3/editorial/c/b8/cb88b3a0-e167-11ee-8a45-8780b0c28c83/65f1f0d0bbc95.image.jpg",
    "https://www.animal-welfare-foundation.org/files/_processed_/f/6/csm_AWF_20250821_El_Impuslo_Marfrig_bedding__body_heavily_soiled__7ee9fe11f9.png",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSZ23eC2LCSxQotjFtwVwSx_Fd8v99newIaE-4bGl8othzCLGITxJ4FgcI-&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSY9rYklM9hvYNwM6scGTb_qUeNyiTuyF0y1DO5XJ_qWHmTHft3V9vZwAin&s=10",
    "https://i.ytimg.com/vi/HcGQaukC4og/hqdefault.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQJ8AJK_7faxDNbr90H_82BtI-Qt4Igtdmyxh_BjFGyRWj1y8hEX-a6fyQ&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ8NZYv-9g8Oukc2rsTEQT1q2-xg4Lwp7hSaG4hMQ-zIrMbbDaVTfXb16s&s=10",
    "https://www.shutterstock.com/image-photo/two-cows-graze-snowy-field-260nw-2798257441.jpg",
    "https://ichef.bbci.co.uk/news/480/cpsprodpb/975d/live/579ce490-1bb0-11f1-9a88-31f0efde6a8b.jpg.webp"
]

CURATED_SNOW_URLS = [
    "https://cdn.sanity.io/images/5dqbssss/production-v4/44d07d4076e88890e7182b6f0e7ed635a1f95f1d-1572x933.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQNbFwXqLImoj9zv1XShz5NeFmDlLf3LgLzdECCuI6xd5xrQjhGNxwLcKk&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS_JkK_f3Y8qpPK8RzbLT9pxqJrMfgcTufPliEG0yfWxjiCVB-uvDPTbboA&s=10",
    "https://media.istockphoto.com/id/530874133/photo/cow-and-her-baby-in-the-snow.jpg?s=612x612&w=0&k=20&c=LucAVlgbHP5pkDvQXqIuTwtqJL3osP_ZynPqKBbaU2U=",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRNj8fSwWj0RHYaXRcg_mDaa8IomO9PbrnxT8IBh1O9twPkntij0KZB-gSg&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT8VWHU-UCjREg75jXBq6WoKFOhuG6ZN7m4Uow6KPejApSOyHG6yrOwQRw&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSJc1JMI-t4slAzoc0rvHTc7wMPJx1rqnW1Y1OxZUuDBYsmgMgObVUWUNk&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTuFsuooNUR8_Gy8ALF44B3cBqA3_Ip6Cd8P95DtMxmfw-fFK5sUwJ0Alng&s=10",
    "https://utbeef.tennessee.edu/wp-content/uploads/sites/127/2025/01/Cattle-in-Snow-by-Brandon-Beavers-ETREC-2000x1200.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSuvyrkW1mvxhsWLXiXXWXgJdFbZzr10kUwKM0USzPh1jUZJJEs3MinYqv8&s=10",
    "https://static.wixstatic.com/media/fa7536_e22476334e1c49aba8ca8cdc1d703bbc~mv2.jpg/v1/fill/w_1000,h_635,al_c,q_85,usm_0.66_1.00_0.01/fa7536_e22476334e1c49aba8ca8cdc1d703bbc~mv2.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR0mLN9OI5_5Dgzp96uHhp8n08rCuM3P8qO1iBq5ZbuDw&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQuUi38ebGmzYh5I-AkAcGRdkGs29b5QWyHywe7xUUpEdUPRguNzC901xE_&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSwd0cvu57pOXF8BinCtqExRAkuHljoXOWqTHZCwiU3Z7uLLWilR6ftg_pd&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ5R5Nis-D3irjaXcVy-8lXEKOWX1LXvNamse8-sbtSEvFugo9J-DSAI4Is&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSpqhwEA1hHdoc64rBqYtYrwpgn7d5k-LDqIV12KTIwjVgTuwuabiW1-PQ&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSIf7By20fho0tSc5ysfPeryOlUD3HNxCe40MdkbLAMJvKgtR2sv1riuvo&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSzIDXLJ8e-S3do8bRkmHKNX5bOR3sBkt-t0UCs4Om4bQ&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQDrv0Xv2dAODkhgtvnVmtWXhU0XvgHfbMJSgzYUdC9lppV4LggnUmP5qM&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTYA1Z0-3BnkkSOKLyhSWGEg42ITZoLE8-HLc0iacAJfLJMK742sWJeA2U&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ9z0rHhhxzedYJJ-4CJS6EZj5t0QBU6He24vW2uD3I1u2gL44DvcGrcjc&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRMWgLHgT8SdO-fnn0owjorV_IOVJDvZRnxTYkJaaaRmczHvuEa0PvXnCVM&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQiX1yOVczAioDb63RJNXrmNEaL0yf1R_G_6DaHu9jd1VJ15OOUtGV5-aIU&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTVQcY0GzjBdU1mP7WUJfC0tWn63H9kvC_SWLt2OaONoc95MdVcQ5DFht0&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSRe2Stn51ofuIOisDQlMviZ25TzoWF5t438VKmJy3aHuHjdO6Ps49a5JA&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTAz7pTZ5876v4Jv5I7RE9aRT7PjCuST7OkbBy4AzOew5NwTG5jeN-yZm8&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQBUGxJUtt7uezNOwKLLPuuAmiBkx2ouOciJnRLD2kCwppL2bH66YsfnpA&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR6RRNGIpaqZSoqz5Zzn0pTUxstUy6HRPxFeO0r1ghUKzylErNbMdTNKBFV&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRMsOlZWLb4QZ7J_G3sM33ERkFJl1WOctgzL9cXMIiiRntR8ItqvmBSmKI&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSFhzMvcSGBKmnLYWgFKofTxSqBRgxrzmGsC1d9H1bS9_AFZJ2I2BQMRG4&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRJ5pxzOOlrzU5ct-v-iCgw-5SJyFVlHaF1waTfCoPlAR5GA9mYcPranBbE&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR4E6kZ-N9cuVb_g1eW0TOC67wlmhHlf-V-Lby-nD2aOIbuOv2gYvOIIAs&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS-QvTLVNav9qN1gzuvEXLWV-ZG0wbsyzV6WjJUKO7FSAtkDfNMtz-fVA8&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTZ2NgMhrnEwI_jCrkYiANghB5RFrDPwKwo7gX96ghdJvkz6U1RfGs6V29M&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQOjc2l8z43nJ6NwlpYv2g1SmcG3CkTJKA03tbTs0VYWt9D9Iaa2PlgCAA&s=10",
    "https://images.pexels.com/photos/19326095/pexels-photo-19326095.jpeg?cs=srgb&dl=pexels-joerg-mangelsen-337913024-19326095.jpg&fm=jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ36dDARYBlUFOVDnpHn7SzPBkwuvkXuXIZvQJMGbo4cQBl9URgo0LVvTA9&s=10",
    "https://eit-wagpress-prod.s3.amazonaws.com/media/images/2016-01-snow-and-livestock.2e16d0ba.fill-1200x700.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSRMTzKlFeNemBnHYUYHRF5YZvD1FHsuInpdJ_GyEEksVof7O-2s0ZqVbU&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcScbg_N0lXzlwAZ5-obeIxh_GB9NzXazx0LXiGySrgGkWXWfDkMaPtXbRrA&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQSW9nvHidSjmUKgO0_YZAo_20ZmrxHWgVcPcUwksHVfHOLrnprdT_OWtxl&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSLKP52tpV2jmOMncZcmjB0bNaDKj188a-rMCMNpBk6wG8ExbCnoZauDTM&s=10",
    "https://www.shutterstock.com/image-photo/young-cow-heifer-standing-under-260nw-2247685261.jpg",
    "https://i.redd.it/ohj9f9pwwx0g1.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTaK8JHmmvc5NLX4NU-BuyIWqcXu1Bm8M620mfH9FEPwrBnyTvexhsrqsM&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRiFwx91YHws5v-EclIm0vEtM1DWRC6F6-6PjRJpom2otMLkxxQqJ38t-o&s=10",
    "https://www.shutterstock.com/image-photo/scottish-highlander-cow-cattle-covered-260nw-2225663181.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTxLkiy1Zs_lqeYHLMYMDm1b4MVegq-RVayZU2_WnAk7l_MmvehbmZQHDJm&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ7ViYh6WNuIq9BDKPCtLBXvT94XxPDxtJYgl-muR3FdqlmJgAwtpwBauQ&s=10",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTAXw5MuDwdLjNVv2OdhHcToltKmhzv5I_wmWvXI3x0C9mzub67Wqamk5k&s=10",
    "https://www.shutterstock.com/image-photo/brown-cow-snow-260nw-2411441919.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSjmXBbloXZoz4QZljLdKRyc2dwNtLEukYExaCF23sny1KPAq6MrZPlC0w&s=10",
    "https://www.clovermeadowsbeef.com/wp-content/uploads/2015/02/1911693_335052903353035_8703950702703904300_n.jpg"
]

# Pipeline Engine
def execute_pipeline() -> int:
    logger.info("=" * 75)
    logger.info("MANUAL CURATED BOVINE HARD NEGATIVES AUTOMATION PIPELINE")
    logger.info("=" * 75)
    logger.info("\n>>> Phase 1: Completely wiping existing output folders and CSV manifests...")
    for old_dir in [DATASET_ROOT, os.path.join(BASE_DIR, "dataset_hard_negatives")]:
        if os.path.exists(old_dir):
            shutil.rmtree(old_dir, ignore_errors=True)
            logger.info(f"Deleted old folder: {old_dir}")

    for old_csv in [MANIFEST_PATH, MANIFEST_COPY_PATH, os.path.join(BASE_DIR, "hard_negatives_index.csv")]:
        if os.path.exists(old_csv):
            try:
                os.remove(old_csv)
                logger.info(f"Deleted old manifest: {old_csv}")
            except Exception as e:
                logger.warning(f"Could not delete {old_csv}: {e}")
    for d in [DIR_TICKS, DIR_MUD, DIR_SNOW]:
        os.makedirs(d, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)
    seen_urls = set()
    seen_hashes: List[Tuple[imagehash.ImageHash, str]] = []
    manifest_records: List[Dict[str, object]] = []

    stats = {
        "ticks_attempted": len(CURATED_TICK_URLS),
        "mud_attempted": len(CURATED_MUD_URLS),
        "snow_attempted": len(CURATED_SNOW_URLS),
        "url_duplicates_skipped": 0,
        "network_or_corrupt_dropped": 0,
        "phash_duplicates_dropped": 0,
        "ticks_saved": 0,
        "mud_saved": 0,
        "snow_saved": 0,
    }

    categories = [
        {
            "name": "ticks_bovine_hide",
            "dir": DIR_TICKS,
            "prefix": "ticks_bovine",
            "urls": CURATED_TICK_URLS,
        },
        {
            "name": "mud_bovine_coat",
            "dir": DIR_MUD,
            "prefix": "mud_bovine",
            "urls": CURATED_MUD_URLS,
        },
        {
            "name": "snow_bovine_coat",
            "dir": DIR_SNOW,
            "prefix": "snow_bovine",
            "urls": CURATED_SNOW_URLS,
        },
    ]
    for cat in categories:
        cat_name = cat["name"]
        cat_dir = cat["dir"]
        prefix = cat["prefix"]
        urls = cat["urls"]
        logger.info("Processing %s (%d URLs)", cat_name, len(urls))

        saved_count = 0
        for idx, url in enumerate(urls):
            if url in seen_urls:
                stats["url_duplicates_skipped"] += 1
                continue
            seen_urls.add(url)

            try:
                resp = session.get(url, timeout=REQUEST_TIMEOUT)
                if resp.status_code != 200:
                    stats["network_or_corrupt_dropped"] += 1
                    logger.warning(f"[{cat_name} #{idx+1}] HTTP {resp.status_code} - Skipped: {url[:70]}...")
                    continue

                raw_bytes = resp.content
                try:
                    buf = io.BytesIO(raw_bytes)
                    with Image.open(buf) as test_img:
                        test_img.verify()
                except Exception as e:
                    stats["network_or_corrupt_dropped"] += 1
                    logger.warning(f"[{cat_name} #{idx+1}] Corrupt byte stream ({e}) - Skipped: {url[:70]}...")
                    continue
                buf.seek(0)
                with Image.open(buf) as opened_img:
                    opened_img.load()
                    img = opened_img.convert("RGB") if opened_img.mode != "RGB" else opened_img.copy()
                ph = imagehash.phash(img)
                is_duplicate = False
                matched_id = ""
                for existing_hash, existing_id in seen_hashes:
                    if (ph - existing_hash) <= PHASH_HAMMING_THRESHOLD:
                        is_duplicate = True
                        matched_id = existing_id
                        break

                if is_duplicate:
                    stats["phash_duplicates_dropped"] += 1
                    continue
                saved_count += 1
                image_id = f"{prefix}_{saved_count:03d}"
                filename = f"{image_id}.jpg"
                filepath = os.path.join(cat_dir, filename)

                img.save(filepath, format="JPEG", quality=JPEG_QUALITY, optimize=True)
                seen_hashes.append((ph, image_id))

                if cat_name == "ticks_bovine_hide":
                    stats["ticks_saved"] += 1
                elif cat_name == "mud_bovine_coat":
                    stats["mud_saved"] += 1
                else:
                    stats["snow_saved"] += 1

                w, h = img.size
                manifest_records.append({
                    "image_id": image_id,
                    "file_path": filepath,
                    "confounder_category": cat_name,
                    "resolution_width": w,
                    "resolution_height": h,
                    "assigned_label": "healthy_negative",
                })

            except requests.exceptions.RequestException as req_err:
                stats["network_or_corrupt_dropped"] += 1
                logger.warning(f"[{cat_name} #{idx+1}] Network error: {req_err}")
            except Exception as ex:
                stats["network_or_corrupt_dropped"] += 1
                logger.warning(f"[{cat_name} #{idx+1}] Processing error: {ex}")
    logger.info("\n" + "=" * 75)
    logger.info("GENERATING MASTER CSV MANIFEST: bovine_hard_negatives_index.csv")
    logger.info("=" * 75)

    fieldnames = [
        "image_id",
        "file_path",
        "confounder_category",
        "resolution_width",
        "resolution_height",
        "assigned_label",
    ]

    for p in [MANIFEST_PATH, MANIFEST_COPY_PATH]:
        with open(p, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(manifest_records)
    total_attempted = stats["ticks_attempted"] + stats["mud_attempted"] + stats["snow_attempted"]
    total_saved = stats["ticks_saved"] + stats["mud_saved"] + stats["snow_saved"]

    print("\n" + "=" * 75)
    print("      MANUAL CURATED BOVINE DATASET FINAL VERIFICATION REPORT")
    print("=" * 75)
    print(f"Total Curated Links Evaluated:        {total_attempted}")
    print(f"  ├── Tick / Flies Links:             {stats['ticks_attempted']}")
    print(f"  ├── Mud Links:                      {stats['mud_attempted']}")
    print(f"  └── Snow Links:                     {stats['snow_attempted']}")
    print("-" * 75)
    print(f"Duplicate URLs Skipped:               {stats['url_duplicates_skipped']}")
    print(f"Network Blocked / Corrupt Streams:    {stats['network_or_corrupt_dropped']}")
    print(f"Perceptual Duplicates Removed (pHash):{stats['phash_duplicates_dropped']}")
    print("-" * 75)
    print(f"TOTAL CLEAN IMAGES STRUCTURED:        {total_saved}")
    print(f"  ├── ticks_bovine_hide:              {stats['ticks_saved']} images")
    print(f"  ├── mud_bovine_coat:                {stats['mud_saved']} images")
    print(f"  └── snow_bovine_coat:               {stats['snow_saved']} images")
    print("-" * 75)
    print(f"Dataset Output Directory:             {DATASET_ROOT}")
    print(f"  ├── Ticks Folder:                   {DIR_TICKS}")
    print(f"  ├── Mud Folder:                     {DIR_MUD}")
    print(f"  └── Snow Folder:                    {DIR_SNOW}")
    print(f"Master CSV Manifest:                  {MANIFEST_PATH}")
    print("=" * 75 + "\n")

    return total_saved

if __name__ == "__main__":
    count = execute_pipeline()
    sys.exit(0 if count > 0 else 1)