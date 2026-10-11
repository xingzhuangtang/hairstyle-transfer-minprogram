#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手绘视频生成器
根据素描风格生成逐帧遮罩，合成手绘视频
效果：一只手拿着笔，一笔一笔地把素描画出来
"""

import os
import cv2
import numpy as np
import subprocess
import tempfile
import shutil
import logging

logger = logging.getLogger(__name__)


class DrawingVideoGenerator:
    """手绘视频生成器 — 服务器端帧合成"""

    SUPPORTED_STYLES = ('pencil', 'ink', 'anime', 'vivid', 'color')

    def __init__(self, ffmpeg_path='ffmpeg'):
        self.ffmpeg_path = ffmpeg_path
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        try:
            subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True, check=True
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            raise RuntimeError(f"ffmpeg 不可用: {self.ffmpeg_path}")

    def generate_video(self, image_path, style='pencil', duration=20, fps=24,
                       output_path=None, max_width=720):
        print(f"🎨 DrawingVideoGenerator.generate_video - style={style}, image_path={image_path}")
        if style not in self.SUPPORTED_STYLES:
            print(f"️ 不支持的风格: {style}, 使用默认 pencil")
            style = 'pencil'

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")

        h, w = image.shape[:2]
        if w > max_width:
            scale = max_width / w
            new_h = int(h * scale)
            image = cv2.resize(image, (max_width, new_h), interpolation=cv2.INTER_LANCZOS4)
            h, w = image.shape[:2]

        if w % 2 != 0 or h % 2 != 0:
            w = w - (w % 2)
            h = h - (h % 2)
            image = image[:h, :w]

        total_frames = duration * fps
        frame_dir = tempfile.mkdtemp(prefix='drawing_video_')

        try:
            logger.info(f"生成手绘视频: style={style}, duration={duration}s, frames={total_frames}, size={w}x{h}")

            stroke_paths = self._extract_stroke_paths(image, style)
            flat_points = stroke_paths[0] if stroke_paths else []
            logger.info(f"提取到 {len(flat_points)} 个边缘点")

            hand_sprite = self._create_hand_sprite(w, h)

            self._draw_hand_drawing_animation(image, flat_points, total_frames, frame_dir, style, hand_sprite)

            if output_path is None:
                output_path = tempfile.mktemp(suffix='.mp4', prefix='drawing_video_')

            self._compile_video(frame_dir, output_path, fps, total_frames)

            file_size = os.path.getsize(output_path)
            logger.info(f"视频生成完成: {output_path} ({file_size / 1024:.0f}KB)")

            return output_path

        finally:
            shutil.rmtree(frame_dir, ignore_errors=True)

    def _create_hand_sprite(self, canvas_w, canvas_h):
        """创建手持笔的精灵图"""
        sprite_w = int(canvas_w * 0.18)
        sprite_h = int(canvas_h * 0.22)
        sprite = np.zeros((sprite_h, sprite_w, 4), dtype=np.uint8)

        cx, cy = sprite_w // 2, sprite_h // 2

        # 笔杆 (深棕色矩形，从右下到左上倾斜)
        pen_angle = -35
        pen_len = int(sprite_h * 0.7)
        pen_w = int(sprite_w * 0.12)
        pen_tip_x = int(sprite_w * 0.3)
        pen_tip_y = int(sprite_h * 0.85)
        pen_end_x = int(sprite_w * 0.7)
        pen_end_y = int(sprite_h * 0.15)
        cv2.line(sprite, (pen_tip_x, pen_tip_y), (pen_end_x, pen_end_y), (60, 40, 20, 255), pen_w)

        # 笔尖 (黑色小三角)
        tip_size = max(3, pen_w // 2)
        cv2.circle(sprite, (pen_tip_x, pen_tip_y), tip_size, (20, 20, 20, 255), -1)

        # 手掌 (肤色椭圆)
        palm_cx = int(sprite_w * 0.65)
        palm_cy = int(sprite_h * 0.45)
        palm_rx = int(sprite_w * 0.35)
        palm_ry = int(sprite_h * 0.3)
        cv2.ellipse(sprite, (palm_cx, palm_cy), (palm_rx, palm_ry), pen_angle, 0, 360, (220, 180, 140, 230), -1)

        # 手指 (几个小椭圆)
        finger_color = (210, 170, 130, 220)
        for i, (fx, fy, frx, fry) in enumerate([
            (int(sprite_w * 0.5), int(sprite_h * 0.3), int(sprite_w * 0.08), int(sprite_h * 0.12)),
            (int(sprite_w * 0.55), int(sprite_h * 0.25), int(sprite_w * 0.07), int(sprite_h * 0.11)),
            (int(sprite_w * 0.62), int(sprite_h * 0.22), int(sprite_w * 0.07), int(sprite_h * 0.1)),
            (int(sprite_w * 0.7), int(sprite_h * 0.25), int(sprite_w * 0.08), int(sprite_h * 0.12)),
        ]):
            cv2.ellipse(sprite, (fx, fy), (frx, fry), -20 + i * 5, 0, 360, finger_color, -1)

        return sprite

    def _extract_stroke_paths(self, image, style):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]

        # 不同风格使用不同的边缘检测参数
        if style == 'pencil':
            # 铅笔素描：细线条，低阈值
            edges = cv2.Canny(gray, 15, 60)
        elif style == 'ink':
            # 水墨风格：粗线条，高阈值
            edges = cv2.Canny(gray, 40, 120)
        elif style == 'anime':
            # 日式动漫：清晰轮廓
            edges = cv2.Canny(gray, 25, 90)
        else:  # vivid, color
            # 淡彩素描：柔和边缘
            edges = cv2.Canny(gray, 20, 80)

        # 不同风格的膨胀程度不同
        if style == 'ink':
            kernel = np.ones((5, 5), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=2)
        elif style == 'anime':
            kernel = np.ones((5, 5), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=2)
        elif style == 'pencil':
            kernel = np.ones((3, 3), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=2)
        else:
            kernel = np.ones((3, 3), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            edge_points = np.column_stack(np.where(edges > 0))
            if len(edge_points) < 10:
                return []
            points_xy = [(int(p[1]), int(p[0])) for p in edge_points]
            points_xy.sort(key=lambda p: (p[1], p[0]))
            if len(points_xy) > 5000:
                step = len(points_xy) // 5000
                points_xy = points_xy[::step]
            return [points_xy]

        contour_list = []
        for contour in contours:
            if len(contour) < 2:
                continue
            points = [(int(p[0][0]), int(p[0][1])) for p in contour]
            area = cv2.contourArea(contour)
            contour_list.append((area, points))

        contour_list.sort(key=lambda x: x[0], reverse=True)

        all_points = []
        for area, points in contour_list:
            all_points.extend(points)

        all_points = list(set(all_points))
        all_points.sort(key=lambda p: (p[1], p[0]))

        if len(all_points) > 15000:
            step = len(all_points) // 15000
            all_points = all_points[::step]

        edge_mask = np.zeros((h, w), dtype=np.uint8)
        for x, y in all_points:
            cv2.circle(edge_mask, (x, y), 15, 255, -1)
        edge_mask = cv2.dilate(edge_mask, np.ones((21, 21), np.uint8), iterations=2)

        uncovered = cv2.bitwise_not(edge_mask)
        fill_ys, fill_xs = np.where(uncovered > 0)
        fill_points = []
        if len(fill_xs) > 0:
            n_fill = min(len(fill_xs), 50000)
            step = max(1, len(fill_xs) // n_fill)
            for i in range(0, len(fill_xs), step):
                fill_points.append((int(fill_xs[i]), int(fill_ys[i])))

        edge_points_sorted = sorted(all_points, key=lambda p: (p[1], p[0]))
        fill_points_sorted = sorted(fill_points, key=lambda p: (p[1], p[0]))

        return [edge_points_sorted, fill_points_sorted]

    def _draw_hand_drawing_animation(self, image, stroke_paths, total_frames, frame_dir, style, hand_sprite):
        h, w = image.shape[:2]

        if isinstance(stroke_paths, list) and len(stroke_paths) == 2:
            edge_points, fill_points = stroke_paths
        else:
            edge_points = stroke_paths if stroke_paths else []
            fill_points = []

        all_points = edge_points + fill_points
        total_points = len(all_points)
        edge_count = len(edge_points)

        sh, sw = hand_sprite.shape[:2]
        pen_tip_offset_x = int(sw * 0.3)
        pen_tip_offset_y = int(sh * 0.85)

        # 不同风格的绘制参数
        if style == 'pencil':
            reveal_radius_factor = 0.03
            line_thickness_factor = 0.01
            blur_size = 7
            color_boost = 1.0
            dilate_iterations = 1
        elif style == 'ink':
            reveal_radius_factor = 0.08
            line_thickness_factor = 0.04
            blur_size = 31
            color_boost = 0.3
            dilate_iterations = 4
        elif style == 'anime':
            reveal_radius_factor = 0.07
            line_thickness_factor = 0.035
            blur_size = 25
            color_boost = 1.8
            dilate_iterations = 3
        else:  # vivid, color
            reveal_radius_factor = 0.05
            line_thickness_factor = 0.02
            blur_size = 15
            color_boost = 1.5
            dilate_iterations = 2

        blurred_bg = cv2.GaussianBlur(image, (51, 51), 0)
        blurred_bg = cv2.addWeighted(image, 0.3, blurred_bg, 0.7, 0)

        if style == 'anime':
            white_mask = np.all(image > 240, axis=2).astype(np.uint8) * 255
            kernel = np.ones((15, 15), np.uint8)
            white_mask = cv2.dilate(white_mask, kernel, iterations=2)
            blurred_bg[white_mask > 0] = [200, 200, 200]

        reveal_radius = max(15, int(min(w, h) * reveal_radius_factor))
        thickness = max(8, int(min(w, h) * line_thickness_factor))
        dilate_kernel = np.ones((31, 31), np.uint8)

        cumulative_mask = np.zeros((h, w), dtype=np.uint8)
        prev_target = 0
        image_f = image.astype(np.float32)
        bg_f = blurred_bg.astype(np.float32)

        for frame_idx in range(total_frames):
            progress = (frame_idx + 1) / total_frames
            target_points = int(progress * total_points)

            canvas = blurred_bg.copy()

            if all_points and target_points > 0:
                current_x, current_y = all_points[min(target_points - 1, len(all_points) - 1)]

                for i in range(prev_target, target_points):
                    x, y = all_points[i]
                    cv2.circle(cumulative_mask, (x, y), reveal_radius, 255, -1)
                    if i > 0:
                        px, py = all_points[i - 1]
                        cv2.line(cumulative_mask, (px, py), (x, y), 255, thickness)

                reveal_mask = cv2.dilate(cumulative_mask, dilate_kernel, iterations=dilate_iterations)
                reveal_mask = cv2.GaussianBlur(reveal_mask, (blur_size, blur_size), 0)
                _, reveal_mask = cv2.threshold(reveal_mask, 127, 255, cv2.THRESH_BINARY)

                reveal_3ch = cv2.merge([reveal_mask, reveal_mask, reveal_mask])
                reveal_inv = cv2.bitwise_not(reveal_3ch)
                img_part = cv2.bitwise_and(image, reveal_3ch)
                bg_part = cv2.bitwise_and(canvas, reveal_inv)
                canvas = cv2.add(img_part, bg_part)

                prev_target = target_points

                if style == 'ink':
                    hsv = cv2.cvtColor(canvas, cv2.COLOR_BGR2HSV)
                    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * color_boost, 0, 255)
                    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 1.3, 0, 255)
                    canvas = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
                elif style == 'anime':
                    hsv = cv2.cvtColor(canvas, cv2.COLOR_BGR2HSV)
                    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * color_boost, 0, 255)
                    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 1.2, 0, 255)
                    canvas = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
                elif style in ('vivid', 'color'):
                    hsv = cv2.cvtColor(canvas, cv2.COLOR_BGR2HSV)
                    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * color_boost, 0, 255)
                    canvas = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

                hand_x = current_x - pen_tip_offset_x
                hand_y = current_y - pen_tip_offset_y
                hand_x = max(0, min(hand_x, w - sw))
                hand_y = max(0, min(hand_y, h - sh))

                hand_bgr = hand_sprite[:, :, :3]
                hand_alpha = hand_sprite[:, :, 3].astype(np.float32) / 255.0

                y1, y2 = hand_y, hand_y + sh
                x1, x2 = hand_x, hand_x + sw
                y1c, y2c = max(0, y1), min(h, y2)
                x1c, x2c = max(0, x1), min(w, x2)
                sy1, sy2 = y1c - y1, y2c - y1
                sx1, sx2 = x1c - x1, x2c - x1

                region = canvas[y1c:y2c, x1c:x2c].astype(np.float32)
                hand_region = hand_bgr[sy1:sy2, sx1:sx2].astype(np.float32)
                alpha = hand_alpha[sy1:sy2, sx1:sx2, np.newaxis]
                blended = hand_region * alpha + region * (1 - alpha)
                canvas[y1c:y2c, x1c:x2c] = blended.astype(np.uint8)

            cv2.imwrite(os.path.join(frame_dir, f'frame_{frame_idx:04d}.png'), canvas)

    def _compile_video(self, frame_dir, output_path, fps, total_frames):
        cmd = [
            self.ffmpeg_path, '-y',
            '-framerate', str(fps),
            '-i', os.path.join(frame_dir, 'frame_%04d.png'),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', 'fast',
            '-crf', '23',
            '-movflags', '+faststart',
            '-t', str(total_frames / fps),
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg 合成失败: {result.stderr}")


def test_generator():
    import sys

    if len(sys.argv) < 2:
        print("用法: python drawing_video_generator.py <图片路径> [风格]")
        print("风格: pencil, ink, anime, vivid")
        sys.exit(1)

    image_path = sys.argv[1]
    style = sys.argv[2] if len(sys.argv) > 2 else 'pencil'

    generator = DrawingVideoGenerator()
    output = generator.generate_video(image_path, style=style)
    print(f"视频已生成: {output}")
    print(f"文件大小: {os.path.getsize(output) / 1024:.0f}KB")


if __name__ == '__main__':
    test_generator()
