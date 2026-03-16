# LangChain Core — Context7 Cache

## Current Version: langchain-core 0.3.x

## Key API Patterns

### Chat Models
- `from langchain_core.language_models.chat_models import BaseChatModel`
- `from langchain_core.messages import HumanMessage, AIMessage, SystemMessage`
- `.invoke(messages)` / `.ainvoke(messages)` — single call
- `.stream(messages)` / `.astream(messages)` — streaming

### Runnables
- `from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel`
- `chain = prompt | llm | parser` — pipe syntax for composition
- `.invoke()`, `.ainvoke()`, `.batch()`, `.abatch()`, `.stream()`, `.astream()`

### Prompts
- `from langchain_core.prompts import ChatPromptTemplate`
- `ChatPromptTemplate.from_messages([("system", "..."), ("human", "{input}")])`
- `.invoke({"input": "value"})` — returns prompt value

### Output Parsers
- `from langchain_core.output_parsers import StrOutputParser, JsonOutputParser`
- `StrOutputParser()` — extracts string content from AI message

### Callbacks
- `from langchain_core.callbacks import CallbackManagerForLLMRun`
- Used in custom LLM implementations

### Documents
- `from langchain_core.documents import Document`
- `Document(page_content="...", metadata={...})`

### Note
- langchain-core is the minimal dependency — use it instead of full langchain package
- Avoid importing from `langchain` directly; prefer `langchain_core`
