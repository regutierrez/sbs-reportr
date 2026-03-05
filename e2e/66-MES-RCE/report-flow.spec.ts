import { test } from "@playwright/test";
import { runReportFlowTest } from "../report-flow-helpers";

test("completes intake and downloads generated report", async ({ page, baseURL }) => {
  test.slow();

  if (typeof baseURL !== "string") {
    throw new Error("Expected a baseURL for API rewrite handling");
  }

  await runReportFlowTest(page, baseURL, 17, "manggahan-elementary", __dirname);
});
//
