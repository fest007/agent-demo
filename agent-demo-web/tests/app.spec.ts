/**
 * 前端 UI 测试用例（Playwright）
 *
 * 测试策略：
 * - UI 交互测试（导航、输入、样式）：直接测试真实前端
 * - 对话流程测试：调用真实后端 API（不 mock），验证端到端链路
 * - 确定性行为测试（错误处理、特定情绪）：保留 mock 以保证可重复性
 *
 * 前置条件：
 * - 前端 dev server 运行在 localhost:3000
 * - 后端 API 运行在 localhost:8000
 */
import { test, expect, type Page } from "@playwright/test";

// ============================================================
// 辅助函数
// ============================================================

/** 获取可见的输入框（排除 Ant Design 隐藏的 textarea） */
function getInput(page: Page) {
  return page.locator('textarea:visible');
}

/** 点击"开始新对话"按钮创建一个新会话 */
async function startNewSession(page: Page) {
  const newChatBtn = page.locator('button:has-text("开始新对话")');
  if (await newChatBtn.isVisible().catch(() => false)) {
    await newChatBtn.click();
    // 等待会话创建完成（输入框出现）
    await getInput(page).waitFor({ state: "visible", timeout: 5000 });
    await page.waitForTimeout(500);
  }
}

/** 发送一条消息并等待 Agent 回复出现（流式完成） */
async function sendAndWaitForResponse(page: Page, message: string) {
  // 确保有会话
  await startNewSession(page);
  const input = getInput(page);
  await input.fill(message);
  await page.locator('button:has-text("发送")').click();
  // 等待加载状态结束（Spin 消失 = 流式完成）
  await page.locator(".ant-spin").last().waitFor({ state: "hidden", timeout: 30000 }).catch(() => {});
  // 再等一小段时间让 React 更新 DOM
  await page.waitForTimeout(300);
}

/** 构建 SSE 格式响应体（用于 mock 测试） */
function buildSseBody(events: Array<{ type: string; data: string | object }>) {
  return events
    .map((e) => `event: ${e.type}\ndata: ${JSON.stringify(e.data)}\n`)
    .join("\n");
}

/** 拦截 /api/chat/stream，返回模拟 SSE 事件流（用于 mock 测试） */
async function mockStreamResponse(
  page: Page,
  events: Array<{ type: string; data: string | object }>
) {
  await page.route("**/api/chat/stream", (route) => {
    route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: buildSseBody(events),
    });
  });
}

// ============================================================
// 测试用例
// ============================================================

test.describe("页面初始化", () => {
  test("首页加载，显示侧边栏和欢迎界面", async ({ page }) => {
    await page.goto("/");

    // 侧边栏标题
    await expect(page.locator("h4", { hasText: "智能 Agent" })).toBeVisible();
    // 侧边栏菜单项
    await expect(page.locator(".ant-menu-item", { hasText: "对话" })).toBeVisible();
    await expect(page.locator(".ant-menu-item", { hasText: "知识库" })).toBeVisible();
    await expect(page.locator(".ant-menu-item", { hasText: "技能" })).toBeVisible();
    await expect(page.locator(".ant-menu-item", { hasText: "工具" })).toBeVisible();
    await expect(page.locator(".ant-menu-item", { hasText: "设置" })).toBeVisible();
    // 欢迎界面（无会话时）
    await expect(page.locator("text=欢迎使用智能助手")).toBeVisible();
    await expect(page.locator('button:has-text("开始新对话")')).toBeVisible();
  });

  test("默认选中对话菜单", async ({ page }) => {
    await page.goto("/");
    const selected = page.locator(".ant-menu-item-selected");
    await expect(selected).toHaveText("对话");
  });
});

test.describe("侧边栏导航", () => {
  test("点击知识库，切换到知识库页面", async ({ page }) => {
    await page.goto("/");
    await page.locator(".ant-menu-item", { hasText: "知识库" }).click();
    await expect(page.locator("h2", { hasText: "知识库管理" })).toBeVisible();
    await expect(page.locator("text=添加知识")).toBeVisible();
  });

  test("点击技能，切换到技能页面", async ({ page }) => {
    await page.goto("/");
    await page.locator(".ant-menu-item", { hasText: "技能" }).click();
    await expect(page.locator("h2", { hasText: "技能管理" })).toBeVisible();
    await expect(page.locator('button:has-text("AI 生成技能")')).toBeVisible();
  });

  test("点击工具，切换到工具页面", async ({ page }) => {
    await page.goto("/");
    await page.locator(".ant-menu-item", { hasText: "工具" }).click();
    await expect(page.locator("h2", { hasText: "工具管理" })).toBeVisible();
  });

  test("点击设置，切换到设置页面", async ({ page }) => {
    await page.goto("/");
    await page.locator(".ant-menu-item", { hasText: "设置" }).click();
    await expect(page.locator("h2", { hasText: "设置" })).toBeVisible();
    await expect(page.locator("text=模型")).toBeVisible();
    await expect(page.locator("text=TTS 引擎")).toBeVisible();
  });

  test("从其他页面点击对话，回到对话页面", async ({ page }) => {
    await page.goto("/");
    await page.locator(".ant-menu-item", { hasText: "设置" }).click();
    await expect(page.locator("h2", { hasText: "设置" })).toBeVisible();

    await page.locator(".ant-menu-item", { hasText: "对话" }).click();
    await expect(page.locator("text=欢迎使用智能助手")).toBeVisible();
  });
});

test.describe("对话流程 - 真实 API", () => {
  test("新建对话并发送消息", async ({ page }) => {
    await page.goto("/");
    await startNewSession(page);

    // 发送消息
    const input = getInput(page);
    await input.fill("你好");
    await page.locator('button:has-text("发送")').click();

    // 用户消息显示
    await expect(page.locator("text=你好").first()).toBeVisible();
    // 等待 Agent 回复
    await page.locator(".ant-spin").last().waitFor({ state: "hidden", timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(2000);

    // 至少应有用户和 Agent 两条消息
    const messageContainers = page.locator('[style*="justify-content: flex-end"], [style*="justify-content: flex-start"]');
    const count = await messageContainers.count();
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test("发送消息后输入框清空", async ({ page }) => {
    await page.goto("/");
    await startNewSession(page);

    const input = getInput(page);
    await input.fill("测试消息");
    await page.locator('button:has-text("发送")').click();

    // 输入框应立即清空（不等响应完成）
    await expect(input).toHaveValue("");
  });

  test("Agent 回复后显示情绪标识", async ({ page }) => {
    await page.goto("/");
    await sendAndWaitForResponse(page, "你好，今天心情不错");
    await page.waitForTimeout(2000);

    // 情绪标识应该出现（ant-tag 元素）
    const tags = page.locator(".ant-tag");
    const tagCount = await tags.count();
    expect(tagCount).toBeGreaterThanOrEqual(1);
  });

  test("语音播放按钮在 Agent 回复后显示", async ({ page }) => {
    await page.goto("/");
    await sendAndWaitForResponse(page, "你好");
    await page.waitForTimeout(2000);

    // VoicePlayer 按钮应该出现
    const agentArea = page.locator('[style*="justify-content: flex-start"]');
    const buttons = agentArea.locator("button");
    const btnCount = await buttons.count();
    expect(btnCount).toBeGreaterThanOrEqual(1);
  });
});

test.describe("消息气泡样式", () => {
  test("用户消息右对齐，Agent 消息左对齐（真实 API）", async ({ page }) => {
    await page.goto("/");
    await sendAndWaitForResponse(page, "你好");
    await page.waitForTimeout(2000);

    // 用户消息容器应有 justify-content: flex-end
    const userBubble = page.locator('[style*="justify-content: flex-end"]').first();
    await expect(userBubble).toBeVisible();

    // Agent 消息容器应有 justify-content: flex-start
    const agentBubble = page.locator('[style*="justify-content: flex-start"]').first();
    await expect(agentBubble).toBeVisible();
  });

  test("消息发送后显示用户和 Agent 头像", async ({ page }) => {
    await page.goto("/");
    await sendAndWaitForResponse(page, "你好");
    await page.waitForTimeout(2000);

    // 应该有两个头像（用户 + Agent）
    const avatars = page.locator(".ant-avatar");
    const count = await avatars.count();
    expect(count).toBeGreaterThanOrEqual(2);
  });
});

test.describe("对话流程 - Mock（确定性行为）", () => {
  test("情绪标识正确显示特定情绪", async ({ page }) => {
    await page.goto("/");
    await startNewSession(page);
    await mockStreamResponse(page, [
      { type: "emotion", data: "happy" },
      { type: "token", data: "测试回复" },
      { type: "done", data: "" },
    ]);

    await sendAndWaitForResponse(page, "讲个笑话");
    await expect(page.locator(".ant-tag", { hasText: "开心" })).toBeVisible();
  });

  test("工具调用在消息中展示", async ({ page }) => {
    await page.goto("/");
    await startNewSession(page);
    await mockStreamResponse(page, [
      { type: "emotion", data: "neutral" },
      { type: "tool_start", data: { name: "web_search", input: '{"query":"天气"}' } },
      { type: "token", data: "今天天气不错" },
      { type: "done", data: "" },
    ]);

    await sendAndWaitForResponse(page, "今天天气怎么样");
    await expect(page.locator("text=web_search")).toBeVisible();
  });

  test("加载状态：发送后显示加载指示器", async ({ page }) => {
    await page.goto("/");
    await startNewSession(page);
    await page.route("**/api/chat/stream", async (route) => {
      await new Promise((r) => setTimeout(r, 500));
      route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: buildSseBody([
          { type: "emotion", data: "neutral" },
          { type: "token", data: "回复" },
          { type: "done", data: "" },
        ]),
      });
    });

    const input = getInput(page);
    await input.fill("测试");
    await page.locator('button:has-text("发送")').click();

    // 加载指示器应该出现
    await expect(page.locator(".ant-spin")).toBeVisible();
    // 等待响应完成
    await expect(page.locator("text=回复")).toBeVisible();
  });
});

test.describe("输入栏交互", () => {
  test("Enter 键发送消息（真实 API）", async ({ page }) => {
    await page.goto("/");
    await startNewSession(page);

    const input = getInput(page);
    await input.fill("Enter测试");
    await input.press("Enter");

    // 用户消息显示
    await expect(page.locator("text=Enter测试")).toBeVisible();
    // 等待 Agent 回复
    await page.waitForTimeout(5000);
    // 消息列表应有至少两条消息
    const messageContainers = page.locator('[style*="justify-content: flex-end"], [style*="justify-content: flex-start"]');
    const count = await messageContainers.count();
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test("Shift+Enter 不发送，而是换行", async ({ page }) => {
    await page.goto("/");
    await startNewSession(page);

    const input = getInput(page);
    await input.fill("第一行");
    await input.press("Shift+Enter");
    await input.type("第二行");

    // 输入框应包含两行文本，不应触发发送
    await expect(input).toHaveValue("第一行\n第二行");
    // 不应有 Agent 回复（只有欢迎页或空状态）
    const agentBubbles = page.locator('[style*="justify-content: flex-start"]');
    const count = await agentBubbles.count();
    expect(count).toBe(0);
  });

  test("空消息不发送", async ({ page }) => {
    await page.goto("/");
    await startNewSession(page);

    const input = getInput(page);
    await input.fill("   ");
    await page.locator('button:has-text("发送")').click();

    // 不应有 Agent 回复
    const agentBubbles = page.locator('[style*="justify-content: flex-start"]');
    const count = await agentBubbles.count();
    expect(count).toBe(0);
  });

  test("加载中时发送按钮显示加载状态", async ({ page }) => {
    await page.goto("/");
    await startNewSession(page);
    await page.route("**/api/chat/stream", async (route) => {
      await new Promise(() => {}); // 永不完成
    });

    const input = getInput(page);
    await input.fill("测试");
    await page.locator('button:has-text("发送")').click();

    await expect(page.locator('button:has-text("发送")')).toHaveClass(/ant-btn-loading/);
  });
});

test.describe("多轮对话", () => {
  test("连续发送多条消息，所有消息都显示", async ({ page }) => {
    await page.goto("/");
    await startNewSession(page);
    let callCount = 0;
    await page.route("**/api/chat/stream", (route) => {
      callCount++;
      route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: buildSseBody([
          { type: "emotion", data: "neutral" },
          { type: "token", data: `第${callCount}次回复` },
          { type: "done", data: "" },
        ]),
      });
    });

    await sendAndWaitForResponse(page, "第一条");
    await expect(page.locator("text=第1次回复")).toBeVisible();

    await sendAndWaitForResponse(page, "第二条");
    await expect(page.locator("text=第2次回复")).toBeVisible();

    await expect(page.locator("text=第一条")).toBeVisible();
    await expect(page.locator("text=第二条")).toBeVisible();
  });
});

test.describe("错误处理", () => {
  test("流式请求失败时显示错误信息", async ({ page }) => {
    await page.goto("/");
    await startNewSession(page);
    await page.route("**/api/chat/stream", (route) => {
      route.abort("failed");
    });

    await sendAndWaitForResponse(page, "测试错误");
    await expect(page.locator("p", { hasText: "错误" })).toBeVisible();
  });
});

test.describe("侧边栏折叠", () => {
  test("点击折叠按钮，侧边栏折叠", async ({ page }) => {
    await page.goto("/");

    // 组件使用 trigger={null}，自定义按钮在侧边栏底部
    const collapseBtn = page.locator(".ant-layout-sider .ant-btn-text").last();
    await collapseBtn.click();

    const sider = page.locator(".ant-layout-sider");
    await expect(sider).toHaveClass(/ant-layout-sider-collapsed/);
  });
});

test.describe("会话管理", () => {
  test("新建对话按钮创建会话并显示输入框", async ({ page }) => {
    await page.goto("/");
    await startNewSession(page);

    // 输入框和发送按钮应该出现
    await expect(getInput(page)).toBeVisible();
    await expect(page.locator('button:has-text("发送")')).toBeVisible();
  });

  test("会话列表显示在侧边栏", async ({ page }) => {
    await page.goto("/");
    await startNewSession(page);

    // 侧边栏应显示"新对话"按钮和会话列表
    await expect(page.locator('button:has-text("新对话")')).toBeVisible();
  });
});
