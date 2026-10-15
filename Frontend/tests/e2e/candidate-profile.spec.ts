import { expect, test, type Page } from "@playwright/test";

const routes = [
  ["/", "Good morning, Arjun!"],
  ["/resume", "Resume and candidate profile"],
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
  await page.getByRole("main").first().waitFor();
  await page.waitForLoadState("networkidle").catch(() => undefined);
}

test("all six routes render at desktop and mobile widths without horizontal overflow", async ({ page }) => {
  for (const [route, heading] of routes) {
    await page.setViewportSize({ width: 1440, height: 900 });
    await gotoReady(page, route);

    await expect(page.locator("main h1").last()).toHaveText(heading);

    expect(await page.evaluate(() => document.documentElement.scrollWidth))
      .toBeLessThanOrEqual(await page.evaluate(() => document.documentElement.clientWidth));

    await page.setViewportSize({ width: 390, height: 844 });

    expect(await page.evaluate(() => document.documentElement.scrollWidth))
      .toBeLessThanOrEqual(await page.evaluate(() => document.documentElement.clientWidth));
  }
});

test("resume file selection, validation, navigation, and reset behave correctly", async ({ page }) => {
  await gotoReady(page, "/resume");
  await expect(page.getByText("Drop your resume here", { exact: true })).toBeVisible();

  const fileInput = page.locator('input[type="file"]');

  // Select a valid resume and verify its metadata and local preview.
  await fileInput.setInputFiles(validResume);

  await expect(page.getByText(validResume.name, { exact: true })).toBeVisible();
  await expect(page.getByText(/1 KB/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Open PDF preview" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Upload and analyze" })).toBeEnabled();
  await expect(
    page.getByText(/No file leaves this browser until the backend upload contract is implemented/)
  ).toBeVisible();

  // Confirm navigation to the Skill Gap page still works.
  await page.getByRole("link", { name: "Skill Gap", exact: true }).click();
  await expect(page.getByText("9 skills", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Cloud Fundamentals" }).first()
  ).toBeVisible();

  // Resume metadata is shared across client-side navigation; browser File data must be reselected.
  await page.getByRole("link", { name: "Resume", exact: true }).click();
  await expect(page.getByText(validResume.name, { exact: true })).toBeVisible();
  await expect(page.getByText(/File must be reselected after navigation/)).toBeVisible();

  // Select the resume again before testing replacement validation.
  await fileInput.setInputFiles(validResume);
  await expect(page.getByText(validResume.name, { exact: true })).toBeVisible();
  await expect(page.getByText(/1 KB/)).toBeVisible();

  // An unsupported replacement must show an error and not be accepted.
  await fileInput.setInputFiles({
    name: "unsupported.png",
    mimeType: "image/png",
    buffer: Buffer.from("not a resume"),
  });

  await expect(
    page.locator('[role="alert"]').filter({
      hasText: "This file type is not supported",
    })
  ).toBeVisible();
  await expect(page.getByText(validResume.name, { exact: true })).toHaveCount(0);

  // A valid file can be selected again after the validation error.
  await fileInput.setInputFiles({
    ...validResume,
    name: "candidate-reselected.pdf",
  });

  await expect(
    page.getByText("candidate-reselected.pdf", { exact: true })
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Open PDF preview" })).toBeVisible();

  // Removing the selected file resets the interface.
  await page.getByRole("button", { name: "Remove" }).click();

  await expect(page.getByText("Drop your resume here", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Upload and analyze" })).toBeDisabled();
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
  await expect(
    page.getByRole("progressbar", { name: "Sample learning roadmap progress" })
  ).toHaveAttribute("aria-valuenow", "38");

  await page.getByRole("link", { name: "Learning Roadmap", exact: true }).click();
  await expect(roadmapProgress).toHaveAttribute("aria-valuenow", "38");

  await page.reload();
  await expect(
    page.getByRole("progressbar", { name: "Overall roadmap progress" })
  ).toHaveAttribute("aria-valuenow", "23");
});

test("sample insights remain consistent and assistant replies without a service", async ({ page }) => {
  const serviceRequests: string[] = [];

  page.on("request", (request) => {
    if (/\/api\/|openai|azure|anthropic/i.test(request.url())) {
      serviceRequests.push(request.url());
    }
  });

  await gotoReady(page, "/");
  await expect(page.getByText("72", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Career Readiness", exact: true }).click();
  await expect(page.locator("#overall-score-heading")).toContainText("72");
  await expect(
    page.getByRole("progressbar", { name: "Interview preparation readiness" })
  ).toHaveAttribute("aria-valuenow", "61");

  await page.getByRole("link", { name: "AI Career Assistant New" }).click();
  await page.getByRole("button", { name: "Which skill gap should I focus on first?" }).click();
  await page.getByRole("button", { name: "Which skill gap should I focus on first?" }).click();

  const conversation = page.getByLabel("Conversation");
  const demoReply =
    "The shared sample profile suggests practicing Cloud Fundamentals next (42/100 current, 75/100 target). These are demo values, not results extracted from your resume.";

  await expect(conversation.getByText(demoReply, { exact: true })).toHaveCount(2);
  await expect(
    conversation.getByText(/parsed your resume|analyzed your resume contents/i)
  ).toHaveCount(0);
  expect(serviceRequests).toEqual([]);
});

test("skill filters preserve the no-results empty state", async ({ page }) => {
  await gotoReady(page, "/skill-gap");

  await page.getByRole("button", { name: "Medium priority" }).click();
  await page.getByLabel("Filter by category").selectOption("Data & Cloud");

  await expect(page.getByText(/No skills match both filters/)).toBeVisible();
  await expect(page.getByText("0 skills", { exact: true })).toBeVisible();
});
