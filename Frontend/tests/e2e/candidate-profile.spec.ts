import { expect, test, type Page } from "@playwright/test";

const routes = [
  ["/", "Good morning, Arjun!"],
  ["/resume", "Upload your resume"],
  ["/skill-gap", "Your skill gap"],
  ["/career-readiness", "Career readiness"],
  ["/learning-roadmap", "Learning roadmap"],
  ["/career-assistant", "Career assistant"],
] as const;

const validResume = {
  name: "candidate-phase31.pdf",
  mimeType: "application/pdf",
  buffer: Buffer.from("local regression fixture"),
};

async function gotoReady(page: Page, route: string) {
  await page.goto(route);
  await page.locator("main").waitFor();
  await page.waitForLoadState("networkidle").catch(() => undefined);
}

test("all six routes render at desktop and mobile widths without horizontal overflow", async ({ page }) => {
  for (const [route, heading] of routes) {
    await page.setViewportSize({ width: 1440, height: 900 });
    await gotoReady(page, route);
    await expect(page.locator("main h1")).toHaveText(heading);
    expect(await page.evaluate(() => document.documentElement.scrollWidth))
      .toBeLessThanOrEqual(await page.evaluate(() => document.documentElement.clientWidth));

    await page.setViewportSize({ width: 390, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth))
      .toBeLessThanOrEqual(await page.evaluate(() => document.documentElement.clientWidth));
  }
});

test("resume metadata survives client navigation, invalid replacement, preview, and reset", async ({ page }) => {
  await gotoReady(page, "/resume");
  await expect(page.getByText("Drop your resume here", { exact: true })).toBeVisible();

  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(validResume);
  await expect(page.getByText(validResume.name, { exact: true })).toBeVisible();
  await expect(page.getByText(/1 KB/)).toBeVisible();
  await expect(page.getByText(/Ready for sample preview/)).toBeVisible();

  await page.getByRole("link", { name: "Skill Gap", exact: true }).click();
  await expect(page.getByText("9 skills", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Cloud Fundamentals" }).first()).toBeVisible();
  await page.getByRole("link", { name: "Resume", exact: true }).click();
  await expect(page.getByText(validResume.name, { exact: true })).toBeVisible();
  await expect(page.getByText(/1 KB/)).toBeVisible();
  await expect(page.getByText(/Reselect the file to continue/)).toBeVisible();

  await fileInput.setInputFiles({
    name: "unsupported.png",
    mimeType: "image/png",
    buffer: Buffer.from("not a resume"),
  });
  await expect(page.getByText(/This file type is not supported/)).toHaveAttribute("role", "alert");
  await expect(page.getByText(validResume.name, { exact: true })).toBeVisible();
  await expect(page.getByText(/1 KB/)).toBeVisible();

  await fileInput.setInputFiles({ ...validResume, name: "candidate-reselected.pdf" });
  await page.getByRole("button", { name: "Preview sample results" }).click();
  await expect(page.getByText("Sample preview ready", { exact: true })).toBeVisible();
  await expect(page.getByText(/Illustrative results for candidate-reselected\.pdf/)).toBeVisible();
  await expect(page.getByText(/This preview uses illustrative sample values only/)).toBeVisible();
  await expect(page.getByText(/not uploaded or analyzed/)).toBeVisible();

  await page.getByRole("link", { name: "Skill Gap", exact: true }).click();
  await page.getByRole("link", { name: "Resume", exact: true }).click();
  await expect(page.getByText("Sample preview ready", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Upload another" }).click();
  await expect(page.getByText("Drop your resume here", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Skill Gap", exact: true }).click();
  await page.getByRole("link", { name: "Resume", exact: true }).click();
  await expect(page.getByText("Drop your resume here", { exact: true })).toBeVisible();
});

test("roadmap progress is shared with Dashboard and resets on refresh", async ({ page }) => {
  await gotoReady(page, "/learning-roadmap");
  const roadmapProgress = page.getByRole("progressbar", { name: "Overall roadmap progress" });
  await expect(roadmapProgress).toHaveAttribute("aria-valuenow", "23");

  await page.getByRole("button", { name: "Mark Type-safe application features complete" }).click();
  await expect(roadmapProgress).toHaveAttribute("aria-valuenow", "28");
  await expect(page.getByRole("button", { name: "Mark Type-safe application features complete" })).toHaveCount(0);

  await page.getByRole("button", { name: "Mark Routing and server rendering complete" }).click();
  await expect(roadmapProgress).toHaveAttribute("aria-valuenow", "38");
  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  await expect(page.getByRole("progressbar", { name: "Sample learning roadmap progress" })).toHaveAttribute("aria-valuenow", "38");
  await page.getByRole("link", { name: "Learning Roadmap", exact: true }).click();
  await expect(roadmapProgress).toHaveAttribute("aria-valuenow", "38");

  await page.reload();
  await expect(page.getByRole("progressbar", { name: "Overall roadmap progress" })).toHaveAttribute("aria-valuenow", "23");
});

test("sample insights remain consistent and assistant replies without a service", async ({ page }) => {
  const serviceRequests: string[] = [];
  page.on("request", (request) => {
    if (/\/api\/|openai|azure|anthropic/i.test(request.url())) serviceRequests.push(request.url());
  });

  await gotoReady(page, "/");
  await expect(page.getByText("72", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Career Readiness", exact: true }).click();
  await expect(page.locator("#overall-score-heading")).toContainText("72");
  await expect(page.getByRole("progressbar", { name: "Interview preparation readiness" })).toHaveAttribute("aria-valuenow", "61");

  await page.getByRole("link", { name: "AI Career Assistant New" }).click();
  await page.getByRole("button", { name: "Which skill gap should I focus on first?" }).click();
  await page.getByRole("button", { name: "Which skill gap should I focus on first?" }).click();
  const conversation = page.getByLabel("Conversation");
  const demoReply = "The shared sample profile suggests practicing Cloud Fundamentals next (42/100 current, 75/100 target). These are demo values, not results extracted from your resume.";
  await expect(conversation.getByText(demoReply, { exact: true })).toHaveCount(2);
  await expect(conversation.getByText(/parsed your resume|analyzed your resume contents/i)).toHaveCount(0);
  expect(serviceRequests).toEqual([]);
});

test("skill filters preserve the no-results empty state", async ({ page }) => {
  await gotoReady(page, "/skill-gap");
  await page.getByRole("button", { name: "Medium priority" }).click();
  await page.getByLabel("Filter by category").selectOption("Data & Cloud");
  await expect(page.getByText(/No skills match both filters/)).toBeVisible();
  await expect(page.getByText("0 skills", { exact: true })).toBeVisible();
});
