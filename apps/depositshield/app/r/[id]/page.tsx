import { Report } from "@/components/Report";
import { getSessionBundle } from "@/lib/db/dynamo";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export default async function SharedReport({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const bundle = await getSessionBundle(id).catch(() => null);

  return (
    <main>
      <div className="brand">
        <h1>
          Deposit<span className="mark">Shield</span>
        </h1>
      </div>

      {!bundle ? (
        <p className="muted" style={{ marginTop: 24 }}>
          Report not found.
        </p>
      ) : !bundle.report ? (
        <p className="muted" style={{ marginTop: 24 }}>
          This inspection has no report yet.
        </p>
      ) : (
        <>
          <p className="tagline">Shared condition report</p>
          <Report
            report={bundle.report.report}
            meta={bundle.report.meta}
            propertyLabel={bundle.session.propertyLabel}
            phase={bundle.session.phase}
            generatedAt={bundle.report.generatedAt}
          />
        </>
      )}
    </main>
  );
}
