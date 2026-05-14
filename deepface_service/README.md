# DeepFace 独立服务（Hugging Face Spaces Docker）

这个目录用于部署独立的人脸情绪识别服务，供主 Flask App 通过 HTTP 调用。

## 接口说明

- `GET /`：服务信息
- `GET /health`：健康检查
- `POST /analyze_face`：上传图片并返回情绪识别结果（`form-data` 字段名：`file`）

成功响应示例：

```json
{
  "success": true,
  "emotion": "happy",
  "emotion_cn": "开心",
  "confidence": 0.86,
  "source": "deepface_remote"
}
```

失败响应示例：

```json
{
  "success": false,
  "message": "未识别到清晰人脸"
}
```

## 本地运行（可选）

```bash
python app.py
```

本地默认地址：`http://127.0.0.1:7860`

## 部署到 Hugging Face Spaces（Docker Space）

1. 创建 Hugging Face Space。  
2. `SDK` 选择 `Docker`。  
3. 把以下文件上传到 Space 根目录：`app.py`、`requirements.txt`、`Dockerfile`、`README.md`。  
4. 等待自动构建完成。  
5. 线上测试：  
   - `GET https://xxx.hf.space/health`  
   - `POST https://xxx.hf.space/analyze_face`  
6. `curl` 示例：  

```bash
curl -X POST "https://xxx.hf.space/analyze_face" -F "file=@/path/to/test.jpg"
```

## 主应用连接

在主应用环境变量中配置：

```env
DEEPFACE_API_URL=https://xxx.hf.space/analyze_face
```

## 隐私说明

- 服务只做瞬时分析，不长期保存上传图片。  
- 图片会写入临时文件，分析结束后立即删除。  
