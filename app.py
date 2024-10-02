import json
import subprocess
import logging
import time

from logging.handlers import RotatingFileHandler
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pymysql

# 引入字幕生成代码
import transfer2vtt
import pandas as pd
# 引入处理音频代码
import audioPreprocess

# 引入自己的webvtt-py包
from webvtt import *
from webvtt import WebVTT
from webvtt import webvtt
import webvtt

from format_transfer import *


# 处理视频(因为单个视频太大了,所以需要进行音视频分离)
from moviepy.editor import *

app = Flask(__name__)
CORS(app)  # 这会为所有路由添加CORS支持


@app.before_first_request
def setup_logging():
    if not app.debug:
        file_handler = RotatingFileHandler('runtime.log', maxBytes=1024 * 1024 * 100, backupCount=10)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)


# /: 根目录下
@app.route("/")
def index():
    print("I am english")
    print("我是中文")
    return "hello world!"


# @app.route("/findPerson", methods=['POST'])
def findPerson(video):
    """
    自定义字幕块位置
    """
    video_path = "./sources/" + video.split(".")[0] + "/" + video
    print(video_path)
    # video_path = "./sources/two-man-talk/two-man-talk.mp4"
    print("开始改变字幕位置了")
    # 随视频改变字幕位置
    json_res = setCaptions(video)
    return json_res


def setCaptions(video):
    """
    根据检测画面的结果来自动化设置字幕位置
    """
    # 找到要更改的字幕文件
    vtt_path = "./webvtt-captions/" + video.split(".")[0] + ".vtt"
    print("vtt_path = ", vtt_path)
    # 先读取原始webvtt内容
    vtt = webvtt.read(vtt_path)
    # 读取csv文件，将内容解析出来
    df = pd.read_csv("new_file.csv", usecols=['timestamp', 'in_left', 'in_right', 'line', 'position'])
    # 遍历每一行，针对每个时间戳，改变字幕位置
    for idx, row in df.iterrows():
        cur_timestamp = '0' + row['timestamp'][:-4]
        for caption in vtt.captions:
            # print(cur_timestamp, caption.start[:-4], caption.end[:-4])
            if caption.start[:-4] <= cur_timestamp <= caption.end[:-4]:
                print("row = ", row)
                print('找到了位置')
                # 开始做操作了，设置line 和 position
                caption.pos_styles['line'] = str(row['line'])[2:] + '%'
                caption.pos_styles['position'] = str(row['position'])[2:] + '%'
                # 在左侧
                # if row['in_left'] == 1:
                #     caption.pos_styles['align'] = 'left'
                # else:
                #     caption.pos_styles['align'] = 'right'
    # 更改完毕，将内容写回
    f = open(vtt_path, 'w', encoding='utf-8')
    vtt.write(f)
    f.close()

    time.sleep(5)


    vtt_name = video.split(".")[0] + ".mp4"

    with open(vtt_path, 'r', encoding='utf-8') as file:
        file_content = file.read()

    values = (vtt_name, file_content)
    print("values = ", values)
    conn = pymysql.connect(host='localhost', user='root', passwd="123456", db='promising_cinema')
    cur = conn.cursor()
    query = "INSERT INTO captions(video_name, content) VALUES(%s, %s)"
    cur.execute(query, values)
    conn.commit()
    for r in cur:
        print(r)
    cur.close()
    conn.close()


    # 将这玩意发给前端
    json_res = vtt_to_json(vtt_path)
    print("更改完毕")

    return json_res




def extract_audio_from_video(file):
    """
    使用moviepy从视频文件中分离出音频
    """
    filename, extension = file.rsplit('.', 1)
    video_path = f"sources/{filename}/{file}"
    audio_path = f"sources/{filename}/{filename}.mp3"

    video = VideoFileClip(video_path)
    audio = video.audio
    audio.write_audiofile(audio_path)
    audio.close()
    video.close()


@app.route("/json2vtt", methods=["POST"])
def json2vtt():
    """
    ....前端用的工具函数....
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
    print("type(data) = ", type(data))
    # todo 利用webvtt-py将content更改为vtt格式的文件，然后发送给请求端
    vtt = WebVTT()
    # captions = []

    for dict_item in data:
        if 'base_info' in dict_item:
            print("有base_info在")
            base_info_dict = dict_item['base_info']
        if 'captions' in dict_item:
            print("有captions在")
            captions_list = dict_item['captions']
    # frameCount = base_info_dict['frameCount']
    video_name = base_info_dict['video_name']
    # fps = base_info_dict['fps']
    video_width = base_info_dict['width']
    # 遍历 captions 数据, 创建字幕块，
    fps = 30
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
    vtt格式文件转track的json形式, 返回给前端
    """
    print("开始进行vtt转json")
    import os
    # 检查是否有文件在请求中
    # if 'file' not in request.files:
    #     return 'No file part in the request'
    file = request.files["file"]
    if file.filename == "":
        return "No file selected for upload"
    print("file = ", file, " filename = ", file.filename)
    filename = secure_filename(file.filename)
    relative_path = 'uploads'  # 你的相对路径
    current_directory = os.path.dirname(os.path.realpath(__file__))
    # 使用os.path.join来获取完整的文件路径
    filepath = os.path.join(current_directory, relative_path, filename)
    # 确保上传目录存在
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)

    vtt = webvtt.read(filepath)

    # todo 这里fps待定
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
    print("vtt转json成功，发送给前端")
    return jsonify(full_info)


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

@app.route("/give_me_track_text_json", methods=["POST"])
def give_me_track_text_json():
    file = request.form.get('name')
    filename, extension = file.rsplit('.', 1)



@app.route("/give_me_captions", methods=["POST"])
def make_captions():
    # try:
    # 一. 获取前端想要处理的视频
    file = request.form.get('name')
    filename, extension = file.rsplit('.', 1)
    app.logger.info("要处理的视频是：" + file)

    # 二. 开始处理, 初步得到没有处理过的字幕文件
    #   1. 分离出视频与音频
    extract_audio_from_video(file)
    app.logger.info(file + "分离完成")
    #   2. 对音频进行预处理(分离人声、降噪处理)
    audioPreprocess.audio_preprocess(filename)
    app.logger.info("分离人声，降噪完成")
    #   3. 开始转录
    transfer2vtt.transcribe(filename)
    app.logger.info("转录完成")

    # 三. 深度处理, 得到处理过的字幕文件
    #   1. 通过TalkNet模型, 识别出说话人, 记录说话人位置信息
    # 确保talknet目录下demo文件夹内有视频文件, 然后在talknet目录下执行
    # python demoTalkNet.py --videoName two-man-talk
    #   1.1 确保talknet项目中有对应的视频文件
    # cmd = (
    #         "d: "
    #         "&& "
    #         "cd D:\\code\\promising-video\\speaker-dection\\TalkNet-ASD-main "
    #         "&& "
    #         "activate talknet "
    #         "&& "
    #         "python demoTalkNet.py --videoName " + filename
    # )
    # output = subprocess.call(cmd, shell=True, stdout=None)
    app.logger.info("说话人识别完成")
    #   2. 通过说话人位置信息, 自动化设置字幕位置, 并将字幕返回给前端
    json_res = findPerson(file)

    need_send_file_path = './webvtt-captions/' + filename + '.vtt'

    return send_file(need_send_file_path, as_attachment=True)



@app.errorhandler(Exception)
def handle_exception(e):
    # 对于我们没有明确处理的异常，我们将其记录到日志中
    app.logger.error('An error occurred: %s' % e)
    return '抱歉，发生了异常: ' + str(e), 500


# 大坑，这个东西要放到所有函数下面，要不然它下面的函数就不会被执行
if __name__ == "__main__":
    logging.basicConfig(filename='demo.log', level=logging.INFO)
    app.run()
