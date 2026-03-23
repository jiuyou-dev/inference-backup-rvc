# RVC 推理备份仓库（WebUI 简化版）

## 开源项目
**原项目地址：** https://github.com/RVC-Project/Retrieval-Based-Voice-Conversion
**许可证：** MIT License

---

## WebUI 启动方式

```bash
# 进入仓库目录
cd inference-backup-rvc

# 启动 RVC WebUI（端口 7860）
python rvc_infer_only.py
```

启动后访问：**http://localhost:7860**

---

## 命令行推理启动方式

```bash
python rvc_infer_json.py -i 输入音频.wav
```

### 批处理脚本
```bash
# Windows
run_rvc.bat

# Linux/Mac
bash run_rvc.sh
```

---

## 参数说明

### 必填参数
| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | `-i` | （必填） | 输入音频文件路径 |

### 可选参数
| 参数 | 简写 | 默认值 | 说明 | 音色转换阶段 |
|------|------|--------|------|--------------|
| `--model` | `-m` | guanguanV1.pth | RVC 模型文件名 | 模型加载 |
| `--pitch` | `-p` | 0 | 音调调整（半音，范围 -24 ~ 24） | F0 提取 |
| `--f0_method` | `-f` | rmvpe | F0 提取方法 | F0 提取 |
| `--file_index` | | null | 检索索引文件路径 | 检索匹配 |
| `--index_rate` | | 0 | 索引率（范围 0 ~ 1，越高越保留原音） | 检索匹配 |
| `--filter_radius` | | 3 | 滤波半径（范围 0 ~ 7） | F0 提取 |
| `--resample_sr` | | 0 | 输出采样率（0=跟随模型） | 后处理 |
| `--rms_mix_rate` | | 1.0 | RMS 混合率（范围 0 ~ 1） | 后处理 |
| `--protect` | | 0.33 | 原声保护参数（范围 0 ~ 0.5） | 混合输出 |

### F0 方法说明
| 方法 | 说明 | 适用场景 |
|------|------|----------|
| `rmvpe` | 预训练模型提取（推荐） | 通用场景，效果最好 |
| `harvest` | 收割算法 | 低频语音，速度慢但稳定 |
| `crepe` | 深度学习提取 | 精度高，GPU 占用较高 |

---

## 音色转换流程位置

```
输入音频
    ↓
[Step 1] F0 提取 ← pitch, f0_method, filter_radius 在此阶段生效
    ↓
[Step 2] 检索匹配 ← index_rate 在此阶段生效
    ↓
[Step 3] 音色转换
    ↓
[Step 4] 后处理 ← resample_sr, rms_mix_rate 在此阶段生效
    ↓
[Step 5] 混合输出 ← protect 在此阶段控制原声比例
    ↓
输出 WAV 文件
```

---

## 典型使用场景

### 1. 基础音色转换
```bash
python rvc_infer_json.py -i voice.wav -m guanguanV1.pth
```

### 2. 音调调整（升调/降调）
```bash
# 升调 5 个半音
python rvc_infer_json.py -i voice.wav -p 5

# 降调 5 个半音
python rvc_infer_json.py -i voice.wav -p -5
```

### 3. 使用不同 F0 方法
```bash
python rvc_infer_json.py -i voice.wav -f harvest
```

### 4. 保留更多原声
```bash
python rvc_infer_json.py -i voice.wav --index_rate 0.75 --protect 0.5
```

---

## 免责声明

**本项目仅供学习研究使用。**

1. AI 生成的语音可能被误用于深度伪造、诈骗等非法用途
2. 使用者需自行承担因使用本项目产生的全部风险和责任
3. 请遵守各开源项目的许可证条款
4. 请确保使用目的符合当地法律法规

**原始开源项目责任：** RVC 的开发者对原项目承担完全责任，本仓库仅为备份和配置方案。

---

## 许可证

本仓库内容遵循原项目 MIT License 许可证。
