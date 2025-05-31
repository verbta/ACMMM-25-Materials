import os
import asyncio
import aiohttp
import base64
import json
from pathlib import Path
import cv2
import re
import numpy as np


API_KEY = 'XXXXXX'
BASE_URL = "XXXXXX"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def encode_image(image):
    _, encoded_img = cv2.imencode('.jpg', image)
    return base64.b64encode(encoded_img).decode('utf-8')




def apply_random_mask(image, grid_size=6, num_mask_blocks=9):
    h, w = image.shape[:2]
    masked_image = image.copy()

    block_h = h // grid_size
    block_w = w // grid_size

    all_blocks = [(i, j) for i in range(grid_size) for j in range(grid_size)]
    masked_blocks = np.random.choice(len(all_blocks), num_mask_blocks, replace=False)

    for block_idx in masked_blocks:
        i, j = all_blocks[block_idx]
        y_start = i * block_h
        y_end = (i + 1) * block_h if i != grid_size - 1 else h
        x_start = j * block_w
        x_end = (j + 1) * block_w if j != grid_size - 1 else w

        masked_image[y_start:y_end, x_start:x_end] = 0

    return masked_image


def split_and_visualize(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"can not load image: {image_path}")

    masked_img = apply_random_mask(img, grid_size=30, num_mask_blocks=450)

    # make save dir if not exist
    save_dir = 'XXX'
    os.makedirs(save_dir, exist_ok=True)

    filename = os.path.basename(image_path)
    save_path = os.path.join(save_dir, filename)

    cv2.imwrite(save_path, masked_img)

    masked_encoded = encode_image(masked_img)

    return masked_encoded

async def analyze_global_ans(session, situation, ori):

    retries = 0
    MAX_RETRIES= 3

    while retries < MAX_RETRIES:
        try:
            async with session.post(
                    url=f"{BASE_URL}chat/completions",
                    json={
                        "model": "XXX",
                        "temperature": 0.5,
                        "response_format":{"type": "json_object"},
                        "messages": [
                            {"role": "user", "content": [{"type": "text", "text": "You are an impartial evaluator. Your job is only to judge the relevance "
                                                                                  "between the masked image and situation. Score the relevance from 0 to 10."
                                                                                  "Only output one number."
                                                                                  }]},

                            {"role": "user", "content": [{"type": "text", "text": f"Situation: {situation}."}]},
                            {"role": "user", "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{ori}"}}]},
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


async def process_image(session, image_path):
    try:
        ori = split_and_visualize(image_path)
        anno_path = os.path.splitext(image_path)[0] + '.json'
        with open(anno_path, 'r', encoding='utf-8') as f:  #gt
            meta = json.load(f)
            situation = meta.get("situation/task", "")
            score = await analyze_global_ans(session, situation, ori)
            print(score)
            meta["score_situation"] = score
        with open(anno_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=4, ensure_ascii=False)
            print(f"The image has been processed successfully: {image_path}")
    except Exception as e:
        print(f"An error occurred while processing the image: {image_path}, error information: {e}")


async def batch_process_images(folder_path, batch_size):
    image_files = [f for f in os.listdir(folder_path) if f.endswith(".jpg")]

    image_files = [os.path.join(folder_path, f) for f in image_files]
    timeout = aiohttp.ClientTimeout(total=300)

    async with aiohttp.ClientSession(timeout=timeout) as session:

        for i in range(0, len(image_files), batch_size):
            batch = image_files[i:i + batch_size]
            tasks = [process_image(session, path) for path in batch]
            await asyncio.gather(*tasks)
            print(f"Processed batch {i // batch_size + 1}/{(len(image_files) - 1) // batch_size + 1}")



if __name__ == "__main__":
    folder_path = "path1"  #same as the Initial_anno.py path
    asyncio.run(batch_process_images(folder_path, 16))