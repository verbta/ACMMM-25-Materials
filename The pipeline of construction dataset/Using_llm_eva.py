import os
import asyncio
import aiohttp
import base64
import json
from pathlib import Path
import cv2
import re
from collections import defaultdict
from sentence_transformers import SentenceTransformer, util

"""
And then we using paraphrase-MiniLM-L12-v2 to measure the silimarity among them.

Let the answer1 is the output by MLLM1 in step1
    the answer2 is the output by MLLM2 in step3
    the answer3 is the output by MLLM3 in step3

    if similarity(answer1, answer2) < 0.7 or similarity(answer1, answer3) < 0.7 or similarity(answer2, answer3) < 0.7:
       remove
"""

model = SentenceTransformer('paraphrase-MiniLM-L12-v2')
save_path = '/home/chq/Eva_MLLMBench/New_result/gemini-2.5-pro-preview-05-06'
ori_path = '/home/chq/Eva_MLLMBench/eng'

anno_files = [f for f in os.listdir(ori_path) if f.endswith(".json")]

model_result_files = [os.path.join(save_path, f) for f in anno_files]
gt_files = [os.path.join(ori_path, f) for f in anno_files]

score = 0
for i in range(len(model_result_files)):
    model_path = model_result_files[i]
    gt_path = gt_files[i]
    with open(model_path, 'r', encoding='utf-8') as f:
         model_result = json.load(f)

    with open(gt_path, 'r', encoding='utf-8') as f:
         gt_result = json.load(f)
    if isinstance(gt_result['question'], list):
        a = gt_result['answer'][0]
        a1 = gt_result['answer'][1]
        b = model_result["Answer1"]
        b1 = model_result["Answer2"]

        embedding1 = model.encode(a, convert_to_tensor=True)
        embedding2 = model.encode(a1, convert_to_tensor=True)
        embedding3 = model.encode(b, convert_to_tensor=True)
        embedding4 = model.encode(b1, convert_to_tensor=True)

        s1 = util.cos_sim(embedding1, embedding3)
        s2 = util.cos_sim(embedding2, embedding4)
        score += (s1 + s2)
        chq = 1
    else:
        if 'Answer' not in model_result:
            score = score + 0
        else:
            a = gt_result['answer']
            b = model_result['Answer']
            embedding1 = model.encode(a, convert_to_tensor=True)
            embedding2 = model.encode(b, convert_to_tensor=True)
            s3 = util.cos_sim(embedding1, embedding2)
            score += s3


            c = gt_result.get('visual_clues',"")
            d = model_result.get('Visual_clues',"")

            chq = 1
chq = 1