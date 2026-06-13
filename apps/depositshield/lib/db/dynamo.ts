/**
 * DynamoDB single-table store for DepositShield, used as an audit / event log.
 *
 * Item layout (see infra/dynamodb-table.yaml):
 *   Session meta:  PK=SESSION#<id>  SK=META          GSI1PK=USER#<userId> GSI1SK=<createdAt>
 *   Photo event:   PK=SESSION#<id>  SK=PHOTO#<seq>   (one per uploaded photo)
 *   Report:        PK=SESSION#<id>  SK=REPORT
 *
 * Querying PK=SESSION#<id> returns the full audit trail for a session.
 */
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import {
  DynamoDBDocumentClient,
  GetCommand,
  PutCommand,
  QueryCommand,
} from "@aws-sdk/lib-dynamodb";

import type { InspectionMeta } from "../inspection/client";
import type { InspectionReport } from "../inspection/schema";

export type Phase = "move_in" | "move_out";

export interface SessionMeta {
  id: string;
  userId: string;
  propertyLabel: string;
  phase: Phase;
  status: "created" | "reported";
  createdAt: string;
}

export interface PhotoEvent {
  key: string;
  seq: number;
  uploadedAt: string;
}

export interface StoredReport {
  report: InspectionReport;
  meta: InspectionMeta;
  generatedAt: string;
}

export interface SessionBundle {
  session: SessionMeta;
  photos: PhotoEvent[];
  report: StoredReport | null;
}

const TABLE = process.env.DEPOSITSHIELD_TABLE ?? "depositshield";

let cachedDoc: DynamoDBDocumentClient | null = null;
function doc(): DynamoDBDocumentClient {
  if (!cachedDoc) {
    cachedDoc = DynamoDBDocumentClient.from(new DynamoDBClient({ region: process.env.AWS_REGION }), {
      marshallOptions: { removeUndefinedValues: true },
    });
  }
  return cachedDoc;
}

export async function createSession(s: SessionMeta): Promise<void> {
  await doc().send(
    new PutCommand({
      TableName: TABLE,
      Item: {
        PK: `SESSION#${s.id}`,
        SK: "META",
        GSI1PK: `USER#${s.userId}`,
        GSI1SK: s.createdAt,
        type: "session",
        ...s,
      },
    }),
  );
}

export async function addPhotoEvents(sessionId: string, keys: string[]): Promise<PhotoEvent[]> {
  const now = new Date().toISOString();
  const events: PhotoEvent[] = keys.map((key, i) => ({ key, seq: i, uploadedAt: now }));
  await Promise.all(
    events.map((e) =>
      doc().send(
        new PutCommand({
          TableName: TABLE,
          Item: {
            PK: `SESSION#${sessionId}`,
            SK: `PHOTO#${String(e.seq).padStart(4, "0")}`,
            type: "photo",
            ...e,
          },
        }),
      ),
    ),
  );
  return events;
}

export async function putReport(
  sessionId: string,
  report: InspectionReport,
  meta: InspectionMeta,
): Promise<StoredReport> {
  const stored: StoredReport = { report, meta, generatedAt: new Date().toISOString() };
  await doc().send(
    new PutCommand({
      TableName: TABLE,
      Item: { PK: `SESSION#${sessionId}`, SK: "REPORT", type: "report", ...stored },
    }),
  );
  // Flip session status to reported.
  const meta0 = await getSessionMeta(sessionId);
  if (meta0) await createSession({ ...meta0, status: "reported" });
  return stored;
}

export async function getSessionMeta(sessionId: string): Promise<SessionMeta | null> {
  const res = await doc().send(
    new GetCommand({ TableName: TABLE, Key: { PK: `SESSION#${sessionId}`, SK: "META" } }),
  );
  return (res.Item as SessionMeta | undefined) ?? null;
}

export async function getSessionBundle(sessionId: string): Promise<SessionBundle | null> {
  const res = await doc().send(
    new QueryCommand({
      TableName: TABLE,
      KeyConditionExpression: "PK = :pk",
      ExpressionAttributeValues: { ":pk": `SESSION#${sessionId}` },
    }),
  );
  const items = res.Items ?? [];
  const session = items.find((i) => i.SK === "META") as SessionMeta | undefined;
  if (!session) return null;
  const photos = items
    .filter((i) => typeof i.SK === "string" && i.SK.startsWith("PHOTO#"))
    .map((i) => i as unknown as PhotoEvent)
    .sort((a, b) => a.seq - b.seq);
  const report = (items.find((i) => i.SK === "REPORT") as StoredReport | undefined) ?? null;
  return { session, photos, report };
}

export async function listSessionsByUser(userId: string, limit = 25): Promise<SessionMeta[]> {
  const res = await doc().send(
    new QueryCommand({
      TableName: TABLE,
      IndexName: "GSI1",
      KeyConditionExpression: "GSI1PK = :u",
      ExpressionAttributeValues: { ":u": `USER#${userId}` },
      ScanIndexForward: false,
      Limit: limit,
    }),
  );
  return (res.Items as SessionMeta[] | undefined) ?? [];
}
