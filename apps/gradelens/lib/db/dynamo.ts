/**
 * DynamoDB single-table access for GradeLens.
 *
 * Table layout (see infra/gradelens/dynamodb-table.yaml):
 *   Grading record: PK=`GRADING#<id>`, SK=`META`
 *                   GSI1PK=`USER#<userId>`, GSI1SK=`<createdAt ISO>`
 *
 * On-demand billing; one item per grading session.
 */
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import {
  DynamoDBDocumentClient,
  GetCommand,
  PutCommand,
  QueryCommand,
} from "@aws-sdk/lib-dynamodb";

import type { GradeCallMeta } from "../grading/client";
import type { GradingResult } from "../grading/schema";

export interface GradingRecord {
  id: string;
  userId: string;
  createdAt: string;
  deviceHint: string | null;
  photoKeys: string[];
  result: GradingResult;
  meta: GradeCallMeta;
}

const TABLE = process.env.GRADELENS_TABLE ?? "gradelens";

let cachedDoc: DynamoDBDocumentClient | null = null;
function doc(): DynamoDBDocumentClient {
  if (!cachedDoc) {
    const base = new DynamoDBClient({ region: process.env.AWS_REGION });
    cachedDoc = DynamoDBDocumentClient.from(base, {
      marshallOptions: { removeUndefinedValues: true },
    });
  }
  return cachedDoc;
}

export async function putGrading(record: GradingRecord): Promise<void> {
  await doc().send(
    new PutCommand({
      TableName: TABLE,
      Item: {
        PK: `GRADING#${record.id}`,
        SK: "META",
        GSI1PK: `USER#${record.userId}`,
        GSI1SK: record.createdAt,
        ...record,
      },
    }),
  );
}

export async function getGrading(id: string): Promise<GradingRecord | null> {
  const res = await doc().send(
    new GetCommand({ TableName: TABLE, Key: { PK: `GRADING#${id}`, SK: "META" } }),
  );
  return (res.Item as GradingRecord | undefined) ?? null;
}

export async function listGradingsByUser(
  userId: string,
  limit = 25,
): Promise<GradingRecord[]> {
  const res = await doc().send(
    new QueryCommand({
      TableName: TABLE,
      IndexName: "GSI1",
      KeyConditionExpression: "GSI1PK = :u",
      ExpressionAttributeValues: { ":u": `USER#${userId}` },
      ScanIndexForward: false, // newest first
      Limit: limit,
    }),
  );
  return (res.Items as GradingRecord[] | undefined) ?? [];
}
