import { notFound } from "next/navigation";

import { SampleReportPreview } from "@/features/reports/components/sample-report-preview";
import { isDemoEnabled } from "@/services/adapters/demo-mode";

// A layout sample with invented data. Outside demo mode it does not exist, so
// no real workflow can land on it; signed reports print from /reports/print.
export default function ReportPreviewPage() {
  if (!isDemoEnabled()) {
    notFound();
  }

  return <SampleReportPreview />;
}
