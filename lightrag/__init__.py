from .lightrag import LightRAG as LightRAG, QueryParam as QueryParam

# 在导入时自动配置 tiktoken 离线模式
try:
    from .tiktoken_offline import setup_tiktoken_offline

    setup_tiktoken_offline()
except Exception as e:
    import warnings

    warnings.warn(f"Failed to setup tiktoken offline mode: {e}", RuntimeWarning)

__version__ = "1.4.8"
__author__ = "Zirui Guo"
__url__ = "https://github.com/HKUDS/LightRAG"
