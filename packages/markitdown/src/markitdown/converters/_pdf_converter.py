import sys
import io

from typing import BinaryIO, Any


from ._html_converter import HtmlConverter
from .._base_converter import DocumentConverter, DocumentConverterResult
from .._stream_info import StreamInfo
from .._exceptions import MissingDependencyException, MISSING_DEPENDENCY_MESSAGE
from .CustomMammothCoverImage import *

# 忽略PyMuPDF的警告:<frozen importlib._bootstrap>:241: DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute
import warnings
warnings.filterwarnings("ignore", message="builtin type.*has no __module__ attribute")

import fitz  # PyMuPDF
from io import BytesIO


# Try loading optional (but in this case, required) dependencies
# Save reporting of any exceptions for later
_dependency_exc_info = None
try:
    import pdfminer
    import pdfminer.high_level
except ImportError:
    # Preserve the error and stack trace for later
    _dependency_exc_info = sys.exc_info()


ACCEPTED_MIME_TYPE_PREFIXES = [
    "application/pdf",
    "application/x-pdf",
]

ACCEPTED_FILE_EXTENSIONS = [".pdf"]


class PdfConverter(DocumentConverter):
    """
    Converts PDFs to Markdown. Most style information is ignored, so the results are essentially plain-text.
    """

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,  # Options to pass to the converter
    ) -> bool:
        mimetype = (stream_info.mimetype or "").lower()
        extension = (stream_info.extension or "").lower()

        if extension in ACCEPTED_FILE_EXTENSIONS:
            return True

        for prefix in ACCEPTED_MIME_TYPE_PREFIXES:
            if mimetype.startswith(prefix):
                return True

        return False

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,  # Options to pass to the converter
    ) -> DocumentConverterResult:
        # 构建模型
        llm_client= kwargs.get("llm_client", None)
        llm_model = kwargs.get("llm_model", None)
        llm_prompt = kwargs.get("llm_prompt", None)
        customMammothCoverImage = CustomMammothCoverImage(llm_client, llm_model, llm_prompt, 'pdf')

        # Check the dependencies
        if _dependency_exc_info is not None:
            raise MissingDependencyException(
                MISSING_DEPENDENCY_MESSAGE.format(
                    converter=type(self).__name__,
                    extension=".pdf",
                    feature="pdf",
                )
            ) from _dependency_exc_info[
                1
            ].with_traceback(  # type: ignore[union-attr]
                _dependency_exc_info[2]
            )



        # assert isinstance(file_stream, io.IOBase)  # for mypy
        # return DocumentConverterResult(
        #     markdown=pdfminer.high_level.extract_text(file_stream),
        # )

        # 将流内容读入内存
        file_bytes = file_stream.read()

        # 使用 PyMuPDF 从内存中打开 PDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        content_items = []

        # 遍历 PDF 文件中的每一页
        for page_num in range(len(doc)):
            page_content = []
            # 加载当前页的内容
            page = doc.load_page(page_num)

            # 提取带有位置信息的文本块
            text_blocks = page.get_text("blocks")
            # 提取页面上的所有图像对象，并获取它们的边界框信息
            image_list = page.get_images(full=True)

            # 收集文本项
            for tb in text_blocks:
                rect = (tb[0], tb[1], tb[2], tb[3])  # Text block rectangle
                page_content.append({
                    'type': 'text',
                    'content': tb[4],   # 文本内容
                    'rect': rect         # 文本块的位置信息
                })

            # 收集图像项
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # 模拟传入图像信息给 mammoth_convert_image 方法（需要适配）
                class ImageWrapper:
                    def __init__(self, image_data, ext):
                        self.image = image_data
                        self.ext = ext

                fake_image = {
                    "image": image_bytes,
                    "ext": image_ext
                }
                result = customMammothCoverImage.mammoth_convert_image(fake_image)

                # Approximate the image's position using its bounding box
                image_rect = page.get_image_bbox(img)
                page_content.append({
                    'type': 'image',
                    'content': '[' + result['alt'] + ']()',
                    'rect': image_rect  # 获取图像的大致位置
                })

            # 根据内容项在页面上的垂直位置（y坐标），然后是水平位置（x坐标）对它们进行排序
            page_content.sort(key=lambda item: (item['rect'][1], item['rect'][0]))
            content_items.extend(page_content)

        # 只保留 content 字段，拼接为字符串
        full_text = ""
        for info in content_items:
            full_text += info["content"] + "\n"

        return DocumentConverterResult(
            markdown=full_text,
        )
