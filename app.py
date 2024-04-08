import json

from flask import Flask, request, send_from_directory, send_file, jsonify
from flask_cors import CORS
import os

from webvtt import WebVTT
from werkzeug.utils import secure_filename

import predict_by_yolov8
import transfer2vtt
import predict_by_yolov3
import pandas as pd

# 引入自己的webvtt-py包
import webvtt
from webvtt.structures import Caption

# 音频处理
from pydub import AudioSegment

# 处理视频(因为单个视频太大了,所以需要进行音视频分离)
from moviepy.editor import *

from audioPreprocess import *

app = Flask(__name__)
CORS(app)  # 这会为所有路由添加CORS支持


# 音频转录为字幕
# @app.route('/transcribe', methods=['POST'])
def transfer(name):
    # 对音频进行转录
    # name = request.form.get('name')
    # language = request.form.get('language')
    print(request.form)
    print("I am transcribing: ", name)
    # transfer2vtt.transcribe(name, language)
    transfer2vtt.transcribe(name)
    return 'ok'
    # return "{},的字幕转录成功！".format(name)


# /: 根目录下
@app.route("/")
def index():
    print("I am english")
    print("我是中文")
    return "hello world!"


# 找到一个人的片段并且移动字幕位置
@app.route("/findPerson", methods=['POST'])
def findPerson():
    video = request.form.get('name')
    print(video)
    video_path = "./sources/" + video.split(".")[0] + "/" + video
    print(video_path)
    # video_path = "./sources/two-man-talk/two-man-talk.mp4"

    # 找到一个人的片段，并且标注ta在视频中的左侧还是右侧.
    # predict_by_yolov3.predict_go(video_path)
    # predict_by_yolov8.doIt(video_path)

    # return "ok哈哈哈哈"
    print("开始改变字幕位置了")
    # 随视频改变字幕位置
    setCaptions(video)

    # 将修改后的字幕发送给前端
    # 假设setCaptions函数将修改后的字幕保存在同一个目录
    print("发送")
    subtitle_path = os.path.join("./webvtt-captions", video.split(".")[0])
    # subtitle_path = "./webvtt-captions"
    subtitle_filename = video.split(".")[0] + ".vtt"  # 假设的字幕文件名
    print("subtitle_filename = ", subtitle_filename)
    print("subtitle_path = ", subtitle_path)
    return send_file('./webvtt-captions/' + subtitle_filename, as_attachment=True)
    # return send_from_directory(path = './webvtt-captions',directory='./webvtt-captions', filename = subtitle_filename, as_attachment = True)

    # return "自动化修改字幕successfully!"


# 根据检测画面的结果来自动化设置字幕位置
def setCaptions(video):
    # 找到要更改的字幕文件
    vtt_path = "./webvtt-captions/" + video.split(".")[0] + ".vtt"
    print("vtt_path = ", vtt_path)
    # 先读取原始webvtt内容
    vtt = webvtt.read(vtt_path)
    # 读取csv文件，将内容解析出来
    df = pd.read_csv("detections.csv", usecols=['timestamp', 'in_left', 'in_right'])
    # 遍历每一行，针对每个时间戳，改变字幕位置
    for idx, row in df.iterrows():
        cur_timestamp = '0' + row['timestamp'][:-4]
        for caption in vtt.captions:
            # print(cur_timestamp, caption.start[:-4], caption.end[:-4])
            if caption.start[:-4] <= cur_timestamp <= caption.end[:-4]:
                print('找到了位置')
                # 在左侧
                if row['in_left'] == 1:
                    caption.pos_styles['align'] = 'left'
                else:
                    caption.pos_styles['align'] = 'right'

    # 更改完毕，将内容写回
    f = open(vtt_path, 'w', encoding='utf-8')
    vtt.write(f)

    print("更改完毕")
    # print(df)
    return "自动化修改字幕完成."


# @app.route('/audioPreprocess', methods=['POST'])
def audio_preprocess(filename):
    # filename, extension = request.form.get('name').rsplit('.', 1)
    # 1. 分割音频
    print("step 1")
    n = audio_split(filename)
    # n = 12

    # 2. 利用spleeter来提取人声
    print("step 2")
    vocals_separator(filename, n)

    # 3. 对分离出来的人声进行降噪处理
    print("step 3")
    noise_filter(filename, n)

    # 4. 合并
    print("step 4")
    combine_audio(filename, n)

    return jsonify({'message': "ok！"}), 200


@app.route('/extract_audio_from_video', methods=['POST'])
def extract_audio_from_video():
    """
    使用moviepy从视频文件中提取音频。
    参数:
    video_path: 视频文件的路径。
    audio_path: 保存提取音频的路径。
    """
    param = request.form.get('name')
    print("param = ", param)
    filename, extension = param.rsplit('.', 1)
    video_path = f"sources/{filename}/{param}"
    audio_path = f"sources/{filename}/{filename}.mp3"

    video = VideoFileClip(video_path)
    audio = video.audio
    audio.write_audiofile(audio_path)
    audio.close()
    video.close()

    # 这里分离完成之后继续自动操作接下来的流程！！！

    # audioProcess
    audio_preprocess(filename)

    # whisper 转录
    # trans_res = transfer(filename)

    # 手动去cmd中生成detections.csv,将csv放入此目录中

    # findPerson自动设置字幕位置
    # findPerson(filename)

    return "ok"


@app.route("/json2vtt", methods=["POST"])
def json2vtt():
    """
    track的json文件转vtt格式
    """
    import os
    # 检查是否有文件在请求中
    if 'file' not in request.files:
        return 'No file part in the request'
    file = request.files["file"]
    if file.filename == "":
        return "No file selected for upload"
    # 读取json文件内容
    content = file.read().decode('utf-8')
    data = json.loads(content)

    # todo 利用webvtt-py将content更改为vtt格式的文件，然后发送给请求端
    vtt = WebVTT()
    # captions = []

    for dict_item in data:
        if 'base_info' in dict_item:
            base_info_dict = dict_item['base_info']
        if 'captions' in dict_item:
            captions_list = dict_item['captions']
    # frameCount = base_info_dict['frameCount']
    video_name = base_info_dict['video_name']
    fps = base_info_dict['fps']
    video_width = base_info_dict['width']
    # 遍历 captions 数据, 创建字幕块，
    for i, caption in enumerate(captions_list):
        left = caption['left']
        # 得到起止时间戳
        start_timestamp = frame_to_timestamp(caption['startFrame'], fps)
        end_timestamp = frame_to_timestamp(caption['endFrame'], fps)
        print("startFrame = ", caption['startFrame'])
        print("start_timestamp = ", start_timestamp)
        print("end_timestamp = ", end_timestamp)
        # 得到文本
        text = caption['text']
        text_list = []
        text_list.append(text)
        print(text_list)
        c = Caption(start_timestamp, end_timestamp, text_list)
        # todo 这里有待修改，因为top和left是字幕块的左上角，之后要想办法求出来字幕块的中心位置
        if left <= video_width / 3:
            c.pos_styles['align'] = 'left'
        if left >= (video_width * 2) / 3:
            c.pos_styles['align'] = 'right'
        vtt.captions.append(c)

    # 获取当前代码文件的绝对路径
    current_path = os.path.dirname(os.path.abspath(__file__))
    # 将该路径与你的文件名进行拼接
    vtt_file_path = os.path.join(current_path, video_name + ".vtt")

    with open(vtt_file_path, 'w', encoding="utf-8") as vtt_file:
        vtt.write(vtt_file)

    return send_file(vtt_file_path, as_attachment=True)


@app.route("/vtt2json", methods=["POST"])
def vtt2json():
    """
    vtt格式文件转track的json形式
    """
    import os
    # 检查是否有文件在请求中
    if 'file' not in request.files:
        return 'No file part in the request'
    file = request.files["file"]
    if file.filename == "":
        return "No file selected for upload"

    filename = secure_filename(file.filename)
    relative_path = 'uploads'  # 你的相对路径
    current_directory = os.path.dirname(os.path.realpath(__file__))
    # 使用os.path.join来获取完整的文件路径
    filepath = os.path.join(current_directory, relative_path, filename)
    # 确保上传目录存在
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)

    vtt = webvtt.read(filepath)

    # todo 将vtt内容转换为json格式文件，返回给前端，前端对文件进行解析，将字幕文件添加到音轨
    fps = 30
    info_list = []
    for caption in vtt.captions:
        # 遍历字幕中的每一行，将开始和结束的时间转换为对应的帧序号
        start_frames = time_to_frames(caption.start, fps)
        end_frames = time_to_frames(caption.end, fps)
        info = {}
        info['startFrame'] = start_frames
        info['endFrame'] = end_frames
        if caption.pos_styles['align'] == 'left':
            info['left'] = 1
        if caption.pos_styles['align'] == 'right':
            info['right'] = 1
        info['text'] = caption.text
        info_list.append(info)
    # 将信息列表转化为 JSON 格式的字符串

    full_info = {'captions': info_list}
    return jsonify(full_info)

    # # 将 JSON 格式的字符串保存到文件
    # with open('vtt2jsonfile.json', 'w') as json_file:
    #     json_file.write(info_json)
    #
    #
    #
    # return "收到啦"


def frame_to_timestamp(frame, fps):
    """
    Converts the frame number to timestamp
    :param frame: frame number (int)
    :param fps: frames per second (int)
    """
    total_seconds = frame / fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int((total_seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def time_to_frames(time, fps):
    # 将HH:MM:SS.SSS格式的时间转换为秒数
    h, m, s = map(float, time.split(':'))
    sec = h * 3600 + m * 60 + s
    # 计算对应的帧序号
    frames = int(sec * fps)
    return frames


# 大坑，这个东西要放到所有函数下面，要不然它下面的函数就不会被执行
if __name__ == "__main__":
    app.run()
