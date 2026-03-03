import { expect, test } from "@playwright/test";

type CharacterPayload = {
  id?: string | null;
  name: string;
  race: string;
  alignment?: string | null;
  ability_scores: Record<string, number>;
  class_levels: Array<{ class_name: string; level: number }>;
  feats: Array<{ name: string; level_gained: number; method: string }>;
  skills: Record<string, number>;
  equipment: Array<{ name: string; kind: string; quantity: number }>;
  traits: unknown[];
  conditions: string[];
  overrides: unknown[];
};

const CORS_HEADERS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET,POST,PUT,OPTIONS",
  "access-control-allow-headers": "Content-Type",
};

function respondJson(body: unknown) {
  return {
    status: 200,
    headers: {
      "content-type": "application/json",
      ...CORS_HEADERS,
    },
    body: JSON.stringify(body),
  };
}

test.use({ viewport: { width: 1024, height: 1366 } });

test("create -> save -> open sheet with condition/resource persistence", async ({ page }) => {
  const store = new Map<string, CharacterPayload>();

  await page.route("**/health", async (route) => {
    await route.fulfill(
      respondJson({ ok: true, env: "test", version: "v2-smoke" })
    );
  });

  await page.route("**/api/v2/content/feats**", async (route) => {
    await route.fulfill(
      respondJson([
        {
          id: 1,
          name: "Weapon Finesse",
          feat_type: "Combat",
          prerequisites: "Dex 13",
          benefit: "Use Dex for attack rolls.",
          source_book: "CRB",
          ui_enabled: 1,
          ui_tier: "active",
          policy_reason: "allowlisted",
        },
        {
          id: 2,
          name: "Rapid Shot",
          feat_type: "Combat",
          prerequisites: "Dex 13",
          benefit: "Extra ranged attack.",
          source_book: "CRB",
          ui_enabled: 1,
          ui_tier: "active",
          policy_reason: "allowlisted",
        },
      ])
    );
  });

  await page.route("**/api/v2/content/races**", async (route) => {
    await route.fulfill(
      respondJson([
        {
          id: 11,
          name: "Tiefling",
          race_type: "Humanoid",
          size: "Medium",
          base_speed: 30,
          source_book: "Bestiary",
          ui_enabled: 1,
          ui_tier: "active",
          policy_reason: "allowlisted",
        },
      ])
    );
  });

  await page.route("**/api/v2/content/policy-summary", async (route) => {
    await route.fulfill(
      respondJson({
        accepted_total: 120,
        active_total: 118,
        deferred_total: 2,
        reason_counts: {
          allowlisted: 118,
          class_not_in_allowlist: 2,
        },
        tier_counts: {
          active: 118,
          deferred: 2,
        },
      })
    );
  });

  await page.route("**/api/v2/characters/validate", async (route) => {
    const payload = JSON.parse(route.request().postData() ?? "{}") as CharacterPayload;
    await route.fulfill(
      respondJson({
        ok: true,
        name: payload.name,
        total_levels: payload.class_levels.reduce((sum, entry) => sum + entry.level, 0),
        feat_prereq_results: payload.feats.map((feat) => ({
          feat_name: feat.name,
          level_gained: feat.level_gained,
          valid: true,
          missing: [],
        })),
        invalid_feats: [],
      })
    );
  });

  await page.route("**/api/v2/rules/derive", async (route) => {
    const payload = JSON.parse(route.request().postData() ?? "{}") as CharacterPayload;
    await route.fulfill(
      respondJson({
        character: payload,
        derived: {
          total_level: payload.class_levels.reduce((sum, entry) => sum + entry.level, 0),
          bab: 6,
          fort: 4,
          ref: 10,
          will: 8,
          hp_max: 57,
          ac_total: 19,
          ac_touch: 14,
          ac_flat_footed: 15,
          cmb: 7,
          cmd: 21,
          initiative: 6,
          spell_slots: {
            "1": 4,
            "2": 3,
          },
          skill_totals: {
            Perception: 16,
            Stealth: 14,
          },
          attack_lines: [
            {
              name: "Rapier",
              attack_bonus: 11,
              damage: "1d6+1",
              notes: "18-20/x2",
            },
          ],
          feat_prereq_results: payload.feats.map((feat) => ({
            feat_name: feat.name,
            level_gained: feat.level_gained,
            valid: true,
            missing: [],
          })),
          breakdown: [
            { key: "BAB", value: 6, source: "Investigator levels" },
            { key: "AC(total)", value: 19, source: "10 + dex + armor" },
          ],
        },
      })
    );
  });

  await page.route("**/api/v2/characters", async (route) => {
    const method = route.request().method();

    if (method === "GET") {
      const summaries = Array.from(store.entries()).map(([id, payload]) => ({
        id,
        name: payload.name,
        race: payload.race,
        class_str: payload.class_levels.map((entry) => `${entry.class_name} ${entry.level}`).join(", "),
        total_level: payload.class_levels.reduce((sum, entry) => sum + entry.level, 0),
        modified_at: "2026-03-02T12:00:00Z",
      }));
      await route.fulfill(respondJson(summaries));
      return;
    }

    if (method === "POST") {
      const payload = JSON.parse(route.request().postData() ?? "{}") as CharacterPayload;
      const id = payload.id ?? "char-smoke-1";
      store.set(id, { ...payload, id });
      await route.fulfill(respondJson({ id, name: payload.name }));
      return;
    }

    await route.fulfill({ status: 405, headers: CORS_HEADERS, body: "" });
  });

  await page.route("**/api/v2/characters/*", async (route) => {
    const method = route.request().method();
    const id = route.request().url().split("/").pop() ?? "";
    if (id === "validate") {
      await route.fallback();
      return;
    }

    if (method === "GET") {
      const payload = store.get(id);
      if (!payload) {
        await route.fulfill({ status: 404, headers: CORS_HEADERS, body: "" });
        return;
      }
      await route.fulfill(respondJson(payload));
      return;
    }

    if (method === "PUT") {
      const payload = JSON.parse(route.request().postData() ?? "{}") as CharacterPayload;
      store.set(id, { ...payload, id });
      await route.fulfill(respondJson({ id, name: payload.name }));
      return;
    }

    await route.fulfill({ status: 405, headers: CORS_HEADERS, body: "" });
  });

  await page.goto("/");

  await expect(page.getByTestId("creator-view")).toBeVisible();
  await page.getByTestId("input-name").fill("Smoke Hero");
  await page.getByTestId("input-class").fill("Investigator");
  await page.getByTestId("input-level").fill("9");

  await page.getByTestId("derive-button").click();
  await expect(page.getByText("Derived preview refreshed from API V2.")).toBeVisible();

  await page.getByTestId("save-button").click();
  await expect(page.getByText("Character saved to API V2.")).toBeVisible();

  await page.getByTestId("tab-library").click();
  await expect(page.getByTestId("library-view")).toBeVisible();
  await expect(page.getByTestId("library-card")).toHaveCount(1);
  await expect(page.getByTestId("library-view").getByText("Smoke Hero").first()).toBeVisible();

  await page.getByRole("button", { name: "Open Sheet" }).first().click();
  await expect(page.getByTestId("sheet-view")).toBeVisible();
  await expect(page.getByTestId("sheet-name")).toContainText("Smoke Hero");
  await expect(page.getByTestId("quick-combat-panel")).toBeVisible();
  await expect(page.getByTestId("combat-selected-attack")).toContainText("Rapier");

  await expect(page.getByTestId("stat-ref")).toContainText("Ref +10");
  await page.getByTestId("condition-toggle-heroism").check();
  await expect(page.getByTestId("stat-ref")).toContainText("Ref +12");

  await expect(page.getByTestId("resource-inspiration-current")).toHaveValue("7");
  await page.getByTestId("resource-inspiration-dec").click();
  await expect(page.getByTestId("resource-inspiration-current")).toHaveValue("6");

  await expect(page.getByTestId("resource-consumable-healing_potion")).toContainText("3");
  await page.getByTestId("resource-consumable-dec-healing_potion").click();
  await expect(page.getByTestId("resource-consumable-healing_potion")).toContainText("2");

  await expect(page.getByTestId("spell-used-1")).toContainText("0");
  await page.getByTestId("spell-used-inc-1").click();
  await expect(page.getByTestId("spell-used-1")).toContainText("1");

  await page.reload();
  await page.getByTestId("tab-library").click();
  await expect(page.getByTestId("library-view")).toBeVisible();
  await page.getByRole("button", { name: "Open Sheet" }).first().click();

  await expect(page.getByTestId("sheet-view")).toBeVisible();
  await expect(page.getByTestId("condition-toggle-heroism")).toBeChecked();
  await expect(page.getByTestId("stat-ref")).toContainText("Ref +12");
  await expect(page.getByTestId("resource-inspiration-current")).toHaveValue("6");
  await expect(page.getByTestId("resource-consumable-healing_potion")).toContainText("2");
  await expect(page.getByTestId("spell-used-1")).toContainText("1");
});
