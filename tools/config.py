import json
import toml
import copy
import shutil
import datetime
from pathlib import Path
from hipporag_lite import HippoRAG
from typing import Optional, Tuple, Dict, List, Any

from astrbot.api import logger

class ConfigManager:
    '''配置管理类'''

    @staticmethod
    def load_toml(file_path: Path) -> Dict[str, Any]:
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return toml.load(f)
            logger.error(f"TOML 不存在: {file_path}")
            return {}
        except Exception as e:
            logger.error(f"加载 {file_path} 失败: {e}")
            return {}
    
    @staticmethod
    def save_toml(data: Dict[str, Any], file_path: Path):
        try:
            existing_data = ConfigManager.load_toml(file_path)
            existing_data.update(data)
            
            with open(file_path, "w", encoding="utf-8") as f:
                toml.dump(existing_data, f)
        except Exception as e:
            logger.error(f"保存 {file_path} 失败: {e}")

    @staticmethod
    def load_json(file_path: Path, default: Dict) -> Dict:
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
            return default
        except Exception as e:
            logger.error(f"加载 {file_path} 失败: {e}")
            return default

    @staticmethod
    def save_json(data: Dict[str, Any], file_path: Path):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存 {file_path} 失败: {e}")

# 自身目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 处理配置文件路径
CONFIG_DIR = BASE_DIR / "config.toml"

# 版本信息
MAJOR_VERSION = 2
MINOR_VERSION = 2
PATCH_VERSION = 2
VERSION_SUFFIX = "stable"

# 导入配置文件
cfg = ConfigManager.load_toml(CONFIG_DIR)

# 加载数据文件夹路径
paths_config = cfg["paths"]
        
data_dir = BASE_DIR / paths_config["data_dir"]
groups_dir = BASE_DIR / paths_config["groups_dir"]
public_dir = BASE_DIR / paths_config["public_dir"]
private_dir = BASE_DIR / paths_config["private_dir"]
whitelist_dir = BASE_DIR / paths_config["whitelist_dir"]
        
# 创建目录，确保所有必要的目录存在
data_dir.mkdir(exist_ok=True, parents=True)
groups_dir.mkdir(exist_ok=True, parents=True)
public_dir.mkdir(exist_ok=True, parents=True)
private_dir.mkdir(exist_ok=True, parents=True)
whitelist_dir.mkdir(exist_ok=True, parents=True)

# 解析数据文件夹路径
DATA_DIR = data_dir
GROUPS_DIR = groups_dir
PUBLIC_DIR = public_dir
PRIVATE_DIR = private_dir
WHITELIST = whitelist_dir

# 加载API配置
api_config = cfg["api"]

# 解析API配置
API_URL = api_config.get("url", "")
MODELS = api_config.get("models", [])
API_KEY = api_config.get("api_key", "")
FUNC = api_config.get("funccall_model","")
EMBED = api_config.get("embedding_model", [])
EMB_URL = api_config.get("embedding_url", "")
PRE_MOD = set(api_config.get("pre_mod", [])) # 转换为集合

# 加载搜索引擎配置
se_config = cfg["search_engine"]

# 解析搜索引擎配置
SAPI_KEY = se_config.get("sapi_key", "")
SAPI_URL = se_config.get("surl", "")

# 加载文件路径配置
paths_config = cfg["files"]

# 解析文件路径
BASIC_FILE = BASE_DIR / paths_config.get("base_file", "")
USER_WHITELIST_FILE = BASE_DIR / paths_config.get("user_whitelist_file", "")
GROUP_WHITELIST_FILE = BASE_DIR / paths_config.get("group_whitelist_file", "")

# 加载白名单配置
whitelist_config = cfg["whitelist_config"]

# 解析白名单路径
WHITELIST_MODE  = whitelist_config.get("whitelist_mode", 0)

# 加载对话配置
basic_config = cfg["basic_config"]

class ChatConfig:
    '''变量容器类，配置的动态载体'''
    def __init__(self, ID: int):

        self.group = ID # ID : 此配置归属的组的ID
        self.file : Path = self._path_generation(ID) # 数据存储位置
        self.name : str = self._name_generation(ID) # 生成组群的名称
        self.config_name : str = self._file_generation(ID)  # 配置文件名称
        self.personality_file : Path = self.file / "personalitys" # 人格文件位置

        # rag数据保存位置,以此代表相应的实例写入配置文件,相当于特殊的self.mess,不过仅指代不存储信息
        self.rag_file : str = str(self.file / "RAG_file_base") # 基文件，用于随意修改，而不影响需要存储的信息
        self.hipporag : HippoRAG = self._creat_rag(self.rag_file)

        # 基础配置
        self.rd : int = basic_config.get("rd", 6)
        self.mod : int = basic_config.get("mod", 3)
        self.prt : bool= basic_config.get("prt", True)
        self.tkc : bool = basic_config.get("tkc", False)
        self.rag : bool = basic_config.get("rag", False)
        self.ssin : bool = basic_config.get("ssin", False)
        self.allin : bool = basic_config.get("allin", False)
        self.search : bool = basic_config.get("search", False)
        self.mess : List[dict] = basic_config.get("memory", []) 
        self.cooldown : float = basic_config.get("cooldown", 300.0)
        self.max_token : int = basic_config.get("max_token", 1024)
        self.max_recall : int = min(self.rd , basic_config.get("max_recall", 2))
        self.current_personality : str = basic_config.get("default_personality", "你是名叫华尔的猫娘。") 

    def _path_generation(self, ID) -> Path:#函数形式生成，方便拓展
        """生成数据存储位置"""
        if ID == 0 :
            return PUBLIC_DIR
        elif ID == 1 :
            return PRIVATE_DIR
        else:
            return GROUPS_DIR / str(ID)

    def _file_generation(self, ID) -> str:
        """生成配置文件的名称"""
        if ID == 0 :
            return 'base'
        elif ID == 1 :
            return 'private_config'
        else:
            return 'group_config'
        
    def _name_generation(self, ID) -> str:
        """生成群的名称(编号|private|public)"""
        if ID == 0 :
            return 'public'
        elif ID == 1 :
            return 'private'
        else:
            return str(self.group)
        
    def _creat_rag(self, filename: str) -> HippoRAG:
        """新建一个rag实例"""
        return  HippoRAG(
                        api_key=API_KEY,
                        llm_base_url=API_URL,
                        save_dir=filename, 
                        llm_model_name=EMBED[1],
                        embedding_model_name=EMBED[0],
                        embedding_base_url=EMB_URL)
    
    def _reset_rag(self):
        """重置rag"""
        self.hipporag = self._creat_rag(self.rag_file)

    def save_group(self) -> str:
        """一键保存群组配置"""
        save_path = self.file / f"{self.config_name}.json"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "rd" : self.rd,
            "prt" : self.prt,
            "mod" : self.mod,
            "tkc" : self.tkc,
            "rag" : self.rag,
            "ssin" : self.ssin,
            "allin" : self.allin,
            "memory" : self.mess,
            "search" : self.search,
            "cooldown" : self.cooldown,
            "rag_file" : self.rag_file,
            "max_token" : self.max_token,
            "max_recall" : self.max_recall,
            "default_personality" : self.current_personality,
        }
        
        try :
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"组群: {self.name} 保存成功")
            return "✅ 保存成功"
        except Exception as e:
            logger.exception(f"未知保存错误：{e}")
            return "⚠️ 系统异常，请联系管理员"

    def load_group(self) -> str:
        """加载此群组的配置"""
        load_path = self.file / f"{self.config_name}.json"
        if not load_path.exists():
            logger.warning(f"群组 {self.group} 的配置文件不存在，已自动生成")
            self.save_group()
            return
        
        try :
            with open(load_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.rd = data.get("rd", 6)
                self.mod = data.get("mod", 3)
                self.prt = data.get("prt", True)
                self.tkc = data.get("tkc", False)
                self.rag = data.get("rag", False)
                self.mess = data.get("memory", [])
                self.ssin = data.get("ssin", False)
                self.allin = data.get("allin", False)
                self.search = data.get("search", False)
                self.cooldown = data.get("cooldown", 300.0)
                self.max_recall = data.get("max_recall", 2)
                self.max_token = data.get("max_token", 1024)
                self.rag_file = data.get("rag_file", str(self.file / "RAG_file_base"))
                self.current_personality = data.get("default_personality", "你是名叫华尔的猫娘。")
            return "✅ 加载成功"
        except Exception as e:
            logger.exception(f"未知加载错误{e}")
            return "⚠️ 系统异常，请联系管理员"

    def _conf_info(self):
        """打印此类变量信息（除去mess）"""
        simple_fields = [
            "rd", "prt", "mod", "tkc", "rag", "ssin", "allin","search", "cooldown","rag_file", 
            "max_token","max_recall", "current_personality", "group", "name", "config_name"
        ]
        return {field: getattr(self, field) for field in simple_fields}
    
    def copy_config(self, new_config):
        """为重置准备的深拷贝"""
        simple_fields = [
            "rd", "prt", "mod", "tkc", "rag", "ssin", "allin", "search", "mess",
            "cooldown", "max_token","max_recall", "current_personality"
        ]
        for field in {field: getattr(self, field) for field in simple_fields}:
            if hasattr(new_config, field):
                # 使用深拷贝，如果是可变类型（如 dict 或 list），否则直接赋值
                setattr(new_config, field, copy.deepcopy(getattr(self, field)))

class Information:
    """信息类，维护一些项目信息"""
    @staticmethod
    def full_version() -> str:
        """生成完整版本号"""
        return f"{MAJOR_VERSION}.{MINOR_VERSION}.{PATCH_VERSION}-{VERSION_SUFFIX}"

    @staticmethod
    def build_date() -> str:
        """获取构建日期"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
class Tools:
    """工具类，包含一些常用函数"""
    @staticmethod
    def _parse_args(arg: List[str], *opts: str) -> Optional[Tuple[str, str]]:
        '''
        参数解析器（双参数且其一为可选）

        用于将两个参数提取出来，不受制于实际传入时的位置。

        Args:
            arg: 整段文本
            opts: 不定长，可选参数所有的选项，会作为第二个返回值返回
        '''

        if len(arg) != 2 or not opts:
            return None
            
        # 智能识别参数位置
        a1 = next((a for a in arg if a in opts), None)
        a2 = next((g for g in arg if g != a1), None)
        
        return (a2, a1) if a2 and a1 else None
    
    @staticmethod
    def _extract_args(main_str: str, command: str) -> list[str]:
        """
        参数提取器（为AstrBot语境设计）

        移除主串中的命令部分，将剩余内容按空格分割为列表
        
        Args:
            main_str: 整段文本
            command: 需要从主串中移除的命令部分
        
        返回:
            移除命令后剩余内容按空格分割的列表（自动过滤空字符串）
        """
        # 移除主串中开头的命令部分（若存在）
        if main_str.startswith(command):
            # 去掉命令后，再移除首尾多余空格
            remaining = main_str[len(command):].strip()
        else:
            # 若主串不包含命令，直接处理整个主串
            remaining = main_str.strip()
        
        # 按空格分割（多个空格会被视为单个分隔符，空字符串会被过滤）
        return remaining.split()
    
    
# 由于astrbot的特性，这里自己实现md渲染逻辑
CSS = r"""
/* ===== Root & Reset ===== */
@page { size: auto; margin: 0 }
:root{
  --fg:#24292f; --bg:#fff; --muted:#57606a;
  --border:#d0d7de; --soft:#f6f8fa; --link:#0969da;
  --code-bg:#f6f8fa; --kbd-bg:#fafbfc; --kbd-border:#c6cbd1;
  --table-stripe:#fafbfc;
}
*{box-sizing:border-box}
html,body{background:var(--bg)}
body{
  margin:0; padding:32px;
  font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"Noto Sans","Liberation Sans",sans-serif,"Apple Color Emoji","Segoe UI Emoji";
  color:var(--fg);
  -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
}
.markdown-body{ max-width: 920px; margin:0 auto }

/* ===== Headings ===== */
h1,h2,h3,h4,h5,h6{
  margin:1.2em 0 .6em; line-height:1.25; font-weight:700
}
h1,h2,h3{ border-bottom:1px solid var(--border); padding-bottom:.3em }
h1{font-size:2.0em} h2{font-size:1.6em} h3{font-size:1.35em}
h4{font-size:1.15em} h5{font-size:1.05em} h6{font-size:.95em; color:var(--muted)}

/* ===== Text & Lists ===== */
p,ul,ol,blockquote,pre,table,figure{ margin:.9em 0 }
ul,ol{ padding-left:1.4em }
li + li{ margin-top:.25em }
hr{ height:1px; border:0; background:var(--border); margin:1.5em 0 }
a{ color:var(--link); text-decoration:none }
a:hover{text-decoration:underline}

/* ===== Blockquote ===== */
blockquote{
  border-left:4px solid var(--border);
  padding:0 1em; color:var(--muted); margin-left:0
}

/* ===== Code & Pre ===== */
code,pre,kbd{
  font-family: ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono","Courier New",monospace;
  font-size:85%
}
code{ background:var(--code-bg); padding:.2em .4em; border-radius:6px }
pre{
  background:var(--code-bg); padding:14px 16px; border-radius:10px;
  overflow:auto; position:relative; border:1px solid var(--border)
}
pre code{ background:transparent; padding:0 }
/* 可选：行号（给 <pre> 添加 class="linenums" 生效） */
pre.linenums{ counter-reset:line }
pre.linenums code{ display:block }
pre.linenums code > span{ display:block; counter-increment:line }
pre.linenums code > span::before{
  content:counter(line);
  display:inline-block; width:2ch; margin-right:1ch; text-align:right;
  color:var(--muted)
}
/* 行内 kbd */
kbd{
  background:var(--kbd-bg); border:1px solid var(--kbd-border);
  border-bottom:3px solid var(--kbd-border);
  border-radius:6px; padding:.1em .35em; font-weight:600
}

/* ===== Tables ===== */
table{ border-collapse:collapse; width:100%; overflow:hidden; border-radius:8px }
th,td{ border:1px solid var(--border); padding:8px 10px; vertical-align:top }
thead th{ background:var(--soft); text-align:left }
tbody tr:nth-child(odd){ background:var(--table-stripe) }

/* ===== Images & Figures ===== */
img{ max-width:100%; height:auto; border-radius:8px }
figure{ margin:1em 0 }
figcaption{
  text-align:center; font-size:.9em; color:var(--muted); margin-top:.4em
}

/* ===== Alerts / Callouts ===== */
.note,.tip,.warn,.danger{
  border:1px solid var(--border); border-left:6px solid #6e7781;
  background:#fff; padding:.9em 1em; border-radius:10px; margin:1em 0
}
.tip{ border-left-color:#2da44e }
.warn{ border-left-color:#d29922 }
.danger{ border-left-color:#d1242f }

/* ===== Task List ===== */
.task-list-item{ list-style:none; margin-left:-.3em }
.task-list-item input[type="checkbox"]{
  vertical-align:middle; margin-right:.4em
}

/* ===== Small Utilities ===== */
.small{ font-size:.9em; color:var(--muted) }
.mono{ font-family: ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono","Courier New",monospace }
.center{ text-align:center }
.right{ text-align:right }

/* ===== Page breaking helpers (for长图裁切) ===== */
.page-break{ break-after:page }
.no-break{ break-inside:avoid }

/* ===== Dark mode ===== */
@media (prefers-color-scheme: dark){
  :root{
    --fg:#c9d1d9; --bg:#0d1117; --muted:#8b949e;
    --border:#30363d; --soft:#161b22; --link:#58a6ff;
    --code-bg:#161b22; --kbd-bg:#0d1117; --kbd-border:#30363d;
    --table-stripe:#0f141b;
  }
  body{ background:var(--bg); color:var(--fg) }
  .note,.tip,.warn,.danger{ background:var(--bg) }
}

/* ===== Print-ish density (使渲染更锐利) ===== */
@media print{
  body{ padding:24px }
  *{ -webkit-print-color-adjust:exact; print-color-adjust:exact }
}
"""

HTML_SKELETON = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
<style>{css}</style>
</head>
<body>
<main class="markdown-body">
  <!-- 标题区可选 -->
  <!-- <header class="center small" style="margin-bottom:12px">由 AstrBot 渲染</header> -->

  {content}

  <!-- 可选分页锚点：<div class="page-break"></div> -->
</main>
</body>
</html>
"""
