import { ReportPrintView } from "@/features/reports/components/report-print-view";

type ReportPrintPageProps = {
  searchParams?: Promise<{ report_id?: string | string[] }>;
};

const REPORT_ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;

export default async function ReportPrintPage({ searchParams }: ReportPrintPageProps) {
  const reportIdParam = (await Promise.resolve(searchParams))?.report_id;
  const reportId = typeof reportIdParam === "string" && REPORT_ID.test(reportIdParam) ? reportIdParam : undefined;

  return <ReportPrintView reportId={reportId} />;
}
