"""
Suppress qwen-tts warnings and messages.
Import this before using qwen-tts to suppress startup messages.
"""

import warnings
import sys
import os
from io import StringIO

# Suppress all warnings
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

# Capture and suppress stderr during qwen_tts import
class SuppressOutput:
    def __enter__(self):
        self._original_stderr = sys.stderr
        self._original_stdout = sys.stdout
        sys.stderr = StringIO()
        sys.stdout = StringIO()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr = self._original_stderr
        sys.stdout = self._original_stdout

def suppress_qwen_warnings():
    """Suppress qwen-tts startup warnings and messages."""
    # This needs to be called before importing qwen_tts
    warnings.filterwarnings('ignore', message='.*flash-attn.*')
    warnings.filterwarnings('ignore', message='.*SoX.*')
    warnings.filterwarnings('ignore', category=UserWarning)
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow logs

