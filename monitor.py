#!/usr/bin/env python3
"""抖音直播间批量监控 - 自动化采集核心
独立运行，不依赖 Claude Code。
读取 config.json 配置，执行采集并写入 status.json。
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from urllib.parse import quote

# ── 路径 ──
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SKILL_DIR, "config.json")
STATUS_PATH = os.path.join(SKILL_DIR, "status.json")
COOKIE_PATH = os.path.expanduser("~/.claude/douyin_cookies.json")
DEFAULT_SAVE_DIR = os.path.expanduser("~/Desktop/抖音直播间截图")

BRAND_ALIASES = {"SK2": "SK-II", "sk2": "SK-II"}

# ── 状态写入（同时输出到 stderr 供前端子进程捕获） ──
_started_at = ""


def write_status(status, brand="", step="", progress="", completed=None, errors=None):
    global _started_at
    if status == "running" and not _started_at:
        _started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "status": status,
        "currentBrand": brand,
        "currentStep": step,
        "progress": progress,
        "completedBrands": completed or [],
        "errors": errors or [],
        "startedAt": _started_at,
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # 也输出到控制台
    tag = f"[{data['updatedAt'].split()[1]}]"
    print(f"  {tag} [{status}] {brand} {step}")


# ── 截图辅助 ──
def ensure_dir(save_dir, brand):
    date_str = datetime.now().strftime("%Y-%m-%d")
    d = os.path.join(save_dir, brand, date_str)
    os.makedirs(d, exist_ok=True)
    return d


async def screenshot(page, filepath, label="", retries=2):
    for attempt in range(retries):
        try:
            await page.screenshot(path=filepath, timeout=60000, full_page=False)
            return True
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(2)
            else:
                print(f"  ⚠️  截图失败 {label}: {e}")
                return False
    return False


# ── 浏览器操作辅助 ──
async def click_text(page, text, check_pos=None):
    """通过 JS 点击包含指定文本的元素"""
    js = f"""
    () => {{
        const all = document.querySelectorAll('*');
        for (const el of all) {{
            if (el.textContent.trim() === '{text}') {{
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0) {{
                    {'const x=Math.round(r.x); if(x!==' + str(check_pos) + ') continue;' if check_pos else ''}
                    el.dispatchEvent(new MouseEvent('click', {{bubbles:true, view:window}}));
                    return 'clicked at ' + Math.round(r.x) + ',' + Math.round(r.y);
                }}
            }}
        }}
        return 'not found';
    }}
    """
    return await page.evaluate(js)


async def click_minimize(page):
    """点击右上角缩小按钮 (SVG at 821,22)"""
    js = """
    () => {
        const svgs = document.querySelectorAll('svg');
        for (const svg of svgs) {
            const r = svg.getBoundingClientRect();
            if (Math.round(r.x) === 821 && Math.round(r.y) === 22) {
                svg.dispatchEvent(new MouseEvent('click', {bubbles: true, view: window}));
                return 'minimized';
            }
        }
        // Fallback: try any small SVG in top-right corner
        for (const svg of svgs) {
            const r = svg.getBoundingClientRect();
            if (r.x > 780 && r.y < 50 && r.width < 30 && r.height < 30) {
                svg.dispatchEvent(new MouseEvent('click', {bubbles: true, view: window}));
                return 'minimized-fallback';
            }
        }
        return 'not found';
    }
    """
    return await page.evaluate(js)


async def click_product(page, index):
    """点击商品列表中的第 index 个商品"""
    js = """
    (index) => {
        const items = document.querySelectorAll('[data-e2e="promotion-title"]');
        if (items[index]) {
            items[index].dispatchEvent(new MouseEvent('click', {bubbles: true, view: window}));
            return items[index].textContent.trim().substring(0, 50);
        }
        return null;
    }
    """
    return await page.evaluate(js, index)


async def count_products(page):
    """统计商品数量"""
    return await page.evaluate("document.querySelectorAll('[data-e2e=\"promotion-title\"]').length")


async def find_livestream(page, brand):
    """在搜索结果中找到最优直播间 URL，返回 (url, is_certified)"""
    try:
        result = await page.evaluate("""
        () => {
            const candidates = [];
            const all = document.querySelectorAll('a');
            for (const a of all) {
                const href = a.getAttribute('href') || '';
                if (!href.includes('live.douyin.com') || href.includes('action_type')) continue;

                // 向上找 5 层，检查是否有 直播中 标签和 认证徽章
                let el = a;
                let hasLive = false, hasBadge = false;
                for (let i = 0; i < 5; i++) {
                    if (!el) break;
                    const txt = el.textContent || '';
                    if (txt.includes('直播中')) hasLive = true;
                    if (txt.includes('认证徽章')) hasBadge = true;
                    el = el.parentElement;
                }

                // 提取干净的 URL
                let url = href;
                if (url.startsWith('//')) url = 'https:' + url;
                // 去掉 action_type 参数
                const cleanUrl = url.split('?')[0] + '?&from_search=true';

                if (hasLive) {
                    candidates.push({ url: cleanUrl, badge: hasBadge });
                }
            }

            if (candidates.length === 0) return null;

            // 优先选择有认证徽章的
            const certified = candidates.filter(c => c.badge);
            const chosen = certified.length > 0 ? certified[0] : candidates[0];
            return JSON.stringify(chosen);
        }
        """)

        if result:
            data = json.loads(result)
            return data["url"], data["badge"]
        return None, False
    except Exception as e:
        print(f"  ⚠️  搜索解析失败: {e}")
        return None, False


async def wait_for_page_load(page, timeout=8):
    """等待页面稳定加载"""
    for i in range(timeout):
        await asyncio.sleep(1)
        # 简单检查：页面不再有大量 loading 状态
        ready = await page.evaluate("""
        () => {
            return {
                url: window.location.href,
                title: document.title,
                bodyReady: document.body ? document.body.children.length > 0 : false
            };
        }
        """)
        if ready.get("bodyReady") and "live.douyin.com" in ready.get("url", ""):
            # 额外等一会让直播流加载
            if i >= 3:
                break


# ── 处理单个品牌 ──
async def process_brand(browser_context, brand, save_dir, completed_list, total):
    """处理单个品牌的完整流程"""
    brand_clean = brand.strip()
    # 别名映射
    display_brand = brand_clean
    search_brand = BRAND_ALIASES.get(brand_clean, brand_clean)

    write_status("running", display_brand, "搜索直播间...",
                 f"{len(completed_list)+1}/{total}", completed_list)

    # 创建新标签页
    page = await browser_context.new_page()

    try:
        # ── 搜索 ──
        search_url = f"https://www.douyin.com/search/{quote(search_brand)}?type=live"
        await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(6)

        # 查找直播间
        live_url, is_certified = await find_livestream(page, search_brand)

        if not live_url:
            write_status("running", display_brand, "未找到直播间，跳过",
                         f"{len(completed_list)+1}/{total}", completed_list)
            print(f"  ⚠️  {display_brand}: 当前没有直播")
            completed_list.append(f"{display_brand}(无直播)")
            return

        tag = "官方认证" if is_certified else "普通"
        print(f"  → {display_brand}: 找到直播间 [{tag}]")

        # ── 进入直播间 ──
        write_status("running", display_brand, "进入直播间...",
                     f"{len(completed_list)+1}/{total}", completed_list)

        await page.goto(live_url, timeout=60000, wait_until="domcontentloaded")
        await wait_for_page_load(page, 8)

        # 确认进入了直播间
        current_url = page.url
        if "live.douyin.com" not in current_url:
            print(f"  ⚠️  {display_brand}: 未成功进入直播间 (URL={current_url})")
            completed_list.append(f"{display_brand}(进入失败)")
            return

        # ── 截图首页 ──
        write_status("running", display_brand, "截图直播间首页...",
                     f"{len(completed_list)+1}/{total}", completed_list)

        brand_dir = ensure_dir(save_dir, display_brand)
        path_home = os.path.join(brand_dir, "01-直播间首页.png")
        ok = await screenshot(page, path_home, "首页")
        if not ok:
            print(f"  ⚠️  {display_brand}: 首页截图失败，仍继续")

        # ── 展开商品面板 ──
        write_status("running", display_brand, "展开小黄车...",
                     f"{len(completed_list)+1}/{total}", completed_list)

        panel_clicked = False
        for attempt in range(3):
            result = await click_text(page, "全部商品", check_pos=696)
            if "clicked" in result:
                panel_clicked = True
                break
            await asyncio.sleep(2)

        if not panel_clicked:
            # 尝试不用坐标过滤
            for attempt in range(2):
                result = await page.evaluate("""
                () => {
                    const all = document.querySelectorAll('*');
                    for (const el of all) {
                        if (el.textContent.trim() === '全部商品') {
                            const r = el.getBoundingClientRect();
                            if (r.width > 0 && r.height > 0) {
                                el.dispatchEvent(new MouseEvent('click', {bubbles:true, view:window}));
                                return 'clicked';
                            }
                        }
                    }
                    return 'not found';
                }
                """)
                if "clicked" in result:
                    panel_clicked = True
                    break
                await asyncio.sleep(2)

        if not panel_clicked:
            print(f"  ⚠️  {display_brand}: 未找到全部商品按钮")

        await asyncio.sleep(3)

        # ── 截图商品面板 ──
        write_status("running", display_brand, "截图商品面板...",
                     f"{len(completed_list)+1}/{total}", completed_list)
        path_panel = os.path.join(brand_dir, "02-商品面板.png")
        await screenshot(page, path_panel, "商品面板")

        # ── 统计商品数量 ──
        prod_count = await count_products(page)
        print(f"  → {display_brand}: 共 {prod_count} 个商品")
        n_to_capture = min(3, prod_count)

        # ── 截图前 N 个商品 ──
        for i in range(n_to_capture):
            label = f"商品{i+1}"
            write_status("running", display_brand, f"截图{label}...",
                         f"{len(completed_list)+1}/{total}", completed_list)

            # 点击商品
            prod_name = await click_product(page, i)
            if prod_name is None:
                print(f"  ⚠️  {display_brand}: 商品{i+1} 不存在")
                break

            # 等待详情加载
            await asyncio.sleep(3)

            # 截图
            path_prod = os.path.join(brand_dir, f"03-商品{i+1}.png" if i == 0 else
                                     (f"04-商品{i+1}.png" if i == 1 else f"05-商品{i+1}.png"))
            await screenshot(page, path_prod, label)

            # 如果不是最后一个商品，点击缩小按钮返回
            if i < n_to_capture - 1:
                await asyncio.sleep(1)
                min_result = await click_minimize(page)
                if "minimized" in min_result:
                    await asyncio.sleep(2)
                else:
                    print(f"  ⚠️  {display_brand}: 缩小按钮未找到，尝试刷新")
                    await page.goto(live_url, timeout=60000, wait_until="domcontentloaded")
                    await asyncio.sleep(5)
                    # 重新打开全部商品
                    for _ in range(3):
                        r = await click_text(page, "全部商品")
                        if "clicked" in r:
                            break
                        await asyncio.sleep(2)
                    await asyncio.sleep(3)

        completed_list.append(display_brand)
        write_status("running", "", f"{display_brand} ✅ 完成",
                     f"{len(completed_list)}/{total}", completed_list)
        print(f"  ✅ {display_brand} 完成")

    except Exception as e:
        err_msg = f"{display_brand}: {str(e)[:80]}"
        print(f"  ❌ 错误: {err_msg}")
        completed_list.append(f"{display_brand}(出错)")
        # 更新 errors
        current_errors = []
        if os.path.exists(STATUS_PATH):
            try:
                with open(STATUS_PATH) as f:
                    s = json.load(f)
                    current_errors = s.get("errors", [])
            except:
                pass
        current_errors.append(err_msg)
        write_status("running", display_brand, "出错",
                     f"{len(completed_list)}/{total}", completed_list, current_errors)
    finally:
        await page.close()


# ── 主流程 ──
async def main():
    global _started_at

    # ── 检查并安装 Playwright ──
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ 需要安装 Playwright: pip install playwright && playwright install chromium")
        write_status("error", "依赖缺失", "请运行: pip install playwright && playwright install chromium",
                     "", [], ["Playwright 未安装"])
        sys.exit(1)

    # ── 读取配置 ──
    if not os.path.exists(CONFIG_PATH):
        write_status("error", "未找到配置", "请先在前端面板中保存配置", "", [], ["config.json 不存在"])
        print("❌ 未找到 config.json，请先在前端配置面板中保存配置")
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    brands = config.get("brands", [])
    save_dir = config.get("savePath", DEFAULT_SAVE_DIR)
    save_dir = os.path.expanduser(save_dir)

    if not brands:
        write_status("error", "品牌列表为空", "请先配置品牌", "", [], ["品牌列表为空"])
        print("❌ 品牌列表为空")
        sys.exit(1)

    total = len(brands)
    print(f"\n🎯 共 {total} 个品牌: {', '.join(brands)}")
    print(f"📁 保存到: {save_dir}")

    # ── 初始化状态 ──
    _started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_status("running", "", "启动浏览器...", f"0/{total}", [])

    # ── 启动浏览器 ──
    try:
        async with async_playwright() as p:
            # 优先使用系统 Chrome（避免滑块验证）
            # macOS Chrome 默认路径
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ]
            use_chrome = any(os.path.exists(c) for c in chrome_paths)

            if use_chrome:
                print("🍎 使用系统 Chrome（降低风控概率）")
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=os.path.expanduser("~/.claude/douyin-browser-data"),
                    headless=False,
                    executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-web-security",
                    ],
                    viewport={"width": 1280, "height": 720},
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                )
            else:
                print("🤖 使用 Playwright 内置 Chromium")
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=os.path.expanduser("~/.claude/douyin-browser-data"),
                    headless=False,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-web-security",
                    ],
                    viewport={"width": 1280, "height": 720},
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                )

            # 注入反检测脚本（更全面的指纹伪装）
            await browser.add_init_script("""
                // 隐藏 webdriver 标志
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                // 模拟 Chrome 环境
                window.chrome = { runtime: {} };
                // 模拟 plugins
                Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
                // 模拟 languages
                Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
                // 覆盖 permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (params) => (
                    params.name === 'notifications' ? Promise.resolve({state: 'denied'}) : originalQuery(params)
                );
            """)

            # ── 加载已保存的 cookies ──
            if os.path.exists(COOKIE_PATH):
                try:
                    with open(COOKIE_PATH, "r") as f:
                        cookies = json.load(f)
                    await browser.add_cookies(cookies)
                    print(f"🍪 已加载 {len(cookies)} 个 cookies")
                except Exception as e:
                    print(f"  ⚠️  Cookie 加载失败: {e}")

            # ── 打开首页确认登录 ──
            page = browser.pages[0] if browser.pages else await browser.new_page()

            # 抖音首页可能加载较慢，retry + 长超时
            login_ok = False
            for attempt in range(3):
                try:
                    await page.goto(
                        "https://www.douyin.com",
                        timeout=60000,
                        wait_until="load",
                    )
                    await asyncio.sleep(3)
                    login_ok = True
                    break
                except Exception as e:
                    print(f"  ⚠️  首页加载尝试 {attempt+1}/3 失败: {str(e)[:60]}")
                    if attempt < 2:
                        await asyncio.sleep(5)

            if not login_ok:
                print("❌ 抖音首页连续加载失败，请检查网络")
                write_status("error", "网络错误", "抖音首页无法加载", "", [], ["首页加载超时"])
                return

            # 检查登录状态
            logged_in = await page.evaluate("""
                () => !!document.querySelector('a[href*="/user/self"]')
            """)

            if not logged_in:
                print("⚠️  未检测到登录状态，请在打开的浏览器窗口中手动扫码登录。")
                print(f"   浏览器会自动打开抖音首页，扫码后等待程序检测...")
                write_status("running", "", "⚠️ 请在浏览器中扫码登录抖音", f"0/{total}", [])
                # 等待 120 秒，每 2 秒检测一次
                WAIT_SECONDS = 120
                for i in range(WAIT_SECONDS):
                    await asyncio.sleep(1)
                    if i % 5 == 0:
                        remain = WAIT_SECONDS - i
                        print(f"   等待登录中... 剩余 {remain} 秒")
                        write_status("running", "",
                                     f"等待扫码登录 ({remain}s)...", f"0/{total}", [])
                    logged_in = await page.evaluate("""
                        () => !!document.querySelector('a[href*="/user/self"]')
                    """)
                    if logged_in:
                        print("✅ 登录成功！")
                        write_status("running", "", "登录成功，开始采集...", f"0/{total}", [])
                        await asyncio.sleep(2)
                        break

                if not logged_in:
                    print("❌ 登录超时，请手动登录后重新运行")
                    write_status("error", "登录超时", "请扫码登录后重试", "", [],
                                 ["登录超时"])
                    return

            # ── 处理每个品牌 ──
            completed = []
            for idx, brand in enumerate(brands):
                print(f"\n{'='*40}")
                print(f"[{idx+1}/{total}] {brand}")
                print(f"{'='*40}")
                await process_brand(browser, brand, save_dir, completed, total)

                # 品牌间等待（防风控）
                if idx < total - 1:
                    wait_time = 7 if total <= 10 else 10
                    if (idx + 1) % 3 == 0:
                        wait_time += 10
                        print(f"  ⏸️  连续处理 3 个品牌，额外等待 10 秒...")
                    print(f"  ⏳ 等待 {wait_time} 秒防止风控...")
                    write_status("running", "", f"等待 {wait_time}s...",
                                 f"{len(completed)}/{total}", completed)
                    await asyncio.sleep(wait_time)

            # ── 全部完成 ──
            write_status("completed", "", "全部采集完成！",
                         f"{total}/{total}", completed)
            print(f"\n{'='*40}")
            print(f"✅ 全部完成！共处理 {total} 个品牌")
            print(f"📁 截图保存在: {save_dir}")
            print(f"{'='*40}")

            # 保存 cookies 供后续使用
            try:
                cookies = await browser.cookies()
                with open(COOKIE_PATH, "w") as f:
                    json.dump(cookies, f)
            except:
                pass

    except Exception as e:
        print(f"\n❌ 致命错误: {e}")
        write_status("error", "致命错误", str(e)[:100], "", [], [str(e)[:200]])


if __name__ == "__main__":
    asyncio.run(main())
