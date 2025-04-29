from typing import Optional, Any
import os
import uuid
import mammoth

class CustomMammothCoverImage:
  def __init__(self,llm_client: Optional[Any] = None,llm_model: Optional[str] = None,llm_prompt: Optional[str] = None,type: Optional[str] = None,kbId: Optional[str] = None):
        self.llm_client=llm_client
        self.llm_model = llm_model
        self.llm_prompt = llm_prompt
        self.type = type
        self.custom_image_converter = mammoth.images.img_element(self.mammoth_convert_image)
        # 延迟导入
        from markitdown import MarkItDown
        self.mdImage = MarkItDown(llm_client=llm_client, llm_model=llm_model)

  def mammoth_convert_image(self, image):
        output_dir = "./static/temp"
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 获取文件后缀
        if self.type == 'docx' or self.type == 'pptx':
            content_type = image.content_type.lower()
        elif self.type == 'pdf':
            content_type = image["ext"].lower()

        # 根据 content_type 创建合适的文件扩展名
        if "png" in content_type:
            extension = ".png"
        elif "jpeg" in content_type or "jpg" in content_type:
            extension = ".jpg"
        else:
            extension = ".bin"  # 如果类型未知，使用 .bin 扩展名

        # 构造唯一的文件名，避免覆盖已有的文件
        # 图片名称: uuid + 后缀
        imageName = uuid.uuid4().hex + extension
        filename = os.path.join(output_dir, imageName)
        i = 1
        while os.path.exists(filename):
            filename = os.path.join(output_dir, f"image_{i}{extension}")
            i += 1

        # 打开图像并写入文件
        if self.type == 'docx':
            # doc
            with image.open() as image_bytes:
                with open(filename, 'wb') as file:
                    file.write(image_bytes.read())
        elif self.type == 'pptx':
            # ppt
            with open(filename, 'wb') as f:
                f.write(image.blob)
        elif self.type == 'pdf':
            # pdf
            with open(filename, 'wb') as f:
                f.write(image["image"])

        result = self.mdImage.convert(filename,llm_prompt=self.llm_prompt)
        #print(self.llm_client)
        # 最后删除这个图片
        os.remove(filename)
        return {
            "alt": result.text_content
        }