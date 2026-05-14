"""功能模块：封装具体业务能力，供路由层调用。"""

from pathlib import Path
import wave

import numpy as np


EMOTION_CN_MAP = {
    "calm": "平稳",
    "tense": "紧张",
    "excited": "激动",
    "tired": "疲惫",
    "low": "低落",
}


def _demo_features_from_file(file_path):
    size = Path(file_path).stat().st_size
    duration = max(1.2, min(12.0, size / 22000.0))
    energy = max(0.015, min(0.085, size / 1800000.0))
    zcr = max(0.05, min(0.16, 0.06 + (size % 70000) / 700000.0))
    return round(duration, 3), round(energy, 5), round(zcr, 5)


def _read_wav_as_mono(file_path):
    with wave.open(file_path, "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        raw_data = wav_file.readframes(frame_count)

    if frame_count <= 0 or sample_rate <= 0:
        raise ValueError("音频帧为空或采样率无效")

    if sample_width == 1:
        samples = np.frombuffer(raw_data, dtype=np.uint8).astype(np.float32)
        samples = (samples - 128.0) / 128.0
    elif sample_width == 2:
        samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(raw_data, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"不支持的采样位深: {sample_width * 8} bit")

    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)

    duration = frame_count / float(sample_rate)
    return samples, duration


def _compute_features(samples):
    if samples.size < 2:
        raise ValueError("音频样本过短，无法分析")

    rms_energy = float(np.sqrt(np.mean(np.square(samples))))
    zero_crossing_rate = float(np.mean((samples[:-1] * samples[1:]) < 0))
    return rms_energy, zero_crossing_rate


def _volume_level_from_energy(rms_energy):
    if rms_energy < 0.015:
        return "low"
    if rms_energy < 0.035:
        return "medium-low"
    if rms_energy < 0.08:
        return "medium"
    return "high"


def _rule_predict(duration, rms_energy, zero_crossing_rate):
    if rms_energy >= 0.08 and zero_crossing_rate >= 0.12:
        return "excited", 78, 0.78
    if rms_energy >= 0.055 and zero_crossing_rate >= 0.08:
        return "tense", 65, 0.65
    if rms_energy < 0.02 and duration < 2.5:
        return "low", 62, 0.62
    if rms_energy < 0.03 and duration >= 2.5:
        return "tired", 58, 0.58
    return "calm", 30, 0.72


def analyze_audio_file(file_path):
    warning = ""
    suffix = Path(file_path).suffix.lower()

    if suffix == ".wav":
        samples, duration = _read_wav_as_mono(file_path)
        rms_energy, zero_crossing_rate = _compute_features(samples)
    else:
        duration, rms_energy, zero_crossing_rate = _demo_features_from_file(file_path)
        warning = "录音已接收，当前版本对非 wav 文件使用演示级规则分析。"

    emotion, audio_score, confidence = _rule_predict(duration, rms_energy, zero_crossing_rate)
    volume_level = _volume_level_from_energy(rms_energy)

    return {
        "emotion": emotion,
        "emotion_cn": EMOTION_CN_MAP[emotion],
        "confidence": round(float(confidence), 4),
        "audio_score": int(audio_score),
        "features": {
            "duration": round(float(duration), 3),
            "rms_energy": round(float(rms_energy), 5),
            "zero_crossing_rate": round(float(zero_crossing_rate), 5),
            "volume_level": volume_level,
        },
        "warning": warning,
    }
