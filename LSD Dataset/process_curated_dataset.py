"""
Manual Curated Bovine Hard-Negatives Processing Pipeline
========================================================
Processes the user-provided curated list of verified bovine negative control images:
  - Category 1: Tick clusters on cow hide/skin -> ./dataset_bovine_hard_negatives/ticks_bovine_hide/
  - Category 2: Dried mud & caked manure crusts -> ./dataset_bovine_hard_negatives/mud_bovine_coat/

Zero-Mistake Quality Control:
  1. Complete deletion & reset of legacy folders and manifests.
  2. Resilient HTTP streaming with browser-compliant headers and try-except wrapping.
  3. Strict PIL byte integrity check (detects and drops corrupt/truncated streams).
  4. Perceptual hashing (pHash) deduplication (Hamming distance threshold <= 6).
  5. Format normalization: Uniform 24-bit RGB JPEGs at 95% quality.
  6. Pristine master CSV manifest generation: bovine_hard_negatives_index.csv.
"""

import os
import sys
import io
import shutil
import csv
import logging
from typing import Dict, List, Tuple, Optional
import requests
from PIL import Image
import imagehash

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Curated_Bovine_Pipeline")

# ---------------------------------------------------------------------------
# Paths and Constants
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATASET_ROOT = os.path.join(BASE_DIR, "dataset_bovine_hard_negatives")
DIR_TICKS = os.path.join(DATASET_ROOT, "ticks_bovine_hide")
DIR_MUD = os.path.join(DATASET_ROOT, "mud_bovine_coat")
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

# ---------------------------------------------------------------------------
# Target Curated URL Lists
# ---------------------------------------------------------------------------
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
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTG_5OLU_dnjsrZeeRnd6RX33yZhhmQu83rfuqvFlQXruDqOdEbWy0KikI&s=10"
]

CURATED_MUD_URLS = [
    # Batch 1 (Initial Curated Set)
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
    # Batch 2 (Additional Curated Mud & Manure Links)
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
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR9oSi_VHWqx5i2ubNQgxnCfMswze-BfvyyQkQvc8Y6Xg&s",
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
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTFsJ_q-R61I5bptPzFUi64eWdXStcypvmimcKtFtKxJQ&s=10"
]

# ---------------------------------------------------------------------------
# Pipeline Engine
# ---------------------------------------------------------------------------
def execute_pipeline():
    logger.info("=" * 75)
    logger.info("MANUAL CURATED BOVINE HARD NEGATIVES AUTOMATION PIPELINE")
    logger.info("=" * 75)

    # 1. Complete wipe of old dataset folders and previous CSV manifests
    logger.info("\n>>> Phase 1: Completely wiping existing output folders and CSV manifests...")
    for old_dir in [DATASET_ROOT, os.path.join(BASE_DIR, "dataset_hard_negatives")]:
        if os.path.exists(old_dir):
            shutil.rmtree(old_dir, ignore_errors=True)
            logger.info(f"Deleted old folder: {old_dir}")

    for old_csv in [MANIFEST_PATH, os.path.join(BASE_DIR, "hard_negatives_index.csv")]:
        if os.path.exists(old_csv):
            try:
                os.remove(old_csv)
                logger.info(f"Deleted old manifest: {old_csv}")
            except Exception as e:
                logger.warning(f"Could not delete {old_csv}: {e}")

    # Recreate pristine output directory structure
    os.makedirs(DIR_TICKS, exist_ok=True)
    os.makedirs(DIR_MUD, exist_ok=True)
    logger.info(f"Created fresh directory: {DIR_TICKS}")
    logger.info(f"Created fresh directory: {DIR_MUD}")

    # Initialize session and deduplication state
    session = requests.Session()
    session.headers.update(HEADERS)
    seen_hashes: List[Tuple[imagehash.ImageHash, str]] = []
    manifest_records: List[Dict[str, str]] = []

    stats = {
        "ticks_attempted": len(CURATED_TICK_URLS),
        "mud_attempted": len(CURATED_MUD_URLS),
        "network_or_corrupt_dropped": 0,
        "duplicates_dropped": 0,
        "ticks_saved": 0,
        "mud_saved": 0,
    }

    categories = [
        {
            "name": "ticks_bovine_hide",
            "dir": DIR_TICKS,
            "prefix": "ticks_bovine",
            "urls": CURATED_TICK_URLS
        },
        {
            "name": "mud_bovine_coat",
            "dir": DIR_MUD,
            "prefix": "mud_bovine",
            "urls": CURATED_MUD_URLS
        }
    ]

    # 2. Process each category
    for cat in categories:
        cat_name = cat["name"]
        cat_dir = cat["dir"]
        prefix = cat["prefix"]
        urls = cat["urls"]

        logger.info("\n" + "-" * 75)
        logger.info(f"PROCESSING CATEGORY: {cat_name} ({len(urls)} target curated links)")
        logger.info("-" * 75)

        saved_count = 0
        for idx, url in enumerate(urls):
            try:
                resp = session.get(url, timeout=REQUEST_TIMEOUT)
                if resp.status_code != 200:
                    stats["network_or_corrupt_dropped"] += 1
                    logger.warning(f"[{cat_name} #{idx+1}] HTTP {resp.status_code} - Skipped: {url[:70]}...")
                    continue

                raw_bytes = resp.content

                # PIL byte stream integrity verification
                try:
                    buf = io.BytesIO(raw_bytes)
                    test_img = Image.open(buf)
                    test_img.verify()
                except Exception as e:
                    stats["network_or_corrupt_dropped"] += 1
                    logger.warning(f"[{cat_name} #{idx+1}] Corrupt byte stream ({e}) - Skipped: {url[:70]}...")
                    continue

                # Reopen after verify to load into memory
                buf.seek(0)
                img = Image.open(buf)
                img.load()

                # Convert to uniform RGB
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Perceptual hash deduplication
                ph = imagehash.phash(img)
                is_duplicate = False
                matched_id = ""
                for existing_hash, existing_id in seen_hashes:
                    dist = ph - existing_hash
                    if dist <= PHASH_HAMMING_THRESHOLD:
                        is_duplicate = True
                        matched_id = existing_id
                        break

                if is_duplicate:
                    stats["duplicates_dropped"] += 1
                    logger.info(f"[{cat_name} #{idx+1}] Discarded duplicate (pHash match to {matched_id})")
                    continue

                # Save approved image
                saved_count += 1
                image_id = f"{prefix}_{saved_count:03d}"
                filename = f"{image_id}.jpg"
                filepath = os.path.join(cat_dir, filename)

                img.save(filepath, format="JPEG", quality=JPEG_QUALITY, optimize=True)
                seen_hashes.append((ph, image_id))

                if cat_name == "ticks_bovine_hide":
                    stats["ticks_saved"] += 1
                else:
                    stats["mud_saved"] += 1

                w, h = img.size
                manifest_records.append({
                    "image_id": image_id,
                    "file_path": filepath,
                    "confounder_category": cat_name,
                    "resolution_width": w,
                    "resolution_height": h,
                    "assigned_label": "healthy_negative"
                })

                logger.info(f"[{cat_name} #{saved_count:02d}] Saved {filename} ({w}x{h} px)")

            except requests.exceptions.RequestException as re:
                stats["network_or_corrupt_dropped"] += 1
                logger.warning(f"[{cat_name} #{idx+1}] Network error: {re}")
            except Exception as ex:
                stats["network_or_corrupt_dropped"] += 1
                logger.warning(f"[{cat_name} #{idx+1}] Processing error: {ex}")

    # 3. Master manifest generation
    logger.info("\n" + "=" * 75)
    logger.info("GENERATING PRISTINE MASTER CSV MANIFEST: bovine_hard_negatives_index.csv")
    logger.info("=" * 75)

    fieldnames = [
        "image_id",
        "file_path",
        "confounder_category",
        "resolution_width",
        "resolution_height",
        "assigned_label"
    ]

    for p in [MANIFEST_PATH, MANIFEST_COPY_PATH]:
        with open(p, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in manifest_records:
                writer.writerow(r)
        logger.info(f"Wrote manifest with {len(manifest_records)} records to: {p}")

    # 4. Final verification report
    total_saved = stats["ticks_saved"] + stats["mud_saved"]

    print("\n" + "=" * 75)
    print("      MANUAL CURATED BOVINE DATASET FINAL VERIFICATION REPORT")
    print("=" * 75)
    print(f"Total Curated Links Evaluated:        {stats['ticks_attempted'] + stats['mud_attempted']}")
    print(f"  ├── Tick Links Provided:            {stats['ticks_attempted']}")
    print(f"  └── Mud Links Provided:             {stats['mud_attempted']}")
    print("-" * 75)
    print(f"Network Blocked / Corrupt Streams:    {stats['network_or_corrupt_dropped']}")
    print(f"Perceptual Duplicates Removed (pHash):{stats['duplicates_dropped']}")
    print("-" * 75)
    print(f"TOTAL CLEAN IMAGES STRUCTURED:        {total_saved} (Requirement Target: 50 - 100)")
    print(f"  ├── ticks_bovine_hide:              {stats['ticks_saved']} images")
    print(f"  └── mud_bovine_coat:                {stats['mud_saved']} images")
    print("-" * 75)
    print(f"Dataset Output Directory:             {DATASET_ROOT}")
    print(f"  ├── Ticks Folder:                   {DIR_TICKS}")
    print(f"  └── Mud Folder:                     {DIR_MUD}")
    print(f"Master CSV Manifest:                  {MANIFEST_PATH}")
    print(f"Target Range 50-100 Achieved:         {'YES' if 50 <= total_saved <= 100 else 'NO'}")
    print("=" * 75 + "\n")

    return total_saved

if __name__ == "__main__":
    count = execute_pipeline()
    if count < 50:
        sys.exit(1)
    sys.exit(0)
