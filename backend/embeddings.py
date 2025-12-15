from __future__ import annotations

# Keras patch should already be applied by _keras_patch.py imported in main.py
# But we ensure it here as well for safety
import sys
try:
    import tf_keras
    if 'keras' not in sys.modules or sys.modules.get('keras') != tf_keras:
        sys.modules['keras'] = tf_keras
except ImportError:
    pass

from dataclasses import dataclass
from typing import List, Protocol

from backend.settings import Settings


class EmbeddingsLike(Protocol):
    def embed_documents(self, texts: List[str]) -> List[List[float]]: ...

    def embed_query(self, text: str) -> List[float]: ...


@dataclass(frozen=True)
class EmbeddingsConfig:
    model_name: str
    dimensions: int


def get_embeddings(settings: Settings) -> EmbeddingsLike:
    """
    Return a LangChain-compatible embeddings object backed by sentence-transformers.

    We prefer `langchain_huggingface.HuggingFaceEmbeddings` (newer split package),
    but fall back to `langchain_community.embeddings.HuggingFaceEmbeddings`.
    """
    # #region agent log
    import json, sys, os
    try:
        with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"embeddings.py:31","message":"get_embeddings entry","data":{"python_executable":sys.executable,"keras_in_modules":"keras" in sys.modules,"transformers_imported":"transformers" in sys.modules},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    except: pass
    # #endregion
    
    # CRITICAL: Ensure keras patch is applied BEFORE any transformers import
    # This must happen here because this function might be called lazily
    import sys
    import os
    
    # Set environment variables
    os.environ['TF_USE_LEGACY_KERAS'] = '1'
    os.environ['KERAS_BACKEND'] = 'tensorflow'
    
    # #region agent log
    try:
        with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
            keras_before = sys.modules.get('keras')
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"embeddings.py:47","message":"Before tf_keras import","data":{"keras_module":str(type(keras_before)) if keras_before else None,"keras_module_name":getattr(keras_before,'__name__',None) if keras_before else None},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    except: pass
    # #endregion
    
    try:
        import tf_keras
        # Aggressively patch keras BEFORE importing anything that uses transformers
        sys.modules['keras'] = tf_keras
        
        # Also pre-patch common submodules
        if hasattr(tf_keras, 'utils'):
            sys.modules['keras.utils'] = tf_keras.utils
        if hasattr(tf_keras, 'layers'):
            sys.modules['keras.layers'] = tf_keras.layers
        if hasattr(tf_keras, 'models'):
            sys.modules['keras.models'] = tf_keras.models
        
        # #region agent log
        try:
            with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                keras_after = sys.modules.get('keras')
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"embeddings.py:60","message":"After keras patch","data":{"keras_module":str(type(keras_after)),"keras_is_tf_keras":keras_after is tf_keras,"tf_keras_version":getattr(tf_keras,'__version__',None)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
        # #endregion
        
        # #region agent log
        try:
            import importlib.metadata
            keras_meta_version = None
            try:
                keras_meta_version = importlib.metadata.version('keras')
            except:
                pass
            with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"embeddings.py:68","message":"Package metadata check","data":{"keras_metadata_version":keras_meta_version},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
        # #endregion
        
    except ImportError as e:
        # #region agent log
        try:
            with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"embeddings.py:73","message":"tf_keras import failed","data":{"error":str(e)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
        # #endregion
        pass

    # #region agent log
    try:
        with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"embeddings.py:78","message":"Before HuggingFaceEmbeddings import","data":{"transformers_imported":"transformers" in sys.modules,"keras_in_modules":"keras" in sys.modules,"keras_module":str(type(sys.modules.get('keras'))) if 'keras' in sys.modules else None},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            f.flush()
    except Exception as log_err:
        try:
            with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"embeddings.py:81","message":"Log write error","data":{"error":str(log_err)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
    # #endregion

    # Now safe to import HuggingFaceEmbeddings (which will import transformers)
    try:
        # Newer: pip install langchain-huggingface
        # #region agent log
        try:
            with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"embeddings.py:88","message":"About to import langchain_huggingface","data":{},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                f.flush()
        except: pass
        # #endregion
        from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore
        # #region agent log
        try:
            with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"embeddings.py:94","message":"HuggingFaceEmbeddings imported","data":{"success":True},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                f.flush()
        except: pass
        # #endregion
    except Exception as e:  # pragma: no cover
        # #region agent log
        try:
            import traceback
            with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"embeddings.py:100","message":"HuggingFaceEmbeddings import failed","data":{"error":str(e),"error_type":type(e).__name__,"traceback":traceback.format_exc()},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                f.flush()
        except: pass
        # #endregion
        from langchain_community.embeddings import HuggingFaceEmbeddings  # type: ignore

    # #region agent log
    try:
        with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"embeddings.py:95","message":"Before creating HuggingFaceEmbeddings instance","data":{},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    except: pass
    # #endregion

    # Using sentence-transformers models; these are public on Hugging Face.
    result = HuggingFaceEmbeddings(model_name=settings.embeddings_model_name)
    
    # #region agent log
    try:
        with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"embeddings.py:100","message":"get_embeddings exit","data":{"success":True},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    except: pass
    # #endregion
    
    return result




