import { type Page, expect, test } from "@playwright/test";

const RAM = { name: "Amy Nguyen", scope: "New York Metro territory" };
const DIRECTOR = { name: "Jennifer Walsh", scope: "Northeast region" };

async function signInAs(page: Page, name: string) {
  await page.goto("/login");
  await page.getByRole("button", { name: new RegExp(name) }).click();
  await expect(page).toHaveURL("/");
  await expect(page.getByText(/Good (morning|afternoon|evening)/)).toBeVisible();
}

test("unauthenticated visits are sent to the login page", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
});

test("login page lists the demo accounts grouped by role", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByText("Demo accounts")).toBeVisible();
  const section = page.locator("section");
  await expect(section.getByText("Executives")).toBeVisible();
  // 2 execs + 6 directors + 15 RAMs from the seeded users table
  await expect(section.getByRole("button")).toHaveCount(23);
  await expect(page.getByText("novapharma-demo")).toBeVisible();
});

test("one-click sign-in shows the user's data scope and pricing access", async ({ page }) => {
  await signInAs(page, RAM.name);
  await expect(page.getByText(RAM.scope).first()).toBeVisible();
  await expect(page.getByText(/pricing \(WAC\) isn't available/)).toBeVisible();
  await expect(page.locator("aside").getByText(RAM.name)).toBeVisible();
});

test("theme toggle cycles system -> light -> dark and survives a reload", async ({ page }) => {
  await signInAs(page, RAM.name);
  const toggle = page.getByTitle(/^Theme:/).first();
  const theme = () => page.evaluate(() => document.documentElement.dataset.theme ?? "system");
  expect(await theme()).toBe("system");
  await toggle.click();
  expect(await theme()).toBe("light");
  await toggle.click();
  expect(await theme()).toBe("dark");
  await page.reload();
  expect(await theme()).toBe("dark"); // applied before paint from localStorage
  await page.getByTitle(/^Theme:/).first().click(); // back to system for other tests
});

test("on a phone the sidebar starts closed and opens as an overlay", async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await signInAs(page, RAM.name);
  const sidebar = page.locator("aside");
  await expect(sidebar).not.toBeInViewport();
  await page.getByTitle("Open sidebar").click();
  await expect(sidebar).toBeInViewport();
  await context.close();
});

test("sign out returns to the login page", async ({ page }) => {
  await signInAs(page, RAM.name);
  await page.getByTitle("Sign out").click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/); // the session cookie is gone
});

test.describe("live (real LLM calls)", () => {
  test.skip(!process.env.E2E_LIVE, "set E2E_LIVE=1 to run against the real models");
  test.setTimeout(180_000);

  test("ask, stream, reopen, rename and delete a chat", async ({ page }) => {
    await signInAs(page, DIRECTOR.name);
    await page.getByPlaceholder(/Ask about/).fill("Compare territories in my region by total volume");
    await page.keyboard.press("Enter");

    await expect(page.getByRole("status")).toBeVisible(); // "Understanding your question..."
    await expect(page).toHaveURL(/\/chat\/[0-9a-f-]{36}$/, { timeout: 60_000 }); // new chat got its URL
    const table = page.getByRole("button", { name: "table", exact: true });
    await expect(table).toBeVisible({ timeout: 150_000 });
    await table.click();
    await expect(page.getByRole("cell", { name: "New England" })).toBeVisible(); // Director scope
    await expect(page.getByRole("cell", { name: "Texas" })).toHaveCount(0); // out of scope

    const url = page.url();
    await page.reload();
    await expect(page).toHaveURL(url);
    await expect(page.getByText("Compare territories in my region by total volume")).toBeVisible();

    const row = page.locator("aside nav .group").first();
    await row.hover();
    await row.getByTitle("Rename").click();
    const input = page.locator("aside nav input");
    await input.fill("E2E renamed chat");
    await input.press("Enter");
    await expect(page.locator("aside").getByText("E2E renamed chat")).toBeVisible();

    const renamed = page.locator("aside nav .group", { hasText: "E2E renamed chat" });
    await renamed.hover();
    await renamed.getByTitle("Delete").click();
    await page.getByRole("button", { name: "Delete", exact: true }).click();
    await expect(page.locator("aside").getByText("E2E renamed chat")).toHaveCount(0);
    await expect(page).toHaveURL("/");
  });
});
