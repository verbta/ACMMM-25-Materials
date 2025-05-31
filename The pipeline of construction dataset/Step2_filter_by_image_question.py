import os, glob, json, random, shutil, math, pathlib
import torch
from PIL import Image
import asyncio
import aiohttp
import base64
import json
from pathlib import Path
import cv2
import re




IMG_DIR     = "XXX"
DELETE_DIR  = "XXX"
BATCH_SIZE  = 150           # random select number of image-question pairs
COVERAGE_PASSES = 3        # The round of filter all dataset

os.makedirs(DELETE_DIR, exist_ok=True)
def encode_image(image):
    _, encoded_img = cv2.imencode('.jpg', image)
    return base64.b64encode(encoded_img).decode('utf-8')

def collect_pairs(root):
    jpg_files = glob.glob(os.path.join(root, "*.jpg"))
    pairs = []
    for jpg in jpg_files:
        json_path = os.path.splitext(jpg)[0] + ".json"
        if os.path.exists(json_path):
            pairs.append((jpg, json_path))
    return pairs

async def analyze_global(session, img, question):


    retries = 0
    MAX_RETRIES= 3

    while retries < MAX_RETRIES:
        try:
            async with session.post(
                    url=f"{BASE_URL}chat/completions",
                    json={
                        "model": "XXX",
                        "temperature": 0.5,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": [{"type": "text", "text": "You will be provided with an image and a question about the image. Your task"
                                                                                  " is to judge the relevance between image and question. Score this from 0 to 10."
                                                                                    "Note only output a number."}]},
                            {"role": "user", "content": [{"type": "text", "text": "Original image and its top-left, top-right, bottom-left"
                                                                                  "bottom-right sub images are shown as follows:"}]},
                            {"role": "user", "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}}]},
                            {"role": "user", "content": [{"type": "text", "text": question}]},
                        ],
                    },
                    headers=headers,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    print(f"Global analysis wrong with code: {response.status}")
                    return None
        except Exception as e:
            retries += 1
            print(f"Global analysis wrong，retry ({retries}/{MAX_RETRIES}): {e}")
            if retries >= MAX_RETRIES:
                print("The number of retry maximum, failed process。")
                return None

async def process_image(session, img, question, path):
    try:
        rev = []
        length = len(img)
        for i in range(length):
            for j in range(length):
                rev[i][j]= await analyze_global(session, img[i], question[j])

        valid_indices = []
        for i in range(len(rev)):
            if rev[i].max() == rev[i][i]:  #
                valid_indices.append(i)
        filtered_paths = path[valid_indices].tolist()

        paths_to_delete = [p for p in path if p not in filtered_paths]

        for p in paths_to_delete:
            print(p)

        # Delete the instance that the self-relevance is not max
        for p in paths_to_delete:
            try:
                if os.path.exists(p):
                    if os.path.isfile(p):
                        os.remove(p)
                        print(f"Delete: {p}")
                else:
                    print(f"file not exist, continue: {p}")
            except Exception as e:
                print(f"delete error: {p}, error information: {e}")

    except Exception as e:
        print(f"An error occurred while processing the image.: {image_path}, error information: {e}")

async def batch_process_images(folder_path):
    pairs = collect_pairs(folder_path)
    passes_done = 0
    while passes_done < COVERAGE_PASSES and pairs:
        random.shuffle(pairs)
        for start in range(0, len(pairs), BATCH_SIZE):
            batch_pairs = pairs[start:start + BATCH_SIZE]
            if not batch_pairs:
                break  #

            imgs, texts, paths = [], [], []  #
            for jpg, js in batch_pairs:
                try:
                    with open(js, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                        caption = meta.get("question", "")  #
                except Exception as e:
                    print(f"load json error {js}, error information: {e}")
                    caption = ""
                try:
                    img = encode_image(jpg)
                except Exception as e:
                    print(f"load image error {jpg} error information: {e}")
                    continue

                imgs.append(img)
                texts.append(caption)
                paths.append((jpg, js))
            if not imgs:
               continue
            async with aiohttp.ClientSession(timeout=timeout) as session:
                tasks = process_image(session, imgs, texts, js)
                await asyncio.gather(*tasks)





if __name__ == "__main__":
    folder_path = "path"  # Replace with the path to your image folder.
    asyncio.run(batch_process_images(folder_path))
