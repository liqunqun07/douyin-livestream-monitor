# Claude Code 配置参考（含免订阅方案）

本项目的核心驱动是 **Claude Code** + **Playwright MCP**。Claude Code 有两种使用方式：

- **官方版**：需要 Claude 订阅（Pro / Max）
- **CC Switch 版**：开源方案，可接入第三方 API，无需官方订阅

---

## 一、官方版（有 Claude 订阅）

### 安装 Claude Code

```bash
npm install -g @anthropic-ai/claude-code
# 或
brew install claude-code
```

安装后运行 `claude` 首次启动，按提示在浏览器中完成 Claude 账号授权。

### 配置 Playwright MCP

编辑 `~/.claude/settings.json`：

```json
{
  "mcpServers": {
    "playwright": {
      "type": "stdio",
      "command": "npx",
      "args": ["@playwright/mcp"]
    }
  }
}
```

安装浏览器：

```bash
npx playwright install chromium
```

### 安装本 Skill

```bash
mkdir -p ~/.claude/skills
cp -r douyin-livestream-monitor ~/.claude/skills/
```

### 使用

```bash
cd ~/.claude/skills/douyin-livestream-monitor
claude
```

在 Claude Code 中输入：

```
看直播间 兰蔻,SK-II,赫莲娜
```

---

## 二、CC Switch 版（免 Claude 订阅）

### 适用场景

没有 Claude 订阅，但想用本项目。通过 CC Switch 将底层模型替换为：
- **免费方案**：ModelScope（魔搭）、Ollama（本地模型）
- **付费方案**：MiniMax、OpenRouter、AnyRouter 等

### 原理

```
用户输入
    │
    ▼
Claude Code CLI（无需订阅）
    │
    ▼
CC Switch（模型路由层）
    │
    ▼
第三方 API / 本地模型（替代 Claude 模型）
    │
    ▼
Playwright MCP（浏览器操作）
```

CC Switch 会拦截 Claude Code 对 Anthropic API 的调用，透明地转发到你配置的任意兼容 API。

### 安装步骤

#### 1. 安装 CC Switch

```bash
# 方式 A：桌面版（推荐，带 GUI）
git clone https://github.com/farion1231/cc-switch.git
cd cc-switch
# 按 README 指引安装

# 方式 B：Web 版（适合服务器/无 GUI 环境）
git clone https://github.com/farion1231/cc-switch-web.git
cd cc-switch-web
# 按 README 指引安装
```

#### 2. 安装 Claude Code CLI

CC Switch 需要 Claude Code CLI 作为前端，但不需要 Claude 订阅账号：

```bash
npm install -g @anthropic-ai/claude-code
```

> 安装后**不要**运行 `claude` 授权，后续由 CC Switch 接管 API 调用。

#### 3. 配置 CC Switch

在 CC Switch 的配置界面（或配置文件）中添加模型供应商：

**示例：接入 ModelScope（魔搭，免费）**

```
提供商: ModelScope
API 地址: https://api-inference.modelscope.cn/v1
API Key: （在 modelscope.cn 控制台获取）
模型: Qwen/Qwen3-235B-A22B
```

**示例：接入 Ollama（本地模型，完全免费）**

```
提供商: Ollama
API 地址: http://127.0.0.1:11434/v1
API Key: 任意值（Ollama 不需要 key）
模型: qwen3:latest（或 deepseek-r1、glm4 等）
```

**示例：接入 MiniMax（付费，Anthropic 兼容 API）**

```
提供商: MiniMax
API 地址: https://api.minimax.chat/v1
API Key: （在 minimax 控制台获取）
模型: deepseek-v3（或其他 MiniMax 支持模型）
```

#### 4. 配置 Playwright MCP

与官方版相同，编辑 `~/.claude/settings.json`：

```json
{
  "mcpServers": {
    "playwright": {
      "type": "stdio",
      "command": "npx",
      "args": ["@playwright/mcp"]
    }
  }
}
```

```bash
npx playwright install chromium
```

#### 5. 安装本 Skill

```bash
mkdir -p ~/.claude/skills
cp -r douyin-livestream-monitor ~/.claude/skills/
```

#### 6. 使用

在 CC Switch 中启动 Claude Code（CC Switch 会接管 API）：

```bash
cd ~/.claude/skills/douyin-livestream-monitor
# 通过 CC Switch 的界面按钮启动 Claude Code
# 或在终端通过 CC Switch 包装后的命令启动
```

然后在 Claude Code 中输入：

```
看直播间 兰蔻,SK-II,赫莲娜
```

---

## 三、CC Switch 配置文件示例

以下是一份完整的 CC Switch 配置，可根据实际情况修改：

### cc-switch-config.json

```json
{
  "currentProvider": "modelscope",
  "providers": {
    "modelscope": {
      "name": "ModelScope 魔搭",
      "type": "openai",
      "apiBase": "https://api-inference.modelscope.cn/v1",
      "apiKey": "your-modelscope-api-key",
      "models": {
        "claude-sonnet": "Qwen/Qwen3-235B-A22B",
        "claude-opus": "Qwen/Qwen3-235B-A22B"
      },
      "notes": "免费，需注册阿里云/魔搭账号，每天有免费额度"
    },
    "ollama": {
      "name": "Ollama 本地",
      "type": "openai",
      "apiBase": "http://127.0.0.1:11434/v1",
      "apiKey": "ollama",
      "models": {
        "claude-sonnet": "qwen3:latest",
        "claude-opus": "qwen3:latest"
      },
      "notes": "完全免费，需安装 Ollama 并下载模型，速度取决于本地硬件"
    },
    "minimax": {
      "name": "MiniMax",
      "type": "openai",
      "apiBase": "https://api.minimax.chat/v1",
      "apiKey": "your-minimax-api-key",
      "models": {
        "claude-sonnet": "deepseek-v3",
        "claude-opus": "deepseek-v3"
      },
      "notes": "付费，Anthropic 兼容 API，98元/月套餐或按量计费"
    },
    "openrouter": {
      "name": "OpenRouter",
      "type": "openai",
      "apiBase": "https://openrouter.ai/api/v1",
      "apiKey": "your-openrouter-api-key",
      "models": {
        "claude-sonnet": "anthropic/claude-3.5-sonnet",
        "claude-opus": "anthropic/claude-3-opus"
      },
      "notes": "付费，可直连官方 Claude 模型，按量计费"
    },
    "deepseek": {
      "name": "DeepSeek 官方",
      "type": "openai",
      "apiBase": "https://api.deepseek.com/v1",
      "apiKey": "your-deepseek-api-key",
      "models": {
        "claude-sonnet": "deepseek-chat",
        "claude-opus": "deepseek-chat"
      },
      "notes": "付费，价格极低，性能接近 Claude"
    }
  }
}
```

### CC Switch Web 版配置（config.yml）

```yaml
# cc-switch-web 配置示例
port: 3000
providers:
  - name: modelscope
    type: openai
    api_base: https://api-inference.modelscope.cn/v1
    models:
      - claude-sonnet: Qwen/Qwen3-235B-A22B
      - claude-opus: Qwen/Qwen3-235B-A22B
  - name: ollama
    type: openai
    api_base: http://127.0.0.1:11434/v1
    models:
      - claude-sonnet: qwen3:latest
      - claude-opus: qwen3:latest
  - name: deepseek
    type: openai
    api_base: https://api.deepseek.com/v1
    models:
      - claude-sonnet: deepseek-chat
      - claude-opus: deepseek-chat
```

---

## 四、方案对比

| 方案 | 费用 | 智能水平 | 稳定性 | 配置难度 |
|------|------|---------|--------|---------|
| 官方 Claude 订阅 | Pro $20/月 | ⭐⭐⭐⭐⭐ 最高 | ⭐⭐⭐⭐⭐ | ⭐ 最低 |
| CC Switch + ModelScope | 免费 | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐ | ⭐⭐ |
| CC Switch + Ollama | 免费 | ⭐⭐~⭐⭐⭐ 看本地配置 | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| CC Switch + MiniMax | ¥98/月 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| CC Switch + DeepSeek API | 极低 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| CC Switch + OpenRouter | 按量 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |

**推荐**：
- 首次体验 → ModelScope 免费方案
- 完全免费 → Ollama 本地模型（需好显卡）
- 性价比 → DeepSeek API
- 最佳体验 → 官方 Claude 订阅

---

## 五、注意事项

- **免费模型处理复杂任务可能出错**：国产模型在长链路推理、复杂 JS 执行上不如 Claude，如果采集过程中频繁出错，建议换更强的模型
- **API Key 安全**：不要将 API Key 提交到 Git 仓库（本项目 `.gitignore` 已排除 `config.json`）
- **Playwright MCP 不变**：无论用哪种 Claude 方案，Playwright MCP 配置完全相同
- **SKILL.md 仍然需要**：CC Switch 只替换底层模型，Claude Code 仍然读取 `SKILL.md` 作为指令文档
- **首次运行需要扫码登录抖音**，与采用哪种 Claude 方案无关

---

## 六、相关资源

- [CC Switch GitHub](https://github.com/farion1231/cc-switch) — 桌面版
- [CC Switch Web](https://github.com/Laliet/cc-switch-web) — Web 版
- [ModelScope (魔搭)](https://modelscope.cn) — 免费模型 API
- [Ollama](https://ollama.com) — 本地模型运行器
- [MiniMax](https://minimax.chat) — Anthropic 兼容 API
- [OpenRouter](https://openrouter.ai) — 多模型路由
- [SNOW CLI](https://github.com/snowclimber-cli/snow) — Claude Code 完全开源平替
