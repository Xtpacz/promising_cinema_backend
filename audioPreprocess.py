import os
import subprocess

from pydub import AudioSegment
from spleeter.separator import Separator
from multiprocessing import freeze_support

import numpy as np
import scipy.io.wavfile as wavfile
from scipy import signal

import tqdm
from tqdm._tqdm import trange


"""
切割音频文件，每个文件为8分钟
"""
def audio_split(filename) -> int:
    # 确保目录存在
    output_dir = f"./sources/{filename}/audio-split/"
    os.makedirs(output_dir, exist_ok=True)
    # 读取音频文件
    audio_path = f'./sources/{filename}/{filename}.mp3'  # 更改为你的音频文件路径
    audio = AudioSegment.from_file(audio_path)
    # 每段音频的长度不超过9分钟（以毫秒为单位）
    max_length_per_chunk = 480000  # 8分钟 = 480秒 = 480000毫秒,少弄点
    # 总音频长度（以毫秒为单位）
    total_length = len(audio)
    print(f"当前处理音频:{filename}, 总长度为{total_length / 1000}秒")
    # 计算需要分成的段数，确保每段不超过10分钟
    n = total_length // max_length_per_chunk + (1 if total_length % max_length_per_chunk > 0 else 0)
    # 分割并保存音频
    for i in trange(n):
        start = i * max_length_per_chunk
        end = start + max_length_per_chunk if i < n - 1 else total_length
        chunk = audio[start:end]
        file_path = os.path.join(output_dir, f"{i}.mp3")  # 文件以序号命名
        chunk.export(file_path, format='mp3')
    print(f'音频分割完成，根据最大分段长度8分钟，音频被分割为{n}部分保存在{output_dir}')
    return n


"""
利用spleeter分离出vocals
"""
def vocals_separator(filename, n):
    freeze_support()
    # 确保目录存在
    output_dir = f"./sources/{filename}/audio-separate/"
    os.makedirs(output_dir, exist_ok=True)
    # 使用嵌入配置
    # separator = Separator('spleeter:2stems')
    print("分离背景声与人声.")
    for i in range(n):
        source_dir = f"sources/{filename}/audio-split/{i}.mp3"
        target_dir = f"sources/{filename}/audio-separate"
        # print(f"当前正在处理第{i}个片段")
        # 试试cli控制台
        cmd = fr'D:\programs\Anaconda\Scripts\activate.bat D:\programs\Anaconda && conda activate myserver && spleeter separate -o {target_dir} {source_dir}'
        subprocess.call(cmd, shell=True)

        # # 分离文件，不管用
        # separator.separate_to_file(f'D:/code/promising-video/the-server/sources/{filename}/audio-split/{i}.mp3',
        #                            f"sources/{filename}/audio-separate/")
    print("分离完成.")

"""
将分离之后的音频文件合并
"""
def combine_audio(filename, n):
    print("合并人声.")
    base_path = f"sources/{filename}/audio-separate"
    output_file = f"sources/{filename}/{filename}_preprocessed.mp3"
    # 初始化空的音频片段
    combined = AudioSegment.empty()
    # 循环遍历指定范围的数字，加载并合并MP3文件
    for index in trange(n):
        # 变为mp3
        wav_path = f"{base_path}/{index}/{filename}_filtered.wav"
        # 构建当前MP3文件的路径
        mp3_path = f"{base_path}/{index}/vocals.mp3"
        audio = AudioSegment.from_wav(wav_path)
        audio.export(mp3_path, format="mp3", bitrate="192k")
        # 加载MP3文件
        audio_segment = AudioSegment.from_file(mp3_path, format="mp3")
        # 合并到当前的音频片段中
        combined += audio_segment
    # 导出合并后的MP3文件
    combined.export(output_file, format="mp3")

    print("合并完成, 保存位置 = ", output_file)



"""
将音频文件降噪
"""
def noise_filter(audio_name, n):
    print("人声降噪.")
    for idx in range(n):
        cur_file = f"sources/{audio_name}/audio-separate/{idx}/vocals.wav"
        print("in = ", cur_file)
        # 设计低通滤波器去掉高频噪声
        # 读取音频文件
        sample_rate, data = wavfile.read(cur_file)
        # 设计一个低通滤波器
        order = 4
        cutoff_freq = 4000
        nyquist_freq = 0.5 * sample_rate
        normal_cutoff = cutoff_freq / nyquist_freq
        b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
        # 根据情况处理单双声道
        if len(data.shape) == 2 and data.shape[1] == 2:  # 双声道
            filtered_data = np.zeros_like(data)  # 创建和原音频同样形状的数组来保存过滤后的数据
            for i in range(2):
                filtered_data[:, i] = signal.lfilter(b, a, data[:, i])
        else:  # 单声道
            filtered_data = signal.lfilter(b, a, data)
        # 保存去噪后的音频文件
        output_file_path = f"sources/{audio_name}/audio-separate/{idx}/" + audio_name + '_filtered.wav'
        print("out = ", output_file_path)
        wavfile.write(output_file_path, sample_rate, filtered_data)
    print("降噪完成.")