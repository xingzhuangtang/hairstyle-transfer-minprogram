#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DashScope AI 视频生成器（高级选项）
使用万相图生视频 API 将素描图转为手绘风格视频
"""

import os
import time
import requests
import logging

logger = logging.getLogger(__name__)


class DashScopeVideoGenerator:
    """DashScope 图生视频 — 高级手绘视频选项"""

    STYLE_PROMPTS = {
        'pencil': (
            "A hand slowly drawing this pencil sketch with fine pencil strokes, "
            "progressively revealing the portrait stroke by stroke, "
            "cross-hatching technique, realistic pencil drawing animation, "
            "the drawing appears gradually as if being sketched by an invisible artist"
        ),
        'ink': (
            "A Chinese calligraphy brush painting this ink wash portrait stroke by stroke, "
            "ink spreading on rice paper, traditional Sumi-e painting process, "
            "the image gradually appears as brush strokes flow across the paper"
        ),
        'anime': (
            "An artist drawing this anime portrait with clean precise lines, "
            "progressively revealing the illustration, line art first then color fill, "
            "anime drawing process animation, cel-shading technique"
        ),
        'vivid': (
            "A soft pastel sketch being gently drawn, gradually revealing the portrait "
            "with light color touches, watercolor wash effect, "
            "the image appears as if painted by gentle brush strokes"
        ),
        'color': (
            "A soft pastel sketch being gently drawn, gradually revealing the portrait "
            "with light color touches, the image appears as if painted by gentle brush strokes"
        ),
    }

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('DASHSCOPE_API_KEY')
        if not self.api_key:
            raise ValueError('未找到 DASHSCOPE_API_KEY')

        self.endpoint = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/image2video/image-synthesis'
        logger.info(f'DashScope 视频生成器初始化, endpoint={self.endpoint}')

    def generate(self, image_url, style='pencil', duration=5):
        """
        生成手绘视频

        Args:
            image_url: 素描图片公网URL
            style: 风格
            duration: 视频时长(秒)

        Returns:
            str: 生成的视频文件本地路径
        """
        prompt = self.STYLE_PROMPTS.get(style, self.STYLE_PROMPTS['pencil'])

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-DashScope-Async': 'enable',
        }

        request_data = {
            'model': 'wan2.5-i2v-preview',
            'input': {
                'prompt': prompt,
                'img_url': image_url,
            },
            'parameters': {
                'resolution': '720P',
                'duration': 10,
                'n': 1,
            },
        }

        logger.info(f'调用 DashScope 图生视频 API, style={style}, img_url={image_url[:80]}...')
        response = requests.post(self.endpoint, headers=headers, json=request_data, timeout=120)

        if response.status_code != 200:
            error = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            raise Exception(f'DashScope API 错误 {response.status_code}: {error}')

        result_data = response.json()
        task_id = result_data.get('output', {}).get('task_id')
        if not task_id:
            raise Exception(f'无效的 API 响应: {result_data}')

        video_url = self._wait_for_task(task_id)
        return self._download_video(video_url)

    def _wait_for_task(self, task_id, max_wait=600):
        logger.info(f'等待视频生成完成, task_id={task_id}')

        headers = {
            'Authorization': f'Bearer {self.api_key}',
        }
        query_url = f'https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}'
        start = time.time()

        while time.time() - start < max_wait:
            response = requests.get(query_url, headers=headers, timeout=120)
            if response.status_code != 200:
                time.sleep(10)
                continue

            data = response.json()
            status = data.get('output', {}).get('task_status', 'UNKNOWN')

            if status == 'SUCCEEDED':
                results = data.get('output', {}).get('results', [])
                if results and results[0].get('url'):
                    return results[0]['url']
                raise Exception('任务成功但无视频结果')

            if status == 'FAILED':
                msg = data.get('output', {}).get('message', '未知错误')
                raise Exception(f'视频生成失败: {msg}')

            logger.info(f'任务状态: {status}, 等待10秒...')
            time.sleep(10)

        raise Exception(f'视频生成超时 (>{max_wait}秒)')

    def _download_video(self, url, save_path=None):
        if save_path is None:
            import tempfile
            save_path = tempfile.mktemp(suffix='.mp4', prefix='dashscope_video_')

        logger.info(f'下载视频: {url[:80]}...')
        response = requests.get(url, timeout=300)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            f.write(response.content)

        logger.info(f'视频下载完成: {save_path} ({os.path.getsize(save_path) / 1024:.0f}KB)')
        return save_path
