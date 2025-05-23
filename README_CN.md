# DIY Your AI Agent: 基于大模型的智能终端助手

> 使用MCP实现的AI Agent: [MCP Agent Demo](https://github.com/whitejoce/mcp_agent)

## 🔥 项目简介  

本项目是一个 **基于大模型（LLM）的终端智能助手（Linux Agent）**，能够自动分析用户输入，判断是否需要执行终端命令，并以 **JSON 格式** 返回结果，确保交互安全。

<img src="./img/test.png" alt="运行示例">

**对话与指令执行的协作流程**
```plaintext
用户输入 → LLM意图识别 → 判断是否需要执行指令 → 
   → 是：LLM生成指令 → 执行指令 → 结果反馈 → 生成自然语言回复
   → 否：直接生成自然语言回复
```

**主要特性：**  
- 🖥 **智能解析**：判断用户请求是否涉及文件操作、进程管理等  
- 🔒 **安全防护**：遇到危险命令（如 `rm -rf`）自动二次确认  
- 🔄 **交互式体验**：提供 JSON 格式的结构化响应，确保易读性和可扩展性  
- ⚡ **即时执行**：用户确认后，自动在 Bash 终端执行命令并返回结果  

## 🛠 运行示例  

启动交互式智能终端：  
```bash
python agent.py
```
然后输入任意 Linux 相关指令，例如：  

```plaintext
Smart_Shell> 查看当前目录文件
```

**Agent 响应（JSON 格式）：**  
```json
{
  "action": "execute_command",
  "command": "ls -l",
  "explanation": "列出当前目录的详细信息"
}
```
如果是危险操作，如 `rm -rf`，会自动提示二次确认。  

---

## 📖 原理解析  

该智能助手采用 **LLM + 规则约束** 的方式工作，核心逻辑包括：  

1. **基于 LLM 推理**：使用 Qwen/Qwen2.5-7B-Instruct 模型 (或其他LLM)，分析用户输入  
2. **规则引导**：基于设定的规则（如 JSON 输出格式），确保 AI 响应符合约定  
3. **交互机制**：用户可以手动确认命令，防止误操作  
4. **终端执行**：调用 `subprocess.Popen()` 运行 Bash 命令，并返回执行结果  

> 最小可行代码: 可以查看`agent_mvp.py`, 浏览精简版代码。
---

## 🚀 快速开始  

### 1️⃣ **环境准备**  

需要 **Python 3.8+**，并安装 OpenAI 和 rich (富文本)库：  

```bash
pip install openai rich
```

### 2️⃣ **配置 API**  

修改 `agent.py`：  
```python
url = "your_api_url"
api_key = "your_api_key"
```

---

## 💡 如何做得更好？  

如果你想让这个 Agent 更加智能和强大，可以尝试以下几种方式：  

1️⃣ **与 AI 直接对话** —— *Ask the Friendly AI* 🤖  
   - 直接在终端与大模型讨论你的创意，让 AI 帮你完善思路。  
   - 你可以向它提问：“如何让 Agent 更自主？” 或者“如何优化我的终端助手？”  

2️⃣ **Model Context Protocol** 🏗️  
   - MCP（Model Context Protocol）是一种开放协议，旨在实现大型语言模型（LLM）与外部数据源和工具的无缝集成。
   - 通过标准化AI系统与数据源的交互方式，MCP帮助模型获取更丰富的上下文信息，从而生成更准确、更相关的响应。
   - 你可以参考[MCP官方文档](https://modelcontextprotocol.io/introduction), [FastMCP](https://gofastmcp.com/getting-started/welcome)来了解MCP的概念和应用。 

3️⃣ **用 AI 驱动自动化脚本** 🚀  
   - 让 AI 不仅执行命令，还能**调用其他自动化脚本**，形成更强的自适应工作流。  
   - 可以通过编写自动化脚本，比如**批量整理文件、自动化日志分析**，然后让 AI 调用这些`最佳实践`，实现更高阶的智能自动化。  

这些改进方向，可以让你的 AI 终端助手不仅仅是一个“命令解析器”，而是一个真正具备智能性的 Agent！💡✨

---

## 📜 License  

本项目采用 **MIT 许可证**，欢迎自由修改和使用！  

## 🤝 贡献  

欢迎 Issue & PR！如果你有更好的想法，欢迎贡献代码！  
