"""
Keras 3 compatibility patch for transformers/sentence-transformers.

This module must be imported before any transformers or sentence-transformers imports.
It patches sys.modules to make tf_keras available as keras.

CRITICAL: This must be imported FIRST, before any other backend imports.
"""
from __future__ import annotations

import sys
import os

# Set environment variables BEFORE any imports
os.environ['TF_USE_LEGACY_KERAS'] = '1'
os.environ['KERAS_BACKEND'] = 'tensorflow'

# CRITICAL: Patch keras module BEFORE transformers can check for it
try:
    # Import tf_keras first
    import tf_keras
    
    # Aggressively patch sys.modules to make tf_keras available as keras
    # This must happen before ANY transformers import
    sys.modules['keras'] = tf_keras
    
    # Also pre-patch common keras submodules that transformers might check
    if hasattr(tf_keras, 'utils'):
        sys.modules['keras.utils'] = tf_keras.utils
    if hasattr(tf_keras, 'layers'):
        sys.modules['keras.layers'] = tf_keras.layers
    if hasattr(tf_keras, 'models'):
        sys.modules['keras.models'] = tf_keras.models
    
    # Remove any existing keras.* modules that might be keras 3
    for key in list(sys.modules.keys()):
        if key.startswith('keras.') and key not in ['keras.utils', 'keras.layers', 'keras.models']:
            try:
                del sys.modules[key]
            except KeyError:
                pass
    
    # Monkey-patch importlib.metadata to prevent transformers from detecting keras 3
    # This intercepts the check that transformers does
    try:
        import importlib.metadata
        original_version = importlib.metadata.version
        
        def patched_version(package_name):
            if package_name == 'keras':
                # Return tf-keras version instead
                return tf_keras.__version__ if hasattr(tf_keras, '__version__') else '2.20.1'
            return original_version(package_name)
        
        importlib.metadata.version = patched_version
        
        # Also patch distributions() method which transformers might use
        if hasattr(importlib.metadata, 'distributions'):
            original_distributions = importlib.metadata.distributions
            
            def patched_distributions(**kwargs):
                for dist in original_distributions(**kwargs):
                    # Filter out keras 3 if it exists
                    if dist.metadata['Name'] == 'keras' and dist.version.startswith('3.'):
                        continue
                    yield dist
            
            importlib.metadata.distributions = patched_distributions
    except (ImportError, AttributeError):
        # Fallback if importlib.metadata is not available
        pass
    
    # Also patch pkg_resources if it's available (some environments use this)
    try:
        import pkg_resources
        original_get_distribution = pkg_resources.get_distribution
        
        def patched_get_distribution(dist):
            if dist == 'keras':
                # Return a fake distribution object for tf-keras
                class FakeDist:
                    version = tf_keras.__version__ if hasattr(tf_keras, '__version__') else '2.20.1'
                    project_name = 'keras'
                return FakeDist()
            return original_get_distribution(dist)
        
        pkg_resources.get_distribution = patched_get_distribution
        
        # Also patch working_set to filter out keras 3
        if hasattr(pkg_resources, 'working_set'):
            for dist in list(pkg_resources.working_set):
                if dist.project_name == 'keras' and dist.version.startswith('3.'):
                    pkg_resources.working_set.remove(dist)
    except (ImportError, AttributeError):
        pass
    
    # Patch __import__ to intercept keras imports
    original_import = __import__
    
    def patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'keras' or (fromlist and 'keras' in fromlist):
            return tf_keras
        return original_import(name, globals, locals, fromlist, level)
    
    # Only patch if keras 3 might be installed
    # We'll use the builtin __import__ but ensure sys.modules is patched
    builtins = sys.modules.get('builtins', __builtins__)
    if hasattr(builtins, '__import__'):
        # Store original but don't override - sys.modules patch should be enough
        pass
    
except ImportError as e:
    import warnings
    warnings.warn(f"tf_keras not found: {e}. Install with: pip install tf-keras")
    pass

