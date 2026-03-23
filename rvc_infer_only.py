#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RVC 纯推理入口 - Python 3.11 适配版
移除 uvr5、process_ckpt、parselmouth 依赖，仅支持推理

F0 方法支持：rmvpe / harvest / crepe
不支持：pm (parselmouth)
"""
import os
import sys

# ============================================================
# 项目根目录
# ============================================================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# ============================================================
# 环境变量（推理必需）
# ============================================================
os.environ.setdefault('weight_root', os.path.join(PROJECT_ROOT, 'assets', 'weights'))
os.environ.setdefault('weight_uvr5_root', os.path.join(PROJECT_ROOT, 'assets', 'uvr5_weights'))
os.environ.setdefault('index_root', os.path.join(PROJECT_ROOT, 'logs'))
os.environ.setdefault('outside_index_root', os.path.join(PROJECT_ROOT, 'assets', 'indices'))
os.environ.setdefault('rmvpe_root', os.path.join(PROJECT_ROOT, 'assets', 'rmvpe'))

# ============================================================
# 核心推理模块导入（不触发 uvr5 / process_ckpt / parselmouth）
# ============================================================
from configs.config import Config
from infer.modules.vc.modules import VC

# ============================================================
# 加载配置
# ============================================================
config = Config()

# ============================================================
# 初始化 VC 推理引擎
# ============================================================
vc = VC(config)

# ============================================================
# Gradio UI
# ============================================================
import gradio as gr
import torch
import numpy as np
import soundfile as sf

now_dir = os.getcwd()
weight_root = os.environ['weight_root']

# 获取可用模型列表
def get_model_list():
    try:
        return [f for f in os.listdir(weight_root) if f.endswith('.pth')]
    except Exception:
        return []

def get_index_list():
    index_root = os.environ['index_root']
    outside_root = os.environ['outside_index_root']
    indices = []
    for d in [index_root, outside_root]:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith('.index'):
                    indices.append(os.path.join(d, f))
    return indices

def get_audio_duration(audio_path):
    try:
        info = sf.info(audio_path)
        return info.duration
    except Exception:
        return 0

# ============================================================
# 推理函数
# ============================================================
def vc_inference(
    audio_input,
    model_name,
    sid,
    pitch,
    f0_method,
    file_index,
    index_rate,
    filter_radius,
    resample_sr,
    rms_mix_rate,
    protect,
):
    """
    变声推理主函数
    """
    if audio_input is None:
        return "请上传音频文件", None, None

    # 校验模型
    if not model_name:
        return "请选择模型", None, None

    # 加载模型
    try:
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
        print(f"[DEBUG] get_vc called with model_name={repr(model_name)}, sid={sid}", flush=True)
        # 切换模型（内部会加载模型权重）
        ret = vc.get_vc(model_name)
        print(f"[DEBUG] get_vc returned type={type(ret).__name__}, value={repr(ret)[:300]}", flush=True)
        # ret 格式: (spk_select, protect0, protect1, index, index2)
    except Exception as e:
        return f"模型加载失败: {e}", None, None

    # 保存输入音频
    input_path = os.path.join(now_dir, "temp_input_infer.wav")
    if isinstance(audio_input, str):
        # Gradio 6.x Audio(type="filepath") 返回字符串路径，直接复制
        import shutil
        shutil.copy(audio_input, input_path)
    elif hasattr(audio_input, 'name'):
        # File object from older Gradio versions
        with open(input_path, 'wb') as f:
            f.write(audio_input.read())
    elif isinstance(audio_input, tuple):
        # numpy array (sample_rate, data)
        sr, data = audio_input
        sf.write(input_path, data, sr)
    else:
        return f"音频格式不支持: {type(audio_input).__name__}", None, None

    output_path = os.path.join(now_dir, "temp_output_infer.wav")

    # 检查 F0 方法
    if f0_method == "pm":
        return "不支持 pm 方法（parselmouth），请选择 rmvpe / harvest / crepe", None, None

    try:
        # 执行推理
        result = vc.vc_single(
            sid=sid,  # sid is integer speaker ID, model is loaded by get_vc()
            input_audio_path=input_path,
            f0_up_key=pitch,
            f0_file=None,
            f0_method=f0_method,
            file_index=file_index or '',
            file_index2='',
            index_rate=index_rate,
            filter_radius=filter_radius,
            resample_sr=resample_sr,
            rms_mix_rate=rms_mix_rate,
            protect=protect,
        )

        # 详细日志
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
        print(f"[DEBUG] vc_single returned type={type(result).__name__}, len={len(result) if hasattr(result,'__len__') else 'N/A'}", flush=True)
        print(f"[DEBUG] result={repr(result)[:500]}", flush=True)

        msg, audio_data = result[0], result[1]

        # 检查音频数据是否有效
        if audio_data is None or audio_data == (None, None):
            return f"推理失败: {msg}", None, None

        sr, audio = audio_data
        if sr is None or audio is None:
            return f"推理失败: {msg}", None, None

        sf.write(output_path, audio, sr)
        duration = len(audio) / sr
        info_text = f"Success! Duration: {duration:.2f}s | Time: {msg}"
        return info_text, output_path, f"{sr} Hz"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"推理异常: {e}", None, None
    finally:
        # 清理临时文件
        if os.path.exists(input_path):
            os.remove(input_path)


# ============================================================
# 创建 Gradio 界面
# ============================================================
F0_METHODS = ["rmvpe", "harvest", "crepe"]  # 移除 pm
DEFAULT_F0 = "rmvpe"

with gr.Blocks(title="RVC 纯推理 (Python 3.11)") as demo:
    gr.Markdown("# 🎤 RVC 纯推理界面")
    gr.Markdown(f"**PyTorch**: {torch.__version__} | **CUDA**: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        gr.Markdown(f"**GPU**: {torch.cuda.get_device_name(0)}")

    with gr.Row():
        with gr.Column(scale=1):
            # ---- 输入区域 ----
            audio_input = gr.Audio(
                label="上传音频 (16kHz 效果最佳)",
                type="filepath"
            )

            model_dropdown = gr.Dropdown(
                choices=get_model_list(),
                value=get_model_list()[0] if get_model_list() else None,
                label="选择模型 (.pth)",
                interactive=True,
            )
            refresh_btn = gr.Button("🔄 刷新模型列表", size="sm")
            sid_slider = gr.Slider(
                minimum=0, maximum=108, value=0, step=1,
                label="说话人ID (sid)", interactive=True,
                info="切换说话人音色，不同sid音色不同"
            )

            with gr.Accordion("高级参数", open=False):
                pitch_slider = gr.Slider(
                    minimum=-24, maximum=24, value=0, step=1,
                    label="音调调整 (半音)", interactive=True
                )
                f0_method = gr.Radio(
                    choices=F0_METHODS,
                    value=DEFAULT_F0,
                    label="F0 提取方法",
                    interactive=True,
                )
                index_dropdown = gr.Dropdown(
                    choices=get_index_list(),
                    value=None,
                    label="检索索引文件 (.index，可选)",
                    interactive=True,
                    allow_custom_value=True,
                )
                index_rate = gr.Slider(
                    minimum=0, maximum=1, value=0, step=0.05,
                    label="索引率 (index_rate)", interactive=True
                )
                filter_radius = gr.Slider(
                    minimum=0, maximum=7, value=3, step=1,
                    label="Filter Radius (滤波半径)", interactive=True
                )
                resample_sr = gr.Slider(
                    minimum=0, maximum=48000, value=0, step=1,
                    label="输出采样率 (0=跟随模型)", interactive=True
                )
                rms_mix_rate = gr.Slider(
                    minimum=0, maximum=1, value=1, step=0.05,
                    label="RMS 混合率", interactive=True
                )
                protect = gr.Slider(
                    minimum=0, maximum=0.5, value=0.33, step=0.01,
                    label="保护参数 (protect)", interactive=True
                )

            infer_btn = gr.Button("🎵 开始推理", variant="primary", size="lg")
            save_params_btn = gr.Button("💾 保存参数", size="lg")

        with gr.Column(scale=1):
            # ---- 输出区域 ----
            output_info = gr.Textbox(label="输出信息", lines=3, interactive=False)
            audio_output = gr.Audio(label="变声结果")
            output_sr = gr.Textbox(label="输出采样率", lines=1, interactive=False)
            save_status = gr.Textbox(label="保存状态", lines=1, interactive=False)

    # ---- 事件绑定 ----
    def refresh_models():
        models = get_model_list()
        return gr.update(choices=models, value=models[0] if models else None)

    # 保存参数函数
    def save_rvc_params(
        audio_input, model_name, sid, pitch, f0_method,
        file_index, index_rate, filter_radius, resample_sr, rms_mix_rate, protect,
        output_path="F:/实验文件夹/ChatTTS/params_rvc.json"
    ):
        """保存当前 RVC 推理参数到 JSON 文件"""
        import json, os
        params = {
            "model": model_name,
            "sid": sid,
            "pitch": pitch,
            "f0_method": f0_method,
            "file_index": file_index,
            "index_rate": index_rate,
            "filter_radius": filter_radius,
            "resample_sr": resample_sr,
            "rms_mix_rate": rms_mix_rate,
            "protect": protect,
        }
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=2)
        return f"✅ RVC 参数已保存到: {output_path}"

    # 模型切换时，自动加载模型并更新 sid 滑块范围
    def on_model_change(model_name):
        if not model_name:
            return gr.update(minimum=0, maximum=108, value=0)
        try:
            ret = vc.get_vc(model_name)
            # ret[0] 是 {"visible": True, "maximum": n_spk, ...}
            spk_update = ret[0] if isinstance(ret, tuple) else ret
            n_spk = spk_update.get("maximum", 108) if isinstance(spk_update, dict) else 108
            print(f"[Model Change] model={model_name}, n_spk={n_spk}", flush=True)
            return gr.update(minimum=0, maximum=max(0, n_spk - 1), value=0)
        except Exception as e:
            print(f"[Model Change] Error: {e}", flush=True)
            return gr.update(minimum=0, maximum=108, value=0)

    refresh_btn.click(
        fn=refresh_models,
        inputs=[],
        outputs=model_dropdown,
    )

    model_dropdown.change(
        fn=on_model_change,
        inputs=model_dropdown,
        outputs=sid_slider,
    )

    infer_btn.click(
        fn=vc_inference,
        inputs=[
            audio_input,
            model_dropdown,
            sid_slider,
            pitch_slider,
            f0_method,
            index_dropdown,
            index_rate,
            filter_radius,
            resample_sr,
            rms_mix_rate,
            protect,
        ],
        outputs=[output_info, audio_output, output_sr],
    )

    # 保存参数按钮事件
    save_params_btn.click(
        fn=save_rvc_params,
        inputs=[
            audio_input,
            model_dropdown,
            sid_slider,
            pitch_slider,
            f0_method,
            index_dropdown,
            index_rate,
            filter_radius,
            resample_sr,
            rms_mix_rate,
            protect,
        ],
        outputs=[save_status],
    )

    # 示例说明
    gr.Markdown("---")
    gr.Markdown("""
    **使用方法：**
    1. 上传音频文件（建议 16kHz 单声道 WAV）
    2. 选择 RVC 模型文件
    3. 调整参数后点击「开始推理」
    4. 等待推理完成，下载结果

    **F0 方法说明：**
    - **rmvpe**（默认）：精度高，速度快，推荐使用
    - **harvest**：精度高，速度较慢，CPU 友好
    - **crepe**：精度最高，GPU 显存占用较大

    **注意：** 本界面已移除 uvr5（人声分离）和 pm（parselmouth）功能。
    """)

# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("RVC 纯推理界面 - Python 3.11 适配版")
    print("=" * 60)
    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Model dir: {weight_root}")
    print(f"Index dir: {os.environ['index_root']}")
    print(f"rmvpe dir: {os.environ['rmvpe_root']}")
    print()
    print("F0 methods available: rmvpe, harvest, crepe")
    print("F0 methods NOT available: pm (parselmouth removed)")
    print()
    print("启动服务: http://localhost:7860")
    print("按 Ctrl+C 停止服务")
    print("=" * 60)

    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        quiet=False,
    )
