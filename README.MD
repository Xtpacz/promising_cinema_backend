稍后更新readme

后端的大致功能如下
![](https://coldwater.oss-cn-beijing.aliyuncs.com/img/20240408213149.png)



处理流程大概分成两部分
1. 前端发送请求，后端生成一个初始版本的字幕文件，返回给前端
2. 前端再次发送请求，请求后端对字幕进行个性化处理



### TODO

一. 代码完善
1. 异常处理
2. 解耦

二. 代码上传
1. 上传解析webvtt文件的代码
2. 上传TalkNet的代码