---
name: douyin-livestream-monitor
description: 抖音品牌直播间批量监控工具。当用户提到"看直播间"、"监控直播"、"截图直播"、"查看xx直播间"、"小黄车"、"直播间商品"、"抖音直播"、"采集直播间"、"直播截图"、"批量采集"、"多个品牌"等关键词时触发。接收逗号分隔的品牌列表，自动逐个搜索进入直播间，采集截图并保存到桌面文件夹。注意风控处理和大批量场景下的节流策略。
---

# 抖音直播间批量监控工具

## 概述

本 skill 用于自动化采集抖音品牌直播间的视觉信息。核心流程：
1. **输入解析** — 接收逗号分隔的品牌名称列表（如 "赫莲娜,海蓝之谜,SK-II"）
2. **逐个处理** — 遍历每个品牌：搜索直播间 → 进入 → 截图 → 关掉当前页 → 下一个
3. **商品采集** — 每个品牌截图：直播间首页 → 商品面板 → 前3个商品详情
4. **文件整理** — 统一保存到 `~/Desktop/抖音直播间截图/{品牌}/{日期}/` 目录下

## 使用方式

本工具通过 **Claude Code** 执行采集，通过前端面板配置和查看进度。

### 完整流程

```bash
# 第一步：启动配置面板（浏览器自动打开）
cd ~/.claude/skills/douyin-livestream-monitor
bash start.sh
```

**前端操作：**
1. 填写品牌列表（逗号隔开），设置保存路径
2. 点击「保存配置」
3. 点击「▶️ 开始采集」— 状态变为等待中

**切换到 Claude Code 终端：**
4. 输入 `看直播间`（或 `看直播间 兰蔻,SK-II`）
5. Skill 读取 `config.json` 获取配置，执行采集
6. 前端面板实时显示进度

启动配置面板后，前端服务器会一直在后台运行，可随时打开浏览器查看进度。

---

## 前端配置面板

本工具包含一个本地 Web 配置面板，提供可视化配置和实时监控功能：

- **位置**: `frontend/` 目录
- **启动方式**: 运行 `bash start.sh` 或 `python3 frontend/server.py`
- **功能**:
  - 填写品牌列表（自动保存到 `config.json`）
  - 选择截图保存路径
  - 点击「开始采集」按钮启动自动化流程
  - 实时显示运行进度、步骤和日志
  - 支持停止正在运行的采集任务
- **通信方式**: 面板通过 `config.json` 和 `status.json` 与采集进程通信
  - `config.json` — 读取品牌列表和保存路径
  - `status.json` — 写入当前进度、步骤、完成状态

---

## Cookie 存储路径

- **存储文件**: `~/.claude/douyin_cookies.json`
- **格式**: JSON 数组
- **管理方式**: 通过 browser_run_code_unsafe 读写

### 保存 cookies
```javascript
async (page) => {
  const cookies = await page.context().cookies();
  return JSON.stringify(cookies);
}
```
然后用 Bash 将返回的 JSON 写入 `~/.claude/douyin_cookies.json`。

### 加载 cookies
先用 Bash 读取文件内容，然后：
```javascript
async (page) => {
  const cookiesJson = `[文件内容]`;
  const cookies = JSON.parse(cookiesJson);
  await page.context().addCookies(cookies);
  return "Cookies loaded: " + cookies.length;
}
```

---

## 工作流程

### Phase 0: 风控与错误处理（重要）

抖音有较强的反爬/风控机制，遇到以下情况需特殊处理：

**常见风控表现及应对：**
- **连接重置/ERR_CONNECTION_CLOSED** → 等待2-3秒重试 navigation
- **页面空白/加载失败** → 刷新页面重试
- **出现验证码/滑块** → 立即告知用户"触发了安全验证，请手动完成页面上的验证"
- **跳转到 user/self 或异常页面** → 点击了小黄车以外的元素，立即重新 navigate 到直播间 URL
- **"服务异常"提示** → 刷新页面重试
- **协议弹窗** → 点击"同意"按钮后继续

**重试机制：**
- 每个关键步骤（进入直播间、点击商品、关闭详情）最多重试2次
- 如果连续失败，告知用户"当前直播间可能存在访问限制"

---

### Phase 1: 输入解析

用户可能输入单个品牌或多个品牌（逗号分隔），例如：
- "赫莲娜" → 单个品牌
- "赫莲娜,海蓝之谜,SK-II" → 多个品牌
- "赫莲娜、海蓝之谜、SK2" → 支持中文顿号分隔

**同时读取 config.json（前端配置面板生成）：**
- 路径: skill 目录下的 `config.json`
- 如果存在且包含 brands 列表，优先使用 config 中的 brands
- 如果用户同时在消息中指定了品牌，则以用户消息为准（覆盖 config）
- 用 Bash 读取并解析：
  ```bash
  # 读取前端配置
  SKILL_DIR=$(find /Users/smzdm/.claude/skills -maxdepth 1 -name "douyin-livestream-monitor" -type d 2>/dev/null | head -1)
  if [ -f "$SKILL_DIR/config.json" ]; then
    cat "$SKILL_DIR/config.json"
  fi
  ```

处理逻辑：
1. 按 `,`、`、`、`；`、`;` 分割字符串
2. 去除每个品牌名前后的空格
3. 过滤空字符串
4. 特殊映射：`SK2` → `SK-II`
5. 告知用户：`"共 N 个品牌：品牌1、品牌2、...、品牌N"`

---

### Phase 2: 登录管理

每次操作前先执行登录检查：

1. **打开抖音首页**：`browser_navigate` → `https://www.douyin.com`
2. **注入已保存的 cookies**：
   - Bash 检查 `~/.claude/douyin_cookies.json` 是否存在且非空
   - 存在则读取并用 `browser_run_code_unsafe` 注入 cookies
   - 注入后 `browser_navigate` 刷新 `https://www.douyin.com`
3. **验证登录状态**：`browser_snapshot` 检查是否有用户标识（`a[href*="/user/self"]` 是否存在）
4. **如需登录**：截图二维码 → 告知用户扫码 → 等待确认 → 刷新验证 → 保存 cookies

---

## 状态同步（前端实时监控）

Skill 运行期间需要持续写入 `status.json`，供前端面板实时显示。用 Bash 写入：

```bash
# 写入状态到 status.json
SKILL_DIR=$(find /Users/smzdm/.claude/skills -maxdepth 1 -name "douyin-livestream-monitor" -type d 2>/dev/null | head -1)
cat > "$SKILL_DIR/status.json" << 'JSONEOF'
{
  "status": "running",
  "currentBrand": "赫莲娜",
  "currentStep": "截图直播间首页",
  "progress": "2/5",
  "completedBrands": ["CPB", "圣罗兰"],
  "errors": [],
  "startedAt": "2026-05-14 12:00:00",
  "updatedAt": "2026-05-14 12:15:00"
}
JSONEOF
```

**status 字段说明：**
- `status`: `"idle"` | `"running"` | `"completed"` | `"error"`
- `currentBrand`: 当前正在处理的品牌
- `currentStep`: 当前步骤描述（如"搜索直播间"、"截图首页"、"点击全部商品"等）
- `progress`: 进度字符串 `"已处理数/总数"`
- `completedBrands`: 已完成的品牌列表
- `errors`: 错误信息列表
- `startedAt` / `updatedAt`: 时间戳

**关键更新点：**
1. 开始遍历前：写入 `status: "running"`
2. 每个品牌开始时：更新 `currentBrand` 和 `progress`
3. 每个步骤完成后：更新 `currentStep`
4. 每个品牌完成后：追加到 `completedBrands`
5. 全部完成：写入 `status: "completed"`
6. 发生错误：写入 `status: "error"` 并记录错误信息

核心循环逻辑（每次更新状态时同步写入 status.json）：

```
total = len(brands)
completed = []

# 初始化状态
write_status("running", "", "开始采集...", "0/"+total, [])

for index, brand in enumerate(brands):
  1. 更新状态: write_status("running", brand, "搜索直播间...", completed+1/total, completed)
  2. 搜索品牌直播间
  3. 更新状态: write_status("running", brand, "进入直播间并截图首页", ...)
  4. 进入直播间
  5. 截图首页
  6. 更新状态: write_status("running", brand, "展开小黄车...", ...)
  7. 展开小黄车，截图商品面板
  8. 更新状态: write_status("running", brand, "截图商品1/3", ...)
  9. 截图前3个商品详情（每次点击后更新 currentStep）
  10. 关闭当前品牌页
  11. completed.append(brand)
  12. 更新状态: write_status("running", "", "等待中", completed+1/total, completed)
  13. 品牌间等待（防止风控）

# 全部完成
write_status("completed", "", "全部采集完成", total+"/"+total, all_brands)
```

**write_status 函数（用 Bash 实现）：**
```bash
write_status() {
  local status=$1 brand=$2 step=$3 progress=$4
  local completed_json=$5
  SKILL_DIR=$(find /Users/smzdm/.claude/skills -maxdepth 1 -name "douyin-livestream-monitor" -type d 2>/dev/null | head -1)
  cat > "$SKILL_DIR/status.json" << JSONEOF
{
  "status": "$status",
  "currentBrand": "$brand",
  "currentStep": "$step",
  "progress": "$progress",
  "completedBrands": $completed_json,
  "errors": [],
  "startedAt": "$started_at",
  "updatedAt": "$(date '+%Y-%m-%d %H:%M:%S')"
}
JSONEOF
}
```
将 started_at 在开始时设为当前时间，后续每次调用沿用。

#### 品牌间间隔策略

**关键：每次处理完一个品牌后，关闭当前 livestream 标签页，再打开新的搜索标签页。**

- **少量品牌（≤5个）**：品牌间等待 1-2 秒即可
- **中等数量（5-10个）**：品牌间等待 3-5 秒
- **大批量（10个以上）**：品牌间等待 5-8 秒，每 5 个品牌后额外等待 15 秒
- **超大批量（50个以上）**：每 10 个品牌为一组，组间等待 30 秒

#### 多品牌时告知用户进度

每完成一个品牌，告知用户当前进度，例如：
```
[3/5] 资生堂 ✅ → 下一个：可丽金（等待 5 秒...）
```

---

### Phase 4: 搜索品牌直播间

单个品牌搜索流程：

1. **打开新标签页**：用 `browser_tabs` 创建新标签并导航到搜索URL
2. **构造搜索URL**：`https://www.douyin.com/search/{encodeURIComponent(品牌名)}?type=live`
3. **等待加载**：等待 2-3 秒让搜索结果渲染，加载完毕立即处理
4. **查看页面**：用 `browser_snapshot` 检查页面结构
5. **定位直播间结果**：在结果中找到包含"直播中"标签的卡片
6. **优先选择官方旗舰店**：有"认证徽章"的优先
7. **点击进入**：直接 navigate 到直播间 URL（比点击更可靠）

**注意**：
- 如果搜索结果为空，告知用户该品牌当前没有直播，跳过该品牌
- 如果有多个直播间，优先选择官方旗舰店或数据表现最好的
- SK2 品牌需要搜索 "SK-II" 才能出结果

---

### Phase 5: 截图直播间首页

进入直播间后：

1. 等待页面加载（2-3秒），加载完毕立即截图
2. 确认 URL 是 `live.douyin.com/xxxxx` 格式
3. 使用 `browser_take_screenshot` 全屏截图（如果超时，改用 `browser_run_code_unsafe` 中 `page.screenshot()`）
4. 通过 Bash 复制到桌面：
   ```bash
   mkdir -p ~/Desktop/{品牌名}/{YYYY-MM-DD}
   ```
5. **文件**: `~/Desktop/抖音直播间截图/{品牌名}/{YYYY-MM-DD}/01-直播间首页.png`

---

### Phase 6: 小黄车商品列表

**注意：以下点击操作有风控风险，务必按精确步骤执行**

1. **找到「全部商品」按钮**：
   - 用 `browser_snapshot` 或 `page.evaluate` 查找
   - 通常位于右侧面板底部，位置不固定，需动态检测

2. **点击「全部商品」展开列表**：
   - 使用 `browser_run_code_unsafe` 执行 JavaScript 点击（比 browser_click 更可靠，绕过 bytereplay 遮罩层）：
   ```javascript
   async (page) => {
     const result = await page.evaluate(() => {
       const all = document.querySelectorAll('*');
       for (const el of all) {
         if (el.textContent.trim() === '全部商品') {
           const r = el.getBoundingClientRect();
           if (Math.round(r.x) === 696 && el.children.length === 2) {
             el.dispatchEvent(new MouseEvent('click', {bubbles: true, view: window}));
             return 'clicked';
           }
         }
       }
       return 'not found';
     });
     return result;
   }
   ```
   - 点击后等待 1-2 秒

3. **处理协议弹窗**（如果出现）：
   ```javascript
   async (page) => {
     const result = await page.evaluate(() => {
       const els = document.querySelectorAll('*');
       for (const el of els) {
         if (el.textContent.trim() === '同意') {
           const r = el.getBoundingClientRect();
           if (r.width > 0) { el.click(); return 'agreed'; }
         }
       }
       return 'no agreement needed';
     });
     return result;
   }
   ```

4. **截图**：`02-商品面板.png`

---

### Phase 7: 前3个商品详情

使用 `[data-e2e="promotion-title"]` 定位商品元素。每次点击一个商品后，详情会以浮层形式展示在右侧。

**点击商品**：
```javascript
async (page) => {
  const result = await page.evaluate((index) => {
    const items = document.querySelectorAll('[data-e2e="promotion-title"]');
    if (items[index]) {
      items[index].dispatchEvent(new MouseEvent('click', {bubbles: true, view: window}));
      return 'clicked item ' + (index + 1) + ': ' + items[index].textContent.trim().substring(0, 40);
    }
    return 'not found';
  }, index);
  return result;
}
```

**点击后等待 1-2 秒，然后截图**：`03-商品1.png`、`04-商品2.png`、`05-商品3.png`

**关闭商品详情并返回商品列表（关键操作！）**：
不要使用 Escape 键（抖音会拦截），使用以下两步流程：

**第一步：点击「缩小」按钮**（右上角缩小图标，位置约 (821, 22)）
```javascript
async (page) => {
  // 点击右上角的缩小按钮（SVG图标），返回到商品列表
  const svgs = document.querySelectorAll('svg');
  for (const svg of svgs) {
    const r = svg.getBoundingClientRect();
    if (Math.round(r.x) === 821 && Math.round(r.y) === 22) {
      svg.dispatchEvent(new MouseEvent('click', {bubbles: true, view: window}));
      return 'minimized';
    }
  }
  return 'minimize not found';
}
```
点击后等待 1 秒，商品列表（data-e2e="promotion-title"）仍然可见，无需点击返回箭头。

**完整流程 for each product (index i = 0, 1, 2):**
```
1. 商品列表可见 → 点击商品 i（data-e2e="promotion-title"[i]）
2. 等待 1-2 秒 → 截图（03-商品1.png / 04-商品2.png / 05-商品3.png）
3. 如果 i < 2（不是最后一个商品）：
   a. 点击「缩小」按钮（SVG at (821, 22)）
   b. 等待 1 秒 → 商品列表会自动显示
4. 最后一个商品截图后，不需要关闭
```

**注意**：
- 缩小后商品列表会重新出现，直接点击下一个商品即可
- 如果商品列表没出现（罕见情况），刷新页面重新开始该品牌

---

### Phase 8: 文件整理

从 `config.json` 读取保存路径（如果不存在则使用默认路径 `~/Desktop/抖音直播间截图`）：

```bash
# 读取配置中的保存路径
SKILL_DIR=$(find /Users/smzdm/.claude/skills -maxdepth 1 -name "douyin-livestream-monitor" -type d 2>/dev/null | head -1)
SAVE_DIR="~/Desktop/抖音直播间截图"
if [ -f "$SKILL_DIR/config.json" ]; then
  CONFIG_SAVE_PATH=$(python3 -c "import json; print(json.load(open('$SKILL_DIR/config.json')).get('savePath', '$SAVE_DIR'))" 2>/dev/null)
  if [ -n "$CONFIG_SAVE_PATH" ]; then
    SAVE_DIR="$CONFIG_SAVE_PATH"
  fi
fi

mkdir -p "$SAVE_DIR/{品牌名}/{YYYY-MM-DD}"
```

**最终文件结构：**
```
~/Desktop/抖音直播间截图/{品牌名}/{YYYY-MM-DD}/
├── 01-直播间首页.png
├── 02-商品面板.png
├── 03-商品1.png
├── 04-商品2.png
└── 05-商品3.png
```

---

## 准确元素定位参考

| 目标 | 定位方法 | 备注 |
|------|---------|------|
| 登录状态 | `a[href*="/user/self"]` 是否存在 | 存在即已登录 |
| 「全部商品」按钮 | 文本匹配 `全部商品`，寻找 x≈696 且 children.length==2 的 DIV | 在小黄车面板底部 |
| 「同意」协议按钮 | 文本匹配 `同意` | 首次使用小黄车时出现 |
| 商品标题 | `[data-e2e="promotion-title"]` | 商品列表中的每个商品 |
| 关闭详情按钮 | 右上角 x>790, y<50 的小 img (cursor:pointer) | 坐标约 (840, 22) |
| 直播间搜索结果 | 搜索页面中"直播中"标签 | `type=live` 搜索 |

**重要**：优先使用 `browser_run_code_unsafe` 执行 JavaScript 来点击元素，因为 Playwright 原生的 `browser_click` 可能被抖音的 bytereplay 遮罩层拦截。对于 `page.evaluate` 和 `page.waitForTimeout`，需要包裹在 `async (page) => { ... }` 函数中。

---

## 注意事项

1. **风控处理**：遇到任何异常（验证码、白屏、连接重置），先重试1-2次，仍失败则告知用户并跳过该品牌
2. **只截前3个商品**：不要多截，节省时间
3. **品牌名使用原文**：用户说"赫莲娜"就用"赫莲娜"，不需要翻译，但 SK2 → SK-II
4. **日期格式**：`YYYY-MM-DD`
5. **登录态过期**：如果注入 cookies 后仍然未登录，引导用户重新扫码
6. **告知用户进度**：每一步都打印当前操作，让用户知道进度
7. **大批量场景**：品牌数 > 10 时，每完成 5 个品牌输出一次进度汇总，提醒用户当前采集进度
8. **标签页管理**：每个品牌处理完后关闭其标签页（`browser_tabs close`），避免标签页堆积
9. **截图超时**：如果 `browser_take_screenshot` 超时（5000ms），改用 `browser_run_code_unsafe` 中 `page.screenshot()` 方法
