# 抖音直播间批量监控工具

自动化采集抖音品牌直播间的商品截图信息，通过 **Claude Code** + **Playwright** 驱动浏览器操作。

## 功能

- 批量采集多个品牌的抖音直播间
- 自动搜索官方旗舰店直播间并进入
- 截图直播间首页、商品面板（小黄车）
- 展开前 3 个商品详情并截图
- 前端配置面板，实时查看采集进度
- 支持待采集品牌列表配置

## 截图效果

采集完成后，每个品牌在桌面生成如下目录结构：

```
~/Desktop/抖音直播间截图/{品牌}/{YYYY-MM-DD}/
├── 01-直播间首页.png
├── 02-商品面板.png
├── 03-商品1.png
├── 04-商品2.png
└── 05-商品3.png
```

## 前置要求

- [Claude Code](https://claude.ai/code) — AI 命令行工具
- [Playwright MCP](https://github.com/microsoft/playwright-mcp) — 浏览器自动化
- Python 3（配置面板使用）
- 抖音账号（用于扫码登录）

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/liqunqun07/douyin-livestream-monitor.git
cd douyin-livestream-monitor
```

### 2. 安装为 Claude Code Skill

将项目目录复制或链接到 Claude Code 的 skills 目录：

```bash
# 创建 skills 目录（如果不存在）
mkdir -p ~/.claude/skills

# 复制项目到 skills 目录
cp -r douyin-livestream-monitor ~/.claude/skills/
```

或者直接在工作目录中使用。

### 3. 配置 Playwright MCP

确保你的 `~/.claude/settings.json` 中配置了 Playwright MCP：

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

### 4. 启动配置面板

```bash
cd ~/.claude/skills/douyin-livestream-monitor
bash start.sh
```

浏览器会自动打开配置面板。

## 使用方法

### 方式一：通过前端面板（推荐）

1. 运行 `bash start.sh` 启动配置面板
2. 在浏览器中填写品牌列表（逗号隔开）
3. 点击「保存配置」
4. 点击「开始采集」
5. 切换到 Claude Code 终端，输入 `看直播间`

### 方式二：直接输入指令

在 Claude Code 中直接输入：

```
看直播间 兰蔻,SK-II,赫莲娜
```

或只输入品牌名：

```
提取城野医生、OLAY、芙丽芳丝、可复美
```

### 登录

首次使用需要扫码登录抖音：

1. 输入指令后，Claude Code 会自动打开抖音首页
2. 如果未登录，会提示扫码
3. 扫码登录后，Cookies 会自动保存，下次无需重复登录

## 项目结构

```
douyin-livestream-monitor/
├── SKILL.md           # Claude Code Skill 定义（核心指令）
├── README.md          # 本文件
├── start.sh           # 启动配置面板
├── frontend/          # Web 配置面板
│   ├── index.html     # 前端界面
│   └── server.py      # 后端 API 服务
├── config.json        # 用户配置（gitignored）
├── status.json        # 运行状态（gitignored）
├── scripts/           # 辅助脚本
└── references/        # 参考文档
```

## 注意事项

- 抖音有风控机制，遇到验证码需手动处理
- 品牌间有间隔等待策略，防止触发风控
- 批量采集时建议不要超过 20 个品牌
- Cookies 保存在 `~/.claude/douyin_cookies.json`
- 本工具仅供学习研究使用

## License

MIT
