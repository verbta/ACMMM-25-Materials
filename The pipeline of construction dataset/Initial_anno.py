import os
import asyncio
import aiohttp
import base64
import json
from pathlib import Path
import cv2

"""
Initial Annotation
"""

API_KEY = 'XXXXXX'
BASE_URL = "XXXXXX"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

def encode_image(image):
    _, encoded_img = cv2.imencode('.jpg', image)
    return base64.b64encode(encoded_img).decode('utf-8')

def split_and_visualize(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Image not found at {image_path}")

    h, w = img.shape[:2]

    top_left = img[:h // 2, :w // 2]
    top_right = img[:h // 2, w // 2:]
    bottom_left = img[h // 2:, :w // 2]
    bottom_right = img[h // 2:, w // 2:]

    def upscale(part):
        return cv2.resize(part, (w, h), interpolation=cv2.INTER_LANCZOS4)

    top_left_upscaled = upscale(top_left)
    top_right_upscaled = upscale(top_right)
    bottom_left_upscaled = upscale(bottom_left)
    bottom_right_upscaled = upscale(bottom_right)

    original_encoded = encode_image(img)
    top_left_encoded = encode_image(top_left_upscaled)
    top_right_encoded = encode_image(top_right_upscaled)
    bottom_left_encoded = encode_image(bottom_left_upscaled)
    bottom_right_encoded = encode_image(bottom_right_upscaled)

    return original_encoded, top_left_encoded, top_right_encoded, bottom_left_encoded, bottom_right_encoded

async def analyze_global(session, image_base64, tl, tr, bl, br):
    example_dict = {
        "situation/task": "...",
        "question": "...",
        "answer": "...",
        "visual clue": [{"clue1": "...", "reasoning": "..."}, {"clue2": "...", "reasoning": "..."}]
    }
    example_json_string = json.dumps(example_dict, ensure_ascii=False, indent=2)
    Question1 = (
    "Imagine you need to use this image to solve a specific problem or complete a specific task"
    "(e.g., geographical positioning, temporal inference, route planning, urban management, disaster detection, "
    "future prediction, event tracing, traffic safety, sports analysis, human intention speculation). Note that you"
    "should not be limited to the given scenarios; if you have other scenarios more suitable for the given image, "
    "you can design them yourself. Please first clarify the specific context or task you set, then carry out detail "
    "mining and logical exploration: in the context you set, please carefully examine the image, paying special attention "
    "to those unobtrusive details that contain rich information. Your goal is: based on the specific context you set and "
    "the special details you find, put forward a key question. This question should:"
    "1.Go beyond surface description: It should not be a simple object recognition ('What is this?'), counting ('How many are there?'), or color question ('hat color is it?')."
    "2.Be supported by details: It needs to be answered by combining (visually small) detailed visual elements in the image."
    "3.Inspire in-depth thinking: Answering the question often requires further inference."
    "4.Be closely tied to the set context: It is directly related to the task you initially envisioned to solve or complete."
    "5.Focus on the content itself: Avoid discussing image quality, shooting techniques or angles, and avoid diverging towards art, literature, etc."
    "Please first explain the context/task you set, then put forward the question you designed that requires in-depth reasoning "
    "combined with visual details to solve. Finally, give the answer and a description of the visual clues supporting the answer "
    "and the reasoning. Note that some images have more than two clues, and you should find all clues that can support the "
    "answer. The result output format is:\n"
    f"```json\n{example_json_string}\n```")


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
                            {"role": "system", "content": [{"type": "text", "text": "You are an expert for image analysis"}]},
                            {"role": "user", "content": [{"type": "text", "text": "Original image and its top-left, top-right, bottom-left"
                                                                                  "bottom-right sub images are shown as follows:"}]},
                            {"role": "user", "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}]},
                            {"role": "user", "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{tl}"}}]},
                            {"role": "user", "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{tr}"}}]},
                            {"role": "user", "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{bl}"}}]},
                            {"role": "user", "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{br}"}}]},
                            {"role": "user", "content": [{"type": "text", "text": Question1}]},
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
        ori, tl, tr, bl, br = split_and_visualize(image_path)

        global_description = await analyze_global(session, ori, tl, tr, bl, br)
        if global_description is None:
            print(f"Global analysis wrong: {image_path}")
            return

        cleaned_json = global_description.strip('`').strip().replace('json', '', 1).strip().strip('`')

        try:
            parsed_data = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            print(f"transform JSON wrong with: {e}")
            return


        json_path = Path(image_path).with_suffix(".json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=4, ensure_ascii=False)

        print(f"The image has been processed successfully: {image_path}")
    except Exception as e:
        print(f"An error occurred while processing the image.: {image_path}, error information: {e}")

async def batch_process_images(folder_path):
    image_files = [f for f in os.listdir(folder_path) if f.endswith(".jpg")]
    print("ori image number:", len(image_files))
    anno_files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
    anno_names = {file.split(".")[0] for file in anno_files}

    filtered_image_files = [
        img_file for img_file in image_files if img_file.split(".")[0] not in anno_names
    ]
    filtered_image_files = [os.path.join(folder_path, f) for f in filtered_image_files]
    print("filtered image number:", len(filtered_image_files))
    image_files = [os.path.join(folder_path, f) for f in filtered_image_files]
    timeout = aiohttp.ClientTimeout(total=500)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [process_image(session, path) for path in image_files]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    folder_path = "path1"  # Replace with the path to your image folder.
    asyncio.run(batch_process_images(folder_path))