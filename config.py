"""
简历解析工具 - 配置文件
"""

from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# OCR 配置
OCR_CONFIG = {
    "use_angle_cls": True,       # 启用方向分类
    "lang": "ch",                # 语言：ch(中文)、en(英文)、japan(日语)、korean(韩语)
    "det_db_thresh": 0.3,        # 文本检测阈值
    "det_db_box_thresh": 0.5,    # 文本框阈值
    "use_gpu": False,            # 是否使用 GPU
}

# 图片预处理配置
PREPROCESS_CONFIG = {
    "denoise_h": 10,             # 去噪强度
    "deskew_angle_threshold": 0.5,  # 纠偏角度阈值
    "clahe_clip_limit": 2.0,     # 对比度增强 clip limit
    "clahe_grid_size": (8, 8),    # CLAHE 网格大小
    "binary_block_size": 11,      # 自适应二值化 block size
    "binary_c": 2,               # 自适应二值化 C 值
}

# 简历标题模式（支持中英文）
SECTION_PATTERNS = [
    # 基础信息
    (r"姓名|Name", "姓名"),
    (r"手机|电话|Phone|Tel|Mobile", "联系方式"),
    (r"邮箱|Email|E-mail", "邮箱"),
    (r"年龄|生日|出生|生日|Date of Birth", "个人信息"),
    (r"性别|男|女|地址|Address", "基本信息"),
    
    # 教育背景
    (r"教育|学历|Education|Background", "教育背景"),
    (r"学校|毕业院校|University|College", "学校"),
    (r"专业|Major|专业方向", "专业"),
    (r"时间|起止时间|Period", "时间"),
    
    # 工作经历
    (r"工作经历|工作背景|Employment|Experience|Job", "工作经历"),
    (r"公司|单位|Company|Organization", "公司"),
    (r"职位|岗位|Position|Title", "职位"),
    
    # 项目经历
    (r"项目经历|项目经验|Project", "项目经历"),
    (r"项目名称|Project Name", "项目名称"),
    (r"项目描述|项目职责", "项目描述"),
    
    # 技能
    (r"技能|特长|Skills|Technical|技术", "技能特长"),
    
    # 证书
    (r"证书|认证|Certifications|License", "证书资质"),
    
    # 自我介绍
    (r"简介|Summary|关于我|个人简介|Profile", "个人简介"),
    
    # 其他
    (r"爱好|Hobby|Interests", "兴趣爱好"),
    (r"荣誉|奖励|Awards|Honors", "荣誉奖励"),
    (r"语言|Language", "语言能力"),
]

# 支持的文件类型
SUPPORTED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"]
SUPPORTED_PDF_EXTENSIONS = [".pdf"]
SUPPORTED_DOCX_EXTENSIONS = [".docx", ".doc"]

# RAG 配置（预留）
RAG_CONFIG = {
    "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "vector_db": "chroma",  # chroma / milvus / qdrant
    "collection_name": "resume_sections",
    "top_k": 5,
}
