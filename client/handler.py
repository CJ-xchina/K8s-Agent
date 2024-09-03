import re
import sys
from typing import Any, List, Optional, Sequence, Tuple, Union, Dict

from langchain_core.pydantic_v1 import Field
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple, Union
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import GenerationChunk, ChatGenerationChunk, LLMResult
from uuid import UUID




class MyPrintHandler(BaseCallbackHandler):
    """自定义LLM CallbackHandler，用于打印大模型返回的思考过程"""

    def __init__(self):
        BaseCallbackHandler.__init__(self)

    def on_llm_new_token(
            self,
            token: str,
            *,
            chunk: Optional[Union[GenerationChunk, ChatGenerationChunk]] = None,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        end = ""
        content = token + end
        sys.stdout.write(content)
        sys.stdout.flush()
        return token

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        end = ""
        content = "\n" + end
        sys.stdout.write(content)
        sys.stdout.flush()
        return response
