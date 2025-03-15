# DIY-Your-AI-Agent: AI-powered Smart Terminal Assistant  

[中文文档](https://github.com/whitejoce/DIY-your-AI-agent/blob/main/README_CN.md)

## 🔥 Project Overview  

This project is an **AI-powered smart terminal assistant (Linux Agent) based on Large Language Models (LLM)**. It automatically analyzes user input, determines whether a terminal command needs to be executed, and returns results in **JSON format**, ensuring secure interactions.  

**Collaboration Process Between Conversation and Command Execution:**  
```plaintext
User Input → LLM Intent Recognition → Determine if Command Execution is Needed →  
   → Yes: LLM Generates Command → Execute Command → Return Result → Generate Natural Language Response  
   → No: Directly Generate Natural Language Response  
```
**Key Features:**  
- 🖥 **Intelligent Parsing**: Determines whether user requests involve file operations, process management, etc.  
- 🔒 **Security Protection**: Automatically prompts for confirmation when encountering dangerous commands (e.g., `rm -rf`).  
- 🔄 **Interactive Experience**: Provides structured JSON responses to ensure readability and scalability.  
- ⚡ **Instant Execution**: Automatically executes commands in the Bash terminal upon user confirmation and returns results.  

## 🛠 Example Usage  

Start the interactive smart terminal:  
```bash
python agent_en.py
```
Then enter any Linux-related command, for example:  

```plaintext
Smart_Shell> Show the files in the current directory
```

**Agent Response (JSON Format):**  
```json
{
  "action": "execute_command",
  "command": "ls -l",
  "explanation": "Lists detailed information of the current directory"
}
```
If the command is potentially dangerous, such as `rm -rf`, the system will automatically prompt for a second confirmation.  

---

## 📖 How It Works  

This AI Agent operates based on **LLM + rule constraints**, with core logic including:  

1. **LLM-based reasoning**: Uses models like Qwen/Qwen2.5-7B-Instruct (or other LLMs) to analyze user input.  
2. **Rule-based guidance**: Ensures AI responses comply with predefined formats (e.g., JSON output).  
3. **Interactive mechanism**: Users manually confirm commands to prevent accidental operations.  
4. **Terminal execution**: Uses `os.popen` to run Bash commands and return execution results.  

---

## 🚀 Quick Start  

### 1️⃣ **Environment Setup**  

Requires **Python 3.8+**, and install OpenAI-related dependencies:  
```bash
pip install openai
```  

### 2️⃣ **Configure API**  

Modify `agent_en.py`:  
```python
url = "your_openai_api_url"
api_key = "your_openai_api_key"
```  

---

## 💡 How to Improve?  

If you want to make this Agent more intelligent and powerful, consider the following approaches:  

1️⃣ *Ask the Friendly AI* 🤖  
   - Engage in discussions with the model directly in the terminal to refine your ideas.  
   - Ask questions like: "How can I make the Agent more autonomous?" or "How can I optimize my terminal assistant?"  

2️⃣ **Model Context Protocol (MCP) 🏗️**  
   - MCP (Model Context Protocol) is an open protocol designed to seamlessly integrate Large Language Models (LLMs) with external data sources and tools.  
   - By standardizing interactions between AI systems and data sources, MCP enables models to generate more accurate and contextually relevant responses.  
   - Refer to the [MCP Official Repository](https://github.com/modelcontextprotocol) and [Anthropic Blog](https://www.anthropic.com/news/model-context-protocol) to learn more.  

3️⃣ **AI-driven Automation Scripts 🚀**  
   - Enable AI not just to execute commands but also to **invoke other automation scripts**, forming a more adaptive workflow.  
   - Write automation scripts for tasks like **batch file organization or automated log analysis**, and let AI call them at appropriate times to achieve higher-level intelligent automation.  

By implementing these improvements, your AI terminal assistant can evolve beyond just a "command parser" into a truly intelligent Agent! 💡✨  

---

## 📜 License  

This project is licensed under the **MIT License**—feel free to modify and use it!  

## 🤝 Contributions  

Issues & PRs are welcome! If you have better ideas, feel free to contribute code!  
