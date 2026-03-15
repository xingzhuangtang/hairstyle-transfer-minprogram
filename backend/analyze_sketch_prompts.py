#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析素描风格Prompt差异问题
"""

import os
import json

def analyze_prompts():
    """分析不同风格的Prompt差异"""
    
    # 模拟转换器的Prompt设置
    style_prompts = {
        "pencil": "Convert this photo to detailed pencil sketch style, maintain facial features perfectly clear, fine delicate lines with varying thickness, soft realistic shadows and highlights, professional pencil drawing technique with cross-hatching for depth, natural skin texture with subtle shading, expressive eyes with detailed iris and reflections, elaborate hair texture showing individual strands and volume, high contrast black and white pencil drawing, masterful shading techniques creating depth and dimension, pure pencil sketch without any colors",
        "anime": "Japanese anime style BLACK AND WHITE sketch, clean precise linework with MONOCHROME rendering, meticulously detailed hair with CLEARLY SEPARATED strands showing DISTINCT SPATIAL DEPTH, PRONOUNCED spatial sense with foreground and background hair layers, professional line art technique, exquisite facial features with typical anime aesthetics, large expressive eyes with detailed highlights and precise iris rendering, elaborate hair texture with DIMENSIONAL LAYERS clearly visible, professional anime art style with clean BLACK outlines, MONOCHROME PALETTE with high contrast, CLEAR DEPTH PERCEPTION with overlapping hair strands, masterful anime style with SPATIAL HIERARCHY in hair rendering, each hair layer at DIFFERENT DEPTH PLANES creating strong effect, dramatic SHADING and HIGHLIGHTS throughout the portrait, pure black and white sketch without any colors",
        "ink": "Traditional Chinese ink wash painting, PURE BLACK AND WHITE MONOCHROME, delicate brushwork with ink strokes in varying intensities, elegant hair rendering with VISIBLE LAYERED STRANDS showing DEPTH and SPATIAL SEPARATION, each hair layer clearly DISTINCT with spatial sense between layers, artistic interpretation with refined ink strokes, masterful ink wash technique showing hair VOLUME DEPTH and DIMENSIONAL LAYERS, refined facial features with delicate ink lines, expressive eyes with precise ink detailing, professional Sumi-e style in MONOCHROME, dynamic hair strokes with natural ink gradation from light to dark, CLEAR SPATIAL RELATIONSHIPS between hair strands, PRONOUNCED LAYERING EFFECT with foreground middle and background hair clearly separated, traditional Chinese ink painting without any colors, pure black ink on white background",
        "color": "Vibrant colored sketch style with 10 to 30 percent COLOR SATURATION, pencil sketch foundation with SUBTLE COLOR ACCENTS, maintaining clear sketch lines with LIGHT PASTEL COLOR TOUCHES, preserving character features with GENTLE COLOR HINTS, artistic beauty with RESTRAINED COLORFUL ELEMENTS, soft color wash over detailed pencil work, MUTED COLOR PALETTE with delicate hues, sketch texture visible through LIGHT COLOR LAYERS, balanced monochrome and SUBTLE COLOR combination",
        "vivid": "Vibrant colored sketch style with 10 to 30 percent COLOR SATURATION, pencil sketch foundation with SUBTLE COLOR ACCENTS, maintaining clear sketch lines with LIGHT PASTEL COLOR TOUCHES, preserving character features with GENTLE COLOR HINTS, artistic beauty with RESTRAINED COLORFUL ELEMENTS, soft color wash over detailed pencil work, MUTED COLOR PALETTE with delicate hues, sketch texture visible through LIGHT COLOR LAYERS, balanced monochrome and SUBTLE COLOR combination",
    }
    
    print("=" * 80)
    print("素描风格Prompt分析报告")
    print("=" * 80)
    
    # 分析各风格的Prompt特点
    for style, prompt in style_prompts.items():
        print(f"\n🎨 {style.upper()} 风格分析:")
        print(f"   Prompt长度: {len(prompt)} 字符")
        
        # 关键词分析
        keywords = {
            "MONOCHROME": "MONOCHROME" in prompt.upper(),
            "BLACK AND WHITE": "BLACK AND WHITE" in prompt.upper(),
            "COLOR": "COLOR" in prompt.upper() and style in ["color", "vivid"],
            "SPATIAL": "SPATIAL" in prompt.upper(),
            "DEPTH": "DEPTH" in prompt.upper(),
            "LAYER": "LAYER" in prompt.upper(),
            "STRAND": "STRAND" in prompt.upper(),
            "HAIR": "HAIR" in prompt.upper(),
            "FACIAL": "FACIAL" in prompt.upper() or "FACE" in prompt.upper(),
        }
        
        print("   关键词分析:")
        for keyword, exists in keywords.items():
            status = "✅" if exists else "❌"
            print(f"     {status} {keyword}")
        
        # Prompt重点内容
        print(f"   重点内容:")
        if style == "pencil":
            print("     - 强调铅笔绘画技巧和阴影")
            print("     - 注重细节和纹理")
            print("     - 纯黑白风格")
        elif style == "anime":
            print("     - 强调动漫风格的线条")
            print("     - 大量的空间感和层次感描述")
            print("     - 突出眼睛和头发细节")
        elif style == "ink":
            print("     - 强调中国水墨画风格")
            print("     - 注重笔触和墨色变化")
            print("     - 强调层次和空间分离")
        elif style in ["color", "vivid"]:
            print("     - 允许10-30%的色彩饱和度")
            print("     - 在素描基础上添加淡彩")
            print("     - 保持线条清晰可见")
    
    print(f"\n" + "=" * 80)
    print("问题分析:")
    print("=" * 80)
    
    print("\n🔍 可能的问题点:")
    print("1. Prompt过于复杂和冗长")
    print("2. 某些风格的描述可能相互冲突")
    print("3. AI模型对特定艺术风格的理解偏差")
    print("4. 关键词重复过多可能导致混淆")
    
    print("\n🎯 具体分析:")
    
    # 铅笔素描 (效果好)
    print("\n✅ 铅笔素描效果好可能原因:")
    print("   - Prompt简洁明确，聚焦于核心素描技巧")
    print("   - 'pencil sketch'是AI理解度最高的风格")
    print("   - 没有复杂的文化或风格要求")
    
    # 彩色素描 (效果好)
    print("\n✅ 彩色素描效果好可能原因:")
    print("   - 明确的颜色饱和度限制(10-30%)")
    print("   - 在素描基础上添加色彩，逻辑清晰")
    print("   - 颜色描述具体且有限制")
    
    # 动漫素描 (效果差)
    print("\n❌ 动漫素描效果差可能原因:")
    print("   - Prompt过于冗长，包含大量重复关键词")
    print("   - 'SPATIAL HIERARCHY', 'DEPTH PLANES'等复杂概念")
    print("   - 过度强调头发层次可能适得其反")
    print("   - 动漫风格本身AI理解就有偏差")
    
    # 水墨素描 (效果差)
    print("\n❌ 水墨素描效果差可能原因:")
    print("   - 'ink wash painting'对西方AI模型理解困难")
    print("   - 大量的'SPATIAL', 'LAYER'关键词可能混淆")
    print("   - 'Sumi-e'等东方艺术术语识别度低")
    print("   - 墨色渐变描述过于复杂")
    
    print(f"\n" + "=" * 80)
    print("改进建议:")
    print("=" * 80)
    
    print("\n💡 优化策略:")
    print("1. 简化Prompt，去除重复关键词")
    print("2. 使用更通用的艺术术语")
    print("3. 减少抽象概念，增加具体描述")
    print("4. 测试不同长度和复杂度的Prompt")
    
    print("\n📝 建议的新Prompt:")
    
    simplified_prompts = {
        "anime": "Japanese anime style black and white sketch, clean line art with detailed hair strands, expressive eyes with highlights, monochrome drawing with clear outlines and shading",
        "ink": "Chinese ink wash painting style, black and white sketch with brush strokes, elegant hair rendering with clear layers, traditional ink painting technique",
    }
    
    for style, prompt in simplified_prompts.items():
        print(f"\n{style.upper()} (简化版):")
        print(f"   {prompt}")
        print(f"   长度: {len(prompt)} 字符 (原版: {len(style_prompts[style])})")
    
    return style_prompts, simplified_prompts

if __name__ == "__main__":
    analyze_prompts()
