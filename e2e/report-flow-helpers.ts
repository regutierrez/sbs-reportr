import * as fs from "node:fs";
import * as path from "node:path";

import { expect, test, type Page } from "@playwright/test";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BuildingEntry {
  __EMPTY: number;
  "Building Name": string;
  "Testing Date": string;
  "Building Location": string;
  "Number of Storey": number;
  "Coring Locations": number;
  "Rebound Hammer Test Locations": number;
  "Rebar Scan Locations": number;
  "Number of rebar samples": number;
  "Chipping of Slab"?: number;
  "Foundation Locations"?: number;
  "Number of extracted cores"?: number;
  "Non-shrink Grout Product": string;
  "Epoxy A&B Product": string;
  "Prepared By"?: string;
  Role?: string;
  Inspector?: string;
  "Inspector Title"?: string;
}

interface FormField {
  label: string;
  value: string;
  exact?: boolean;
  useRole?: boolean;
  roleName?: string;
}

// ---------------------------------------------------------------------------
// JSON data loader
// ---------------------------------------------------------------------------

const JSON_FILE = path.join(
  __dirname,
  "PSRRRP Firm 3 - List of for reporting_v2.json",
);

function loadAllEntries(): BuildingEntry[] {
  return JSON.parse(fs.readFileSync(JSON_FILE, "utf-8"));
}

export function loadBuildingData(entryId: number): BuildingEntry {
  const entries = loadAllEntries();
  const entry = entries.find((e) => e.__EMPTY === entryId);
  if (!entry) {
    throw new Error(
      `No entry with __EMPTY=${entryId} found in ${JSON_FILE}`,
    );
  }
  return entry;
}

// ---------------------------------------------------------------------------
// Convert a JSON entry into the REQUIRED_FIELDS array
// ---------------------------------------------------------------------------

export function buildRequiredFields(data: BuildingEntry, options?: { skipSubstructure?: boolean }): FormField[] {
  const fields: FormField[] = [
    { label: "Testing Date", value: data["Testing Date"] },
    { label: "Building Name", value: data["Building Name"] },
    { label: "Building Location", value: data["Building Location"] },
    { label: "Number of Storey", value: String(data["Number of Storey"]) },
    { label: "Rebar Scan Locations", value: String(data["Rebar Scan Locations"]) },
    { label: "Rebound Hammer Test Locations", value: String(data["Rebound Hammer Test Locations"]) },
    { label: "Coring Locations", value: String(data["Coring Locations"]) },
    { label: "Number of rebar samples", value: String(data["Number of rebar samples"]) },
    { label: "Non-shrink Grout Product", value: data["Non-shrink Grout Product"] },
    { label: "Epoxy A&B Product", value: data["Epoxy A&B Product"] },
  ];

  if (!options?.skipSubstructure) {
    if (data["Foundation Locations"] != null) {
      fields.push({ label: "Foundation Locations", value: String(data["Foundation Locations"]) });
    }
    if (data["Number of extracted cores"] != null) {
      fields.push({ label: "Number of extracted cores", value: String(data["Number of extracted cores"]) });
    }
  }

  if (data["Prepared By"]) {
    fields.push({
      label: "Prepared By",
      value: data["Prepared By"],
      useRole: true,
      roleName: "Prepared by Prepared by is",
    });
  }
  if (data["Role"]) {
    fields.push({ label: "Role", value: data["Role"] });
  }

  return fields;
}

// ---------------------------------------------------------------------------
// Photo-upload constants
// ---------------------------------------------------------------------------

const SUBSTRUCTURE_PHOTO_LABELS: ReadonlyArray<string> = [
  "Foundation Coring Photos",
  "Foundation Rebar Scanning Photos",
  "Restoration, Backfilling, and Compaction Photos",
];

export const REQUIRED_PHOTO_LABELS: ReadonlyArray<string> = [
  "Building Photo",
  "Rebar Scanning Photos",
  "Rebound Hammer Test Photos",
  "Concrete Coring Photos",
  "Core Samples Family Photo",
  "Rebar Extraction Photos",
  "Rebar Samples Family Photo",
  "Chipping of Slab Photos",
  "Restoration Photos",
  ...SUBSTRUCTURE_PHOTO_LABELS,
];

export const LABEL_TO_FOLDER: Record<string, string> = {
  "Building Photo": "building-photo.jpeg",
  "Rebar Scanning Photos": "rebar-scanning-photos",
  "Rebound Hammer Test Photos": "rebound-hammer-photos",
  "Concrete Coring Photos": "concrete-coring-photos",
  "Core Samples Family Photo": "core-samples-family-photos",
  "Rebar Extraction Photos": "rebar-extraction-photos",
  "Rebar Samples Family Photo": "rebar-samples-family-photo",
  "Chipping of Slab Photos": "chipping-of-slab-photos",
  "Restoration Photos": "restoration-photos",
  "Foundation Coring Photos": "foundation-coring-photos",
  "Foundation Rebar Scanning Photos": "foundation-rebar-scanning-photos",
  "Restoration, Backfilling, and Compaction Photos":
    "restoration-backfilling-compaction-photos",
};

// ---------------------------------------------------------------------------
// Page helpers
// ---------------------------------------------------------------------------

const LOCAL_API_ORIGIN = "http://localhost:9999";

export async function rewriteLocalApiOrigin(
  page: Page,
  targetOrigin: string,
): Promise<void> {
  if (targetOrigin === LOCAL_API_ORIGIN) {
    return;
  }

  await page.addInitScript(
    ({ localApiOrigin, rewrittenOrigin }) => {
      const localReportsPrefix = `${localApiOrigin}/reports`;

      const rewriteUrl = (url: string) => {
        if (typeof url !== "string") {
          return url;
        }

        if (!url.startsWith(localReportsPrefix)) {
          return url;
        }

        return rewrittenOrigin + "/api" + url.slice(localApiOrigin.length);
      };

      const originalFetch = window.fetch.bind(window);

      window.fetch = ((input: any, init: any) => {
        if (typeof input === "string") {
          return originalFetch(rewriteUrl(input), init);
        }

        if (input instanceof URL) {
          return originalFetch(rewriteUrl(input.toString()), init);
        }

        if (input instanceof Request && input.url.startsWith(localApiOrigin)) {
          return originalFetch(new Request(rewriteUrl(input.url), input), init);
        }

        return originalFetch(input, init);
      }) as typeof window.fetch;

      const originalOpen = XMLHttpRequest.prototype.open;

      XMLHttpRequest.prototype.open = function (method: string, url: any, ...rest: any[]) {
        if (typeof url === "string") {
          return originalOpen.call(this, method, rewriteUrl(url), ...rest);
        }

        if (url instanceof URL) {
          return originalOpen.call(
            this,
            method,
            rewriteUrl(url.toString()),
            ...rest,
          );
        }

        return originalOpen.call(this, method, url, ...rest);
      };
    },
    {
      localApiOrigin: LOCAL_API_ORIGIN,
      rewrittenOrigin: targetOrigin,
    },
  );
}

export async function fillRequiredFormFields(
  page: Page,
  fields: FormField[],
): Promise<void> {
  for (const field of fields) {
    if (field.useRole && field.roleName) {
      await page.getByRole("textbox", { name: field.roleName }).fill(field.value);
    } else if (field.exact) {
      await page.getByLabel(field.label, { exact: true }).fill(field.value);
    } else {
      await page.getByLabel(field.label).fill(field.value);
    }
  }
}

export async function uploadRequiredPhotoGroups(
  page: Page,
  baseDir: string,
  options?: { skipSubstructure?: boolean },
): Promise<void> {
  const labelsToUpload = options?.skipSubstructure
    ? REQUIRED_PHOTO_LABELS.filter((label) => !SUBSTRUCTURE_PHOTO_LABELS.includes(label))
    : REQUIRED_PHOTO_LABELS;

  for (const label of labelsToUpload) {
    const itemPath = path.join(baseDir, LABEL_TO_FOLDER[label]);
    let filesToUpload: string[] = [];

    if (fs.existsSync(itemPath)) {
      if (fs.statSync(itemPath).isDirectory()) {
        filesToUpload = fs
          .readdirSync(itemPath)
          .filter(
            (f) =>
              f.endsWith(".jpeg") || f.endsWith(".jpg") || f.endsWith(".png"),
          )
          .map((f) => path.join(itemPath, f));
      } else {
        filesToUpload = [itemPath];
      }
    }

    if (filesToUpload.length > 0) {
      const fileInput = page
        .locator("article", {
          has: page.getByRole("heading", { name: label, exact: true }),
        })
        .locator('input[type="file"]')
        .first();

      if ((await fileInput.count()) === 0) {
        console.warn(`No upload field found for label: ${label}`);
        continue;
      }

      await fileInput.setInputFiles(filesToUpload);
    } else {
      console.warn(`No files found for label: ${label} at ${itemPath}`);
    }
  }
}

// ---------------------------------------------------------------------------
// Full test orchestrator
// ---------------------------------------------------------------------------

export async function runReportFlowTest(
  page: Page,
  baseURL: string,
  entryId: number,
  filenameSubstring: string,
  photoBaseDir: string,
  options?: { skipSubstructure?: boolean },
): Promise<void> {
  const data = loadBuildingData(entryId);
  const fields = buildRequiredFields(data, options);

  await rewriteLocalApiOrigin(page, new URL(baseURL).origin);
  await page.goto("/");
  await fillRequiredFormFields(page, fields);
  await uploadRequiredPhotoGroups(page, photoBaseDir, options);

  const continueToConfirmationButton = page.getByRole("button", {
    name: "Continue to Confirmation",
  });

  await expect(continueToConfirmationButton).toBeEnabled();

  if (process.env.PW_STOP_BEFORE_CONTINUE === "1") {
    await page.pause();
    return;
  }

  await continueToConfirmationButton.click();

  await expect(page).toHaveURL(/\/confirm$/);

  const continueToGenerateButton = page.getByRole("button", {
    name: "Continue and Generate PDF",
  });

  await expect(continueToGenerateButton).toBeEnabled();

  const downloadPromise = page.waitForEvent("download", {
    timeout: 60_000,
  });

  await continueToGenerateButton.click();

  const download = await downloadPromise;
  const suggestedFilename = download.suggestedFilename();

  await expect(
    page.getByText("Report generated. Download started."),
  ).toBeVisible({
    timeout: 60_000,
  });

  expect(suggestedFilename).toMatch(/-activity-report\.pdf$/i);
  expect(suggestedFilename).not.toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:\.pdf)?$/i,
  );
  expect(suggestedFilename.toLowerCase()).toContain(filenameSubstring);

  const downloadedFilePath = path.join(test.info().outputDir, suggestedFilename);
  await download.saveAs(downloadedFilePath);
  expect(fs.existsSync(downloadedFilePath)).toBe(true);
}
