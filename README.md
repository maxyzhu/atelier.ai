### File Structure

atelier/
│
├── contracts/                   # 模块间接口定义
│   ├── __init__.py
│   ├── requests.py              # request / response 数据结构
│   ├── recording.py             # S0 + Delta schema（供recorder和agents共用）
│   ├── bridge.py                # bridge指令 / 返回结构（供agents和bridge共用）
│   └── tools.py                 # 工具定义结构
│
├── gateway/                     # GatewayLLM
│   ├── __init__.py
│   ├── gateway.py               # 主逻辑：拆分request，分发，管理workflow
│   └── prompts/
│       └── gateway.yaml
│
├── agents/                      # 软件专用子LLM
│   └── sketchup/
│       ├── __init__.py
│       ├── agent.py             # SketchupLLM主逻辑 + FSM
│       ├── fsm.py               # 状态机
│       └── prompts/
│           ├── modeling.yaml
│           ├── material.yaml
│           └── check.yaml
│
├── recorder/                    # 通用录制模块
│   ├── __init__.py
│   ├── recorder.py              # 主逻辑：管理S0, linear_flow, undo_log
│   └── adapters/
│       ├── __init__.py
│       └── sketchup/
│           ├── __init__.py
│           └── observer.rb      # Ruby Observer（SketchUpAdapter）
│
├── toolbox/                     # 工具持久化
│   ├── __init__.py
│   ├── toolbox.py               # 读写工具定义，管理success/failure log
│   └── tools/                   # 工具存储（yaml文件）
│       └── sketchup/
│
├── bridge/                      # MCP bridge
│   ├── __init__.py
│   └── sketchup_bridge.py       # sketchup-mcp TCP连接封装
│
├── explore/                     # 草稿、实验、原型
│
├── tests/
│   ├── test_gateway.py
│   ├── test_agent.py
│   ├── test_recorder.py
│   └── test_toolbox.py
│
├── .env                        # API keys, MCP port, max iterations, max rework
├── main.py                    # Entry point
├── pyproject.toml               # uv 依赖管理
└── requirements.md           # pydantic, anthropic, pyyaml
└── README.md                   # Introduction