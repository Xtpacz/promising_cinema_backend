import whisper
from whisper.utils import get_writer

# def transcribe(file_name, target_language):
def transcribe(file):
    # 选择base模型
    model = whisper.load_model("base")
    # file = file_name.split(".")[0]
    # 没有预处理
    # path = f"sources/{file}/{file_name}"
    # 预处理之后
    path = f"sources/{file}/{file}_preprocessed.mp3"
    # print(f"要转录{path},语言为{target_language}")
    # result = model.transcribe(path, language=target_language)
    result = model.transcribe(path)
    # 将结果写入webvtt-captions文件夹中
    writer = get_writer('vtt', "webvtt-captions")
    writer(result, file)
    # print(result)
