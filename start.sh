#!/bin/bash
cd /home/chengdudu/resume_parser
export HOME=/home/chengdudu
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
export PYTHONPATH=/home/chengdudu/resume_parser:$PYTHONPATH
exec /usr/bin/python3 -c "
import sys
sys.path.insert(0, '/home/chengdudu/resume_parser')
from web_app import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8000)
"
